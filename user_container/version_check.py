"""
Background version checker — polls GitHub releases to detect available updates.
"""

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from user_container.config import settings

logger = logging.getLogger(__name__)

GITHUB_RELEASE_URL = "https://api.github.com/repos/bokamix/zeno-blue/releases/tags/latest"
CHECK_INTERVAL = 3600  # 1 hour

# Module-level state
_can_update = False
_update_version: str | None = None


def get_update_status() -> dict:
    return {
        "can_update": _can_update,
        "update_version": _update_version,
    }


async def _check_for_update():
    global _can_update, _update_version

    local_build_time = settings.build_time
    if local_build_time in ("unknown", ""):
        # Can't compare — no local build time
        return

    try:
        local_dt = datetime.fromisoformat(local_build_time.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                GITHUB_RELEASE_URL,
                headers={"Accept": "application/vnd.github+json"},
            )
            if resp.status_code != 200:
                logger.debug(f"[VersionCheck] GitHub API returned {resp.status_code}")
                return

            data = resp.json()
            published_at = data.get("published_at")
            if not published_at:
                return

            remote_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))

            if remote_dt > local_dt:
                tag = data.get("tag_name", "latest")
                _can_update = True
                _update_version = tag
                logger.info(f"[VersionCheck] Update available: {tag} (published {published_at})")
            else:
                _can_update = False
                _update_version = None

    except Exception as e:
        logger.debug(f"[VersionCheck] Failed to check for updates: {e}")


async def start_version_check():
    """Run an initial check, then repeat every CHECK_INTERVAL seconds."""
    await _check_for_update()
    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        await _check_for_update()
