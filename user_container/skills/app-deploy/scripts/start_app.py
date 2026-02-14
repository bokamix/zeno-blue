# /// script
# dependencies = ["httpx"]
# ///

"""Start a stopped app."""

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
    parser = argparse.ArgumentParser(description="Start a stopped app.")
    parser.add_argument("--app-id", required=True, help="The app_id to start")
    args = parser.parse_args()

    app_id = args.app_id

    try:
        response = httpx.post(f"{API_BASE}/apps/{app_id}/__start", timeout=30)

        if response.status_code == 404:
            print(json.dumps({
                "error": f"App '{app_id}' not found. Use list_apps.py to see available apps."
            }))
            sys.exit(1)

        response.raise_for_status()

        print(json.dumps({
            "status": "started",
            "app_id": app_id,
            "url": get_app_url(app_id),
            "note": "App has been started. It may take a moment to become available."
        }, indent=2))

    except httpx.ConnectError:
        print(json.dumps({"error": "Cannot connect to server. Is the container running?"}))
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(json.dumps({"error": f"HTTP error: {e.response.status_code}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"Failed to start app: {str(e)}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
