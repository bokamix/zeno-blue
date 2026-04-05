"""
Background version checker — polls GitHub releases to detect available updates.

Each push to main creates a new release tagged build-{sha}. This module
fetches /releases/latest (GitHub's "latest" pointer) and compares the
release tag's commit hash with the local git hash from .build_info.
"""

import asyncio
import logging
from pathlib import Path

import httpx

from user_container.config import settings

logger = logging.getLogger(__name__)

GITHUB_LATEST_URL = "https://api.github.com/repos/bokamix/zeno-blue/releases/latest"
CHECK_INTERVAL = 3600  # 1 hour

# Module-level state
_can_update = False
_update_version: str | None = None


def get_update_status() -> dict:
    return {
        "can_update": _can_update,
        "update_version": _update_version,
    }


def _read_local_hash() -> str:
    """Read GIT_HASH directly from .build_info on disk.

    This bypasses settings (which may be frozen to the Docker ENV var baked
    at image build time) so that an in-place update that writes a new
    .build_info is immediately reflected on the next version check.
    """
    build_info_path = Path.home() / ".zeno" / "app" / ".build_info"
    if build_info_path.is_file():
        for line in build_info_path.read_text().splitlines():
            if line.startswith("GIT_HASH="):
                return line.partition("=")[2].strip()
    # Fall back to the value frozen into settings (env var or startup .build_info)
    return settings.git_hash


async def _check_for_update():
    global _can_update, _update_version

    local_hash = _read_local_hash()
    if local_hash in ("unknown", ""):
        return

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                GITHUB_LATEST_URL,
                headers={"Accept": "application/vnd.github+json"},
            )
            if resp.status_code != 200:
                logger.debug(f"[VersionCheck] GitHub API returned {resp.status_code}")
                return

            data = resp.json()
            tag = data.get("tag_name", "")

            # Tag format: build-{full_sha}
            remote_hash = tag.removeprefix("build-")[:7] if tag.startswith("build-") else ""

            if not remote_hash:
                logger.debug(f"[VersionCheck] Unexpected tag format: {tag}")
                return

            if remote_hash != local_hash[:7]:
                _can_update = True
                _update_version = remote_hash
                logger.info(f"[VersionCheck] Update available: local={local_hash} remote={remote_hash}")
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
