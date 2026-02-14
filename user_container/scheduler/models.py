"""
Pydantic models for Job Scheduler.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ScheduledJob(BaseModel):
    """A scheduled/recurring job definition."""

    id: str
    conversation_id: str
    name: str
    prompt: str
    cron_expression: str
    schedule_description: str
    timezone: str = "Europe/Warsaw"
    is_enabled: bool = True
    created_at: datetime
    updated_at: datetime
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    run_count: int = 0

    class Config:
        from_attributes = True


class ScheduledJobRun(BaseModel):
    """A single execution of a scheduled job."""

    id: int
    scheduled_job_id: str
    job_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str  # "running", "completed", "failed"
    result_preview: Optional[str] = None

    class Config:
        from_attributes = True


class CreateScheduledJobRequest(BaseModel):
    """Request to create a scheduled job (from agent tool)."""

    conversation_id: str
    name: str
    prompt: str
    cron_expression: str
    schedule_description: str


class UpdateScheduledJobRequest(BaseModel):
    """Request to update a scheduled job."""

    is_enabled: Optional[bool] = None
    name: Optional[str] = None
    prompt: Optional[str] = None
    cron_expression: Optional[str] = None
    schedule_description: Optional[str] = None
