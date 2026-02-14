"""
Suggestion Generator - Generates strategic follow-up questions using cheap LLM.

Used to show "Related Tasks" while the agent is working on complex tasks (depth > 0).
Generates consulting-style probing questions to help user reach better business insights.
"""

import json
from typing import List, Dict, Any

from user_container.agent.llm_client import LLMClient
from user_container.logger import log_debug


SUGGESTION_SYSTEM_PROMPT = """Suggest 3 SHORT strategic follow-up tasks for the user.

RULES:
1. MAX 6 words per suggestion
2. Use imperative: "Zdefiniuj...", "Przeanalizuj...", "Find..."
3. Different analytical angles (customer, competitor, financial, operational)
4. Match user's language
5. Return ONLY JSON: {"questions": ["task1", "task2", "task3"]}

EXAMPLES:
- "Zdefiniuj grupę docelową"
- "Porównaj z konkurencją"
- "Określ KPIs sukcesu"
- "Find root cause"
- "Benchmark vs industry"
"""


class SuggestionGenerator:
    """Generates strategic business suggestions using cheap LLM (Haiku)."""

    def __init__(self):
        self.llm = LLMClient.cheap()

    def generate(self, user_message: str, history: List[Dict[str, Any]] = None) -> List[str]:
        """
        Generate 3 strategic follow-up suggestions based on user message and context.

        Args:
            user_message: The user's current message/request
            history: Optional conversation history for context

        Returns:
            List of 3 task suggestion strings, or empty list on error
        """
        try:
            # Build context from user message
            user_prompt = f"""User's request: "{user_message}"

Suggest 3 follow-up tasks (max 6 words each)."""

            messages = [
                {"role": "system", "content": SUGGESTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]

            response = self.llm.chat(
                messages=messages,
                tools=None,
                component="suggestions"
            )

            if not response.content:
                log_debug("[Suggestions] Empty response from LLM")
                return []

            content = response.content.strip()
            log_debug(f"[Suggestions] Raw LLM response: {content[:200]}")

            # Handle markdown code blocks
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
                content = content.strip()

            data = json.loads(content)
            questions = data.get("questions", [])

            if isinstance(questions, list):
                # Filter, clean and limit
                questions = [
                    q.strip()[:70] for q in questions
                    if isinstance(q, str) and q.strip()
                ][:3]
                log_debug(f"[Suggestions] Generated {len(questions)} suggestions")
                return questions

            log_debug("[Suggestions] Invalid response format")
            return []

        except json.JSONDecodeError as e:
            log_debug(f"[Suggestions] JSON parse error: {e}")
            return []
        except Exception as e:
            log_debug(f"[Suggestions] Generation failed: {e}")
            return []
