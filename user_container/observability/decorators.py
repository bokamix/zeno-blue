"""
Helper functions for logging to Langfuse.

Provides convenient functions to log LLM generations and tool spans.
"""

from typing import Any, Dict, List, Optional

from user_container.observability.trace_context import get_current_trace, create_span
from user_container.logger import log_debug, log_error


def log_generation(
    name: str,
    model: str,
    input_messages: List[Dict[str, Any]],
    output: Optional[str] = None,
    usage: Optional[Dict[str, int]] = None,
    cost_usd: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log an LLM generation to Langfuse.

    Args:
        name: Generation name (e.g., "llm/agent", "llm/routing")
        model: Model name (e.g., "claude-sonnet-4-5-20250929")
        input_messages: List of input messages
        output: Generated output text
        usage: Token usage dict with prompt_tokens, completion_tokens
        cost_usd: Calculated cost in USD
        metadata: Additional metadata
    """
    trace = get_current_trace()
    if not trace:
        return

    try:
        # Truncate large input messages to prevent Langfuse payload bloat
        MAX_INPUT_SIZE = 50000
        input_to_log = input_messages
        input_str = str(input_messages)
        if len(input_str) > MAX_INPUT_SIZE:
            # Keep last N messages that fit within limit
            truncated = []
            total_size = 0
            for msg in reversed(input_messages):
                msg_size = len(str(msg))
                if total_size + msg_size > MAX_INPUT_SIZE:
                    break
                truncated.insert(0, msg)
                total_size += msg_size
            input_to_log = [{"role": "system", "content": f"[{len(input_messages) - len(truncated)} earlier messages truncated]"}] + truncated

        # Build usage object for Langfuse
        langfuse_usage = None
        if usage:
            langfuse_usage = {
                "input": usage.get("prompt_tokens", 0),
                "output": usage.get("completion_tokens", 0),
                "total": usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0),
            }
            # Add cache info if present
            if usage.get("cache_read_tokens"):
                langfuse_usage["input_cached"] = usage["cache_read_tokens"]

        # Build model parameters
        model_params = {}
        if metadata:
            if metadata.get("thinking_budget"):
                model_params["thinking_budget"] = metadata["thinking_budget"]
            if metadata.get("tool_count"):
                model_params["tool_count"] = metadata["tool_count"]

        # Create generation (Langfuse v3 API)
        generation = trace.start_observation(
            as_type="generation",
            name=name,
            model=model,
            input=input_to_log,
            output=output,
            usage_details=langfuse_usage,
            model_parameters=model_params if model_params else None,
            metadata=metadata or {},
        )
        # End generation immediately
        if generation:
            generation.end()

        log_debug(f"[Langfuse] Logged generation: {name} (model={model}, cost=${cost_usd:.6f})" if cost_usd else f"[Langfuse] Logged generation: {name} (model={model})")
    except Exception as e:
        log_error(f"[Langfuse] Failed to log generation: {e}")


def log_tool_span(
    tool_name: str,
    args: Dict[str, Any],
    result: Any,
    is_error: bool = False,
    duration_ms: Optional[float] = None,
) -> None:
    """
    Log a tool execution span to Langfuse.

    Args:
        tool_name: Name of the tool (e.g., "shell", "read_file")
        args: Tool arguments
        result: Tool result (dict or string)
        is_error: Whether the tool execution resulted in error
        duration_ms: Execution duration in milliseconds
    """
    trace = get_current_trace()
    if not trace:
        return

    try:
        # Truncate large results to avoid bloating Langfuse
        output = result
        if isinstance(result, str) and len(result) > 10000:
            output = result[:10000] + "... [truncated]"
        elif isinstance(result, dict):
            result_str = str(result)
            if len(result_str) > 10000:
                output = {"truncated": True, "preview": result_str[:10000]}

        # Create span (Langfuse v3 API)
        span = trace.start_span(
            name=f"tool:{tool_name}",
            input=args,
            output=output,
            level="ERROR" if is_error else "DEFAULT",
            metadata={"is_error": is_error},
        )

        # End span immediately (tools are synchronous)
        if span:
            span.end()

        log_debug(f"[Langfuse] Logged tool span: {tool_name}" + (" (error)" if is_error else ""))
    except Exception as e:
        log_error(f"[Langfuse] Failed to log tool span: {e}")
