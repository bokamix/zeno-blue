"""
Progress Estimator - Generates fake progress steps using cheap LLM.

Used to show estimated progress steps while the agent is working
on complex tasks (depth > 0). This provides visual feedback to users
indicating the type of work being done.

NOTE: These are ESTIMATES, not real-time progress. The actual agent
execution may differ from these predicted steps.
"""

import json
from typing import List

from user_container.agent.llm_client import LLMClient
from user_container.logger import log_debug


PROGRESS_SYSTEM_PROMPT = """Generate 3-4 SHORT progress steps for this task.

Rules:
- MAX 5 words per step
- Written in {language}
- First person: "Analizuję...", "Tworzę...", "Searching...", "Creating..."
- NO emojis
- Return JSON: {{"steps": ["step1", "step2", "step3"]}}

Examples (Polish):
- "Analizuję zapytanie..."
- "Przeszukuję pliki..."
- "Tworzę rozwiązanie..."
- "Weryfikuję wyniki..."

Examples (English):
- "Analyzing request..."
- "Searching files..."
- "Creating solution..."
- "Verifying results..."
"""


class ProgressEstimator:
    """Generates fake progress steps using cheap LLM (Haiku)."""

    def __init__(self):
        self.llm = LLMClient.cheap()

    def generate(self, user_message: str, language: str = "pl") -> List[str]:
        """
        Generate 3-5 estimated progress steps based on user message.

        Args:
            user_message: The user's current message/request
            language: Language for steps ("pl" or "en")

        Returns:
            List of 3-5 progress step strings, or empty list on error
        """
        try:
            # Build messages for the cheap LLM
            system_prompt = PROGRESS_SYSTEM_PROMPT.format(language=language)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"User's request: {user_message}"}
            ]

            # Call cheap LLM (no tools, no thinking)
            response = self.llm.chat(
                messages=messages,
                tools=None,
                component="progress_estimator"
            )

            if not response.content:
                log_debug("[ProgressEstimator] Empty response from LLM")
                return []

            # Parse JSON response
            content = response.content.strip()

            # Handle case where LLM wraps response in markdown code block
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
                content = content.strip()

            data = json.loads(content)
            steps = data.get("steps", [])

            # Validate and limit to 5 steps
            if isinstance(steps, list):
                # Filter out empty strings, limit length per step, max 5 steps
                steps = [
                    s.strip()[:50] for s in steps
                    if isinstance(s, str) and s.strip()
                ][:5]
                log_debug(f"[ProgressEstimator] Generated {len(steps)} steps")
                return steps

            log_debug("[ProgressEstimator] Invalid response format")
            return []

        except json.JSONDecodeError as e:
            log_debug(f"[ProgressEstimator] JSON parse error: {e}")
            return []
        except Exception as e:
            log_debug(f"[ProgressEstimator] Generation failed: {e}")
            return []
