# /// script
# dependencies = []
# ///

import sys
import argparse
import json
import sqlite3
import os
import uuid
import secrets
import socket
import time
from datetime import datetime
from urllib.parse import urlparse

DB_PATH = "/data/runtime.db"


def get_app_url(app_id: str) -> str:
    """
    Generate app URL based on BASE_URL environment variable.

    Local (localhost/has port): http://{app_id}.lvh.me:{port}/
    Production ({user_id}.{domain}): {scheme}://{app_id}.{user_id}.{domain}/
    """
    base_url = os.getenv("BASE_URL", "http://localhost:18000")
    parsed = urlparse(base_url)
    scheme = parsed.scheme  # http or https
    host = parsed.hostname  # e.g., "localhost" or "user-001.zeno.blue"
    port = parsed.port      # e.g., 18000 or None

    # Local mode: localhost or has explicit port
    if host in ("localhost", "127.0.0.1") or port:
        port_suffix = f":{port}" if port else ":18000"
        return f"http://{app_id}.lvh.me{port_suffix}/"

    # Production mode: {app_id}.{base_host} (subdomain of subdomain)
    # e.g., user-001.zeno.blue → my-app.user-001.zeno.blue
    return f"{scheme}://{app_id}.{host}/"

def find_free_port(db_cursor, start_port=3000, end_port=4000):
    """Find a port that is not in DB and actually free on host."""

    # 1. Get ports used in DB
    db_cursor.execute("SELECT port FROM apps WHERE status='running'")
    used_ports_db = set(row[0] for row in db_cursor.fetchall())

    for port in range(start_port, end_port):
        if port in used_ports_db:
            continue

        # 2. Check if actually free on OS
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) != 0:
                return port

    raise RuntimeError("No free ports available in range")


def wait_for_port(port: int, timeout: float = 10.0, interval: float = 0.5) -> bool:
    """Wait for a port to become available (app listening). Returns True if port opens."""
    start = time.time()
    while time.time() - start < timeout:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) == 0:
                return True
        time.sleep(interval)
    return False

def main():
    parser = argparse.ArgumentParser(description="Register and deploy a web application.")
    parser.add_argument("--name", required=True, help="Friendly name of the app")
    parser.add_argument("--cwd", required=True, help="Working directory for the app")
    parser.add_argument("--cmd", required=True, help="Command to start the app (use {port} placeholder)")
    args = parser.parse_args()

    # Normalize paths
    cwd = os.path.abspath(args.cwd)
    if not os.path.exists(cwd):
        print(json.dumps({"error": f"Directory not found: {cwd}"}))
        sys.exit(1)

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # Ensure table exists (just in case, though app.py does it)
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

        # Find port
        port = find_free_port(cur)
        
        # Generate ID
        # Simple ID from name + short hash to be subdomain-friendly
        # e.g. "my-app" -> "my-app-a1b2"
        safe_name = "".join(c if c.isalnum() else "-" for c in args.name.lower())
        uid = str(uuid.uuid4())[:4]
        app_id = f"{safe_name}-{uid}"
        
        # Insert
        now = datetime.utcnow().isoformat() + "Z"
        cmd_json = json.dumps(args.cmd.split()) # Supervisor expects list of strings
        api_token = secrets.token_urlsafe(32)  # Generate secure API token

        cur.execute(
            "INSERT INTO apps (app_id, name, port, cwd, cmd, status, api_token, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (app_id, args.name, port, cwd, cmd_json, "running", api_token, now)
        )
        
        conn.commit()

        # Supervisor (running in app.py) will pick this up automatically via DB polling.
        # Wait for the app to actually start listening on the assigned port.
        print(json.dumps({"status": "starting", "message": f"Waiting for app to listen on port {port}..."}))

        if not wait_for_port(port, timeout=15.0):
            # App didn't start on the assigned port - likely hardcoded port issue
            cur.execute("DELETE FROM apps WHERE app_id = ?", (app_id,))
            conn.commit()
            conn.close()
            error_msg = (
                f"App failed to start on assigned port {port}. "
                "This usually means your app has a HARDCODED port instead of reading from sys.argv[1]. "
                "Fix your app.py to use: port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000"
            )
            print(json.dumps({"error": error_msg}))
            sys.exit(1)

        conn.close()

        result = {
            "status": "registered",
            "app_id": app_id,
            "port": port,
            "url": get_app_url(app_id),
            "note": "App is running and accessible."
        }
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({"error": f"Failed to register app: {str(e)}"}))
        sys.exit(1)

if __name__ == "__main__":
    main()
