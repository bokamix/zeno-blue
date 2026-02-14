"""
Langfuse client singleton wrapper.

Provides a singleton Langfuse client that is lazily initialized
and gracefully handles missing configuration.
"""

from typing import Optional
import threading

from user_container.config import settings
from user_container.logger import log_debug, log_error


_langfuse_instance = None
_langfuse_lock = threading.Lock()
_init_attempted = False


def get_langfuse():
    """
    Get the Langfuse client singleton.

    Returns None if Langfuse is not configured (missing keys).
    Thread-safe lazy initialization.
    """
    global _langfuse_instance, _init_attempted

    if _init_attempted:
        return _langfuse_instance

    with _langfuse_lock:
        # Double-check after acquiring lock
        if _init_attempted:
            return _langfuse_instance

        _init_attempted = True

        # Check if Langfuse is configured
        if not settings.langfuse_public_key or not settings.langfuse_secret_key:
            log_debug("[Langfuse] Not configured (missing keys), observability disabled")
            return None

        try:
            from langfuse import Langfuse

            _langfuse_instance = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )
            log_debug(f"[Langfuse] Initialized (host: {settings.langfuse_host})")
            return _langfuse_instance
        except ImportError:
            log_debug("[Langfuse] Package not installed, observability disabled")
            return None
        except Exception as e:
            log_error(f"[Langfuse] Failed to initialize: {e}")
            return None


def flush_langfuse():
    """Flush any pending Langfuse events. Call before shutdown."""
    langfuse = get_langfuse()
    if langfuse:
        try:
            langfuse.flush()
            log_debug("[Langfuse] Flushed pending events")
        except Exception as e:
            log_error(f"[Langfuse] Failed to flush: {e}")
