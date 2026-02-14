"""
Trace context management using context variables.

Provides thread-safe trace/span context for async and sync code.
Uses Langfuse v3 API (start_span with TraceContext).
"""

from contextvars import ContextVar
from typing import Any, Dict, List, Optional

from user_container.observability.langfuse_client import get_langfuse
from user_container.logger import log_debug, log_error


# Context variables for current trace and span
_current_trace: ContextVar[Optional[Any]] = ContextVar("current_trace", default=None)
_current_span: ContextVar[Optional[Any]] = ContextVar("current_span", default=None)


def start_trace(
    name: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    input: Optional[Any] = None,
    tags: Optional[List[str]] = None,
) -> Optional[Any]:
    """
    Start a new trace for an agent run.

    Args:
        name: Name of the trace (e.g., "agent_run")
        session_id: Session/conversation ID for grouping traces
        user_id: User identifier
        metadata: Additional metadata dict
        input: Initial input data
        tags: Dynamic tags to add to the trace

    Returns:
        Trace span object or None if Langfuse not configured
    """
    langfuse = get_langfuse()
    if not langfuse:
        return None

    try:
        # Langfuse v3: create trace ID and use start_span with TraceContext
        from langfuse.types import TraceContext
        from user_container.config import settings

        trace_id = langfuse.create_trace_id()
        trace_context = TraceContext(trace_id=trace_id)

        # Start the root span which represents the trace
        trace_span = langfuse.start_span(
            trace_context=trace_context,
            name=name,
            input=input,
            metadata=metadata or {},
        )

        # Build tags list
        all_tags = []

        # Static tags from env
        if settings.langfuse_tags:
            all_tags.extend([t.strip() for t in settings.langfuse_tags.split(",") if t.strip()])

        # Dynamic tags passed in
        if tags:
            all_tags.extend(tags)

        # Set trace-level attributes (session_id, user_id, tags, version)
        # This is required in v3 API - TraceContext doesn't propagate these
        trace_span.update_trace(
            session_id=session_id,
            user_id=user_id,
            version=settings.build_version,
            tags=all_tags if all_tags else None,
            metadata=metadata or {},
        )

        _current_trace.set(trace_span)
        log_debug(f"[Langfuse] Started trace: {name} (session={session_id}, version={settings.build_version})")
        return trace_span
    except Exception as e:
        log_error(f"[Langfuse] Failed to start trace: {e}")
        return None


def end_trace(
    output: Optional[Any] = None,
    status: str = "success",
    metadata: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
) -> None:
    """
    End the current trace.

    Args:
        output: Final output/result
        status: Status string (success, error, timeout, cancelled)
        metadata: Additional metadata to merge
        tags: Additional tags to add at trace end
    """
    trace = _current_trace.get()
    if not trace:
        return

    try:
        # Determine level based on status
        level = "DEFAULT"
        if status == "error":
            level = "ERROR"
        elif status in ("timeout", "cancelled"):
            level = "WARNING"

        # Add final status tag and any additional tags
        if tags:
            trace.update_trace(tags=tags)

        # Update and end the trace span
        trace.update(
            output=output,
            level=level,
            metadata=metadata or {},
        )
        trace.end()

        log_debug(f"[Langfuse] Ended trace with status={status}")
    except Exception as e:
        log_error(f"[Langfuse] Failed to end trace: {e}")
    finally:
        _current_trace.set(None)
        _current_span.set(None)


def get_current_trace() -> Optional[Any]:
    """Get the current trace from context."""
    return _current_trace.get()


def get_current_span() -> Optional[Any]:
    """Get the current span from context."""
    return _current_span.get()


def set_current_span(span: Optional[Any]) -> None:
    """Set the current span in context."""
    _current_span.set(span)


def create_span(
    name: str,
    input: Optional[Any] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Any]:
    """
    Create a span under the current trace.

    Args:
        name: Span name
        input: Input data
        metadata: Additional metadata

    Returns:
        Span object or None
    """
    trace = _current_trace.get()
    if not trace:
        return None

    try:
        span = trace.start_span(
            name=name,
            input=input,
            metadata=metadata or {},
        )
        return span
    except Exception as e:
        log_error(f"[Langfuse] Failed to create span: {e}")
        return None


def add_trace_tags(tags: List[str]) -> None:
    """
    Add tags to the current trace (call after routing decision, etc.).

    Args:
        tags: List of tags to add (e.g., ["depth:direct", "thinking:enabled"])
    """
    trace = _current_trace.get()
    if not trace:
        return

    try:
        trace.update_trace(tags=tags)
        log_debug(f"[Langfuse] Added tags: {tags}")
    except Exception as e:
        log_error(f"[Langfuse] Failed to add tags: {e}")
