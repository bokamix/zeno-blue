"""Security module - centralized security functions and constants."""

import json
import os
from pathlib import Path
from typing import Dict, Optional, Set

from user_container.platform import HAS_SANDBOX_USER


# SINGLE SOURCE OF TRUTH: Safe env vars that user processes can have
# Everything NOT in this list is considered sensitive and goes to secrets.json
SAFE_ENV_WHITELIST: Set[str] = {
    'PATH', 'HOME', 'USER', 'LANG', 'LC_ALL',
    'TERM', 'TMPDIR', 'NODE_PATH', 'PYTHONPATH',
    'BASE_URL', 'WORKSPACE_DIR', 'DATA_DIR',
    'APP_PORT_MIN', 'APP_PORT_MAX',
    'LOG_LEVEL', 'PYTHONUNBUFFERED',
    'PLAYWRIGHT_BROWSERS_PATH',
    # App-specific env vars for Skill API
    'SKILL_API_TOKEN', 'SKILL_API_URL', 'APP_ID',
}

# Path to secrets file (created at startup)
SECRETS_FILE = Path.home() / ".zeno" / "secrets.json"


def get_safe_env() -> Dict[str, str]:
    """
    Get a filtered environment dict safe for user code.
    Uses whitelist approach - only explicitly allowed variables.

    Note: HOME is overridden to /home/sandbox in Docker because:
    - Main process runs as root with HOME=/root
    - User commands are demoted to sandbox user (uid 1000)
    - Tools like uv need writable HOME for cache (~/.cache/uv)
    On native (macOS/Windows), HOME is preserved from the environment.
    """
    env = {k: v for k, v in os.environ.items() if k in SAFE_ENV_WHITELIST}
    if HAS_SANDBOX_USER:
        # Override HOME for sandbox user - they can't write to /root
        env['HOME'] = '/home/sandbox'
    # Otherwise keep HOME from os.environ (already in SAFE_ENV_WHITELIST)
    return env


def get_secret(key: str) -> Optional[str]:
    """
    Read a secret from the protected secrets file.
    For use by trusted skills that need API keys.

    Args:
        key: Secret key name (e.g., 'anthropic_api_key' or 'ANTHROPIC_API_KEY')

    Returns:
        Secret value or None if not found
    """
    key_lower = key.lower()

    # Try secrets file first
    if SECRETS_FILE.exists():
        try:
            with open(SECRETS_FILE) as f:
                secrets = json.load(f)
            if key_lower in secrets:
                return secrets[key_lower]
        except Exception:
            pass

    # Fallback to environment variable (for development)
    return os.getenv(key.upper())


def init_secrets_file() -> None:
    """
    Create secrets file from environment variables at startup.
    Should be called once when container starts.

    Uses whitelist approach: everything NOT in SAFE_ENV_WHITELIST goes to secrets.
    This means you don't have to remember to add new secrets to a blacklist.
    """
    secrets = {}

    # Copy all env vars that are NOT in the safe whitelist
    for key, val in os.environ.items():
        if key not in SAFE_ENV_WHITELIST and val:
            secrets[key.lower()] = val

    # Write secrets file
    try:
        with open(SECRETS_FILE, "w") as f:
            json.dump(secrets, f, indent=2)
        # Make readable only by owner (600 permissions)
        os.chmod(SECRETS_FILE, 0o600)
    except Exception as e:
        print(f"Warning: Could not create secrets file: {e}")
