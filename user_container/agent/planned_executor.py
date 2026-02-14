"""
Planned Executor - handles depth=1 (planned) execution strategy.

This module provides utilities for planned execution:
- Planning prompt injection at the start
- Periodic reflection checkpoints
- Plan/reflection extraction for logging
"""

import re
from typing import Optional

from user_container.config import settings
from user_container.agent.prompts import PLANNING_PROMPT, REFLECTION_PROMPT
from user_container.logger import log as _log


def should_add_planning(depth: int, step_count: int) -> bool:
    """
    Check if we should inject planning prompt.

    Planning is added at step 1 for depth >= 1 tasks.
    """
    return depth >= 1 and step_count == 1


def should_add_reflection(depth: int, step_count: int) -> bool:
    """
    Check if we should inject reflection prompt.

    Reflection is added every N steps for depth >= 1 tasks.
    N is configured via REFLECTION_INTERVAL (default: 7, 0 = disabled).
    """
    if depth < 1:
        return False

    interval = settings.reflection_interval
    if interval <= 0:
        return False

    # Reflect every N steps, but not on step 1 (that's planning)
    return step_count > 1 and step_count % interval == 0


def get_planning_injection() -> str:
    """Get the planning prompt to inject into system prompt."""
    return f"\n\n## PLANNING MODE\n{PLANNING_PROMPT}"


def get_reflection_injection() -> str:
    """Get the reflection prompt to inject as a user message."""
    return REFLECTION_PROMPT


def extract_plan(content: str) -> Optional[str]:
    """Extract <plan>...</plan> block from content."""
    if not content:
        return None
    match = re.search(r'<plan>(.*?)</plan>', content, re.DOTALL)
    return match.group(1).strip() if match else None


def extract_reflection(content: str) -> Optional[str]:
    """Extract <reflection>...</reflection> block from content."""
    if not content:
        return None
    match = re.search(r'<reflection>(.*?)</reflection>', content, re.DOTALL)
    return match.group(1).strip() if match else None


def log_plan(content: str) -> None:
    """Log extracted plan if present."""
    plan = extract_plan(content)
    if plan:
        _log(f"[Plan] {plan[:200]}..." if len(plan) > 200 else f"[Plan] {plan}")


def log_reflection(content: str) -> None:
    """Log extracted reflection if present."""
    reflection = extract_reflection(content)
    if reflection:
        _log(f"[Reflection] {reflection[:200]}..." if len(reflection) > 200 else f"[Reflection] {reflection}")
