#!/usr/bin/env python3
"""Show all logs for a conversation: messages + job activities, chronologically."""
import sqlite3
import sys
import os

DB_PATH = os.path.join(os.path.expanduser("~"), ".zeno", "data", "runtime.db")

def list_conversations(conn):
    rows = conn.execute(
        "SELECT id, created_at, substr(replace(replace(preview, char(10), ' '), char(13), ''), 1, 60) as preview "
        "FROM conversations ORDER BY created_at DESC LIMIT 15"
    ).fetchall()
    print("Recent conversations:\n")
    for r in rows:
        preview = (r[2] or "").strip()
        print(f"  {r[0]}  {r[1][:19]}  {preview}")
    print(f"\nUsage: make logs id=<conversation_id>")

def show_logs(conn, conv_id):
    # Check conversation exists
    c = conn.execute("SELECT id FROM conversations WHERE id = ?", (conv_id,)).fetchone()
    if not c:
        # Try prefix match
        rows = conn.execute("SELECT id FROM conversations WHERE id LIKE ?", (conv_id + "%",)).fetchall()
        if len(rows) == 1:
            conv_id = rows[0][0]
        elif len(rows) > 1:
            print(f"Ambiguous ID '{conv_id}', matches:")
            for r in rows:
                print(f"  {r[0]}")
            return
        else:
            print(f"Conversation '{conv_id}' not found.")
            return

    query = """
        SELECT time, source, type, content FROM (
            SELECT datetime(m.created_at) as time,
                   'MSG' as source,
                   upper(m.role) as type,
                   replace(replace(m.content, char(10), ' '), char(13), '') as content,
                   m.created_at as sort_key
            FROM messages m WHERE m.conversation_id = ?
            UNION ALL
            SELECT datetime(ja.timestamp, 'unixepoch', 'localtime') as time,
                   'LOG' as source,
                   CASE WHEN ja.tool_name IS NOT NULL THEN ja.type || ':' || ja.tool_name ELSE ja.type END as type,
                   CASE WHEN ja.is_error THEN '[ERROR] ' ELSE '' END ||
                   replace(replace(ja.message, char(10), ' '), char(13), '') as content,
                   datetime(ja.timestamp, 'unixepoch') as sort_key
            FROM job_activities ja JOIN jobs j ON ja.job_id = j.id WHERE j.conversation_id = ?
        ) ORDER BY sort_key
    """
    rows = conn.execute(query, (conv_id, conv_id)).fetchall()

    if not rows:
        print("No logs found for this conversation.")
        return

    # Color codes
    RESET = "\033[0m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"

    source_colors = {"MSG": BLUE, "LOG": DIM}
    type_colors = {
        "USER": GREEN,
        "ASSISTANT": CYAN,
        "TOOL": YELLOW,
        "routing": DIM,
        "step": DIM,
        "llm_call": DIM,
    }

    max_content = 120
    for time, source, type_, content in rows:
        content = (content or "").strip()
        if len(content) > max_content:
            content = content[:max_content] + "..."

        sc = source_colors.get(source, "")
        tc = type_colors.get(type_, "")

        if "[ERROR]" in content:
            tc = RED + BOLD
            content = content.replace("[ERROR] ", "")
            type_ = "ERROR:" + type_

        time_short = time[5:] if time else ""  # skip year
        print(f"{DIM}{time_short}{RESET}  {sc}{source:<3}{RESET}  {tc}{type_:<25}{RESET}  {content}")

def main():
    if not os.path.exists(DB_PATH):
        print(f"Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conv_id = sys.argv[1] if len(sys.argv) > 1 else None

    if conv_id:
        show_logs(conn, conv_id)
    else:
        list_conversations(conn)

    conn.close()

if __name__ == "__main__":
    main()
