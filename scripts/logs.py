#!/usr/bin/env python3
"""Show all logs for a conversation: messages + job activities, chronologically."""
import sqlite3
import sys
import os
import shutil

DB_PATH = os.path.join(os.path.expanduser("~"), ".zeno", "data", "runtime.db")

# ANSI color codes
RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"


def list_conversations(conn):
    rows = conn.execute(
        "SELECT id, created_at, substr(replace(replace(preview, char(10), ' '), char(13), ''), 1, 60) as preview "
        "FROM conversations ORDER BY created_at DESC LIMIT 15"
    ).fetchall()
    print("Recent conversations:\n")
    for r in rows:
        preview = (r[2] or "").strip()
        print(f"  {DIM}{r[0]}{RESET}  {r[1][:19]}  {preview}")
    print(f"\nUsage: make logs id=<conversation_id>")


def truncate(text, max_len):
    if not text:
        return ""
    text = text.replace("\n", " ").replace("\r", "").strip()
    if len(text) > max_len:
        return text[:max_len - 3] + "..."
    return text


def format_type(type_str):
    """Shorten common type names."""
    return type_str[:20]


def show_logs(conn, conv_id):
    c = conn.execute("SELECT id FROM conversations WHERE id = ?", (conv_id,)).fetchone()
    if not c:
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
                   m.content as content,
                   m.created_at as sort_key
            FROM messages m WHERE m.conversation_id = ?
            UNION ALL
            SELECT datetime(ja.timestamp, 'unixepoch', 'localtime') as time,
                   'LOG' as source,
                   CASE WHEN ja.tool_name IS NOT NULL THEN ja.type || ':' || ja.tool_name ELSE ja.type END as type,
                   CASE WHEN ja.is_error THEN '[ERROR] ' ELSE '' END || ja.message as content,
                   datetime(ja.timestamp, 'unixepoch') as sort_key
            FROM job_activities ja JOIN jobs j ON ja.job_id = j.id WHERE j.conversation_id = ?
        ) ORDER BY sort_key
    """
    rows = conn.execute(query, (conv_id, conv_id)).fetchall()

    if not rows:
        print("No logs found for this conversation.")
        return

    # Calculate available width for content
    term_width = shutil.get_terminal_size((120, 40)).columns
    # Layout: time(14) + 2 + source(3) + 2 + type(20) + 2 = 43 chars prefix
    prefix_len = 43
    max_content = max(term_width - prefix_len, 30)

    source_colors = {"MSG": BLUE, "LOG": DIM}
    type_colors = {
        "USER": GREEN,
        "ASSISTANT": CYAN,
        "TOOL": YELLOW,
        "routing": DIM,
        "step": DIM,
        "llm_call": MAGENTA,
    }

    for time_str, source, type_, content in rows:
        content = truncate(content, max_content)

        is_error = False
        if content.startswith("[ERROR] "):
            is_error = True
            content = content[8:]

        sc = source_colors.get(source, "")
        tc = type_colors.get(type_, "")
        if is_error:
            tc = RED + BOLD
            type_ = "ERR:" + type_

        type_short = format_type(type_)
        time_short = time_str[5:] if time_str else ""

        print(f"{DIM}{time_short}{RESET}  {sc}{source:<3}{RESET}  {tc}{type_short:<20}{RESET}  {content}")


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
