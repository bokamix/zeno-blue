"""In-process job queue. Replaces Redis for single-user desktop mode."""
import asyncio
import json
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

from user_container.logger import log


class JobQueue:
    """
    Single-process job queue backed by SQLite.

    All job state is stored in the existing `jobs` table in SQLite.
    In-memory structures handle pending queue and wake-up events.
    """

    def __init__(self, db):
        self.db = db
        self._pending: asyncio.Queue = asyncio.Queue()
        # Threading events for ask_user wake-up (agent runs in thread)
        self._sync_events: Dict[str, threading.Event] = {}
        # In-memory job cache for fast access (avoids DB round-trips for hot data)
        self._job_cache: Dict[str, Dict[str, Any]] = {}
        # Suggestions cache (in-memory, short-lived)
        self._suggestions: Dict[str, list] = {}

    # --- Enqueue / Dequeue ---

    def enqueue(self, job_id: str):
        """Add job to pending queue."""
        self._pending.put_nowait(job_id)

    async def dequeue(self, timeout=5) -> Optional[str]:
        """Get next job. Returns None on timeout."""
        try:
            return await asyncio.wait_for(self._pending.get(), timeout)
        except asyncio.TimeoutError:
            return None

    # --- Job State (in-memory cache + SQLite persistence) ---

    def create_job(self, job_id: str, conversation_id: str, message: str,
                   skip_history: bool = False,
                   headless: bool = False,
                   ask_user_default: str = "proceed"):
        """Create a new job in both cache and SQLite."""
        now = datetime.utcnow().isoformat()
        job_data = {
            "id": job_id,
            "conversation_id": conversation_id,
            "message": message,
            "status": "pending",
            "created_at": now,
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None,
            "worker_id": None,
            "question": None,
            "question_options": None,
            "user_response": None,
            "is_cancelled": False,
            "skip_history": skip_history,
            "headless": headless,
            "ask_user_default": ask_user_default,
            "suggestions": None,
        }
        self._job_cache[job_id] = job_data

        # Persist to SQLite
        from user_container.jobs.job import Job
        job = Job(
            id=job_id,
            conversation_id=conversation_id,
            message=message,
            status="pending",
            skip_history=skip_history,
        )
        self.db.save_job(job)

    def set_status(self, job_id: str, status: str = None, **kwargs):
        """Update job status and optional fields."""
        cache = self._job_cache.get(job_id, {})
        if status:
            cache["status"] = status
        for key, value in kwargs.items():
            if value is not None:
                cache[key] = value
        self._job_cache[job_id] = cache

        # Persist important state changes to SQLite
        if status in ("running", "completed", "failed", "cancelled"):
            self._persist_job(job_id)

    def _persist_job(self, job_id: str):
        """Persist job state from cache to SQLite."""
        cache = self._job_cache.get(job_id)
        if not cache:
            return

        from user_container.jobs.job import Job
        job = Job(
            id=cache["id"],
            conversation_id=cache["conversation_id"],
            message=cache["message"],
            status=cache["status"],
            created_at=datetime.fromisoformat(cache["created_at"]) if cache.get("created_at") else datetime.utcnow(),
            started_at=datetime.fromisoformat(cache["started_at"]) if cache.get("started_at") else None,
            completed_at=datetime.fromisoformat(cache["completed_at"]) if cache.get("completed_at") else None,
            result=cache.get("result"),
            error=cache.get("error"),
            worker_id=cache.get("worker_id"),
        )
        try:
            self.db.save_job(job)
        except Exception as e:
            log(f"[JobQueue] Failed to persist job {job_id}: {e}")

    def get_job(self, job_id: str) -> Optional[dict]:
        """Get job data (cache first, then SQLite fallback)."""
        if job_id in self._job_cache:
            return self._job_cache[job_id]
        # Fallback to SQLite for completed jobs
        return self.db.get_job(job_id)

    def get_job_field(self, job_id: str, field: str) -> Any:
        """Get a single field from job data."""
        job = self.get_job(job_id)
        if job:
            return job.get(field)
        return None

    # --- Ask-user flow ---

    def set_question(self, job_id: str, question: str, options: list = None):
        """Set question for ask_user and update status to waiting_for_input."""
        cache = self._job_cache.get(job_id, {})
        cache["status"] = "waiting_for_input"
        cache["question"] = question
        cache["question_options"] = json.dumps(options) if options else None
        cache["user_response"] = None
        self._job_cache[job_id] = cache
        # Create threading event for sync wait
        self._sync_events[job_id] = threading.Event()

    def wait_for_response_sync(self, job_id: str, timeout: float = 300) -> Optional[str]:
        """
        Wait for user response (blocking, for use from worker thread).

        Returns user response string or None on timeout.
        """
        event = self._sync_events.get(job_id)
        if not event:
            return None
        if event.wait(timeout):
            return self._job_cache.get(job_id, {}).get("user_response")
        return None

    def set_response(self, job_id: str, response: str):
        """Set user response and wake up waiting agent."""
        cache = self._job_cache.get(job_id, {})
        cache["user_response"] = response
        cache["status"] = "running"
        self._job_cache[job_id] = cache
        # Wake up the agent thread
        event = self._sync_events.get(job_id)
        if event:
            event.set()

    # --- Cancellation ---

    def cancel(self, job_id: str):
        """Mark job as cancelled."""
        cache = self._job_cache.get(job_id, {})
        cache["is_cancelled"] = True
        self._job_cache[job_id] = cache

    def is_cancelled(self, job_id: str) -> bool:
        """Check if job has been cancelled."""
        cache = self._job_cache.get(job_id, {})
        return cache.get("is_cancelled", False)

    # --- Force Respond ---

    def force_respond(self, job_id: str):
        """Set force_respond flag - agent will stop tools and respond to user."""
        cache = self._job_cache.get(job_id, {})
        cache["is_force_respond"] = True
        self._job_cache[job_id] = cache

    def is_force_respond(self, job_id: str) -> bool:
        """Check if force_respond flag is set."""
        cache = self._job_cache.get(job_id, {})
        return cache.get("is_force_respond", False)

    def clear_force_respond(self, job_id: str):
        """Clear force_respond flag after it's been processed."""
        cache = self._job_cache.get(job_id, {})
        cache["is_force_respond"] = False
        self._job_cache[job_id] = cache

    # --- Suggestions ---

    def set_suggestions(self, job_id: str, suggestions: list):
        """Store related question suggestions for a job."""
        self._suggestions[job_id] = suggestions

    def get_suggestions(self, job_id: str) -> list:
        """Get suggestions for a job."""
        return self._suggestions.get(job_id, [])

    # --- Active jobs ---

    def get_active_job_for_conversation(self, conversation_id: str) -> Optional[dict]:
        """Find active job for a conversation."""
        active_statuses = {"pending", "running", "waiting_for_input"}
        for job_data in self._job_cache.values():
            if (job_data.get("conversation_id") == conversation_id and
                    job_data.get("status") in active_statuses):
                return job_data
        return None

    def get_active_jobs_count(self) -> int:
        """Get count of currently running jobs."""
        return sum(
            1 for j in self._job_cache.values()
            if j.get("status") == "running"
        )

    # --- Cleanup ---

    def cleanup_job(self, job_id: str):
        """Remove job from in-memory cache (after completion + persistence)."""
        self._job_cache.pop(job_id, None)
        self._sync_events.pop(job_id, None)
        self._suggestions.pop(job_id, None)


# Singleton instance
_job_queue: Optional[JobQueue] = None


def get_job_queue() -> JobQueue:
    """Get the global job queue instance."""
    global _job_queue
    if _job_queue is None:
        raise RuntimeError("JobQueue not initialized. Call init_job_queue() first.")
    return _job_queue


def init_job_queue(db) -> JobQueue:
    """Initialize the global job queue."""
    global _job_queue
    _job_queue = JobQueue(db)
    return _job_queue
