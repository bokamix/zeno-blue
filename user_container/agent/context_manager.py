"""
Context Manager - handles context window compression for long-running tasks.

When conversation history approaches the model's context limit, this module
compresses the middle portion while preserving:
- System prompt (first message)
- Recent messages (last N)
- Current plan (if present)
"""

import json
from typing import List, Dict, Any, Optional, Tuple

from user_container.config import settings
from user_container.agent.llm_client import LLMClient
from user_container.agent.context import get_job_id, get_conversation_id
from user_container.logger import log as _log


COMPRESSION_PROMPT = """Summarize this conversation history into a concise context summary.

Focus on:
- Key decisions made
- Important information discovered
- Current state of the task
- Any blockers or issues encountered

Keep it brief but preserve critical context needed for the task to continue.

Conversation to summarize:
{conversation}

Return a concise summary (max 500 words):"""


class ContextManager:
    """
    Manages context window for long-running agent tasks.

    Monitors token usage and compresses conversation history when needed
    to prevent context overflow during complex, multi-step tasks.
    """

    def __init__(
        self,
        max_tokens: int = None,
        compression_threshold: float = None,
        keep_recent: int = None
    ):
        """
        Initialize ContextManager.

        Args:
            max_tokens: Maximum context window size (default from settings)
            compression_threshold: Compress when usage exceeds this (0.0-1.0)
            keep_recent: Number of recent messages to preserve
        """
        self.max_tokens = max_tokens or settings.context_max_tokens
        self.compression_threshold = compression_threshold or settings.context_compression_threshold
        self.keep_recent = keep_recent or settings.context_keep_recent

        # Get cheap LLM for summarization
        try:
            self.llm = LLMClient.cheap()
        except ValueError:
            self.llm = None

    def estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """
        Estimate token count for messages.

        Uses ~4 chars per token as rough approximation.
        For more accuracy, could use tiktoken but this is fast enough.
        """
        total_chars = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total_chars += len(content)
            # Handle tool calls
            tool_calls = msg.get("tool_calls", [])
            for tc in tool_calls:
                if isinstance(tc, dict):
                    total_chars += len(json.dumps(tc))
                else:
                    total_chars += len(str(tc))

        return total_chars // 4

    def usage_percent(self, messages: List[Dict[str, Any]]) -> float:
        """Get context usage as percentage (0.0-1.0)."""
        tokens = self.estimate_tokens(messages)
        return tokens / self.max_tokens

    def should_compress(self, messages: List[Dict[str, Any]]) -> bool:
        """Check if context should be compressed."""
        return self.usage_percent(messages) > self.compression_threshold

    def compress(
        self,
        messages: List[Dict[str, Any]],
        preserve_plan: bool = True
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Compress messages if needed.

        Strategy:
        1. Keep: system prompt (first message)
        2. Keep: last N messages (recent context)
        3. Keep: current plan if present (optional)
        4. Compress: everything else into summary

        Args:
            messages: Full message history
            preserve_plan: Whether to keep plan messages intact

        Returns:
            Tuple of (compressed messages, was_compressed)
        """
        if not self.should_compress(messages):
            return messages, False

        if not self.llm:
            _log("[ContextManager] No LLM for compression, skipping")
            return messages, False

        if len(messages) <= self.keep_recent + 1:
            # Not enough messages to compress
            return messages, False

        _log(f"[ContextManager] Compressing context (usage: {self.usage_percent(messages):.1%})")

        # Split messages
        system_msg = messages[0] if messages and messages[0].get("role") == "system" else None

        # Find safe split point - don't break tool_use/tool_result pairs
        # Start from keep_recent and expand backwards if needed
        split_idx = len(messages) - self.keep_recent
        split_idx = self._find_safe_split_point(messages, split_idx)

        recent_msgs = messages[split_idx:]
        start_idx = 1 if system_msg else 0
        middle_msgs = messages[start_idx:split_idx]

        # Find and preserve plan if present
        plan_msg = None
        if preserve_plan:
            plan_msg = self._find_plan_message(middle_msgs)
            if plan_msg:
                middle_msgs = [m for m in middle_msgs if m != plan_msg]
                # Strip tool_calls from plan_msg - their results are being summarized
                # Keeping tool_calls without their tool_results breaks Anthropic API
                # IMPORTANT: Preserve thinking fields for extended thinking support!
                if plan_msg.get("tool_calls"):
                    new_plan_msg = {
                        "role": plan_msg.get("role"),
                        "content": plan_msg.get("content", "")
                    }
                    # Preserve thinking fields (required for Anthropic extended thinking)
                    if plan_msg.get("thinking"):
                        new_plan_msg["thinking"] = plan_msg["thinking"]
                    if plan_msg.get("thinking_signature"):
                        new_plan_msg["thinking_signature"] = plan_msg["thinking_signature"]
                    plan_msg = new_plan_msg

        if not middle_msgs:
            return messages, False

        # Summarize middle portion
        summary = self._summarize(middle_msgs)

        # Reconstruct compressed history
        compressed = []
        if system_msg:
            compressed.append(system_msg)
        if summary:
            compressed.append({
                "role": "user",
                "content": f"[Previous context summary]\n{summary}"
            })
        if plan_msg:
            compressed.append(plan_msg)
        compressed.extend(recent_msgs)

        # Validate tool pairs before returning - safety check
        if not self._validate_tool_pairs(compressed):
            _log("[ContextManager] WARNING: Tool pairs broken after compression, returning original")
            return messages, False

        new_usage = self.usage_percent(compressed)
        _log(f"[ContextManager] Compressed: {len(messages)} -> {len(compressed)} messages "
             f"(usage: {new_usage:.1%})")

        return compressed, True

    def _find_safe_split_point(self, messages: List[Dict[str, Any]], target_idx: int) -> int:
        """
        Find a safe index to split messages without breaking tool_use/tool_result pairs.

        Anthropic API requires:
        - Each tool_use must have tool_result immediately after
        - Each tool_result must have tool_use immediately before

        Strategy: Only split on 'user' messages - they are always safe boundaries.

        Args:
            messages: Full message list
            target_idx: Desired split index

        Returns:
            Safe split index (always a 'user' message or start of list)
        """
        if target_idx <= 0:
            return target_idx

        # Search backwards from target for a 'user' message
        idx = target_idx
        while idx > 0:
            msg = messages[idx]
            if msg.get("role") == "user":
                return idx
            idx -= 1

        # No user message found, return 0 (will skip compression)
        return 0

    def _find_plan_message(self, messages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find message containing <plan> block."""
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str) and "<plan>" in content:
                return msg
        return None

    def _validate_tool_pairs(self, messages: List[Dict[str, Any]]) -> bool:
        """
        Validate that all tool_use blocks have corresponding tool_result blocks.

        Anthropic API requires each tool_use to have a tool_result immediately after.
        This validation ensures compression didn't break any pairs.

        Returns:
            True if all pairs are valid, False if any are broken
        """
        i = 0
        while i < len(messages):
            msg = messages[i]

            # Check if this is an assistant message with tool_calls
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                tool_calls = msg.get("tool_calls", [])
                expected_ids = set()

                for tc in tool_calls:
                    if isinstance(tc, dict):
                        tool_id = tc.get("id")
                        if tool_id:
                            expected_ids.add(tool_id)

                if not expected_ids:
                    i += 1
                    continue

                # Check that following messages are tool results with matching IDs
                found_ids = set()
                j = i + 1
                while j < len(messages) and messages[j].get("role") == "tool":
                    tool_call_id = messages[j].get("tool_call_id")
                    if tool_call_id:
                        found_ids.add(tool_call_id)
                    j += 1

                # Verify all expected tool results were found
                missing = expected_ids - found_ids
                if missing:
                    _log(f"[ContextManager] Broken tool pairs: missing results for {missing}")
                    return False

                i = j
            else:
                i += 1

        return True

    def _summarize(self, messages: List[Dict[str, Any]]) -> str:
        """
        Summarize messages using cheap LLM.

        Args:
            messages: Messages to summarize

        Returns:
            Summary string
        """
        # Format conversation for summarization
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            # Skip empty messages
            if not content:
                continue

            # Truncate very long content
            if len(content) > 1000:
                content = content[:1000] + "...[truncated]"

            # Handle tool messages
            if role == "tool":
                lines.append(f"[Tool result]: {content[:200]}...")
            elif role == "assistant" and msg.get("tool_calls"):
                tool_names = []
                for tc in msg.get("tool_calls", []):
                    if isinstance(tc, dict):
                        tool_names.append(tc.get("function", {}).get("name", "?"))
                lines.append(f"Assistant: [Used tools: {', '.join(tool_names)}]")
                if content:
                    lines.append(f"Assistant: {content}")
            else:
                lines.append(f"{role.capitalize()}: {content}")

        conversation_text = "\n".join(lines)

        # If conversation is very short, no need to summarize
        if len(conversation_text) < 500:
            return conversation_text

        try:
            response = self.llm.chat(
                messages=[{
                    "role": "user",
                    "content": COMPRESSION_PROMPT.format(conversation=conversation_text)
                }],
                component="context_manager",
                job_id=get_job_id(),
                conversation_id=get_conversation_id()
            )
            return response.content or conversation_text
        except Exception as e:
            _log(f"[ContextManager] Summarization failed: {e}")
            # Fallback: just truncate
            return conversation_text[:2000] + "...[truncated]"


def get_context_stats(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get context usage statistics.

    Returns dict with:
    - tokens: estimated token count
    - usage_percent: usage as percentage
    - message_count: number of messages
    """
    manager = ContextManager()
    tokens = manager.estimate_tokens(messages)
    return {
        "tokens": tokens,
        "usage_percent": manager.usage_percent(messages),
        "message_count": len(messages),
        "max_tokens": manager.max_tokens
    }
