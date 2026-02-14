# /// script
# dependencies = []
# ///

"""View logs from a running app by reading directly from log file."""

import sys
import argparse
import json
import os

LOGS_DIR = "/workspace/logs"


def tail_file(file_path: str, max_lines: int) -> str:
    """Read last N lines from a file."""
    if not os.path.exists(file_path):
        return ""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
        tail_lines = lines[-max_lines:] if len(lines) > max_lines else lines
        return "".join(tail_lines)


def main():
    parser = argparse.ArgumentParser(description="View app logs.")
    parser.add_argument("--app-id", required=True, help="The app_id to get logs for")
    parser.add_argument("--lines", type=int, default=100, help="Number of lines to retrieve (default: 100)")
    args = parser.parse_args()

    app_id = args.app_id
    log_path = os.path.join(LOGS_DIR, f"{app_id}.log")

    if not os.path.exists(log_path):
        print(json.dumps({
            "error": f"No logs found for '{app_id}'. App may not have been started yet.",
            "log_path": log_path
        }))
        sys.exit(1)

    logs = tail_file(log_path, args.lines)
    line_count = len(logs.splitlines()) if logs else 0

    print(json.dumps({
        "app_id": app_id,
        "logs": logs,
        "line_count": line_count,
        "log_path": log_path
    }, indent=2))


if __name__ == "__main__":
    main()
