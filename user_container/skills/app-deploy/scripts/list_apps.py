# /// script
# dependencies = []
# ///

"""List all deployed apps with their status and URLs."""

import json
import sqlite3
import os
from urllib.parse import urlparse

DB_PATH = "/data/runtime.db"


def get_app_url(app_id: str) -> str:
    """Generate app URL based on BASE_URL environment variable."""
    base_url = os.getenv("BASE_URL", "http://localhost:18000")
    parsed = urlparse(base_url)
    scheme = parsed.scheme
    host = parsed.hostname
    port = parsed.port

    if host in ("localhost", "127.0.0.1") or port:
        port_suffix = f":{port}" if port else ":18000"
        return f"http://{app_id}.lvh.me{port_suffix}/"

    return f"{scheme}://{app_id}.{host}/"


def main():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT app_id, name, port, cwd, cmd, status, api_token, created_at
            FROM apps
            ORDER BY created_at DESC
        """)
        rows = cur.fetchall()
        conn.close()

        apps = []
        for row in rows:
            cmd_raw = row["cmd"]
            # cmd is stored as JSON list, convert back to string for display
            try:
                cmd_list = json.loads(cmd_raw)
                cmd_display = " ".join(cmd_list)
            except (json.JSONDecodeError, TypeError):
                cmd_display = cmd_raw

            apps.append({
                "app_id": row["app_id"],
                "name": row["name"],
                "port": row["port"],
                "cwd": row["cwd"],
                "cmd": cmd_display,
                "status": row["status"],
                "api_token": row["api_token"],
                "url": get_app_url(row["app_id"]),
                "created_at": row["created_at"]
            })

        result = {
            "apps": apps,
            "count": len(apps)
        }
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({"error": f"Failed to list apps: {str(e)}"}))


if __name__ == "__main__":
    main()
