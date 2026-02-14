"""
Job Model - Represents a background task in the job queue.

Jobs flow:
1. Created with status="pending", enqueued to in-process queue
2. Async worker picks up, status="running"
3. Completes with status="completed" or "failed"
4. Result persisted to SQLite
"""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field
import uuid


JobStatus = Literal["pending", "running", "waiting_for_input", "completed", "failed", "cancelled"]


class Job(BaseModel):
    """
    Background job for async agent execution.

    Attributes:
        id: Unique job identifier (UUID)
        conversation_id: Conversation this job belongs to
        message: User message that triggered the job
        status: Current job status
        created_at: When job was created
        started_at: When worker started processing
        completed_at: When job finished (success or failure)
        result: Agent response (on success)
        error: Error message (on failure)
        worker_id: ID of worker processing this job
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    message: str
    status: JobStatus = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
    error: Optional[str] = None
    worker_id: Optional[str] = None
    # ask_user support
    question: Optional[str] = None
    question_options: Optional[str] = None  # JSON-encoded list
    user_response: Optional[str] = None
    # Scheduled job support - skip loading conversation history
    skip_history: bool = False

    def mark_running(self, worker_id: str) -> None:
        """Mark job as running by a worker."""
        self.status = "running"
        self.started_at = datetime.utcnow()
        self.worker_id = worker_id

    def mark_completed(self, result: str) -> None:
        """Mark job as completed with result."""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        self.result = result

    def mark_failed(self, error: str) -> None:
        """Mark job as failed with error."""
        self.status = "failed"
        self.completed_at = datetime.utcnow()
        self.error = error

    def mark_cancelled(self) -> None:
        """Mark job as cancelled by user."""
        self.status = "cancelled"
        self.completed_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert to dict for storage."""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "message": self.message,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "worker_id": self.worker_id,
            "question": self.question,
            "question_options": self.question_options,
            "user_response": self.user_response,
            "skip_history": self.skip_history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Job":
        """Create Job from dict data."""
        return cls(
            id=data["id"],
            conversation_id=data["conversation_id"],
            message=data["message"],
            status=data["status"],
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            result=data.get("result"),
            error=data.get("error"),
            worker_id=data.get("worker_id"),
            question=data.get("question"),
            question_options=data.get("question_options"),
            user_response=data.get("user_response"),
            skip_history=bool(data.get("skip_history"))
        )
