"""Auth middleware for ZENO - opt-in password protection for remote access.

When settings.auth_password is None, all requests pass through (localhost mode).
When set, requests must have either:
  - A valid session cookie (zeno_session) from /api/auth/login
  - A valid API key (Authorization: Bearer zeno_...)
"""

import json
import secrets
import time
from typing import Dict, Optional

from fastapi import Request
from fastapi.responses import JSONResponse

from user_container.config import settings
from user_container.logger import log


# In-memory session store: {session_id: {"created_at": timestamp}}
_sessions: Dict[str, dict] = {}

# Public paths that never require auth
PUBLIC_PATHS = {
    "/health",
    "/api/auth/login",
    "/api/auth/status",
    "/setup/status",
    "/setup",
}

# Public path prefixes
PUBLIC_PREFIXES = (
    "/assets/",
    "/favicon.",
    "/sw.js",
    "/registerSW.js",
    "/manifest.webmanifest",
)


def create_session() -> str:
    """Create a new session and return the session ID."""
    session_id = secrets.token_urlsafe(32)
    _sessions[session_id] = {"created_at": time.time()}
    return session_id


def validate_session(session_id: str) -> bool:
    """Check if a session is valid and not expired."""
    session = _sessions.get(session_id)
    if not session:
        return False
    if time.time() - session["created_at"] > settings.auth_session_ttl:
        _sessions.pop(session_id, None)
        return False
    return True


def delete_session(session_id: str):
    """Remove a session."""
    _sessions.pop(session_id, None)


def validate_api_key(token: str, db) -> bool:
    """Check if token matches any stored API key."""
    row = db.fetchone(
        "SELECT value FROM app_state WHERE key = ?",
        ("api_keys",)
    )
    if not row:
        return False
    try:
        keys = json.loads(row["value"])
        return any(k.get("key") == token for k in keys)
    except (json.JSONDecodeError, TypeError):
        return False


def is_public_path(path: str) -> bool:
    """Check if the path is public (no auth required)."""
    if path in PUBLIC_PATHS:
        return True
    for prefix in PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


async def auth_middleware(request: Request, call_next):
    """FastAPI middleware for opt-in auth.

    When auth_password is not set, all requests pass through.
    Admin paths (/admin/*) are exempt (they have their own HTTP Basic Auth).
    """
    # No auth configured - pass through
    if not settings.auth_password:
        return await call_next(request)

    path = request.url.path

    # Public paths - no auth needed
    if is_public_path(path):
        return await call_next(request)

    # Admin panel has its own auth
    if path.startswith("/admin"):
        return await call_next(request)

    # Check Authorization: Bearer <key>
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        # Lazy import to avoid circular dependency
        from user_container.app import db
        if validate_api_key(token, db):
            return await call_next(request)

    # Check session cookie
    session_id = request.cookies.get("zeno_session")
    if session_id and validate_session(session_id):
        return await call_next(request)

    # Not authenticated
    # For API/data requests, return 401 JSON
    api_prefixes = ("/api/", "/chat", "/jobs", "/conversations", "/settings",
                    "/status", "/artifacts", "/apps", "/scheduled-jobs",
                    "/custom-skills", "/container/", "/internal/",
                    "/user-info", "/disk-usage")
    for prefix in api_prefixes:
        if path.startswith(prefix):
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"}
            )

    # For page requests (SPA), let through so frontend can render login screen
    return await call_next(request)
