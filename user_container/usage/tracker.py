"""
Usage Tracker - logs LLM usage and manages balance deductions.
"""
from typing import Dict, Any, Optional

from user_container.logger import log


class UsageTracker:
    """
    Tracks LLM usage and manages balance deductions.
    Thread-safe singleton pattern.
    """
    _instance: Optional["UsageTracker"] = None

    def __init__(self, db):
        """
        Initialize tracker with database connection.
        Use get_instance() instead of direct instantiation.
        """
        self.db = db

    @classmethod
    def get_instance(cls, db=None) -> "UsageTracker":
        """
        Get singleton instance of UsageTracker.

        Args:
            db: Database instance (required on first call)

        Returns:
            UsageTracker instance

        Raises:
            RuntimeError: If called without db and not yet initialized
        """
        if cls._instance is None:
            if db is None:
                raise RuntimeError("UsageTracker not initialized - call with db first")
            cls._instance = cls(db)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None

    def track(
        self,
        model: str,
        provider: str,
        usage: Dict[str, int],
        cost_usd: float,
        component: str,
        job_id: str = None,
        conversation_id: str = None
    ) -> bool:
        """
        Track usage and deduct from balance.

        Args:
            model: Model name
            provider: Provider name (anthropic, openai, groq)
            usage: Token usage dict
            cost_usd: Calculated cost
            component: Calling component (agent, routing, etc.)
            job_id: Optional job ID
            conversation_id: Optional conversation ID

        Returns:
            True if deduction successful, False if insufficient balance
        """
        # Log usage (always, even if balance insufficient)
        self.db.log_usage(
            model=model,
            provider=provider,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            cost_usd=cost_usd,
            component=component,
            job_id=job_id,
            conversation_id=conversation_id
        )

        return True

    def has_sufficient_balance(self, min_amount: float = 0.001) -> bool:
        """Always returns True - billing disabled for desktop mode."""
        return True

    def get_balance(self) -> Dict[str, Any]:
        """Get current balance info."""
        return self.db.get_balance()

    def get_usage_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get usage summary for the last N days."""
        return self.db.get_usage_summary(days)
