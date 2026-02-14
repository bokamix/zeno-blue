"""
Schedule Tool - Create and list scheduled/recurring jobs.

Allows the agent to create CRON-based scheduled jobs that run automatically,
and to list existing scheduled jobs.
"""

from typing import Any, Callable, Dict, TYPE_CHECKING

from user_container.tools.registry import ToolSchema, make_parameters
from user_container.scheduler.cron_utils import parse_cron, humanize_cron

if TYPE_CHECKING:
    from user_container.scheduler.scheduler import JobScheduler
    from user_container.db.db import DB


CREATE_SCHEDULED_JOB_SCHEMA = ToolSchema(
    name="create_scheduled_job",
    description="""Create a scheduled/recurring job that runs automatically.

Use when user asks for recurring tasks like:
- "Every day at 9am do X"
- "Check Y every Monday"
- "Weekly report on Friday at 5pm"
- "Monthly summary on the 1st"

IMPORTANT: ALWAYS use ask_user to confirm the schedule before creating!

Each run creates a NEW conversation (visible in sidebar with clock icon).
Files are stored in /workspace/scheduler/{scheduler_id}/ for persistence across runs.

Examples of cron_expression:
- "0 9 * * *" = Daily at 9:00 AM
- "0 9 * * 1" = Every Monday at 9:00 AM
- "0 17 * * 5" = Every Friday at 5:00 PM
- "0 8 1 * *" = 1st of every month at 8:00 AM
- "30 14 * * 1-5" = Weekdays at 2:30 PM""",
    parameters=make_parameters(
        {
            "name": {
                "type": "string",
                "description": "Short name for the job (e.g., 'Daily News Report', 'Weekly Summary')"
            },
            "prompt": {
                "type": "string",
                "description": "The task to execute each time (what the agent should do)"
            },
            "cron_expression": {
                "type": "string",
                "description": "CRON expression (5 fields: minute hour day month weekday). E.g., '0 9 * * *' for daily at 9am"
            },
            "schedule_description": {
                "type": "string",
                "description": "Human-readable schedule description (e.g., 'Daily at 9:00 AM')"
            },
            "context": {
                "type": "object",
                "description": "Optional context for repeatable execution",
                "properties": {
                    "steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Steps to follow in each run"
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "File paths relevant to this job"
                    },
                    "variables": {
                        "type": "object",
                        "description": "Key-value variables for the job"
                    }
                }
            },
            "files_to_copy": {
                "type": "array",
                "items": {"type": "string"},
                "description": "File paths to copy to the scheduler's directory for persistence"
            }
        },
        required=["name", "prompt", "cron_expression", "schedule_description"]
    ),
    strict=False
)


def make_create_scheduled_job_tool(
    scheduler: "JobScheduler",
    conversation_id: str
) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """
    Factory function to create the create_scheduled_job tool handler.

    Args:
        scheduler: JobScheduler instance
        conversation_id: Current conversation ID (source conversation for the scheduler)

    Returns:
        Tool handler function
    """
    def create_scheduled_job(args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a scheduled job."""
        name = args.get("name")
        prompt = args.get("prompt")
        cron_expression = args.get("cron_expression")
        schedule_description = args.get("schedule_description")
        context = args.get("context")
        files_to_copy = args.get("files_to_copy")

        # Validate CRON expression
        if not parse_cron(cron_expression):
            return {
                "status": "error",
                "error": f"Invalid CRON expression: {cron_expression}. Use 5-field format: minute hour day month weekday"
            }

        # Create the scheduled job
        try:
            job_id = scheduler.add_scheduled_job(
                conversation_id=conversation_id,
                name=name,
                prompt=prompt,
                cron_expression=cron_expression,
                schedule_description=schedule_description,
                context=context,
                files_to_copy=files_to_copy
            )

            # Generate human-readable schedule for confirmation
            humanized = humanize_cron(cron_expression)

            return {
                "status": "success",
                "job_id": job_id,
                "name": name,
                "schedule": humanized,
                "files_dir": f"/workspace/scheduler/{job_id}" if files_to_copy else None,
                "message": f"Scheduled job '{name}' created successfully. It will run {humanized.lower()}. Each run creates a new conversation."
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to create scheduled job: {str(e)}"
            }

    return create_scheduled_job


LIST_SCHEDULED_JOBS_SCHEMA = ToolSchema(
    name="list_scheduled_jobs",
    description="""List all existing scheduled jobs.

Use this tool BEFORE creating or modifying a scheduler to see what already exists.
Returns a list of all scheduled jobs with their details.

Each job includes:
- id: Unique identifier
- name: Human-readable name
- prompt: The task that runs each time
- cron_expression: When it runs (CRON format)
- schedule_description: Human-readable schedule
- is_enabled: Whether the job is active
- next_run_at: When it will run next (if enabled)
- run_count: How many times it has run
- last_run_at: When it last ran (if ever)""",
    parameters=make_parameters({}, required=[]),
    strict=False
)


def make_list_scheduled_jobs_tool(
    db: "DB"
) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """
    Factory function to create the list_scheduled_jobs tool handler.

    Args:
        db: Database instance

    Returns:
        Tool handler function
    """
    def list_scheduled_jobs(args: Dict[str, Any]) -> Dict[str, Any]:
        """List all scheduled jobs."""
        try:
            jobs = db.get_scheduled_jobs()

            if not jobs:
                return {
                    "status": "success",
                    "jobs": [],
                    "message": "No scheduled jobs found."
                }

            # Format jobs for agent consumption
            formatted_jobs = []
            for job in jobs:
                formatted_job = {
                    "id": job["id"],
                    "name": job["name"],
                    "prompt": job["prompt"],
                    "cron_expression": job["cron_expression"],
                    "schedule_description": job.get("schedule_description", humanize_cron(job["cron_expression"])),
                    "is_enabled": job["is_enabled"],
                    "next_run_at": job.get("next_run_at"),
                    "run_count": job.get("run_count", 0),
                    "last_run_at": job.get("last_run_at")
                }
                formatted_jobs.append(formatted_job)

            return {
                "status": "success",
                "jobs": formatted_jobs,
                "count": len(formatted_jobs),
                "message": f"Found {len(formatted_jobs)} scheduled job(s)."
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to list scheduled jobs: {str(e)}"
            }

    return list_scheduled_jobs


# --- Update Scheduled Job Tool ---

UPDATE_SCHEDULED_JOB_SCHEMA = ToolSchema(
    name="update_scheduled_job",
    description="""Update, enable/disable, or delete a scheduled job.

Use when user wants to:
- Change the schedule/time of an existing job
- Modify the task/prompt of a job
- Rename a scheduled job
- Enable or disable a job (pause/resume)
- Delete a job permanently

IMPORTANT: Use list_scheduled_jobs first to get the job ID!

To enable/disable: set enabled=true or enabled=false
To delete permanently: set delete=true

Examples of cron_expression:
- "0 9 * * *" = Daily at 9:00 AM
- "0 6 * * *" = Daily at 6:00 AM
- "0 9 * * 1" = Every Monday at 9:00 AM
- "30 14 * * 1-5" = Weekdays at 2:30 PM""",
    parameters=make_parameters(
        {
            "job_id": {
                "type": "string",
                "description": "The ID of the scheduled job to update (get from list_scheduled_jobs)"
            },
            "name": {
                "type": "string",
                "description": "New name for the job (optional)"
            },
            "prompt": {
                "type": "string",
                "description": "New task/prompt for the job (optional)"
            },
            "cron_expression": {
                "type": "string",
                "description": "New CRON expression for the schedule (optional)"
            },
            "schedule_description": {
                "type": "string",
                "description": "New human-readable schedule description (optional)"
            },
            "enabled": {
                "type": "boolean",
                "description": "Set to true to enable the job, false to disable it (optional)"
            },
            "delete": {
                "type": "boolean",
                "description": "Set to true to permanently delete the job (optional, cannot be undone)"
            }
        },
        required=["job_id"]
    ),
    strict=False
)


def make_update_scheduled_job_tool(
    scheduler: "JobScheduler",
    db: "DB"
) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """Factory function to create the update_scheduled_job tool handler."""
    def update_scheduled_job(args: Dict[str, Any]) -> Dict[str, Any]:
        """Update, enable/disable, or delete an existing scheduled job."""
        job_id = args.get("job_id")

        # Check if job exists
        job = db.get_scheduled_job(job_id)
        if not job:
            return {
                "status": "error",
                "error": f"Scheduled job with ID '{job_id}' not found. Use list_scheduled_jobs to see available jobs."
            }

        job_name = job.get("name", job_id)

        # Handle delete first (mutually exclusive with other operations)
        if args.get("delete"):
            try:
                scheduler.remove_scheduled_job(job_id)
                return {
                    "status": "success",
                    "job_id": job_id,
                    "deleted": True,
                    "message": f"Scheduled job '{job_name}' has been deleted permanently."
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Failed to delete scheduled job: {str(e)}"
                }

        # Handle enabled/disabled toggle
        enabled_changed = False
        if "enabled" in args and args["enabled"] is not None:
            try:
                if args["enabled"]:
                    scheduler.enable_job(job_id)
                    enabled_changed = True
                else:
                    scheduler.disable_job(job_id)
                    enabled_changed = True
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Failed to toggle scheduled job: {str(e)}"
                }

        # Build updates dict for other fields
        updates = {}

        if args.get("name"):
            updates["name"] = args["name"]

        if args.get("prompt"):
            updates["prompt"] = args["prompt"]

        if args.get("cron_expression"):
            cron = args["cron_expression"]
            if not parse_cron(cron):
                return {
                    "status": "error",
                    "error": f"Invalid CRON expression: {cron}. Use 5-field format: minute hour day month weekday"
                }
            updates["cron_expression"] = cron
            # Update next_run_at when cron changes
            from user_container.scheduler.cron_utils import get_next_run
            updates["next_run_at"] = get_next_run(cron)

        if args.get("schedule_description"):
            updates["schedule_description"] = args["schedule_description"]

        # If only enabled was changed (no other updates)
        if not updates and enabled_changed:
            action = "enabled" if args["enabled"] else "disabled"
            return {
                "status": "success",
                "job_id": job_id,
                "is_enabled": args["enabled"],
                "message": f"Scheduled job '{job_name}' has been {action}."
            }

        # If no updates at all
        if not updates and not enabled_changed:
            return {
                "status": "error",
                "error": "No updates provided. Specify at least one field to update (name, prompt, cron_expression, schedule_description, enabled, or delete)."
            }

        try:
            db.update_scheduled_job(job_id, updates)

            # If cron changed and job is enabled, reschedule it by toggling
            # Get fresh job state to check is_enabled (may have changed above)
            current_job = db.get_scheduled_job(job_id)
            if "cron_expression" in updates and current_job and current_job.get("is_enabled"):
                scheduler.disable_job(job_id)
                scheduler.enable_job(job_id)

            # Build response message
            all_changes = list(updates.keys())
            if enabled_changed:
                all_changes.append("enabled" if args["enabled"] else "disabled")

            return {
                "status": "success",
                "job_id": job_id,
                "updated_fields": all_changes,
                "message": f"Successfully updated scheduled job '{job_name}'. Updated: {', '.join(all_changes)}."
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to update scheduled job: {str(e)}"
            }

    return update_scheduled_job
