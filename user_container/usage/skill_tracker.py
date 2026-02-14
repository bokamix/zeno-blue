"""
Skill Usage Tracker - tracks API usage from skill outputs.

Skills that make direct API calls (bypassing LLMClient) can return usage data
in their output. This module detects and tracks that usage automatically.
"""
import json
import re
from typing import Any, Dict, Optional

from user_container.logger import log_debug


def _extract_skill_output(output: Any) -> Optional[Dict[str, Any]]:
    """
    Extract skill output from tool result.

    Shell tool wraps output in {"code": 0, "stdout": "...", "stderr": "..."}.
    This function extracts and parses the actual skill output from stdout.
    """
    if not isinstance(output, dict):
        return None

    # Direct output (not from shell)
    if "provider" in output and "model" in output and "usage" in output:
        return output

    # Shell tool output - parse stdout
    if "code" in output and "stdout" in output:
        stdout = output.get("stdout", "")
        if not stdout or not isinstance(stdout, str):
            return None
        try:
            parsed = json.loads(stdout)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            return None

    return None


def has_trackable_usage(output: Any) -> bool:
    """
    Check if tool output contains trackable API usage.

    Required fields in output (or in stdout for shell tools):
    - provider: str (e.g., "anthropic", "openai")
    - model: str (e.g., "claude-sonnet-4-5-20250929")
    - usage: dict with either:
        - Token-based: {"input_tokens": N, "output_tokens": M}
        - Duration-based: {"duration_seconds": X}
    """
    skill_output = _extract_skill_output(output)
    if skill_output is None:
        return False
    return (
        "provider" in skill_output and
        "model" in skill_output and
        "usage" in skill_output and
        isinstance(skill_output.get("usage"), dict)
    )


def extract_skill_name(tool_name: str, args: Dict[str, Any], output: Dict[str, Any]) -> str:
    """
    Extract skill name for usage tracking component.

    Priority:
    1. Explicit skill_name in output
    2. Extract from shell command path (/skills/{name}/...)
    3. Fallback to "unknown"
    """
    # Explicit skill_name in output takes precedence
    if output.get("skill_name"):
        return output["skill_name"]

    # For shell commands, extract from script path
    if tool_name == "shell":
        cmd = args.get("cmd", "")
        # Pattern: /skills/{skill_name}/scripts/ or /skills/{skill_name}/
        match = re.search(r'/skills/([^/]+)/', cmd)
        if match:
            return match.group(1)

    # Fallback
    return "unknown"


def track_skill_usage(
    tool_name: str,
    args: Dict[str, Any],
    output: Any,
    job_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    component: Optional[str] = None
) -> bool:
    """
    Track API usage from skill output.

    This function checks if the tool output contains usage data and,
    if so, logs it to the database and deducts from the user's balance.

    Args:
        tool_name: Name of the tool that was called
        args: Arguments passed to the tool
        output: Tool output (must be dict with provider, model, usage)
        job_id: Optional job ID for tracking
        conversation_id: Optional conversation ID
        component: Optional component override (e.g., "app:my-app-id")

    Returns:
        True if tracking succeeded, False if no trackable usage or error
    """
    skill_output = _extract_skill_output(output)
    if skill_output is None:
        return False

    if not (
        "provider" in skill_output and
        "model" in skill_output and
        "usage" in skill_output and
        isinstance(skill_output.get("usage"), dict)
    ):
        return False

    try:
        # Import here to avoid circular imports
        from user_container.pricing import calculate_cost, calculate_cost_duration
        from user_container.usage.tracker import UsageTracker

        provider = skill_output["provider"]
        model = skill_output["model"]
        usage = skill_output["usage"]

        # Calculate cost based on usage type
        if "duration_seconds" in usage:
            # Duration-based (e.g., Whisper)
            cost_usd = calculate_cost_duration(provider, model, usage["duration_seconds"])
            # Store as zero tokens - cost is what matters
            usage_for_db = {"prompt_tokens": 0, "completion_tokens": 0}
        else:
            # Token-based (e.g., Vision API)
            # Normalize token key names (skill may use input_tokens or prompt_tokens)
            prompt_tokens = usage.get("prompt_tokens", usage.get("input_tokens", 0))
            completion_tokens = usage.get("completion_tokens", usage.get("output_tokens", 0))
            usage_for_db = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens
            }
            cost_usd = calculate_cost(provider, model, usage_for_db)

        # Use provided component or derive from skill name
        if component is None:
            skill_name = extract_skill_name(tool_name, args, skill_output)
            component = f"skill:{skill_name}"

        tracker = UsageTracker.get_instance()
        success = tracker.track(
            model=model,
            provider=provider,
            usage=usage_for_db,
            cost_usd=cost_usd,
            component=component,
            job_id=job_id,
            conversation_id=conversation_id
        )

        log_debug(f"[SkillUsage] Tracked {component}: ${cost_usd:.6f} ({provider}/{model})")
        return success

    except RuntimeError:
        # UsageTracker not initialized (e.g., during startup)
        return False
    except Exception as e:
        log_debug(f"[SkillUsage] Failed to track: {e}")
        return False
