"""
Loop Detector - detects repetitive tool call patterns.

Prevents agent from getting stuck executing the same action repeatedly.
Works independently of routing depth (applies to depth 0, 1, and 2).

Detection: exact match - same tool + same arguments repeated N times.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from user_container.logger import log_debug


@dataclass
class LoopDetection:
    """Result of loop detection analysis."""
    detected: bool
    tool_name: Optional[str] = None
    repetitions: int = 0


ANTI_LOOP_PROMPT = """⚠️ CRITICAL: LOOP DETECTED - IMMEDIATE ACTION REQUIRED

You have executed the SAME operation multiple times with NO progress.

MANDATORY ACTIONS:
1. STOP calling this tool immediately
2. ANALYZE what you already found from previous results
3. EXECUTE the next logical step (create, move, write, etc.)

If the task is impossible, respond with: "I cannot complete this because [reason]"

DO NOT call the same tool again with the same arguments. Your next response MUST be either:
- A different tool call (mkdir, write_file, edit_file, etc.)
- A text message explaining why you cannot proceed"""


# Strong prompt for when identical results are detected (even more urgent)
FORCE_PROGRESS_PROMPT = """🚨 CRITICAL: You are stuck in a loop.

The last tool calls returned IDENTICAL results. You must:
1. STOP calling the same tool
2. USE the result you already have
3. Take the NEXT action (create file, move file, etc.)

If you cannot proceed, explain WHY to the user instead of retrying."""


# Per-tool usage limits - prevents runaway tool usage
TOOL_LIMITS = {
    "web_search": 10,      # Max web searches per job
    "web_fetch": 15,       # Max URL fetches per job
    "read_file": 30,       # Max file reads per job
    "list_dir": 20,        # Max directory listings per job
    "shell": 25,           # Max shell commands per job
    "write_file": 20,      # Max file writes per job
    "edit_file": 30,       # Max file edits per job
    "search_in_files": 20, # Max file searches per job
    "delegate_task": 5,    # Max delegations per job
    "_total": 60,          # Max total tool calls per job
}


def get_research_synthesis_prompt(tool_name: str, count: int) -> str:
    """Generate synthesis prompt when a tool reaches its usage limit."""
    return f"""🔬 TOOL LIMIT REACHED

You have used `{tool_name}` {count} times in this task.

STOP using this tool. SYNTHESIZE your findings NOW.

Instructions:
1. DO NOT make any more `{tool_name}` calls
2. Review all the results you've gathered so far
3. Identify key themes, patterns, and insights
4. Write a comprehensive response for the user

Your next response MUST be a synthesis of findings, NOT another `{tool_name}` call."""


def get_total_limit_prompt() -> str:
    """Generate prompt when total tool limit is reached."""
    return """🛑 TOTAL TOOL LIMIT REACHED

You have made 60 tool calls in this task.

You MUST now respond to the user with your findings.
DO NOT make any more tool calls.

Summarize what you've accomplished and provide your response to the user."""


def detect_loop(history: List[Dict], threshold: int = 3) -> LoopDetection:
    """
    Check if the last N tool calls are identical.

    Analyzes conversation history to find repetitive patterns where
    the agent executes the exact same tool with the exact same arguments
    multiple times in a row.

    Args:
        history: Conversation history (list of messages)
        threshold: Number of identical calls to trigger detection (default: 3)

    Returns:
        LoopDetection with detection result and details
    """
    # Extract recent tool call signatures (tool_name + arguments)
    signatures = []

    for msg in reversed(history):
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                func = tc.get("function", {})
                name = func.get("name", "")
                args = func.get("arguments", "")
                sig = f"{name}:{args}"
                signatures.append((name, sig))

                if len(signatures) >= threshold:
                    break
        if len(signatures) >= threshold:
            break

    # Not enough tool calls to detect a loop
    if len(signatures) < threshold:
        return LoopDetection(detected=False)

    # Check if all signatures in the window are identical
    unique_sigs = set(sig for _, sig in signatures[:threshold])

    if len(unique_sigs) == 1:
        tool_name = signatures[0][0]
        log_debug(f"[LoopDetector] Loop detected: {tool_name} repeated {threshold}x")
        return LoopDetection(
            detected=True,
            tool_name=tool_name,
            repetitions=threshold
        )

    return LoopDetection(detected=False)


def get_anti_loop_prompt() -> str:
    """Return the anti-loop injection prompt."""
    return ANTI_LOOP_PROMPT


def get_force_progress_prompt() -> str:
    """Return the stronger force progress prompt for identical results."""
    return FORCE_PROGRESS_PROMPT
