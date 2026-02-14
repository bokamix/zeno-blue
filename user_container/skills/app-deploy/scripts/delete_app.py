# /// script
# dependencies = ["httpx"]
# ///

"""Delete an app (stops it first if running)."""

import sys
import argparse
import json
import httpx

API_BASE = "http://localhost:18000"


def main():
    parser = argparse.ArgumentParser(description="Delete an app permanently.")
    parser.add_argument("--app-id", required=True, help="The app_id to delete")
    args = parser.parse_args()

    app_id = args.app_id

    try:
        response = httpx.delete(f"{API_BASE}/apps/{app_id}", timeout=30)

        if response.status_code == 404:
            print(json.dumps({
                "error": f"App '{app_id}' not found. Use list_apps.py to see available apps."
            }))
            sys.exit(1)

        response.raise_for_status()

        print(json.dumps({
            "status": "deleted",
            "app_id": app_id,
            "note": "App has been permanently deleted."
        }, indent=2))

    except httpx.ConnectError:
        print(json.dumps({"error": "Cannot connect to server. Is the container running?"}))
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(json.dumps({"error": f"HTTP error: {e.response.status_code}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"Failed to delete app: {str(e)}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
