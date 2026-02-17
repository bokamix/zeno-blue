"""Shell tool - run commands in the sandbox."""

import os
import re
from typing import Any, Dict
import shlex

from user_container.config import settings
from user_container.db.db import DB
from user_container.runner.runner import Runner
from user_container.tools.registry import ToolSchema, make_parameters
from user_container.security import get_safe_env
from user_container.platform import get_shell_command


# Truncation config
MAX_SHELL_OUTPUT = 2000  # chars

# Detect shell metacharacters that could be used to chain commands
SHELL_METACHARACTERS = re.compile(r'[;&|`$()]|&&|\|\|')

# Blocked path patterns - agent cannot access these
# NOTE: /app/ is blocked EXCEPT /app/user_container/skills/ (for skill execution)
BLOCKED_PATH_PATTERNS = [
    '/etc/passwd',
    '/etc/shadow',
    '/proc/',
    '/.env',
]

# Whitelist for app directory - only skills directory is allowed
# Dynamic: derived from settings.skills_dir so it works in Docker (/app/) and native (~/.zeno/app/)
APP_WHITELIST_PREFIXES = [
    os.path.realpath(settings.skills_dir) + "/",
]
# App root prefix for path security checks (e.g., /app/ in Docker)
_APP_ROOT = os.path.realpath(os.path.dirname(os.path.dirname(settings.skills_dir))) + "/"


def _is_app_path_allowed(path: str) -> bool:
    """Check if /app/ path is in whitelist (only skills allowed)."""
    for prefix in APP_WHITELIST_PREFIXES:
        if path.startswith(prefix):
            return True
    return False

# Dangerous commands/patterns that could cause DoS (CPU/RAM exhaustion)
DANGEROUS_COMMAND_PATTERNS = [
    re.compile(r'^\s*yes\b'),                    # yes command (CPU exhaustion)
    re.compile(r'^\s*yes\s*\|'),                 # yes piped to something
    re.compile(r'\|\s*yes\b'),                   # something piped to yes
    re.compile(r':\(\)\s*\{'),                   # Fork bomb pattern :(){ :|:& };:
    re.compile(r'while\s+(true|:)\s*;?\s*do'),   # Infinite loop: while true; do
    re.compile(r'while\s+\[\[?\s*1\s*\]'),       # while [ 1 ] or while [[ 1 ]]
    re.compile(r'for\s*\(\(\s*;\s*;\s*\)\)'),    # Infinite for loop: for ((;;))
    re.compile(r'/dev/zero'),                    # /dev/zero (memory/disk exhaustion)
    re.compile(r'/dev/urandom.*\|\s*cat'),       # /dev/urandom piped (CPU exhaustion)
    re.compile(r'cat\s+/dev/urandom'),           # cat /dev/urandom
    re.compile(r'dd\s+if=/dev/(zero|urandom)'),  # dd from /dev/zero or /dev/urandom
    re.compile(r'\&\s*$'),                       # Background process (&) at end
    re.compile(r'nohup\s+.*\s+&'),               # nohup with background
    re.compile(r'disown'),                       # disown (detach process)
    re.compile(r'setsid'),                       # setsid (new session)
    # Persistent sessions and network tools
    re.compile(r'(?<!-)\bscreen\b'),              # screen (persistent session) - allows h-screen CSS
    re.compile(r'\btmux\b'),                     # tmux (persistent session)
    re.compile(r'\bnc\s+-l'),                    # netcat listener
    re.compile(r'\bsocat\b'),                    # socat (socket relay)
    # Symlink attacks
    re.compile(r'\bln\s+-s'),                    # ln -s (symlink)
    re.compile(r'\bln\s+.*-s'),                  # ln ... -s (symlink with flags)
]


def normalize_command(cmd: str) -> str:
    """
    Normalize command for security check.
    Collapses whitespace and removes control characters to prevent bypass tricks.
    """
    # Collapse all whitespace (tabs, newlines, multiple spaces) to single space
    cmd = re.sub(r'\s+', ' ', cmd)
    # Remove null bytes and control characters (except space)
    cmd = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', cmd)
    return cmd.lower().strip()


def extract_script_path(cmd: str) -> str | None:
    """
    Extract the script path from commands like:
    - uv run script.py
    - uv run /path/to/script.py args
    - uv run --quiet script.py
    - python script.py
    - python3 -u /path/to/script.py

    Returns the script path or None if not a recognized Python command.
    """
    try:
        parts = shlex.split(cmd)
    except ValueError:
        return None

    i = 0
    while i < len(parts):
        # Handle: uv run [options] script.py [args]
        if parts[i] == 'uv' and i + 1 < len(parts) and parts[i + 1] == 'run':
            i += 2  # Skip 'uv run'
            # Skip options (--flag or --flag value)
            while i < len(parts) and parts[i].startswith('-'):
                i += 1
                # If next part doesn't start with - and isn't a .py, it's a flag value
                if i < len(parts) and not parts[i].startswith('-') and not parts[i].endswith('.py'):
                    i += 1
            # Now we should be at the script
            if i < len(parts) and (parts[i].endswith('.py') or '/' in parts[i]):
                return parts[i]
            return None

        # Handle: python/python3 [options] script.py [args]
        elif parts[i] in ('python', 'python3'):
            i += 1
            # Skip python options (-u, -c, etc.)
            while i < len(parts) and parts[i].startswith('-'):
                # -c means inline code, not a script file
                if parts[i] == '-c':
                    return None
                i += 1
            if i < len(parts) and (parts[i].endswith('.py') or '/' in parts[i]):
                return parts[i]
            return None

        i += 1

    return None


def resolve_script_path(script_path: str, cwd: str) -> str | None:
    """
    Resolve script path to absolute, normalized form.

    Handles:
    - Absolute paths: /app/user_container/skills/image/scripts/analyze.py
    - Relative paths: scripts/analyze.py (resolved against cwd)
    - Path traversal: ../../../workspace/evil.py (normalized away)
    - Symlinks: resolved to real path

    Returns resolved absolute path, or None on error.
    """
    if not script_path:
        return None

    if os.path.isabs(script_path):
        # Absolute path - just normalize
        resolved = os.path.normpath(script_path)
    else:
        # Relative path - join with cwd first
        resolved = os.path.normpath(os.path.join(cwd, script_path))

    # Resolve symlinks (prevents symlink-based escapes)
    try:
        resolved = os.path.realpath(resolved)
    except (OSError, ValueError):
        return None

    return resolved


def is_clean_skill_command(cmd: str, cwd: str = "") -> bool:
    """
    Check if command is a legitimate skill invocation.

    SECURITY: Extracts and resolves the actual script path, then verifies
    it's within /app/user_container/skills/. This prevents:
    - Fake skills directories (/workspace/skills/evil.py)
    - Path traversal (../../workspace/evil.py)
    - Symlink attacks (resolved by realpath)
    - Command chaining (blocked by metacharacter check in command part)

    Metacharacters in quoted arguments (after script path) are allowed,
    since they are not interpreted by shell when properly quoted.
    """
    REAL_SKILLS_PATH = os.path.realpath(settings.skills_dir) + "/"

    # Parse command with shlex to handle quotes properly
    # This will raise ValueError if quotes are unbalanced (escape attempt)
    try:
        parts = shlex.split(cmd)
    except ValueError:
        return False

    if not parts:
        return False

    # Find the script path index
    script_idx = None
    for i, part in enumerate(parts):
        if part.endswith('.py'):
            script_idx = i
            break

    if script_idx is None:
        return False

    # Check metacharacters only in command part (tokens before and including script)
    # This allows: uv run script.py "password with & or $ or ()"
    # But blocks: uv run script.py && evil_command (because && would be a separate token)
    command_tokens = parts[:script_idx + 1]
    for token in command_tokens:
        if SHELL_METACHARACTERS.search(token):
            return False

    # Extract script path from command
    script_path = extract_script_path(cmd)
    if not script_path:
        return False

    # Resolve to absolute path (handles relative paths, .., symlinks)
    cwd = cwd or settings.workspace_dir
    resolved = resolve_script_path(script_path, cwd)
    if not resolved:
        return False

    # Final check: is the resolved script inside the real skills directory?
    return resolved.startswith(REAL_SKILLS_PATH)


def _extract_skill_id(cmd: str, cwd: str = "") -> str | None:
    """Extract the custom skill ID from a skill command path.

    Looks for pattern _custom/{skill_id}/scripts/ in the resolved script path.
    Returns skill_id or None if not a custom skill command.
    """
    script_path = extract_script_path(cmd)
    if not script_path:
        return None
    resolved = resolve_script_path(script_path, cwd or settings.workspace_dir)
    if not resolved:
        return None
    match = re.search(r'_custom/([^/]+)/scripts/', resolved)
    return match.group(1) if match else None


def get_env_for_command(cmd: str, cwd: str = "") -> dict:
    """Return appropriate env vars based on command type.

    Both skills and regular commands get the same safe environment.
    Skills read API keys from /app/secrets.json, not environment variables.
    """
    # All commands get the safe environment (no secrets)
    # Skills access API keys via /app/secrets.json file
    return get_safe_env()


def validate_command(cmd: str, cwd: str) -> None:
    """Validate command doesn't access blocked paths or use dangerous patterns.

    Raises PermissionError if command tries to access sensitive paths
    or uses patterns that could cause DoS (CPU/RAM exhaustion).
    """
    # Check blocked paths
    for pattern in BLOCKED_PATH_PATTERNS:
        if pattern in cmd or pattern in cwd:
            raise PermissionError(f"Access to {pattern} is not allowed")

    # Check app directory paths - only skills directory is allowed
    # Extract paths that start with the app root (e.g., /app/ in Docker, native path otherwise)
    app_root = _APP_ROOT
    escaped_root = re.escape(app_root)
    app_paths = re.findall(escaped_root + r'[^\s\'";&|]*', cmd)
    skills_prefix = os.path.realpath(settings.skills_dir) + "/"
    for path in app_paths:
        if not _is_app_path_allowed(path):
            raise PermissionError(
                f"Access to {path} is not allowed - only {skills_prefix} is accessible"
            )

    # Also check cwd
    if cwd and cwd.startswith(app_root) and not _is_app_path_allowed(cwd):
        raise PermissionError(
            f"Working directory {cwd} is not allowed - only {skills_prefix} is accessible"
        )

    # Normalize command to prevent whitespace/encoding bypass tricks
    normalized = normalize_command(cmd)

    # Check dangerous command patterns (DoS prevention)
    for pattern in DANGEROUS_COMMAND_PATTERNS:
        if pattern.search(normalized):
            raise PermissionError(
                f"Command blocked for security reasons (potential system overload). "
                f"Pattern matched: {pattern.pattern}"
            )


def truncate_shell_output(output: str, max_chars: int = MAX_SHELL_OUTPUT) -> str:
    """
    Truncate shell output intelligently.
    Keeps beginning and end to preserve errors which often appear at the end.
    """
    if not output or len(output) <= max_chars:
        return output

    # Keep first half and last half
    half = max_chars // 2
    truncated_count = len(output) - max_chars
    return (
        output[:half] +
        f"\n\n... [{truncated_count} characters truncated] ...\n\n" +
        output[-half:]
    )


SHELL_SCHEMA = ToolSchema(
    name="shell",
    description="""Execute shell commands in the sandbox environment.

USE FOR:
- Running Python scripts: `uv run script.py` (with PEP 723 dependencies)
- System commands: `ls`, `mkdir`, `cp`, `mv`, `rm`
- Archive operations: `unzip`, `tar`, `gzip`
- Quick data checks: `wc -l`, `du -sh`

DO NOT USE FOR:
- Reading files → use `read_file` instead (faster, no subprocess)
- Writing files → use `write_file` instead
- Searching text → use `search_in_files` instead
- Fetching URLs → use `web_fetch` instead

Commands run in workspace directory by default. Timeout: 30s.""",
    parameters=make_parameters({
        "cmd": {
            "type": "string",
            "description": "Command to run, e.g. `ls -la` or `python -V`.",
        },
        "cwd": {
            "type": ["string", "null"],
            "description": f"Working directory (defaults to {settings.workspace_dir}).",
        },
        "timeout_s": {
            "type": ["integer", "null"],
            "description": "Timeout in seconds (defaults to 120).",
        },
    }),
)

SHELL_DEFAULTS = {
    "cwd": settings.workspace_dir,
    "timeout_s": 120,  # Wall clock timeout (CPU limit is separate in runner.py)
}


def make_shell_tool(runner: Runner, db: DB):
    """Create the shell tool handler."""

    def shell(args: Dict[str, Any]) -> Dict[str, Any]:
        raw_cmd = args.get("cmd")

        # If string, wrap in bash -c to support pipes, &&, || etc.
        if isinstance(raw_cmd, str):
            cmd = get_shell_command(raw_cmd.strip())
        elif isinstance(raw_cmd, list):
            cmd = raw_cmd
        else:
            raise ValueError("shell.cmd must be a list or string")

        cwd = args.get("cwd", settings.workspace_dir)
        timeout_s = int(args.get("timeout_s", SHELL_DEFAULTS["timeout_s"]))

        # Security: validate command doesn't access blocked paths
        cmd_str = raw_cmd if isinstance(raw_cmd, str) else " ".join(cmd)
        validate_command(cmd_str, cwd)

        # Security: select appropriate env vars
        env = get_env_for_command(cmd_str, cwd)

        # Security: skills run as root (need secrets.json), user commands run as sandbox
        is_skill = is_clean_skill_command(cmd_str, cwd)
        demote_to_sandbox = not is_skill

        # Inject per-skill secrets as env vars when running skill commands
        if is_skill:
            skill_id = _extract_skill_id(cmd_str, cwd)
            if skill_id:
                secrets = db.get_skill_secrets(skill_id)
                if secrets:
                    env = {**env, **secrets}

        res = runner.run(cmd=cmd, cwd=cwd, timeout_s=timeout_s, env=env, demote=demote_to_sandbox)

        # Log original command if it was wrapped
        cmd_str = raw_cmd if isinstance(raw_cmd, str) else " ".join(res.cmd)

        db.execute(
            "INSERT INTO runs(cmd,cwd,code,stdout,stderr,started_at,finished_at) VALUES (?,?,?,?,?,?,?)",
            (cmd_str, res.cwd, res.code, res.stdout, res.stderr, res.started_at, res.finished_at),
        )

        # Truncate outputs to save tokens
        stdout = truncate_shell_output(res.stdout)
        stderr = truncate_shell_output(res.stderr)

        return {
            "code": res.code,
            "stdout": stdout,
            "stderr": stderr,
        }

    return shell
