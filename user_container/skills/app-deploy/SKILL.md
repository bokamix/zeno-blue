---
name: app-deploy
description: "Deploy and manage long-running web applications (FastAPI). Use when user wants to deploy an app, host a web server, run an application in background, start a service, or make an app accessible via URL."
---

# App Deployment Skill

This skill allows you to register and run web applications in the background. The system automatically manages ports and routing.

## CRITICAL: Port Handling

Your app **MUST** read the port from command line argument. The system assigns a dynamic port and passes it via `{port}` placeholder.

**WRONG** (will NOT work):
```python
app.run(host="0.0.0.0", port=5000)  # Hardcoded port - BREAKS the app!
```

**CORRECT**:
```python
import sys
port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
app.run(host="0.0.0.0", port=port)  # Reads port from command line
```

If you hardcode the port, the app will start on wrong port and be unreachable via URL.

## Usage

To deploy an app, run the `register_app.py` script.

### Parameters
- `--name`: Friendly name for the app (used in URL).
- `--cwd`: Directory where the app code resides.
- `--cmd`: The command to run. **CRITICAL**: Use `{port}` placeholder for the port argument.

### Example

#### 1. FastAPI App (Recommended)
For web apps with forms/UI, use FastAPI with Jinja2 templates. Simple and works well with proxy.

**File `app.py`:**
```python
# /// script
# dependencies = ["fastapi", "uvicorn", "jinja2", "python-multipart"]
# ///
import sys
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()

# For simple apps, inline HTML works fine:
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>My App</title></head>
<body>
    <h1>Hello World</h1>
    <form method="post" action="/submit">
        <input name="name" placeholder="Your name">
        <button type="submit">Submit</button>
    </form>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML_TEMPLATE

@app.post("/submit")
def submit(name: str = Form(...)):
    return {"message": f"Hello {name}!"}

if __name__ == "__main__":
    import uvicorn
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run(app, host="0.0.0.0", port=port)
```

**Deploy command:**
```bash
uv run /app/user_container/skills/app-deploy/scripts/register_app.py \
  --name "my-app" \
  --cwd "projects/my-app" \
  --cmd "uv run app.py {port}"
```

#### 2. Static Server (Standard Library)
No extra dependencies needed.

```bash
uv run /app/user_container/skills/app-deploy/scripts/register_app.py \
  --name "static-site" \
  --cwd "site" \
  --cmd "python -m http.server {port}"
```

### Output
The script outputs JSON with the `app_id` and the public URL.

## Important Notes
- **Do NOT use Streamlit** - it has WebSocket/CORS issues with the proxy system
- Always use `{port}` placeholder in your cmd
- The script returns the public URL in the output - use that URL to access the app

---

## Managing Existing Apps

Once an app is deployed, you can manage it without re-registering (which would change the URL).

### List All Apps
See all deployed apps with their status, URLs, and commands:
```bash
uv run /app/user_container/skills/app-deploy/scripts/list_apps.py
```

Output includes: `app_id`, `name`, `port`, `cwd`, `cmd`, `status`, `url`, `created_at`

### Restart an App
After modifying code files, restart the app to apply changes (keeps same URL):
```bash
uv run /app/user_container/skills/app-deploy/scripts/restart_app.py --app-id "my-app-a1b2"
```

### Update App Configuration
Change the name, command, or working directory. App auto-restarts if `cmd` or `cwd` changes:
```bash
# Change just the name
uv run /app/user_container/skills/app-deploy/scripts/update_app.py \
  --app-id "my-app-a1b2" \
  --name "New Name"

# Change the command (triggers restart)
uv run /app/user_container/skills/app-deploy/scripts/update_app.py \
  --app-id "my-app-a1b2" \
  --cmd "uv run new_app.py {port}"

# Change multiple fields
uv run /app/user_container/skills/app-deploy/scripts/update_app.py \
  --app-id "my-app-a1b2" \
  --name "Updated App" \
  --cwd "new-location"
```

### Stop / Start Apps
```bash
# Stop a running app
uv run /app/user_container/skills/app-deploy/scripts/stop_app.py --app-id "my-app-a1b2"

# Start a stopped app
uv run /app/user_container/skills/app-deploy/scripts/start_app.py --app-id "my-app-a1b2"
```

### View App Logs
Debug issues by viewing app stdout/stderr:
```bash
uv run /app/user_container/skills/app-deploy/scripts/app_logs.py --app-id "my-app-a1b2"

# Get more lines
uv run /app/user_container/skills/app-deploy/scripts/app_logs.py --app-id "my-app-a1b2" --lines 200
```

### Delete an App
Permanently remove an app (stops it first):
```bash
uv run /app/user_container/skills/app-deploy/scripts/delete_app.py --app-id "my-app-a1b2"
```

---

## Typical Workflow

1. **Create app**: Use `register_app.py` to deploy initially
2. **User requests changes**: Edit the app's code files
3. **Apply changes**: Use `restart_app.py` to restart (same URL)
4. **Tell user**: "Changes applied, refresh the page"

If the startup command or directory needs to change, use `update_app.py` instead of `restart_app.py`.
