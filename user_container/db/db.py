import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any, Dict, List


@dataclass
class JobActivity:
    """Single activity entry for a job."""
    id: int
    job_id: str
    timestamp: float  # time.time()
    type: str  # routing, step, llm_call, tool_call, etc.
    message: str  # short description
    detail: Optional[str]  # full content (for thinking/planning)
    tool_name: Optional[str]  # e.g., "shell", "read_file"
    is_error: bool = False

class DB:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Disable mmap to prevent Bus errors in multiprocess environment
        conn.execute("PRAGMA mmap_size=0;")
        # Wait up to 5s if database is locked by another process
        conn.execute("PRAGMA busy_timeout=5000;")
        # Use DELETE journal mode instead of WAL to avoid .shm mmap issues with fork()
        conn.execute("PRAGMA journal_mode=DELETE;")
        return conn

    def _init(self) -> None:
        with self._lock:
            conn = self._connect()
            cur = conn.cursor()
            cur.execute("""
              CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                forked_from TEXT,
                branch_number INTEGER
              )
            """)
            # Migration: add forked_from and branch_number columns if they don't exist
            try:
                cur.execute("ALTER TABLE conversations ADD COLUMN forked_from TEXT")
            except Exception:
                pass
            try:
                cur.execute("ALTER TABLE conversations ADD COLUMN branch_number INTEGER")
            except Exception:
                pass
            # Migration: add is_archived column
            try:
                cur.execute("ALTER TABLE conversations ADD COLUMN is_archived INTEGER DEFAULT 0")
            except Exception:
                pass
            # Migration: add scheduler_id and is_scheduler_run columns for scheduled job runs
            try:
                cur.execute("ALTER TABLE conversations ADD COLUMN scheduler_id TEXT")
            except Exception:
                pass
            try:
                cur.execute("ALTER TABLE conversations ADD COLUMN is_scheduler_run INTEGER DEFAULT 0")
            except Exception:
                pass
            # Migration: add read_at column for tracking unread conversations
            try:
                cur.execute("ALTER TABLE conversations ADD COLUMN read_at TEXT")
                print("[DB Migration] Added read_at column to conversations table")
            except Exception as e:
                if "duplicate column" not in str(e).lower():
                    print(f"[DB Migration] read_at column already exists or error: {e}")
            # Migration: set read_at for existing non-scheduler conversations to mark them as read
            # Use current time so last_message_at < read_at (marking all old convos as read)
            try:
                now = self.now()
                # For conversations that never had read_at set
                result = cur.execute("UPDATE conversations SET read_at = ? WHERE read_at IS NULL AND COALESCE(is_scheduler_run, 0) = 0", (now,))
                if result.rowcount > 0:
                    print(f"[DB Migration] Set read_at for {result.rowcount} existing conversations")
                # Fix bad migration: read_at = created_at but has messages after (looks wrongly unread)
                result = cur.execute("""
                    UPDATE conversations SET read_at = ?
                    WHERE read_at = created_at
                    AND COALESCE(is_scheduler_run, 0) = 0
                    AND (SELECT MAX(m.created_at) FROM messages m WHERE m.conversation_id = conversations.id) > read_at
                """, (now,))
                if result.rowcount > 0:
                    print(f"[DB Migration] Fixed read_at for {result.rowcount} conversations with stale timestamps")
            except Exception as e:
                print(f"[DB Migration] Error updating read_at values: {e}")
            # Migration: add preview column for custom conversation titles
            try:
                cur.execute("ALTER TABLE conversations ADD COLUMN preview TEXT")
                print("[DB Migration] Added preview column to conversations table")
            except Exception:
                pass  # Column already exists
            # Migration: add summary columns for hierarchical memory system
            try:
                cur.execute("ALTER TABLE conversations ADD COLUMN summary TEXT")
                print("[DB Migration] Added summary column to conversations table")
            except Exception:
                pass  # Column already exists
            try:
                cur.execute("ALTER TABLE conversations ADD COLUMN summary_up_to_message_id INTEGER")
                print("[DB Migration] Added summary_up_to_message_id column to conversations table")
            except Exception:
                pass  # Column already exists
            cur.execute("""
              CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT,
                tool_calls TEXT,
                tool_call_id TEXT,
                thinking TEXT,
                thinking_signature TEXT,
                metadata TEXT,
                internal INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
              )
            """)
            # Migration: add thinking and thinking_signature columns if they don't exist
            try:
                cur.execute("ALTER TABLE messages ADD COLUMN thinking TEXT")
            except Exception:
                pass
            try:
                cur.execute("ALTER TABLE messages ADD COLUMN thinking_signature TEXT")
            except Exception:
                pass
            # Migration: add metadata column if it doesn't exist
            try:
                cur.execute("ALTER TABLE messages ADD COLUMN metadata TEXT")
            except Exception:
                pass
            # Migration: add internal column if it doesn't exist
            try:
                cur.execute("ALTER TABLE messages ADD COLUMN internal INTEGER DEFAULT 0")
            except Exception:
                pass
            # Index for efficient unread message counting
            cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_conv_created ON messages(conversation_id, created_at)")
            cur.execute("""
              CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cmd TEXT NOT NULL,
                cwd TEXT,
                code INTEGER,
                stdout TEXT,
                stderr TEXT,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL
              )
            """)
            cur.execute("""
              CREATE TABLE IF NOT EXISTS apps (
                app_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                port INTEGER NOT NULL,
                cwd TEXT NOT NULL,
                cmd TEXT NOT NULL,
                status TEXT NOT NULL,
                api_token TEXT UNIQUE,
                created_at TEXT NOT NULL
              )
            """)
            # Migration: add api_token column if it doesn't exist
            # Note: SQLite doesn't support UNIQUE constraint in ALTER TABLE ADD COLUMN
            try:
                cur.execute("ALTER TABLE apps ADD COLUMN api_token TEXT")
            except Exception:
                pass
            cur.execute("""
              CREATE TABLE IF NOT EXISTS agent_context (
                conversation_id TEXT PRIMARY KEY,
                active_skills TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
              )
            """)
            cur.execute("""
              CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                result TEXT,
                error TEXT,
                worker_id TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
              )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_conversation ON jobs(conversation_id)")
            # Orchestrator state for checkpointing (B.5)
            cur.execute("""
              CREATE TABLE IF NOT EXISTS orchestrator_state (
                job_id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
              )
            """)
            # App state (key-value store for misc state)
            cur.execute("""
              CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
              )
            """)
            # Job activities (B.12 Activity Log)
            cur.execute("""
              CREATE TABLE IF NOT EXISTS job_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                type TEXT NOT NULL,
                message TEXT NOT NULL,
                detail TEXT,
                tool_name TEXT,
                is_error INTEGER DEFAULT 0,
                FOREIGN KEY (job_id) REFERENCES jobs(id)
              )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_job_activities_job_id ON job_activities(job_id)")
            # Scheduled Jobs (A.7 Job Scheduler)
            cur.execute("""
              CREATE TABLE IF NOT EXISTS scheduled_jobs (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                name TEXT NOT NULL,
                prompt TEXT NOT NULL,
                cron_expression TEXT NOT NULL,
                schedule_description TEXT NOT NULL,
                timezone TEXT NOT NULL DEFAULT 'Europe/Warsaw',
                is_enabled INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_run_at TEXT,
                next_run_at TEXT,
                run_count INTEGER DEFAULT 0,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
              )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_conversation ON scheduled_jobs(conversation_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_enabled ON scheduled_jobs(is_enabled)")
            # Migration: add source_conversation_id, context_json, files_dir to scheduled_jobs
            try:
                cur.execute("ALTER TABLE scheduled_jobs ADD COLUMN source_conversation_id TEXT")
            except Exception:
                pass
            try:
                cur.execute("ALTER TABLE scheduled_jobs ADD COLUMN context_json TEXT")
            except Exception:
                pass
            try:
                cur.execute("ALTER TABLE scheduled_jobs ADD COLUMN files_dir TEXT")
            except Exception:
                pass
            cur.execute("""
              CREATE TABLE IF NOT EXISTS scheduled_job_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scheduled_job_id TEXT NOT NULL,
                job_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT NOT NULL,
                result_preview TEXT,
                FOREIGN KEY (scheduled_job_id) REFERENCES scheduled_jobs(id) ON DELETE CASCADE
              )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_job_runs_job ON scheduled_job_runs(scheduled_job_id)")
            # Usage tracking (prepaid system)
            cur.execute("""
              CREATE TABLE IF NOT EXISTS usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT,
                conversation_id TEXT,
                model TEXT NOT NULL,
                provider TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL,
                completion_tokens INTEGER NOT NULL,
                cost_usd REAL NOT NULL,
                component TEXT NOT NULL,
                created_at TEXT NOT NULL
              )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_usage_log_created ON usage_log(created_at)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_usage_log_job ON usage_log(job_id)")
            # Top-ups history (audit trail)
            cur.execute("""
              CREATE TABLE IF NOT EXISTS topups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount_usd REAL NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL
              )
            """)
            # Balance cache (single row - unlimited in desktop mode)
            cur.execute("""
              CREATE TABLE IF NOT EXISTS balance (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                balance_usd REAL NOT NULL DEFAULT 999999.0,
                total_spent_usd REAL NOT NULL DEFAULT 0.0,
                total_topups_usd REAL NOT NULL DEFAULT 999999.0,
                updated_at TEXT NOT NULL
              )
            """)
            cur.execute("""
              INSERT OR IGNORE INTO balance (id, balance_usd, total_spent_usd, total_topups_usd, updated_at)
              VALUES (1, 999999.0, 0.0, 999999.0, ?)
            """, (self.now(),))
            # User settings (key-value store)
            cur.execute("""
              CREATE TABLE IF NOT EXISTS user_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
              )
            """)
            # Custom skills (user-defined skills stored in DB instead of filesystem)
            cur.execute("""
              CREATE TABLE IF NOT EXISTS custom_skills (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                instructions TEXT NOT NULL,
                required_secrets TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
              )
            """)
            # Migration: add required_secrets column if it doesn't exist
            try:
                cur.execute("ALTER TABLE custom_skills ADD COLUMN required_secrets TEXT")
            except Exception:
                pass
            conn.commit()
            conn.close()

    def execute(self, sql: str, params: tuple = ()):
        """Execute SQL and return cursor (for rowcount etc.)"""
        with self._lock:
            conn = self._connect()
            cur = conn.execute(sql, params)
            conn.commit()
            rowcount = cur.rowcount
            conn.close()
            # Return simple object with rowcount
            class Result:
                pass
            result = Result()
            result.rowcount = rowcount
            return result

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            cur = conn.execute(sql, params)
            row = cur.fetchone()
            conn.close()
            return dict(row) if row else None

    def fetchall(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            cur = conn.execute(sql, params)
            rows = cur.fetchall()
            conn.close()
            return [dict(r) for r in rows]

    @staticmethod
    def now() -> str:
        return datetime.utcnow().isoformat() + "Z"

    def get_conversation_history(
        self,
        conversation_id: str,
        only_visible: bool = False,
        limit: int = None,
        compress_old: bool = True,
        recent_exchanges: int = 5
    ) -> List[Dict[str, Any]]:
        """Get conversation history in OpenAI format with intelligent compression.

        NEW APPROACH: Instead of token budgets that cut messages and cause orphan
        tool_results, we compress old tool outputs to one-line summaries.

        Args:
            conversation_id: The conversation to load history for
            only_visible: If True, only return user-visible messages (internal=0)
            limit: If set, return only the last N messages
            compress_old: If True, compress old messages (>recent_exchanges ago)
            recent_exchanges: Number of recent user-assistant exchanges to keep full

        Returns:
            List of messages in OpenAI format
        """
        import json

        query = "SELECT id, role, content, tool_calls, tool_call_id, thinking, thinking_signature, internal FROM messages WHERE conversation_id=?"
        if only_visible:
            query += " AND internal = 0"
        query += " ORDER BY id ASC"

        rows = self.fetchall(query, (conversation_id,))

        # Apply limit (last N messages) after fetching
        if limit and len(rows) > limit:
            rows = rows[-limit:]

        if not rows:
            return []

        # Find boundary between old (compress) and new (full) messages
        if compress_old:
            boundary_idx = self._find_exchange_boundary(rows, recent_exchanges)
        else:
            boundary_idx = 0  # No compression - all messages are "new"

        # Build tool_name map for compression (tool_call_id -> tool_name)
        tool_name_map = {}
        for r in rows:
            if r["tool_calls"]:
                try:
                    for tc in json.loads(r["tool_calls"]):
                        tool_name_map[tc["id"]] = tc["function"]["name"]
                except (json.JSONDecodeError, KeyError):
                    pass

        history = []
        for i, r in enumerate(rows):
            is_old = i < boundary_idx

            msg = {"role": r["role"]}
            content = r["content"]

            if is_old:
                # OLD message - apply aggressive compression
                if r["role"] == "tool" and content:
                    tool_call_id = r.get("tool_call_id")
                    tool_name = tool_name_map.get(tool_call_id, "tool")
                    content = self._compress_tool_result(content, tool_name)

                elif r["role"] == "assistant" and r["tool_calls"]:
                    # Compress tool_calls arguments for old messages
                    try:
                        tool_calls = json.loads(r["tool_calls"])
                        tool_calls = self._compress_tool_calls(tool_calls)
                        msg["tool_calls"] = tool_calls
                    except json.JSONDecodeError:
                        pass
            else:
                # NEW message - apply light truncation only (existing logic)
                if r["role"] == "tool" and content and len(content) > 4000:
                    head = content[:1500]
                    tail = content[-1500:]
                    truncated_msg = f"\n... [truncated {len(content) - 3000} chars] ...\n"
                    content = head + truncated_msg + tail

                if r["tool_calls"] and "tool_calls" not in msg:
                    try:
                        tool_calls = json.loads(r["tool_calls"])
                        # Light truncation for new messages
                        truncated_calls = []
                        for tc in tool_calls:
                            func = tc.get("function", {})
                            args = func.get("arguments", "")
                            func_name = func.get("name", "")

                            # Only truncate very large content in new messages
                            if func_name in ("write_file", "edit_file") and len(args) > 2000:
                                try:
                                    args_dict = json.loads(args)
                                    path = args_dict.get("path", "?")
                                    file_content = args_dict.get("content", "")
                                    summary_args = {
                                        "path": path,
                                        "content": f"[FILE CONTENT: {len(file_content)} chars - see {path}]"
                                    }
                                    if "old_string" in args_dict:
                                        old_str = args_dict["old_string"]
                                        summary_args["old_string"] = old_str[:200] + "..." if len(old_str) > 200 else old_str
                                    if "new_string" in args_dict:
                                        new_str = args_dict["new_string"]
                                        summary_args["new_string"] = new_str[:200] + "..." if len(new_str) > 200 else new_str
                                    tc = {**tc, "function": {**func, "arguments": json.dumps(summary_args)}}
                                except (json.JSONDecodeError, TypeError):
                                    pass

                            elif func_name == "shell" and len(args) > 2000:
                                try:
                                    args_dict = json.loads(args)
                                    cmd = args_dict.get("cmd", "")
                                    first_line = cmd.split('\n')[0][:200]
                                    summary_args = {"cmd": f"{first_line}... [TRUNCATED: {len(cmd)} chars total]"}
                                    tc = {**tc, "function": {**func, "arguments": json.dumps(summary_args)}}
                                except (json.JSONDecodeError, TypeError):
                                    pass

                            truncated_calls.append(tc)
                        msg["tool_calls"] = truncated_calls
                    except json.JSONDecodeError:
                        pass

            if content:
                msg["content"] = content

            if r["tool_call_id"]:
                msg["tool_call_id"] = r["tool_call_id"]

            if r["thinking"]:
                if is_old:
                    # Compress thinking for old messages
                    msg["thinking"] = "[earlier reasoning]"
                else:
                    try:
                        msg["thinking"] = json.loads(r["thinking"])
                    except (json.JSONDecodeError, TypeError):
                        msg["thinking"] = r["thinking"]

            if r["thinking_signature"]:
                msg["thinking_signature"] = r["thinking_signature"]

            # Skip invalid assistant messages
            if r["role"] == "assistant":
                has_content = msg.get("content")
                has_tool_calls = msg.get("tool_calls")
                has_thinking = msg.get("thinking")
                if not has_content and not has_tool_calls and not has_thinking:
                    continue

            history.append(msg)
        return history

    def _compress_tool_result(self, content: str, tool_name: str) -> str:
        """Compress old tool result to one-line summary.

        Args:
            content: The tool result content
            tool_name: Name of the tool that produced this result

        Returns:
            Compressed summary string
        """
        if not content:
            return content

        # File operations
        if tool_name == "write_file":
            return "[File written successfully]"
        if tool_name == "read_file":
            lines = content.count('\n') + 1
            return f"[Read file: {lines} lines]"
        if tool_name == "edit_file":
            return "[File edited successfully]"
        if tool_name == "list_dir":
            lines = content.count('\n') + 1
            return f"[Listed directory: {lines} items]"

        # Shell commands
        if tool_name in ("shell", "run_script"):
            first_line = content.split('\n')[0][:60] if content else ""
            if len(content) > 60:
                return f"$ {first_line}..."
            return f"$ {first_line}" if first_line else "[Shell executed]"

        # Search/web
        if tool_name == "web_search":
            return "[Web search results]"
        if tool_name == "web_fetch":
            return "[Web page fetched]"
        if tool_name == "search_in_files":
            return "[File search results]"
        if tool_name == "recall_from_chat":
            return "[Chat recall results]"

        # Delegate task
        if tool_name == "delegate_task":
            return "[Subtask completed]"

        # Skill management
        if tool_name == "manage_skill":
            return "[Skill managed]"

        # Default: truncate to ~100 chars
        if len(content) > 100:
            return content[:80] + "..."
        return content

    def _compress_tool_calls(self, tool_calls: list) -> list:
        """Compress tool_calls arguments for old messages.

        Args:
            tool_calls: List of tool call dicts

        Returns:
            List of tool calls with compressed arguments
        """
        import json as json_mod

        compressed = []
        for tc in tool_calls:
            func = tc.get("function", {})
            name = func.get("name", "")
            args_str = func.get("arguments", "{}")

            try:
                args = json_mod.loads(args_str)
            except json_mod.JSONDecodeError:
                compressed.append(tc)
                continue

            # Compress based on tool type
            if name == "write_file":
                content_len = len(args.get("content", ""))
                args = {"path": args.get("path", "?"), "content": f"[{content_len} chars]"}

            elif name == "edit_file":
                args = {
                    "path": args.get("path", "?"),
                    "old_string": "[...]",
                    "new_string": "[...]"
                }

            elif name == "read_file":
                args = {"path": args.get("path", "?")}

            elif name == "shell":
                cmd = args.get("cmd", "")
                if len(cmd) > 50:
                    first_line = cmd.split('\n')[0][:40]
                    args = {"cmd": f"{first_line}..."}

            elif name == "web_fetch":
                args = {"url": args.get("url", "?")}

            elif name == "web_search":
                args = {"query": args.get("query", "?")}

            # Keep delegate_task info
            elif name == "delegate_task":
                args = {
                    "task": args.get("task", "?")[:50] + "..." if len(args.get("task", "")) > 50 else args.get("task", "?")
                }

            compressed.append({
                **tc,
                "function": {**func, "arguments": json_mod.dumps(args)}
            })

        return compressed

    def _find_exchange_boundary(self, rows: list, recent_exchanges: int) -> int:
        """Find index where recent exchanges start.

        An 'exchange' is a non-internal user message + all following assistant/tool
        messages until the next non-internal user message.

        Internal user messages (tool limit warnings, nudges, etc.) are NOT counted
        as exchange boundaries to prevent premature compression of actual results.

        Args:
            rows: List of message rows (must have 'role' and 'internal' keys)
            recent_exchanges: Number of exchanges to keep full

        Returns:
            Index in rows where 'old' messages end (all before this are compressed)
        """
        if not rows:
            return 0

        # Find non-internal user message indices (only real user messages define exchanges)
        user_indices = [
            i for i, r in enumerate(rows)
            if r.get("role") == "user" and not r.get("internal")
        ]

        if len(user_indices) <= recent_exchanges:
            return 0  # All messages are "new"

        # The boundary is at the Nth-from-last user message
        boundary_user_idx = user_indices[-(recent_exchanges)]
        return boundary_user_idx

    def save_message_from_dict(self, conversation_id: str, msg: Dict[str, Any], metadata: Optional[Dict] = None) -> None:
        """Save an OpenAI-format message dict to the database."""
        import json

        role = msg.get("role")
        content = msg.get("content")
        tool_calls = msg.get("tool_calls")
        tool_call_id = msg.get("tool_call_id")
        thinking = msg.get("thinking")  # Extended thinking (Anthropic)
        thinking_signature = msg.get("thinking_signature")  # Required for thinking blocks
        internal = 1 if msg.get("internal") else 0  # Internal messages (not shown to user)

        tool_calls_json = None
        if tool_calls:
            tool_calls_json = json.dumps(tool_calls)

        # Serialize thinking to JSON if it's a dict (redacted_thinking case)
        thinking_value = thinking
        if isinstance(thinking, dict):
            thinking_value = json.dumps(thinking)

        metadata_json = None
        if metadata:
            metadata_json = json.dumps(metadata)

        self.execute(
            """
            INSERT INTO messages(
                conversation_id, role, content, tool_calls, tool_call_id, thinking, thinking_signature, metadata, internal, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                role,
                content,
                tool_calls_json,
                tool_call_id,
                thinking_value,  # May be JSON string for redacted thinking
                thinking_signature,
                metadata_json,
                internal,
                self.now()
            ),
        )

    def get_active_skills(self, conversation_id: str) -> Dict[str, int]:
        """Get active skills with TTL for a conversation."""
        import json
        row = self.fetchone(
            "SELECT active_skills FROM agent_context WHERE conversation_id=?",
            (conversation_id,)
        )
        if row and row.get("active_skills"):
            try:
                return json.loads(row["active_skills"])
            except json.JSONDecodeError:
                return {}
        return {}

    def save_active_skills(self, conversation_id: str, active_skills: Dict[str, int]) -> None:
        """Save active skills with TTL for a conversation (upsert)."""
        import json
        skills_json = json.dumps(active_skills)
        self.execute(
            """
            INSERT INTO agent_context(conversation_id, active_skills, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(conversation_id) DO UPDATE SET
                active_skills = excluded.active_skills,
                updated_at = excluded.updated_at
            """,
            (conversation_id, skills_json, self.now())
        )

    def fork_conversation(self, source_conversation_id: str, up_to_message_id: int) -> Optional[str]:
        """Fork conversation up to and including specified message.

        Args:
            source_conversation_id: The conversation to fork from
            up_to_message_id: Include messages up to and including this ID

        Returns:
            New conversation ID if successful, None if source not found
        """
        import uuid

        with self._lock:
            conn = self._connect()
            try:
                # Verify source conversation exists
                cur = conn.execute(
                    "SELECT id FROM conversations WHERE id = ?",
                    (source_conversation_id,)
                )
                if not cur.fetchone():
                    return None

                # Verify message exists and belongs to conversation
                cur = conn.execute(
                    "SELECT id FROM messages WHERE id = ? AND conversation_id = ?",
                    (up_to_message_id, source_conversation_id)
                )
                if not cur.fetchone():
                    return None

                # Calculate branch number by counting chain depth (walk up the fork chain)
                branch_number = 1
                current_id = source_conversation_id
                while current_id:
                    cur = conn.execute(
                        "SELECT forked_from FROM conversations WHERE id = ?",
                        (current_id,)
                    )
                    row = cur.fetchone()
                    if row and row["forked_from"]:
                        branch_number += 1
                        current_id = row["forked_from"]
                    else:
                        break

                # Create new conversation with fork info
                new_conv_id = str(uuid.uuid4())
                now = self.now()
                conn.execute(
                    "INSERT INTO conversations(id, created_at, forked_from, branch_number, read_at) VALUES (?, ?, ?, ?, ?)",
                    (new_conv_id, now, source_conversation_id, branch_number, now)
                )

                # Copy messages up to and including message_id
                conn.execute("""
                    INSERT INTO messages(
                        conversation_id, role, content, tool_calls, tool_call_id,
                        thinking, thinking_signature, metadata, internal, created_at
                    )
                    SELECT
                        ?, role, content, tool_calls, tool_call_id,
                        thinking, thinking_signature, metadata, internal, created_at
                    FROM messages
                    WHERE conversation_id = ? AND id <= ?
                    ORDER BY id ASC
                """, (new_conv_id, source_conversation_id, up_to_message_id))

                # Copy agent_context if exists
                cur = conn.execute(
                    "SELECT active_skills FROM agent_context WHERE conversation_id = ?",
                    (source_conversation_id,)
                )
                ctx = cur.fetchone()
                if ctx:
                    conn.execute(
                        "INSERT INTO agent_context(conversation_id, active_skills, updated_at) VALUES (?, ?, ?)",
                        (new_conv_id, ctx["active_skills"], self.now())
                    )

                conn.commit()
                return new_conv_id
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all related data.

        Args:
            conversation_id: The conversation to delete

        Returns:
            True if deleted, False if conversation not found
        """
        with self._lock:
            conn = self._connect()
            try:
                # Verify conversation exists
                cur = conn.execute(
                    "SELECT id FROM conversations WHERE id = ?",
                    (conversation_id,)
                )
                if not cur.fetchone():
                    return False

                # Delete related data (messages, context, jobs, activities)
                conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
                conn.execute("DELETE FROM agent_context WHERE conversation_id = ?", (conversation_id,))
                conn.execute("DELETE FROM orchestrator_state WHERE conversation_id = ?", (conversation_id,))
                conn.execute("DELETE FROM scheduled_jobs WHERE conversation_id = ?", (conversation_id,))

                # Delete jobs and their activities
                job_ids = [r["id"] for r in conn.execute(
                    "SELECT id FROM jobs WHERE conversation_id = ?", (conversation_id,)
                ).fetchall()]
                for job_id in job_ids:
                    conn.execute("DELETE FROM job_activities WHERE job_id = ?", (job_id,))
                conn.execute("DELETE FROM jobs WHERE conversation_id = ?", (conversation_id,))

                # Delete the conversation itself
                conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))

                conn.commit()
                return True
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def delete_messages_from(self, conversation_id: str, message_id: int) -> int:
        """Delete a message and all messages after it in a conversation.

        Args:
            conversation_id: The conversation ID
            message_id: The message ID to delete from (inclusive)

        Returns:
            Number of messages deleted
        """
        with self._lock:
            conn = self._connect()
            try:
                # Get the created_at of the target message
                msg = conn.execute(
                    "SELECT created_at FROM messages WHERE id = ? AND conversation_id = ?",
                    (message_id, conversation_id)
                ).fetchone()

                if not msg:
                    return 0

                # Delete this message and all after it
                result = conn.execute(
                    "DELETE FROM messages WHERE conversation_id = ? AND created_at >= ?",
                    (conversation_id, msg["created_at"])
                )
                deleted = result.rowcount

                conn.commit()
                return deleted
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    # --- Job Methods ---

    def save_job(self, job: "Job") -> None:
        """Save or update a job in SQLite."""
        self.execute(
            """
            INSERT INTO jobs(id, conversation_id, message, status, created_at, started_at, completed_at, result, error, worker_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                started_at = excluded.started_at,
                completed_at = excluded.completed_at,
                result = excluded.result,
                error = excluded.error,
                worker_id = excluded.worker_id
            """,
            (
                job.id,
                job.conversation_id,
                job.message,
                job.status,
                job.created_at.isoformat() if job.created_at else None,
                job.started_at.isoformat() if job.started_at else None,
                job.completed_at.isoformat() if job.completed_at else None,
                job.result,
                job.error,
                job.worker_id
            )
        )

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a job by ID from SQLite."""
        return self.fetchone("SELECT * FROM jobs WHERE id = ?", (job_id,))

    def get_jobs_by_conversation(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all jobs for a conversation."""
        return self.fetchall(
            "SELECT * FROM jobs WHERE conversation_id = ? ORDER BY created_at DESC",
            (conversation_id,)
        )

    def get_jobs_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get all jobs with a given status."""
        return self.fetchall(
            "SELECT * FROM jobs WHERE status = ? ORDER BY created_at ASC",
            (status,)
        )

    # --- Job Activity Methods (B.12 Activity Log) ---

    def add_job_activity(
        self,
        job_id: str,
        activity_type: str,
        message: str,
        detail: str = None,
        tool_name: str = None,
        is_error: bool = False
    ) -> int:
        """
        Add activity entry to job.

        Args:
            job_id: The job ID
            activity_type: Type of activity (routing, step, llm_call, tool_call, etc.)
            message: Short description (displayed in log)
            detail: Full content (for thinking/planning - expandable)
            tool_name: Tool name if applicable
            is_error: Whether this is an error activity

        Returns:
            Activity ID
        """
        with self._lock:
            conn = self._connect()
            cur = conn.execute(
                """
                INSERT INTO job_activities(job_id, timestamp, type, message, detail, tool_name, is_error)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (job_id, time.time(), activity_type, message, detail, tool_name, 1 if is_error else 0)
            )
            activity_id = cur.lastrowid
            conn.commit()
            conn.close()
            return activity_id

    def get_job_activities(
        self,
        job_id: str,
        limit: int = 100,
        since_id: int = None,
        include_detail: bool = False
    ) -> List[JobActivity]:
        """
        Get activities for a job.

        Args:
            job_id: The job ID
            limit: Max number of activities to return
            since_id: Only return activities after this ID (for incremental polling)
            include_detail: If False, detail field is truncated to 200 chars

        Returns:
            List of JobActivity objects
        """
        if since_id:
            rows = self.fetchall(
                """
                SELECT id, job_id, timestamp, type, message, detail, tool_name, is_error
                FROM job_activities
                WHERE job_id = ? AND id > ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (job_id, since_id, limit)
            )
        else:
            rows = self.fetchall(
                """
                SELECT id, job_id, timestamp, type, message, detail, tool_name, is_error
                FROM job_activities
                WHERE job_id = ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (job_id, limit)
            )

        activities = []
        for row in rows:
            detail = row.get("detail")
            if detail and not include_detail and len(detail) > 200:
                detail = detail[:200] + "..."

            activities.append(JobActivity(
                id=row["id"],
                job_id=row["job_id"],
                timestamp=row["timestamp"],
                type=row["type"],
                message=row["message"],
                detail=detail,
                tool_name=row.get("tool_name"),
                is_error=bool(row.get("is_error", 0))
            ))

        return activities

    def count_conversation_delegates(self, conversation_id: str) -> int:
        """Count delegate_start activities across all jobs for a conversation.

        Uses JOIN between job_activities and jobs to count delegate_task invocations
        for the entire conversation (across all jobs).
        """
        row = self.fetchone(
            """
            SELECT COUNT(*) as count
            FROM job_activities ja
            JOIN jobs j ON ja.job_id = j.id
            WHERE j.conversation_id = ?
              AND ja.type = 'delegate_start'
            """,
            (conversation_id,)
        )
        return row["count"] if row else 0

    # --- Scheduled Job Methods (A.7 Job Scheduler) ---

    def save_scheduled_job(self, job_data: Dict[str, Any]) -> None:
        """Save or update a scheduled job (upsert)."""
        self.execute(
            """
            INSERT INTO scheduled_jobs(
                id, conversation_id, name, prompt, cron_expression, schedule_description,
                timezone, is_enabled, created_at, updated_at, last_run_at, next_run_at, run_count,
                source_conversation_id, context_json, files_dir
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                prompt = excluded.prompt,
                cron_expression = excluded.cron_expression,
                schedule_description = excluded.schedule_description,
                timezone = excluded.timezone,
                is_enabled = excluded.is_enabled,
                updated_at = excluded.updated_at,
                last_run_at = excluded.last_run_at,
                next_run_at = excluded.next_run_at,
                run_count = excluded.run_count,
                source_conversation_id = excluded.source_conversation_id,
                context_json = excluded.context_json,
                files_dir = excluded.files_dir
            """,
            (
                job_data["id"],
                job_data["conversation_id"],
                job_data["name"],
                job_data["prompt"],
                job_data["cron_expression"],
                job_data["schedule_description"],
                job_data.get("timezone", "Europe/Warsaw"),
                1 if job_data.get("is_enabled", True) else 0,
                job_data.get("created_at", self.now()),
                job_data.get("updated_at", self.now()),
                job_data.get("last_run_at"),
                job_data.get("next_run_at"),
                job_data.get("run_count", 0),
                job_data.get("source_conversation_id"),
                job_data.get("context_json"),
                job_data.get("files_dir")
            )
        )

    def get_scheduled_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a scheduled job by ID."""
        row = self.fetchone("SELECT * FROM scheduled_jobs WHERE id = ?", (job_id,))
        if row:
            row["is_enabled"] = bool(row.get("is_enabled", 0))
        return row

    def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """Get all scheduled jobs."""
        rows = self.fetchall("SELECT * FROM scheduled_jobs ORDER BY created_at DESC")
        for row in rows:
            row["is_enabled"] = bool(row.get("is_enabled", 0))
        return rows

    def get_enabled_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """Get only enabled scheduled jobs."""
        rows = self.fetchall(
            "SELECT * FROM scheduled_jobs WHERE is_enabled = 1 ORDER BY created_at ASC"
        )
        for row in rows:
            row["is_enabled"] = True
        return rows

    def update_scheduled_job(self, job_id: str, updates: Dict[str, Any]) -> None:
        """Update specific fields of a scheduled job."""
        if not updates:
            return

        # Build dynamic UPDATE query
        set_clauses = []
        params = []
        for key, value in updates.items():
            if key == "is_enabled":
                set_clauses.append(f"{key} = ?")
                params.append(1 if value else 0)
            else:
                set_clauses.append(f"{key} = ?")
                params.append(value)

        # Always update updated_at
        set_clauses.append("updated_at = ?")
        params.append(self.now())

        params.append(job_id)
        sql = f"UPDATE scheduled_jobs SET {', '.join(set_clauses)} WHERE id = ?"
        self.execute(sql, tuple(params))

    def delete_scheduled_job(self, job_id: str) -> None:
        """Delete a scheduled job."""
        self.execute("DELETE FROM scheduled_jobs WHERE id = ?", (job_id,))

    def add_scheduled_job_run(
        self,
        scheduled_job_id: str,
        job_id: str,
        status: str,
        result_preview: str = None
    ) -> int:
        """Log a scheduled job run."""
        with self._lock:
            conn = self._connect()
            cur = conn.execute(
                """
                INSERT INTO scheduled_job_runs(scheduled_job_id, job_id, started_at, status, result_preview)
                VALUES (?, ?, ?, ?, ?)
                """,
                (scheduled_job_id, job_id, self.now(), status, result_preview)
            )
            run_id = cur.lastrowid
            conn.commit()
            conn.close()
            return run_id

    def update_scheduled_job_run(self, run_id: int, status: str, result_preview: str = None) -> None:
        """Update a scheduled job run (e.g., when completed)."""
        self.execute(
            """
            UPDATE scheduled_job_runs
            SET completed_at = ?, status = ?, result_preview = ?
            WHERE id = ?
            """,
            (self.now(), status, result_preview, run_id)
        )

    def update_scheduled_job_run_by_job_id(self, job_id: str, status: str, result_preview: str = None) -> None:
        """Update a scheduled job run by its job_id."""
        self.execute(
            """
            UPDATE scheduled_job_runs
            SET completed_at = ?, status = ?, result_preview = ?
            WHERE job_id = ?
            """,
            (self.now(), status, result_preview, job_id)
        )

    def get_scheduled_job_runs(self, scheduled_job_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get run history for a scheduled job."""
        return self.fetchall(
            """
            SELECT * FROM scheduled_job_runs
            WHERE scheduled_job_id = ?
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (scheduled_job_id, limit)
        )

    def get_scheduler_conversations(self, scheduler_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get conversations created by a scheduler."""
        return self.fetchall(
            """
            SELECT
                c.id,
                c.created_at,
                c.is_scheduler_run,
                (SELECT m.content FROM messages m WHERE m.conversation_id = c.id AND m.role = 'assistant' ORDER BY m.id DESC LIMIT 1) as preview
            FROM conversations c
            WHERE c.scheduler_id = ?
            ORDER BY c.created_at DESC
            LIMIT ?
            """,
            (scheduler_id, limit)
        )

    # --- Balance & Usage Methods (Prepaid System) ---

    def get_balance(self) -> Dict[str, Any]:
        """Get current balance."""
        row = self.fetchone("SELECT * FROM balance WHERE id = 1")
        if not row:
            # Initialize if somehow missing
            self.execute(
                "INSERT OR IGNORE INTO balance (id, balance_usd, total_spent_usd, total_topups_usd, updated_at) VALUES (1, 999999.0, 0.0, 999999.0, ?)",
                (self.now(),)
            )
            return {"balance_usd": 999999.0, "total_spent_usd": 0.0, "total_topups_usd": 999999.0, "updated_at": self.now()}
        return row

    def deduct_balance(self, amount: float) -> bool:
        """
        Atomically deduct from balance.
        Returns True if successful, False if insufficient funds.
        """
        with self._lock:
            conn = self._connect()
            # Check current balance
            cur = conn.execute("SELECT balance_usd FROM balance WHERE id = 1")
            row = cur.fetchone()
            if not row or row["balance_usd"] < amount:
                conn.close()
                return False
            # Deduct
            conn.execute(
                """
                UPDATE balance SET
                    balance_usd = balance_usd - ?,
                    total_spent_usd = total_spent_usd + ?,
                    updated_at = ?
                WHERE id = 1
                """,
                (amount, amount, self.now())
            )
            conn.commit()
            conn.close()
            return True

    def add_topup(self, amount: float, note: str = None) -> None:
        """Add a top-up (credits) to balance."""
        with self._lock:
            conn = self._connect()
            # Record top-up
            conn.execute(
                "INSERT INTO topups (amount_usd, note, created_at) VALUES (?, ?, ?)",
                (amount, note, self.now())
            )
            # Update balance
            conn.execute(
                """
                UPDATE balance SET
                    balance_usd = balance_usd + ?,
                    total_topups_usd = total_topups_usd + ?,
                    updated_at = ?
                WHERE id = 1
                """,
                (amount, amount, self.now())
            )
            conn.commit()
            conn.close()

    def get_topups(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get top-up history."""
        return self.fetchall(
            "SELECT * FROM topups ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )

    def log_usage(
        self,
        model: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
        component: str,
        job_id: str = None,
        conversation_id: str = None
    ) -> None:
        """Log a single LLM usage record."""
        self.execute(
            """
            INSERT INTO usage_log (job_id, conversation_id, model, provider, prompt_tokens, completion_tokens, cost_usd, component, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (job_id, conversation_id, model, provider, prompt_tokens, completion_tokens, cost_usd, component, self.now())
        )

    def get_usage_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get usage summary for the last N days."""
        from datetime import datetime, timedelta
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"

        rows = self.fetchall(
            """
            SELECT
                component,
                model,
                COUNT(*) as call_count,
                SUM(prompt_tokens) as total_prompt_tokens,
                SUM(completion_tokens) as total_completion_tokens,
                SUM(cost_usd) as total_cost
            FROM usage_log
            WHERE created_at >= ?
            GROUP BY component, model
            ORDER BY total_cost DESC
            """,
            (cutoff,)
        )

        total_cost = sum(r.get("total_cost", 0) or 0 for r in rows)
        return {
            "period_days": days,
            "total_cost_usd": total_cost,
            "breakdown": rows
        }

    def get_conversation_cost(self, conversation_id: str) -> Dict[str, Any]:
        """Get total cost for a specific conversation."""
        row = self.fetchone(
            """
            SELECT
                COALESCE(SUM(cost_usd), 0) as total_cost,
                COALESCE(SUM(prompt_tokens), 0) as total_prompt_tokens,
                COALESCE(SUM(completion_tokens), 0) as total_completion_tokens,
                COUNT(*) as api_calls
            FROM usage_log
            WHERE conversation_id = ?
            """,
            (conversation_id,)
        )
        if not row:
            return {
                "conversation_id": conversation_id,
                "total_cost_usd": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "api_calls": 0
            }
        return {
            "conversation_id": conversation_id,
            "total_cost_usd": row.get("total_cost", 0) or 0,
            "total_prompt_tokens": row.get("total_prompt_tokens", 0) or 0,
            "total_completion_tokens": row.get("total_completion_tokens", 0) or 0,
            "api_calls": row.get("api_calls", 0) or 0
        }

    # --- User Settings Methods ---

    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        """Get a user setting by key."""
        row = self.fetchone(
            "SELECT value FROM user_settings WHERE key = ?",
            (key,)
        )
        if row:
            return row["value"]
        return default

    def set_setting(self, key: str, value: str) -> None:
        """Set a user setting (upsert)."""
        self.execute(
            """
            INSERT INTO user_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (key, value, self.now())
        )

    def get_all_settings(self) -> Dict[str, str]:
        """Get all user settings as a dict."""
        rows = self.fetchall("SELECT key, value FROM user_settings")
        return {row["key"]: row["value"] for row in rows}

    def delete_setting(self, key: str) -> bool:
        """Delete a user setting. Returns True if deleted."""
        existing = self.fetchone(
            "SELECT key FROM user_settings WHERE key = ?",
            (key,)
        )
        if not existing:
            return False
        self.execute("DELETE FROM user_settings WHERE key = ?", (key,))
        return True

    # --- App API Token Methods ---

    def get_app_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Get an app record by its API token."""
        return self.fetchone("SELECT * FROM apps WHERE api_token = ?", (token,))

    # --- Conversation Memory Methods (Hierarchical Memory System) ---

    def count_messages(self, conversation_id: str) -> int:
        """Count total messages in a conversation."""
        row = self.fetchone(
            "SELECT COUNT(*) as count FROM messages WHERE conversation_id = ?",
            (conversation_id,)
        )
        return row["count"] if row else 0

    def get_user_messages(self, conversation_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """Get all user messages from a conversation.

        Returns messages in chronological order (oldest first).
        """
        sql = """
            SELECT id, role, content, created_at
            FROM messages
            WHERE conversation_id = ? AND role = 'user'
            ORDER BY id ASC
        """
        params = [conversation_id]
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        return self.fetchall(sql, tuple(params))

    def get_messages_for_summary(
        self,
        conversation_id: str,
        after_message_id: int = None,
        exclude_roles: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Get messages for summary generation.

        Args:
            conversation_id: The conversation ID
            after_message_id: Only get messages after this ID (for incremental updates)
            exclude_roles: Roles to exclude (e.g., ['tool'] to skip tool outputs)

        Returns:
            Messages in chronological order
        """
        sql = "SELECT id, role, content, tool_calls, created_at FROM messages WHERE conversation_id = ?"
        params = [conversation_id]

        if after_message_id:
            sql += " AND id > ?"
            params.append(after_message_id)

        if exclude_roles:
            placeholders = ",".join("?" * len(exclude_roles))
            sql += f" AND role NOT IN ({placeholders})"
            params.extend(exclude_roles)

        sql += " ORDER BY id ASC"
        return self.fetchall(sql, tuple(params))

    def get_conversation_summary(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get current summary for a conversation.

        Returns:
            Dict with 'summary' and 'summary_up_to_message_id', or None
        """
        row = self.fetchone(
            "SELECT summary, summary_up_to_message_id FROM conversations WHERE id = ?",
            (conversation_id,)
        )
        if row and row.get("summary"):
            return {
                "summary": row["summary"],
                "summary_up_to_message_id": row.get("summary_up_to_message_id")
            }
        return None

    def save_conversation_summary(
        self,
        conversation_id: str,
        summary: str,
        up_to_message_id: int
    ) -> None:
        """Save or update conversation summary.

        Args:
            conversation_id: The conversation ID
            summary: The summary text
            up_to_message_id: The message ID that this summary covers up to
        """
        self.execute(
            """
            UPDATE conversations
            SET summary = ?, summary_up_to_message_id = ?
            WHERE id = ?
            """,
            (summary, up_to_message_id, conversation_id)
        )

    def get_last_message_id(self, conversation_id: str) -> Optional[int]:
        """Get the ID of the last message in a conversation."""
        row = self.fetchone(
            "SELECT MAX(id) as last_id FROM messages WHERE conversation_id = ?",
            (conversation_id,)
        )
        return row["last_id"] if row else None

    def save_suggestions_to_last_assistant_message(self, conversation_id: str, suggestions: list) -> None:
        """Save follow-up suggestions to the last assistant message's metadata."""
        import json
        row = self.fetchone(
            "SELECT id, metadata FROM messages WHERE conversation_id = ? AND role = 'assistant' AND internal = 0 ORDER BY id DESC LIMIT 1",
            (conversation_id,)
        )
        if not row:
            return
        existing = {}
        if row["metadata"]:
            try:
                existing = json.loads(row["metadata"])
            except (json.JSONDecodeError, TypeError):
                pass
        existing["suggestions"] = suggestions
        self.execute(
            "UPDATE messages SET metadata = ? WHERE id = ?",
            (json.dumps(existing), row["id"])
        )

    # --- Custom Skills Methods ---

    def get_custom_skills(self) -> List[Dict[str, Any]]:
        """Get all custom skills."""
        return self.fetchall("SELECT * FROM custom_skills ORDER BY name ASC")

    def get_custom_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Get a custom skill by ID."""
        return self.fetchone("SELECT * FROM custom_skills WHERE id = ?", (skill_id,))

    def create_custom_skill(self, skill_id: str, name: str, description: str, instructions: str, required_secrets: str = None) -> None:
        """Create a new custom skill."""
        now = self.now()
        self.execute(
            "INSERT INTO custom_skills (id, name, description, instructions, required_secrets, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (skill_id, name, description, instructions, required_secrets, now, now)
        )

    def update_custom_skill(self, skill_id: str, name: str, description: str, instructions: str, required_secrets: str = None) -> bool:
        """Update an existing custom skill. Returns True if found and updated."""
        result = self.execute(
            "UPDATE custom_skills SET name = ?, description = ?, instructions = ?, required_secrets = ?, updated_at = ? WHERE id = ?",
            (name, description, instructions, required_secrets, self.now(), skill_id)
        )
        return result.rowcount > 0

    def delete_custom_skill(self, skill_id: str) -> bool:
        """Delete a custom skill. Returns True if found and deleted."""
        self.delete_skill_secrets(skill_id)
        result = self.execute("DELETE FROM custom_skills WHERE id = ?", (skill_id,))
        return result.rowcount > 0

    # --- Skill Secrets Methods ---

    def get_skill_secrets(self, skill_id: str) -> Dict[str, str]:
        """Get all configured secrets for a skill. Returns {name: value} dict."""
        prefix = f"skill_secret:{skill_id}:"
        rows = self.fetchall(
            "SELECT key, value FROM user_settings WHERE key LIKE ?",
            (prefix + "%",)
        )
        return {row["key"][len(prefix):]: row["value"] for row in rows}

    def get_skill_secrets_status(self, skill_id: str) -> Dict[str, bool]:
        """Get which secrets are configured for a skill (without revealing values). Returns {name: is_set}."""
        prefix = f"skill_secret:{skill_id}:"
        rows = self.fetchall(
            "SELECT key FROM user_settings WHERE key LIKE ?",
            (prefix + "%",)
        )
        return {row["key"][len(prefix):]: True for row in rows}

    def set_skill_secret(self, skill_id: str, key: str, value: str) -> None:
        """Store a secret value for a skill."""
        setting_key = f"skill_secret:{skill_id}:{key}"
        self.set_setting(setting_key, value)

    def delete_skill_secret(self, skill_id: str, key: str) -> bool:
        """Delete a single secret for a skill."""
        setting_key = f"skill_secret:{skill_id}:{key}"
        return self.delete_setting(setting_key)

    def delete_skill_secrets(self, skill_id: str) -> None:
        """Delete all secrets for a skill (cleanup on skill delete)."""
        prefix = f"skill_secret:{skill_id}:%"
        self.execute("DELETE FROM user_settings WHERE key LIKE ?", (prefix,))
