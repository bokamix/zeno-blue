"""
Skill Router - selects relevant skills based on conversation context.

Uses a fast/cheap LLM to analyze conversation history
and decide which skills should be loaded for the current turn.

Implements "skill decay" - skills stay active for N steps (TTL) and
are refreshed when the router confirms they're still needed.
"""

import json
from typing import List, Dict, Any, Optional, Tuple

from user_container.config import settings
from user_container.agent.llm_client import LLMClient
from user_container.agent.context import get_job_id, get_conversation_id
from user_container.logger import log as _log


ROUTER_SYSTEM_PROMPT = """You are a skill router. Your job is to analyze a conversation and decide which skills should be active for the AI assistant.

Available skills:
{skills_json}

Currently active skills (with remaining TTL):
{active_skills_info}

Your task:
1. Decide which skills from "Available skills" should be ADDED (newly needed)
2. Decide which "Currently active skills" should be KEPT (still needed) or DROPPED (no longer needed)

Rules:
- ADD a skill when the user's request clearly matches its "Use when..." description
- KEEP an active skill if the assistant is still working on a task that needs it
- DROP an active skill ONLY if the user has EXPLICITLY asked for something unrelated
- Usually 0-2 skills are sufficient

CRITICAL - When NOT to drop skills:
- If assistant is exploring/reading files → KEEP skills (exploration is part of the task)
- If assistant hasn't completed the user's request yet → KEEP skills
- If assistant is using tools like shell/ls/cat/read_file → KEEP skills (still working)
- Only DROP when user explicitly changes topic (e.g., "forget that, let's do X instead")

IMPORTANT: Return ONLY valid JSON in this exact format:
{{"add": ["skill1"], "keep": ["skill2"], "drop": ["skill3"]}}

Examples:
{{"add": [], "keep": [], "drop": []}}
{{"add": ["pdf"], "keep": [], "drop": []}}
{{"add": [], "keep": ["pdf"], "drop": []}}
{{"add": ["web-reader"], "keep": ["pdf"], "drop": ["docx"]}}
"""

ROUTER_USER_PROMPT = """Conversation:
{conversation}

Which skills should be added, kept, or dropped? Return JSON only:"""


class SkillRouter:
    """
    Routes conversations to appropriate skills using a fast LLM.

    Implements skill decay: skills have a TTL (time-to-live) that decrements
    each step. When router confirms a skill is still needed, TTL resets.
    When TTL reaches 0, skill is dropped.

    Note: This class is stateless. Active skills state is passed in and returned.
    """

    def __init__(self):
        # Use cheap model for routing (fast + cost-effective)
        try:
            self.llm = LLMClient.cheap()
        except ValueError:
            self.llm = None
        self._ttl = settings.skill_ttl

    def route(
        self,
        history: List[Dict[str, Any]],
        available_skills: List[Dict[str, str]],
        active_skills: Dict[str, int],
        limit: int = 10
    ) -> Tuple[List[str], Dict[str, int]]:
        """
        Analyze conversation history and select relevant skills.

        Args:
            history: List of messages from DB (last N turns)
            available_skills: List of {"name": ..., "description": ...}
            active_skills: Current active skills with TTL {name: ttl}
            limit: Max messages to consider (default 10)

        Returns:
            Tuple of (list of skill names to load, updated active_skills dict)
        """
        if not self.llm:
            _log("[SkillRouter] No LLM client, returning empty skills")
            return [], {}

        if not available_skills:
            return [], active_skills

        # Take last N messages
        recent_history = history[-limit:] if len(history) > limit else history

        # Format conversation for the router
        conversation_text = self._format_conversation(recent_history)

        # Format skills for the prompt
        skills_json = json.dumps(available_skills, indent=2)

        # Format active skills info
        active_skills_info = self._format_active_skills(active_skills)

        # Build messages
        messages = [
            {
                "role": "system",
                "content": ROUTER_SYSTEM_PROMPT.format(
                    skills_json=skills_json,
                    active_skills_info=active_skills_info
                )
            },
            {
                "role": "user",
                "content": ROUTER_USER_PROMPT.format(conversation=conversation_text)
            }
        ]

        try:
            _log(f"[SkillRouter] Routing with {self.llm.model} (active: {list(active_skills.keys()) or 'none'})", debug_only=True)

            response = self.llm.chat(
                messages=messages,
                component="skill_router",
                job_id=get_job_id(),
                conversation_id=get_conversation_id()
            )
            content = response.content

            # Debug: _log(f"[SkillRouter] Response: {repr(content)}", debug_only=True)

            # Handle None or empty content
            if not content:
                _log(f"[SkillRouter] Empty response from LLM")
                return self._decay_and_return(active_skills)

            content = content.strip()

            # Extract JSON from markdown code block if present
            content = self._extract_json(content)

            # Parse JSON response
            result = json.loads(content)

            if not isinstance(result, dict):
                _log(f"[SkillRouter] Invalid response format: {content}")
                return self._decay_and_return(active_skills)

            # Extract actions
            to_add = result.get("add", [])
            to_keep = result.get("keep", [])
            to_drop = result.get("drop", [])

            # Validate skill names
            valid_names = {s["name"] for s in available_skills}

            # Work with a copy
            updated_skills = dict(active_skills)

            # Process drops first
            for skill in to_drop:
                if skill in updated_skills:
                    _log(f"[SkillRouter] Dropping skill: {skill}")
                    del updated_skills[skill]

            # Process keeps - reset TTL
            for skill in to_keep:
                if skill in updated_skills:
                    updated_skills[skill] = self._ttl

            # Process adds - add with full TTL
            for skill in to_add:
                if skill in valid_names and skill not in updated_skills:
                    _log(f"[SkillRouter] Adding skill: {skill} (TTL={self._ttl})")
                    updated_skills[skill] = self._ttl

            # Decay TTL for skills not mentioned in keep/add
            mentioned = set(to_add) | set(to_keep) | set(to_drop)
            for skill in list(updated_skills.keys()):
                if skill not in mentioned:
                    updated_skills[skill] -= 1
                    if updated_skills[skill] <= 0:
                        _log(f"[SkillRouter] Skill expired: {skill}")
                        del updated_skills[skill]

            return list(updated_skills.keys()), updated_skills

        except json.JSONDecodeError as e:
            _log(f"[SkillRouter] JSON parse error: {e}, content: {content}")
            return self._decay_and_return(active_skills)
        except Exception as e:
            _log(f"[SkillRouter] Error: {e}")
            return self._decay_and_return(active_skills)

    def _decay_and_return(self, active_skills: Dict[str, int]) -> Tuple[List[str], Dict[str, int]]:
        """Decay all skills by 1 and return remaining active skills."""
        updated = dict(active_skills)
        for skill in list(updated.keys()):
            updated[skill] -= 1
            if updated[skill] <= 0:
                _log(f"[SkillRouter] Skill expired (fallback): {skill}")
                del updated[skill]
        return list(updated.keys()), updated

    def _format_active_skills(self, active_skills: Dict[str, int]) -> str:
        """Format active skills for the prompt."""
        if not active_skills:
            return "(none)"
        lines = [f"- {name} (TTL={ttl})" for name, ttl in active_skills.items()]
        return "\n".join(lines)

    def _format_conversation(self, history: List[Dict[str, Any]]) -> str:
        """Format conversation history for the router prompt.

        Always includes the first user message to preserve original intent,
        even when processing only recent history.
        """
        lines = []

        # Find and always include the first user message (original intent)
        first_user_msg = None
        for msg in history:
            if msg.get("role") == "user" and msg.get("content"):
                first_user_msg = msg
                break

        if first_user_msg:
            content = first_user_msg.get("content", "")
            lines.append(f"[ORIGINAL REQUEST] User: {content[:500]}")
            lines.append("")  # Empty line separator

        for msg in history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            # Skip tool messages - they're noise for routing
            if role == "tool":
                continue

            # For assistant messages with tool_calls, summarize
            if role == "assistant" and msg.get("tool_calls"):
                tool_names = [tc.get("function", {}).get("name", "?")
                             for tc in msg.get("tool_calls", [])]
                lines.append(f"Assistant: [used tools: {', '.join(tool_names)}]")
                if content:
                    lines.append(f"Assistant: {content[:200]}")
            elif content:
                lines.append(f"{role.capitalize()}: {content[:500]}")

        return "\n".join(lines) if lines else "(empty conversation)"

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract JSON from text, handling markdown code blocks."""
        import re
        if not text:
            return text
        # Try to extract from ```json ... ``` or ``` ... ``` block
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if match:
            return match.group(1).strip()
        # Otherwise return as-is (might be raw JSON)
        return text.strip()
