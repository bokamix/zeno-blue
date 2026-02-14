"""
Job Scheduler - APScheduler-based scheduled job execution.

Manages scheduled jobs:
- Loads enabled jobs on startup
- Registers them with APScheduler using CRON triggers
- Triggers jobs by creating jobs and enqueuing to in-process queue
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from user_container.logger import log
from user_container.scheduler.cron_utils import get_next_run, DEFAULT_TIMEZONE
from user_container.usage import UsageTracker

if TYPE_CHECKING:
    from user_container.db.db import DB
    from user_container.jobs.queue import JobQueue


class JobScheduler:
    """
    Background job scheduler using APScheduler.

    Manages scheduled/recurring jobs:
    - Load from database on startup
    - Register with APScheduler
    - Trigger by enqueueing to in-process job queue
    """

    def __init__(self, db: "DB", job_queue: "JobQueue"):
        """
        Initialize JobScheduler.

        Args:
            db: Database instance for persistence
            job_queue: In-process job queue
        """
        self.db = db
        self.job_queue = job_queue
        self.scheduler = BackgroundScheduler(timezone=DEFAULT_TIMEZONE)
        self._started = False

    def start(self) -> None:
        """
        Start the scheduler.

        1. Load enabled jobs from database
        2. Register each with APScheduler
        3. Start the scheduler thread
        """
        if self._started:
            log("[Scheduler] Already started")
            return

        # Load enabled jobs from DB
        jobs = self.db.get_enabled_scheduled_jobs()
        log(f"[Scheduler] Loading {len(jobs)} scheduled jobs")

        for job_data in jobs:
            self._register_job(job_data)

        # Start APScheduler
        self.scheduler.start()
        self._started = True
        log("[Scheduler] Started")

    def stop(self) -> None:
        """Stop the scheduler gracefully."""
        if not self._started:
            return

        self.scheduler.shutdown(wait=False)
        self._started = False
        log("[Scheduler] Stopped")

    def add_scheduled_job(
        self,
        conversation_id: str,
        name: str,
        prompt: str,
        cron_expression: str,
        schedule_description: str,
        context: dict = None,
        files_to_copy: list = None
    ) -> str:
        """
        Create a new scheduled job.

        Args:
            conversation_id: Source conversation (where job was created)
            name: Short name for the job
            prompt: Task to execute
            cron_expression: CRON schedule
            schedule_description: Human-readable schedule
            context: Optional context dict with steps, files, variables
            files_to_copy: Optional list of file paths to copy to scheduler dir

        Returns:
            Job ID
        """
        import json
        import os
        import shutil

        job_id = str(uuid.uuid4())
        now = self.db.now()

        # Calculate next run time
        next_run = get_next_run(cron_expression)
        next_run_str = next_run.isoformat() if next_run else None

        # Handle file copying
        files_dir = None
        if files_to_copy:
            files_dir = f"/workspace/scheduler/{job_id}"
            os.makedirs(files_dir, exist_ok=True)
            for src_path in files_to_copy:
                if os.path.exists(src_path):
                    try:
                        dst_path = os.path.join(files_dir, os.path.basename(src_path))
                        if os.path.isdir(src_path):
                            shutil.copytree(src_path, dst_path)
                        else:
                            shutil.copy2(src_path, dst_path)
                        log(f"[Scheduler] Copied {src_path} -> {dst_path}")
                    except Exception as e:
                        log(f"[Scheduler] Failed to copy {src_path}: {e}")
                else:
                    log(f"[Scheduler] Source file not found: {src_path}")

        # Serialize context
        context_json = json.dumps(context) if context else None

        job_data = {
            "id": job_id,
            "conversation_id": conversation_id,
            "source_conversation_id": conversation_id,
            "name": name,
            "prompt": prompt,
            "cron_expression": cron_expression,
            "schedule_description": schedule_description,
            "timezone": DEFAULT_TIMEZONE,
            "is_enabled": True,
            "created_at": now,
            "updated_at": now,
            "last_run_at": None,
            "next_run_at": next_run_str,
            "run_count": 0,
            "context_json": context_json,
            "files_dir": files_dir
        }

        # Save to database
        self.db.save_scheduled_job(job_data)

        # Register with APScheduler (single process, always local)
        if self._started:
            self._register_job(job_data)
        log(f"[Scheduler] Added job {job_id}: {name} ({schedule_description})")

        return job_id

    def remove_scheduled_job(self, job_id: str) -> None:
        """
        Remove a scheduled job completely.

        Args:
            job_id: Job ID to remove
        """
        import os
        import shutil

        # Get job data to find files_dir
        job_data = self.db.get_scheduled_job(job_id)

        # Remove from APScheduler
        try:
            self.scheduler.remove_job(job_id)
        except Exception:
            pass  # Job might not be registered

        # Remove files directory if exists
        if job_data and job_data.get("files_dir"):
            files_dir = job_data["files_dir"]
            if os.path.exists(files_dir):
                try:
                    shutil.rmtree(files_dir)
                    log(f"[Scheduler] Removed files directory: {files_dir}")
                except Exception as e:
                    log(f"[Scheduler] Failed to remove files directory {files_dir}: {e}")

        # Clear scheduler_id from linked conversations (keep conversations, just unlink)
        self.db.execute(
            "UPDATE conversations SET scheduler_id = NULL WHERE scheduler_id = ?",
            (job_id,)
        )

        # Remove from database
        self.db.delete_scheduled_job(job_id)
        log(f"[Scheduler] Removed job {job_id}")

    def enable_job(self, job_id: str) -> None:
        """Enable a disabled job."""
        job_data = self.db.get_scheduled_job(job_id)
        if not job_data:
            log(f"[Scheduler] Job {job_id} not found")
            return

        # Update database
        self.db.update_scheduled_job(job_id, {"is_enabled": True})

        # Register with APScheduler
        self._register_job(job_data)
        log(f"[Scheduler] Enabled job {job_id}")

    def disable_job(self, job_id: str) -> None:
        """Disable a job (keep in DB but don't execute)."""
        try:
            self.scheduler.remove_job(job_id)
        except Exception:
            pass

        self.db.update_scheduled_job(job_id, {"is_enabled": False})
        log(f"[Scheduler] Disabled job {job_id}")

    def trigger_job(self, job_id: str) -> Optional[tuple[str, str]]:
        """Manually trigger a scheduled job (for testing)."""
        job_data = self.db.get_scheduled_job(job_id)
        if not job_data:
            return None
        return self._trigger_job(job_id)

    def reload_job(self, job_id: str) -> bool:
        """Reload a single job from database and register with APScheduler."""
        job_data = self.db.get_scheduled_job(job_id)
        if not job_data:
            return False

        if not job_data.get("is_enabled"):
            return False

        self._register_job(job_data)
        log(f"[Scheduler] Reloaded job {job_id}: {job_data.get('name')}")
        return True

    def _register_job(self, job_data: dict) -> None:
        """Register a job with APScheduler."""
        job_id = job_data["id"]
        cron_expression = job_data["cron_expression"]

        try:
            self.scheduler.remove_job(job_id)
        except Exception:
            pass

        try:
            trigger = CronTrigger.from_crontab(cron_expression, timezone=DEFAULT_TIMEZONE)
        except ValueError as e:
            log(f"[Scheduler] Invalid CRON expression for job {job_id}: {e}")
            return

        self.scheduler.add_job(
            func=self._trigger_job,
            trigger=trigger,
            args=[job_id],
            id=job_id,
            name=job_data.get("name", job_id),
            replace_existing=True
        )

    def _trigger_job(self, scheduled_job_id: str) -> Optional[tuple[str, str]]:
        """
        Called when a scheduled job fires.
        Creates a NEW conversation and job, enqueues to in-process queue.
        """
        import json

        sj = self.db.get_scheduled_job(scheduled_job_id)
        if not sj:
            log(f"[Scheduler] Scheduled job {scheduled_job_id} not found")
            return None

        if not sj.get("is_enabled"):
            log(f"[Scheduler] Scheduled job {scheduled_job_id} is disabled, skipping")
            return None

        # Create NEW conversation for this run
        new_conv_id = str(uuid.uuid4())
        self.db.execute("""
            INSERT INTO conversations(id, created_at, scheduler_id, is_scheduler_run)
            VALUES (?, ?, ?, 1)
        """, (new_conv_id, self.db.now(), scheduled_job_id))

        # Build prompt with context if available
        prompt = sj["prompt"]
        context_json = sj.get("context_json")
        files_dir = sj.get("files_dir")

        if context_json:
            try:
                context = json.loads(context_json)
                context_parts = []
                if context.get("steps"):
                    steps_str = "\n".join(f"- {s}" for s in context["steps"])
                    context_parts.append(f"Steps to follow:\n{steps_str}")
                if context.get("variables"):
                    vars_str = "\n".join(f"- {k}: {v}" for k, v in context["variables"].items())
                    context_parts.append(f"Variables:\n{vars_str}")
                if files_dir:
                    context_parts.append(f"Working directory for this scheduler: {files_dir}")
                if context_parts:
                    prompt = f"{prompt}\n\n--- Context ---\n" + "\n\n".join(context_parts)
            except json.JSONDecodeError:
                log(f"[Scheduler] Failed to parse context_json for job {scheduled_job_id}")

        # Create job via in-process queue
        job_id = str(uuid.uuid4())
        self.db.save_message_from_dict(new_conv_id, {"role": "user", "content": prompt})
        self.job_queue.create_job(job_id, new_conv_id, prompt, skip_history=True)
        self.job_queue.enqueue(job_id)

        # Update scheduled job stats
        now = self.db.now()
        next_run = get_next_run(sj["cron_expression"])
        next_run_str = next_run.isoformat() if next_run else None

        self.db.update_scheduled_job(scheduled_job_id, {
            "last_run_at": now,
            "next_run_at": next_run_str,
            "run_count": sj.get("run_count", 0) + 1
        })

        # Log the run
        self.db.add_scheduled_job_run(
            scheduled_job_id=scheduled_job_id,
            job_id=job_id,
            status="pending"
        )

        log(f"[Scheduler] Triggered job {scheduled_job_id} -> created conversation {new_conv_id}, job {job_id}")
        return (job_id, new_conv_id)


# Global scheduler instance
_scheduler: Optional[JobScheduler] = None


def get_scheduler() -> JobScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized. Call init_scheduler() first.")
    return _scheduler


def init_scheduler(db: "DB", job_queue: "JobQueue") -> JobScheduler:
    """Initialize the global scheduler."""
    global _scheduler
    _scheduler = JobScheduler(db, job_queue)
    return _scheduler


def close_scheduler() -> None:
    """Stop and close the global scheduler."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.stop()
        _scheduler = None
