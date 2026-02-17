"""
Routing Agent - analyzes user intent and decides execution strategy.

Classifies requests into two depth levels:
- 0 (direct): Simple questions, quick answers
- 1 (standard): Multi-step tasks, sequential execution with planning
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Literal

from user_container.agent.llm_client import LLMClient
from user_container.agent.context import get_job_id, get_conversation_id
from user_container.logger import log as _log


ROUTING_PROMPT = """Analyze this user request and classify its complexity.

## DEPTH LEVELS:
- 0: Simple/conversational - quick answers, reading files, basic info
- 1: Standard tasks - anything requiring tools, multi-step work, analysis, creation

User request: {user_message}

Recent context:
{recent_context}

Respond with a single digit: 0 or 1"""


@dataclass
class RoutingDecision:
    """Result of routing analysis.

    Depth determines execution complexity and token budget:
    - 0: Quick responses (8k token budget)
    - 1: Standard tasks (15k token budget)
    """
    depth: Literal[0, 1]
    reasoning: str

    @classmethod
    def parse(cls, response: str) -> "RoutingDecision":
        """Parse response (single digit 0/1) into RoutingDecision."""
        try:
            clean = response.strip()

            # Find depth digit (0 or 1)
            depth = 1  # default
            for char in clean:
                if char in "01":
                    depth = int(char)
                    break

            return cls(depth=depth, reasoning="")
        except Exception as e:
            _log(f"[RoutingAgent] Failed to parse: {e}, defaulting")
            return cls(depth=1, reasoning="parse error")

    @classmethod
    def default(cls) -> "RoutingDecision":
        """Return default routing (depth=1, standard execution)."""
        return cls(depth=1, reasoning="default")


class RoutingAgent:
    """
    Analyzes user requests and decides execution strategy.

    Uses a cheap/fast LLM to classify request complexity.
    """

    def __init__(self):
        try:
            self.llm = LLMClient.routing()
        except ValueError:
            self.llm = None

    def route(
        self,
        user_message: str,
        history: List[Dict[str, Any]],
        context_limit: int = 3
    ) -> RoutingDecision:
        """
        Analyze user request and return routing decision.

        Args:
            user_message: The current user message to classify
            history: Full conversation history
            context_limit: How many recent messages to include as context

        Returns:
            RoutingDecision with depth, reasoning, etc.
        """
        if not self.llm:
            _log("[RoutingAgent] No LLM client, returning default routing")
            return RoutingDecision.default()

        # Format recent context (excluding the current message)
        recent_context = self._format_recent_context(history, limit=context_limit)

        # Build the routing prompt
        prompt = ROUTING_PROMPT.format(
            user_message=user_message,
            recent_context=recent_context
        )

        try:
            _log(f"[RoutingAgent] Analyzing request with {self.llm.model}", debug_only=True)

            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                component="routing",
                job_id=get_job_id(),
                conversation_id=get_conversation_id()
            )

            if not response.content:
                _log("[RoutingAgent] Empty response, returning default")
                return RoutingDecision.default()

            decision = RoutingDecision.parse(response.content.strip())

            _log(f"[RoutingAgent] Decision: depth={decision.depth}")

            return decision

        except Exception as e:
            _log(f"[RoutingAgent] Error: {e}, returning default")
            return RoutingDecision.default()

    def _format_recent_context(
        self,
        history: List[Dict[str, Any]],
        limit: int = 3
    ) -> str:
        """Format recent conversation history for context."""
        if not history:
            return "(no previous context)"

        # Get last N messages (excluding current)
        recent = history[-limit:] if len(history) > limit else history

        lines = []
        for msg in recent:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            # Skip tool messages
            if role == "tool":
                continue

            # Truncate long content
            if content and len(content) > 200:
                content = content[:200] + "..."

            if content:
                lines.append(f"{role}: {content}")

        return "\n".join(lines) if lines else "(no relevant context)"
