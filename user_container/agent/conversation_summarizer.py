"""
Conversation Summarizer - generates and manages conversation summaries for hierarchical memory.

This module handles:
1. Deciding when a summary needs to be generated/updated
2. Generating semantic summaries of conversation history
3. Caching summaries in the database
"""

import json
from typing import Optional, Dict, Any, List

from user_container.config import settings
from user_container.db.db import DB
from user_container.agent.llm_client import LLMClient
from user_container.agent.context import get_job_id, get_conversation_id
from user_container.logger import log as _log


SUMMARY_PROMPT = """Summarize this conversation focusing on what the USER wanted and what was DONE.

CRITICAL - You MUST include:
- ALL specific values mentioned (prices, numbers, dates, sizes)
- ALL names (people, projects, companies, files, folders)
- ALL decisions made and why
- ALL files created/modified (full paths)
- ALL errors encountered and their status (resolved/pending)
- Current task state (what's done, what's next)

Format as concise bullet points. Be specific - include actual values, not "some price" but "$149".

Conversation:
{conversation}

Summary (max 500 words, bullet points):"""


class ConversationSummarizer:
    """
    Manages conversation summaries for hierarchical memory system.

    Summaries are generated when:
    - Conversation exceeds summary_threshold messages
    - summary_update_interval new messages since last summary
    """

    def __init__(self, db: DB = None):
        """Initialize summarizer.

        Args:
            db: Database instance (optional, will be set later if not provided)
        """
        self.db = db
        self.threshold = settings.summary_threshold
        self.update_interval = settings.summary_update_interval

        # Use cheap LLM for summarization
        try:
            self.llm = LLMClient.cheap()
        except ValueError:
            self.llm = None
            _log("[ConversationSummarizer] No LLM available for summarization")

    def set_db(self, db: DB) -> None:
        """Set database instance (for late binding)."""
        self.db = db

    def should_update_summary(self, conversation_id: str) -> bool:
        """Check if summary needs to be generated or updated.

        Returns True if:
        - Conversation has >= threshold messages AND no summary exists
        - OR >= update_interval new messages since last summary
        """
        if not self.db:
            return False

        total_messages = self.db.count_messages(conversation_id)

        # Not enough messages yet
        if total_messages < self.threshold:
            return False

        # Check existing summary
        summary_data = self.db.get_conversation_summary(conversation_id)

        if not summary_data:
            # No summary exists, need to create one
            return True

        # Check if enough new messages since last summary
        last_summarized_id = summary_data.get("summary_up_to_message_id", 0)
        last_message_id = self.db.get_last_message_id(conversation_id)

        if last_message_id and last_summarized_id:
            new_messages = last_message_id - last_summarized_id
            return new_messages >= self.update_interval

        return False

    async def get_or_update_summary(self, conversation_id: str) -> Optional[str]:
        """Get existing summary or generate new one if needed.

        This is the main entry point for getting a summary.

        Args:
            conversation_id: The conversation ID

        Returns:
            Summary text or None if not available/needed
        """
        if not self.db:
            return None

        # Check if we need to update
        if self.should_update_summary(conversation_id):
            return await self.generate_summary(conversation_id)

        # Return existing summary
        summary_data = self.db.get_conversation_summary(conversation_id)
        return summary_data.get("summary") if summary_data else None

    def get_or_update_summary_sync(self, conversation_id: str) -> Optional[str]:
        """Synchronous version of get_or_update_summary."""
        if not self.db:
            return None

        # Check if we need to update
        if self.should_update_summary(conversation_id):
            return self.generate_summary_sync(conversation_id)

        # Return existing summary
        summary_data = self.db.get_conversation_summary(conversation_id)
        return summary_data.get("summary") if summary_data else None

    async def generate_summary(self, conversation_id: str) -> Optional[str]:
        """Generate summary asynchronously."""
        return self.generate_summary_sync(conversation_id)

    def generate_summary_sync(self, conversation_id: str) -> Optional[str]:
        """Generate or update summary for a conversation.

        Strategy:
        1. If no existing summary: summarize all messages up to now
        2. If existing summary: merge old summary with new messages

        Returns:
            Generated summary text or None on failure
        """
        if not self.db or not self.llm:
            return None

        _log(f"[ConversationSummarizer] Generating summary for {conversation_id[:8]}...")

        # Get existing summary info
        existing = self.db.get_conversation_summary(conversation_id)
        last_summarized_id = existing.get("summary_up_to_message_id", 0) if existing else 0
        old_summary = existing.get("summary", "") if existing else ""

        # Get messages to summarize
        if last_summarized_id > 0:
            # Incremental update: only new messages
            messages = self.db.get_messages_for_summary(
                conversation_id,
                after_message_id=last_summarized_id
            )
        else:
            # Full summary: all messages
            messages = self.db.get_messages_for_summary(conversation_id)

        if not messages:
            return old_summary if old_summary else None

        # Format messages for summarization
        conversation_text = self._format_messages(messages)

        # If we have old summary, include it for context
        if old_summary:
            conversation_text = f"[Previous summary]\n{old_summary}\n\n[New messages]\n{conversation_text}"

        # Generate summary
        try:
            response = self.llm.chat(
                messages=[{
                    "role": "user",
                    "content": SUMMARY_PROMPT.format(conversation=conversation_text)
                }],
                component="conversation_summarizer",
                job_id=get_job_id(),
                conversation_id=get_conversation_id()
            )

            summary = response.content
            if not summary:
                _log("[ConversationSummarizer] Empty response from LLM")
                return old_summary if old_summary else None

            # Get last message ID for tracking
            last_message_id = self.db.get_last_message_id(conversation_id)

            # Save summary
            self.db.save_conversation_summary(
                conversation_id,
                summary,
                last_message_id or 0
            )

            _log(f"[ConversationSummarizer] Summary saved (up to msg {last_message_id})")
            return summary

        except Exception as e:
            _log(f"[ConversationSummarizer] Error generating summary: {e}")
            return old_summary if old_summary else None

    def _format_messages(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages for summarization prompt.

        Focuses on user intents and assistant actions, truncates tool outputs.
        """
        lines = []

        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            # Skip empty messages
            if not content and role != "assistant":
                continue

            # Handle different roles
            if role == "user":
                # User messages are important - include fully (but truncate if huge)
                if len(content) > 2000:
                    content = content[:2000] + "...[truncated]"
                lines.append(f"User: {content}")

            elif role == "assistant":
                # Include tool calls info
                tool_calls = msg.get("tool_calls")
                if tool_calls:
                    if isinstance(tool_calls, str):
                        try:
                            tool_calls = json.loads(tool_calls)
                        except:
                            tool_calls = []

                    tool_names = []
                    for tc in tool_calls:
                        if isinstance(tc, dict):
                            name = tc.get("function", {}).get("name", "?")
                            tool_names.append(name)
                    if tool_names:
                        lines.append(f"Assistant: [Used tools: {', '.join(tool_names)}]")

                if content:
                    # Truncate long assistant content
                    if len(content) > 1000:
                        content = content[:1000] + "...[truncated]"
                    lines.append(f"Assistant: {content}")

            elif role == "tool":
                # Tool outputs - very brief summary
                if content:
                    preview = content[:200] if len(content) > 200 else content
                    # Clean up for readability
                    preview = preview.replace("\n", " ")[:150]
                    lines.append(f"[Tool result]: {preview}...")

        return "\n".join(lines)

    def get_summary(self, conversation_id: str) -> Optional[str]:
        """Get current summary without updating.

        Use this when you just need to read the existing summary.
        """
        if not self.db:
            return None

        summary_data = self.db.get_conversation_summary(conversation_id)
        return summary_data.get("summary") if summary_data else None


def build_context_header(
    total_messages: int,
    visible_messages: int,
    summary: Optional[str]
) -> str:
    """Build the context header message to inject before conversation history.

    This header tells the agent:
    - How many messages exist vs how many are visible
    - Summary of earlier discussion (if available)
    - How to get more details if needed

    Args:
        total_messages: Total messages in conversation
        visible_messages: Number of recent messages visible to agent
        summary: Summary of earlier messages (if any)

    Returns:
        Formatted context header string
    """
    lines = ["## Conversation Context"]

    # Message counts
    if total_messages > visible_messages:
        lines.append(f"\n**This conversation:** {total_messages} messages total, you see the last {visible_messages}.")
    else:
        lines.append(f"\n**This conversation:** {total_messages} messages (full history visible).")

    # Summary
    if summary:
        lines.append(f"\n**Summary of earlier discussion:**\n{summary}")

    # Guidance
    if total_messages > visible_messages:
        lines.append('\n**If you need exact details from earlier:** Use `recall_from_chat("keyword")` to search.')

    return "\n".join(lines)


def get_recent_exchanges_count() -> int:
    """Get number of recent exchanges to keep full (uncompressed).

    Returns:
        Number of user-assistant exchanges to keep full
    """
    return settings.recent_exchanges_full
