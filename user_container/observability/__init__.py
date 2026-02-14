"""
Observability module - Langfuse integration for LLM tracing.

Provides:
- Trace management (start_trace, end_trace)
- Generation logging (log_generation)
- Tool span logging (log_tool_span)

Usage:
    from user_container.observability import start_trace, end_trace, log_generation, log_tool_span

    # Start a trace at the beginning of agent run
    start_trace(name="agent_run", session_id=conversation_id)

    # Log LLM generations
    log_generation(name="llm/agent", model="claude-...", input_messages=[...], output="...", usage={...})

    # Log tool executions
    log_tool_span(tool_name="shell", args={...}, result={...})

    # End trace when done
    end_trace(output="Task completed", status="success")

All functions are no-ops if Langfuse is not configured (graceful degradation).
"""

from user_container.observability.langfuse_client import get_langfuse, flush_langfuse
from user_container.observability.trace_context import start_trace, end_trace, get_current_trace, add_trace_tags, create_span
from user_container.observability.decorators import log_generation, log_tool_span

__all__ = [
    "get_langfuse",
    "flush_langfuse",
    "start_trace",
    "end_trace",
    "get_current_trace",
    "add_trace_tags",
    "create_span",
    "log_generation",
    "log_tool_span",
]
