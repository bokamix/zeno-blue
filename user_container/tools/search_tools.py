"""Search tools - search in files and read file ranges."""

import os
from pathlib import Path
from typing import Any, Dict, List

from user_container.config import settings
from user_container.tools.registry import ToolSchema, make_parameters


# --- Schemas ---

SEARCH_IN_FILES_SCHEMA = ToolSchema(
    name="search_in_files",
    description="""Fast EXACT TEXT search across workspace files (like grep/ripgrep).

USE FOR:
- Finding specific text/phrases in files
- Locating where something is defined or used
- Finding error messages or specific strings

Returns file paths + line numbers + matching snippets. Fast and efficient.""",
    parameters=make_parameters({
        "query": {
            "type": "string",
            "description": "Exact text to search for.",
        },
        "glob": {
            "type": ["string", "null"],
            "description": "File pattern, e.g. '**/*.py' or '*'.",
        },
        "max_results": {
            "type": ["integer", "null"],
            "description": "Maximum number of results (default 50).",
        },
        "case_sensitive": {
            "type": ["boolean", "null"],
            "description": "Case sensitive search (default false).",
        },
        "max_file_bytes": {
            "type": ["integer", "null"],
            "description": "Skip files larger than this (default 512000).",
        },
    }),
)

SEARCH_IN_FILES_DEFAULTS = {
    "glob": "*",
    "max_results": 50,
    "case_sensitive": False,
    "max_file_bytes": 512_000,
}

READ_FILE_RANGE_SCHEMA = ToolSchema(
    name="read_file_range",
    description="Read a specific line range from a file under /workspace.",
    parameters=make_parameters({
        "path": {
            "type": "string",
            "description": "Path relative to /workspace.",
        },
        "start_line": {
            "type": "integer",
            "description": "First line to read (1-based).",
        },
        "end_line": {
            "type": "integer",
            "description": "Last line to read (inclusive).",
        },
        "max_chars": {
            "type": ["integer", "null"],
            "description": "Maximum characters to return (default 20000).",
        },
    }),
)

READ_FILE_RANGE_DEFAULTS = {
    "max_chars": 20_000,
}


# --- Helpers ---

_MAX_FILE_BYTES_DEFAULT = 512_000


def _safe_join(base: str, rel: str) -> str:
    """Safely join paths, preventing directory traversal attacks."""
    rel = (rel or "").lstrip("/").replace("..", "")
    p = os.path.abspath(os.path.join(base, rel))
    base_abs = os.path.abspath(base)
    if not (p == base_abs or p.startswith(base_abs + os.sep)):
        raise PermissionError("Path escape blocked")
    return p


def _iter_files(base_dir: str, glob_pattern: str) -> List[str]:
    """Iterate files matching a glob pattern."""
    files: List[str] = []
    for root, _, filenames in os.walk(base_dir):
        for name in filenames:
            abs_path = os.path.join(root, name)
            rel_path = os.path.relpath(abs_path, base_dir)
            if glob_pattern and not Path(rel_path).match(glob_pattern):
                continue
            files.append(abs_path)
    return files


# --- Tool Handlers ---

def search_in_files(args: Dict[str, Any]) -> Dict[str, Any]:
    """Search text occurrences across /workspace."""
    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query is required")

    glob_pattern = args.get("glob", "*")
    max_results = int(args.get("max_results", 50))
    case_sensitive = bool(args.get("case_sensitive", False))
    max_file_bytes = int(args.get("max_file_bytes", _MAX_FILE_BYTES_DEFAULT))

    base = settings.workspace_dir
    q = query if case_sensitive else query.lower()

    matches: List[Dict[str, Any]] = []
    scanned_files = 0
    skipped_files = 0

    for abs_path in _iter_files(base, glob_pattern):
        if len(matches) >= max_results:
            break

        try:
            st = os.stat(abs_path)
            if st.st_size > max_file_bytes:
                skipped_files += 1
                continue
        except OSError:
            skipped_files += 1
            continue

        rel_path = os.path.relpath(abs_path, base)

        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                scanned_files += 1
                for i, line in enumerate(f, start=1):
                    hay = line if case_sensitive else line.lower()
                    if q in hay:
                        matches.append({
                            "path": rel_path,
                            "line": i,
                            "snippet": line.rstrip("\n")[:500],
                        })
                        if len(matches) >= max_results:
                            break
        except Exception:
            skipped_files += 1
            continue

    return {
        "query": query,
        "glob": glob_pattern,
        "matches": matches,
        "scanned_files": scanned_files,
        "skipped_files": skipped_files,
        "truncated": len(matches) >= max_results,
    }


def read_file_range(args: Dict[str, Any]) -> Dict[str, Any]:
    """Read a line range from a file under /workspace."""
    path = args.get("path")
    if not isinstance(path, str) or not path.strip():
        raise ValueError("path is required")

    start_line = int(args.get("start_line", 1))
    end_line = int(args.get("end_line", start_line))
    if start_line < 1 or end_line < start_line:
        raise ValueError("Invalid start_line/end_line")

    max_chars = int(args.get("max_chars", 20000))
    abs_path = _safe_join(settings.workspace_dir, path)

    out_lines: List[str] = []
    total_chars = 0
    total_lines = 0

    with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
        for idx, line in enumerate(f, start=1):
            total_lines = idx
            if idx < start_line:
                continue
            if idx > end_line:
                break
            if total_chars + len(line) > max_chars:
                remaining = max_chars - total_chars
                if remaining > 0:
                    out_lines.append(line[:remaining].rstrip("\n"))
                    total_chars += remaining
                break
            out_lines.append(line.rstrip("\n"))
            total_chars += len(line)

    return {
        "path": path,
        "start_line": start_line,
        "end_line": end_line,
        "lines": out_lines,
        "total_lines_seen": total_lines,
        "truncated": total_chars >= max_chars,
    }


# --- Recall from Chat ---

RECALL_FROM_CHAT_SCHEMA = ToolSchema(
    name="recall_from_chat",
    description="""Search within the CURRENT conversation history.

USE FOR:
- Finding exact details from earlier in this conversation
- When summary mentions something but you need exact value/quote
- "What was that API key?", "What exact error did we get?"

Returns FULL MESSAGE CONTENT (not snippets) for accurate recall.
Searches ONLY current conversation (not other chats).
Simple keyword matching (case-insensitive).""",
    parameters=make_parameters({
        "query": {
            "type": "string",
            "description": "Text to search for (case-insensitive). Be specific.",
        },
        "role_filter": {
            "type": ["string", "null"],
            "description": "Filter by role: 'user', 'assistant', or null for all.",
        },
        "max_results": {
            "type": ["integer", "null"],
            "description": "Max results (default 5, max 20).",
        },
    }),
)

RECALL_FROM_CHAT_DEFAULTS = {
    "role_filter": None,
    "max_results": 5,  # Fewer results but full content
}


def make_recall_from_chat_tool(db):
    """Create recall_from_chat tool handler.

    Returns FULL message content (not snippets) for accurate recall.
    This is key for the hierarchical memory system - when agent needs
    exact details, they get the complete message.
    """

    def recall_from_chat(args: Dict[str, Any]) -> Dict[str, Any]:
        from user_container.agent.context import get_conversation_id

        query = args.get("query")
        if not query or not query.strip():
            raise ValueError("query is required")

        conversation_id = get_conversation_id()
        if not conversation_id:
            return {"error": "No conversation context", "results": []}

        role_filter = args.get("role_filter")
        max_results = max(1, min(20, int(args.get("max_results", 5))))

        # Build SQL - search for query in content
        sql = """
            SELECT id, role, content, created_at
            FROM messages
            WHERE conversation_id = ?
            AND content LIKE ?
        """
        params = [conversation_id, f"%{query}%"]

        if role_filter in ("user", "assistant", "tool"):
            sql += " AND role = ?"
            params.append(role_filter)
        else:
            # Exclude tool messages by default (they're verbose)
            sql += " AND role IN ('user', 'assistant')"

        sql += " ORDER BY id DESC LIMIT ?"
        params.append(max_results)

        rows = db.fetchall(sql, tuple(params))

        # Format results with FULL content (not snippets)
        results = []
        for row in rows:
            content = row.get("content", "") or ""

            # Truncate extremely long content (>4000 chars) but keep most
            if len(content) > 4000:
                content = content[:3500] + f"\n...[truncated {len(content) - 3500} chars]..."

            results.append({
                "message_id": row["id"],
                "role": row["role"],
                "timestamp": row["created_at"],
                "content": content,  # FULL content, not snippet
            })

        results.reverse()  # Chronological order

        return {
            "query": query,
            "conversation_id": conversation_id[:8] + "...",
            "results_count": len(results),
            "results": results
        }

    return recall_from_chat


def _extract_snippet(content: str, query: str, context_chars: int = 150) -> str:
    """Extract snippet around query match."""
    if not content:
        return ""

    idx = content.lower().find(query.lower())
    if idx == -1:
        return content[:context_chars * 2] + ("..." if len(content) > context_chars * 2 else "")

    start = max(0, idx - context_chars)
    end = min(len(content), idx + len(query) + context_chars)

    snippet = content[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(content):
        snippet = snippet + "..."

    return snippet
