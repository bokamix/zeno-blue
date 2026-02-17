"""File operation tools - read, write, list files in workspace."""

import os
import time
from typing import Any, Dict

from user_container.config import settings
from user_container.tools.registry import ToolSchema, make_parameters


# Truncation config
MAX_FILE_LINES = 500  # lines per read
MAX_DIR_ENTRIES = 100  # entries per list

# Security: Whitelist for app directory - only these patterns are allowed
# Everything else in the app directory is blocked (agent code, prompts, configs, secrets)
# Dynamic: derived from settings.skills_dir so it works in Docker and native
import fnmatch

_SKILLS_DIR_REAL = os.path.realpath(settings.skills_dir)
ALLOWED_APP_PATTERNS = [
    # Markdown documentation in skills
    f'{_SKILLS_DIR_REAL}/*/*.md',
    f'{_SKILLS_DIR_REAL}/*/*/*.md',
    f'{_SKILLS_DIR_REAL}/*/*/*/*.md',
    # Scripts in skills
    f'{_SKILLS_DIR_REAL}/*/scripts/*',
    f'{_SKILLS_DIR_REAL}/*/*/scripts/*',
    f'{_SKILLS_DIR_REAL}/*/scripts/*/*',  # nested in scripts
]
# App root prefix for security checks
_APP_ROOT = os.path.realpath(os.path.dirname(os.path.dirname(settings.skills_dir))) + "/"


def _is_allowed_app_path(abs_path: str) -> bool:
    """Check if path matches whitelist for /app/ access."""
    for pattern in ALLOWED_APP_PATTERNS:
        if fnmatch.fnmatch(abs_path, pattern):
            return True
    return False

# Security: Size limits
MAX_WRITE_SIZE = 25 * 1024 * 1024  # 25MB max per write
MAX_WORKSPACE_SIZE = 500 * 1024 * 1024  # 500MB total workspace quota

# Cache for workspace size (to avoid slow recalculation on every write)
_workspace_size_cache = {'size': 0, 'time': 0}
CACHE_TTL = 10  # seconds


# --- Schemas ---

WRITE_FILE_SCHEMA = ToolSchema(
    name="write_file",
    description="Write a text file under /workspace. Overwrites existing content. Limits: 25MB per file, 500MB total workspace.",
    parameters=make_parameters({
        "path": {
            "type": "string",
            "description": "Path relative to /workspace.",
        },
        "content": {
            "type": "string",
            "description": "Full file content to write.",
        },
    }),
)

READ_FILE_SCHEMA = ToolSchema(
    name="read_file",
    description="Read a text file from /workspace (user files). For large files, use offset/limit for pagination.",
    parameters=make_parameters({
        "path": {
            "type": "string",
            "description": "File path relative to /workspace.",
        },
        "offset": {
            "type": ["integer", "null"],
            "description": "Line number to start from (0-indexed). Default: 0.",
        },
        "limit": {
            "type": ["integer", "null"],
            "description": f"Max lines to return. Default: {MAX_FILE_LINES}.",
        },
    }),
)

READ_FILE_DEFAULTS = {
    "offset": 0,
    "limit": MAX_FILE_LINES,
}

LIST_DIR_SCHEMA = ToolSchema(
    name="list_dir",
    description="List directory entries under /workspace to understand the project layout.",
    parameters=make_parameters({
        "path": {
            "type": ["string", "null"],
            "description": "Relative path to list. Null/empty lists /workspace root.",
        },
    }),
)

LIST_DIR_DEFAULTS = {
    "path": "",
}

EDIT_FILE_SCHEMA = ToolSchema(
    name="edit_file",
    description="Edit a text file by replacing exact text (find-and-replace). Use read_file first to see current content with line numbers.",
    parameters=make_parameters({
        "path": {
            "type": "string",
            "description": "Path relative to /workspace.",
        },
        "old_string": {
            "type": "string",
            "description": "Exact text to find and replace. Must match file content exactly (including whitespace/indentation).",
        },
        "new_string": {
            "type": "string",
            "description": "New text to replace with. Use empty string to delete the old_string.",
        },
        "replace_all": {
            "type": ["boolean", "null"],
            "description": "If true, replace ALL occurrences. Default: false (fails if old_string not unique).",
        },
    }),
)

EDIT_FILE_DEFAULTS = {
    "replace_all": False,
}


# --- Helpers ---

def _safe_join(base: str, rel: str) -> str:
    """
    Safely join paths, preventing directory traversal and symlink attacks.
    Uses realpath to resolve symlinks and ensure the final path is within base.
    """
    rel = (rel or "").lstrip("/").replace("..", "")

    # Strip "workspace/" prefix if present (agent might pass "/workspace/foo" as path)
    # This prevents /workspace/workspace/foo double-nesting
    if rel.startswith("workspace/"):
        rel = rel[len("workspace/"):]

    p = os.path.abspath(os.path.join(base, rel))

    # Resolve symlinks to get the real path
    real_path = os.path.realpath(p)
    base_real = os.path.realpath(base)

    # Check that resolved path is still within base directory
    if not real_path.startswith(base_real + os.sep) and real_path != base_real:
        raise PermissionError("Path escape blocked (symlink or traversal)")

    return real_path


def _get_workspace_size() -> int:
    """
    Calculate total size of workspace directory with caching.
    Uses a TTL cache to avoid slow recalculation on every write.
    """
    now = time.time()

    # Return cached value if still valid
    if now - _workspace_size_cache['time'] < CACHE_TTL:
        return _workspace_size_cache['size']

    # Calculate fresh value
    total_size = 0
    workspace = settings.workspace_dir
    for dirpath, dirnames, filenames in os.walk(workspace):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total_size += os.path.getsize(fp)
            except (OSError, IOError):
                pass

    # Update cache
    _workspace_size_cache['size'] = total_size
    _workspace_size_cache['time'] = now

    return total_size


def _check_workspace_quota(additional_bytes: int = 0) -> None:
    """Check if workspace would exceed quota after writing additional bytes."""
    current_size = _get_workspace_size()
    if current_size + additional_bytes > MAX_WORKSPACE_SIZE:
        used_mb = current_size // (1024 * 1024)
        max_mb = MAX_WORKSPACE_SIZE // (1024 * 1024)
        raise ValueError(
            f"Workspace quota exceeded: {used_mb}MB used, max {max_mb}MB. "
            "Delete some files first."
        )


# --- Tool Handlers ---

def write_file(args: Dict[str, Any]) -> Dict[str, Any]:
    """Write text file to /workspace."""
    path = args.get("path")
    content = args.get("content")

    if not path:
        raise ValueError("path required")

    if content is None:
        raise ValueError(
            "content required - cannot write file without content. "
            "If you intended to include content but it's missing, this may be caused by "
            "response truncation (max_tokens reached). Try: "
            "1) Split into smaller files, "
            "2) Build incrementally using edit_file, "
            "3) Generate shorter/simpler content first."
        )

    # Security: Check content size
    content_size = len(content.encode('utf-8'))
    if content_size > MAX_WRITE_SIZE:
        max_mb = MAX_WRITE_SIZE // (1024 * 1024)
        raise ValueError(
            f"Content too large: {content_size} bytes (max {max_mb}MB). "
            "Split into smaller files."
        )

    # Security: Check workspace quota
    _check_workspace_quota(content_size)

    abs_path = _safe_join(settings.workspace_dir, path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(content)
    return {"ok": True, "path": path}


def read_file(args: Dict[str, Any]) -> Dict[str, Any]:
    """Read text file from /workspace or /app with pagination support."""
    path = args.get("path")
    if not path:
        raise ValueError("path required")

    offset = int(args.get("offset") or 0)
    limit = int(args.get("limit") or MAX_FILE_LINES)

    # Allow reading app directory paths - WHITELIST ONLY (skills documentation)
    if path.startswith(_APP_ROOT) or path.startswith(_SKILLS_DIR_REAL):
        abs_path = os.path.realpath(path)
        # Security: ensure it stays within app root after symlink resolution
        if not abs_path.startswith(_APP_ROOT):
            raise PermissionError("Path escape blocked")
        # Security: only allow whitelisted paths (SKILL.md files)
        if not _is_allowed_app_path(abs_path):
            raise PermissionError(
                f"Access denied: {path} - only skill documentation (SKILL.md) can be read from app directory"
            )
    else:
        abs_path = _safe_join(settings.workspace_dir, path)
    with open(abs_path, "r", encoding="utf-8") as f:
        all_lines = f.readlines()

    total_lines = len(all_lines)
    selected_lines = all_lines[offset:offset + limit]
    lines_returned = len(selected_lines)

    # Format with line numbers (like cat -n) for easier code navigation
    numbered_lines = []
    for i, line in enumerate(selected_lines, start=offset + 1):
        # Ensure line ends with newline for consistent formatting
        line_text = line if line.endswith('\n') else line + '\n'
        numbered_lines.append(f"{i:6d}\t{line_text}")
    content = "".join(numbered_lines)

    result = {
        "path": path,
        "content": content,
        "total_lines": total_lines,
    }

    # Add truncation info if file is larger than returned
    if total_lines > offset + lines_returned:
        result["truncated"] = True
        result["showing"] = f"lines {offset}-{offset + lines_returned - 1} of {total_lines}"
        result["hint"] = f"Use offset={offset + limit} to read more"
    else:
        result["truncated"] = False

    return result


def list_dir(args: Dict[str, Any]) -> Dict[str, Any]:
    """List directory under /workspace with truncation."""
    path = args.get("path", "")
    abs_path = _safe_join(settings.workspace_dir, path)
    if not os.path.isdir(abs_path):
        raise ValueError("Not a directory")

    entries = sorted(os.listdir(abs_path))
    total = len(entries)

    result = {"path": path}

    if total > MAX_DIR_ENTRIES:
        result["entries"] = entries[:MAX_DIR_ENTRIES]
        result["truncated"] = True
        result["total"] = total
        result["showing"] = MAX_DIR_ENTRIES
        result["hint"] = f"Directory has {total} entries. Use shell 'ls' with grep to filter."
    else:
        result["entries"] = entries
        result["truncated"] = False
        result["total"] = total

    return result


def edit_file(args: Dict[str, Any]) -> Dict[str, Any]:
    """Edit text file using find-and-replace."""
    path = args.get("path")
    old_string = args.get("old_string")
    new_string = args.get("new_string")
    replace_all = args.get("replace_all", False)

    # Validation
    if not path:
        raise ValueError("path required")
    if old_string is None:
        raise ValueError("old_string required")
    if new_string is None:
        raise ValueError("new_string required")
    if old_string == new_string:
        raise ValueError("old_string and new_string must be different")
    if not old_string:
        raise ValueError("old_string cannot be empty")

    abs_path = _safe_join(settings.workspace_dir, path)

    # File must exist for edit
    if not os.path.isfile(abs_path):
        raise ValueError(f"File not found: {path}")

    # Read current content
    with open(abs_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check occurrences
    count = content.count(old_string)
    if count == 0:
        raise ValueError(
            f"old_string not found in file. Make sure it matches exactly "
            "(including whitespace and indentation)."
        )
    if count > 1 and not replace_all:
        raise ValueError(
            f"old_string found {count} times. Either provide more context to make it unique, "
            "or set replace_all=true to replace all occurrences."
        )

    # Perform replacement
    if replace_all:
        new_content = content.replace(old_string, new_string)
        replacements = count
    else:
        new_content = content.replace(old_string, new_string, 1)
        replacements = 1

    # Security: Check size
    content_size = len(new_content.encode('utf-8'))
    if content_size > MAX_WRITE_SIZE:
        max_mb = MAX_WRITE_SIZE // (1024 * 1024)
        raise ValueError(f"Result too large: {content_size} bytes (max {max_mb}MB)")

    # Check quota (only count the difference)
    size_diff = content_size - len(content.encode('utf-8'))
    if size_diff > 0:
        _check_workspace_quota(size_diff)

    # Write back
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    # Invalidate workspace size cache since we modified a file
    _workspace_size_cache['time'] = 0

    return {
        "ok": True,
        "path": path,
        "replacements": replacements,
    }
