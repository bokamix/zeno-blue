"""
Context variables for agent execution.

Uses Python's contextvars to pass execution context (like job_id) across
function calls without explicit parameter passing.
"""

from contextvars import ContextVar
from typing import Optional

# Current job ID being processed
current_job_id: ContextVar[Optional[str]] = ContextVar('current_job_id', default=None)

# Current conversation ID being processed
current_conversation_id: ContextVar[Optional[str]] = ContextVar('current_conversation_id', default=None)


def set_job_id(job_id: Optional[str]) -> None:
    """Set the current job ID for this execution context."""
    current_job_id.set(job_id)


def get_job_id() -> Optional[str]:
    """Get the current job ID for this execution context."""
    return current_job_id.get()


def set_conversation_id(conversation_id: Optional[str]) -> None:
    """Set the current conversation ID for this execution context."""
    current_conversation_id.set(conversation_id)


def get_conversation_id() -> Optional[str]:
    """Get the current conversation ID for this execution context."""
    return current_conversation_id.get()
