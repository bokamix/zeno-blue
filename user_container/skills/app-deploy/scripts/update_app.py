# /// script
# dependencies = ["httpx"]
# ///

"""Update app configuration (name, cmd, cwd). Auto-restarts if cmd/cwd changed."""

import sys
import argparse
import json
import os
import httpx
from urllib.parse import urlparse

API_BASE = "http://localhost:18000"


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
    parser = argparse.ArgumentParser(description="Update app configuration.")
    parser.add_argument("--app-id", required=True, help="The app_id to update")
    parser.add_argument("--name", help="New friendly name for the app")
    parser.add_argument("--cmd", help="New command to run (use {port} placeholder)")
    parser.add_argument("--cwd", help="New working directory")
    args = parser.parse_args()

    app_id = args.app_id

    # Build update payload
    data = {}
    if args.name:
        data["name"] = args.name
    if args.cmd:
        data["cmd"] = args.cmd
    if args.cwd:
        data["cwd"] = args.cwd

    if not data:
        print(json.dumps({
            "error": "No updates specified. Use --name, --cmd, or --cwd."
        }))
        sys.exit(1)

    try:
        response = httpx.patch(
            f"{API_BASE}/apps/{app_id}",
            json=data,
            timeout=30
        )

        if response.status_code == 404:
            print(json.dumps({
                "error": f"App '{app_id}' not found. Use list_apps.py to see available apps."
            }))
            sys.exit(1)

        if response.status_code == 400:
            error_detail = response.json().get("detail", "Bad request")
            print(json.dumps({"error": error_detail}))
            sys.exit(1)

        response.raise_for_status()
        result = response.json()

        output = {
            "status": "updated",
            "app_id": app_id,
            "updated_fields": result.get("updated_fields", []),
            "restarted": result.get("restarted", False),
            "url": get_app_url(app_id)
        }

        if result.get("restarted"):
            output["note"] = "App was restarted due to cmd/cwd change."

        print(json.dumps(output, indent=2))

    except httpx.ConnectError:
        print(json.dumps({"error": "Cannot connect to server. Is the container running?"}))
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(json.dumps({"error": f"HTTP error: {e.response.status_code}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"Failed to update app: {str(e)}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
