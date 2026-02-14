"""
CRON utilities for Job Scheduler.

Provides:
- parse_cron: Validate CRON expression
- humanize_cron: Convert CRON to human-readable string
- get_next_run: Calculate next execution time
"""

from datetime import datetime
from typing import Optional

from croniter import croniter


# Hardcoded timezone for MVP (see TODO.md)
DEFAULT_TIMEZONE = "Europe/Warsaw"


def parse_cron(expression: str) -> bool:
    """
    Validate a CRON expression.

    Args:
        expression: CRON expression (5 fields: minute hour day month weekday)

    Returns:
        True if valid, False otherwise

    Examples:
        >>> parse_cron("0 9 * * *")  # Daily at 9:00
        True
        >>> parse_cron("invalid")
        False
    """
    try:
        croniter(expression)
        return True
    except (ValueError, KeyError):
        return False


def get_next_run(expression: str, after: Optional[datetime] = None) -> Optional[datetime]:
    """
    Calculate the next execution time for a CRON expression.

    Args:
        expression: CRON expression
        after: Base time (default: now)

    Returns:
        Next execution datetime, or None if expression is invalid

    Examples:
        >>> get_next_run("0 9 * * *")  # Returns next 9:00 AM
    """
    try:
        base = after or datetime.now()
        cron = croniter(expression, base)
        return cron.get_next(datetime)
    except (ValueError, KeyError):
        return None


def humanize_cron(expression: str) -> str:
    """
    Convert a CRON expression to human-readable description.

    Args:
        expression: CRON expression (5 fields)

    Returns:
        Human-readable description

    Examples:
        >>> humanize_cron("0 9 * * *")
        "Daily at 09:00"
        >>> humanize_cron("0 9 * * 1")
        "Every Monday at 09:00"
        >>> humanize_cron("30 14 1 * *")
        "Monthly on day 1 at 14:30"
    """
    try:
        parts = expression.split()
        if len(parts) != 5:
            return expression  # Return as-is if not standard format

        minute, hour, day, month, weekday = parts

        # Build time string
        time_str = ""
        if minute != "*" and hour != "*":
            time_str = f"at {hour.zfill(2)}:{minute.zfill(2)}"
        elif hour != "*":
            time_str = f"at {hour.zfill(2)}:00"
        elif minute != "*":
            time_str = f"at minute {minute}"

        # Weekday names
        weekday_names = {
            "0": "Sunday", "7": "Sunday",
            "1": "Monday", "2": "Tuesday", "3": "Wednesday",
            "4": "Thursday", "5": "Friday", "6": "Saturday"
        }

        # Month names
        month_names = {
            "1": "January", "2": "February", "3": "March", "4": "April",
            "5": "May", "6": "June", "7": "July", "8": "August",
            "9": "September", "10": "October", "11": "November", "12": "December"
        }

        # Determine schedule type
        if day == "*" and month == "*" and weekday == "*":
            # Daily
            return f"Daily {time_str}".strip()

        elif day == "*" and month == "*" and weekday != "*":
            # Weekly on specific day(s)
            if "-" in weekday:
                # Range like 1-5
                start, end = weekday.split("-")
                return f"Every {weekday_names.get(start, start)} to {weekday_names.get(end, end)} {time_str}".strip()
            elif "," in weekday:
                # Multiple days
                days = [weekday_names.get(d.strip(), d) for d in weekday.split(",")]
                return f"Every {', '.join(days)} {time_str}".strip()
            else:
                day_name = weekday_names.get(weekday, f"day {weekday}")
                return f"Every {day_name} {time_str}".strip()

        elif day != "*" and month == "*" and weekday == "*":
            # Monthly on specific day
            return f"Monthly on day {day} {time_str}".strip()

        elif day != "*" and month != "*":
            # Yearly on specific date
            month_name = month_names.get(month, f"month {month}")
            return f"Yearly on {month_name} {day} {time_str}".strip()

        elif minute == "*" and hour == "*":
            # Every minute/hour
            if day == "*" and month == "*" and weekday == "*":
                return "Every minute"

        # Fallback: return expression with prefix
        return f"Cron: {expression}"

    except Exception:
        return expression


def get_schedule_description(expression: str) -> str:
    """
    Alias for humanize_cron for consistency with tool schema.
    """
    return humanize_cron(expression)
