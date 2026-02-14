"""
Main FastAPI application for the User Container.

Provides:
- Health check endpoint
- Tool listing
- App management (list, stop, proxy)
- Chat endpoint for agent interaction
"""

import os
import sys
import re
import signal
import time
import mimetypes
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, Header
from fastapi.responses import Response, StreamingResponse, FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import shutil
from pathlib import Path
import uuid
import json
import httpx
import asyncio
import urllib.parse

from typing import List

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from user_container.config import settings, get_app_url
from user_container.security import init_secrets_file
from user_container.db.db import DB, JobActivity
from user_container.runner.runner import Runner
from user_container.supervisor.supervisor import Supervisor
from user_container.agent.skill_loader import SkillLoader
from user_container.logger import log_user_message, log
from user_container.observability import flush_langfuse
from user_container.jobs.job import Job
from user_container.jobs.queue import init_job_queue, get_job_queue
from user_container.scheduler.scheduler import init_scheduler, close_scheduler, get_scheduler
from user_container.scheduler.models import UpdateScheduledJobRequest
from user_container import admin as admin_module
from user_container.internal_api import skills as internal_skills
from user_container.internal_api import llm as internal_llm
import threading

# --- Sentry Error Tracking ---
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        release=settings.build_version,
        integrations=[
            StarletteIntegration(),
            FastApiIntegration(),
        ],
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=False,
    )

# --- Config ---

app = FastAPI(title="User Container MVP")


def _get_allowed_origins() -> list[str]:
    """Build list of allowed CORS origins based on configuration."""
    origins = set()

    # Add the container's own origin (from base_url)
    if settings.base_url:
        parsed = urllib.parse.urlparse(settings.base_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        origins.add(origin)

    # Local development: allow common dev origins
    if settings.base_url and ("localhost" in settings.base_url or "127.0.0.1" in settings.base_url or "lvh.me" in settings.base_url):
        origins.update([
            "http://localhost:5173",      # Vite dev server
            "http://localhost:18000",     # Local container
            "http://127.0.0.1:5173",
            "http://127.0.0.1:18000",
        ])
        # Also allow lvh.me variants for subdomain testing
        parsed = urllib.parse.urlparse(settings.base_url)
        if parsed.port:
            origins.add(f"http://lvh.me:{parsed.port}")

    return list(origins) if origins else ["*"]  # Fallback to * only if nothing configured


app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Subdomain Middleware ---

@app.middleware("http")
async def subdomain_proxy_middleware(request: Request, call_next):
    """
    Middleware to route requests based on subdomains.
    Supports:
      - *.localhost (Chrome/Firefox/Safari)
      - *.lvh.me (Universal)
      - {app_id}-{user_id}.{domain} (Production pattern from BASE_URL)

    If a subdomain is detected (e.g., "app-123.lvh.me"), it attempts to proxy
    the request to the corresponding app.
    """
    from urllib.parse import urlparse

    host = request.headers.get("host", "").split(":")[0]  # Remove port

    app_subdomain = None

    # Local patterns
    if host.endswith(".localhost"):
        app_subdomain = host[:-len(".localhost")]
    elif host.endswith(".lvh.me"):
        app_subdomain = host[:-len(".lvh.me")]
    else:
        # Production pattern: {app_id}.{base_host} (subdomain of subdomain)
        # e.g., my-app.user-001.zeno.blue
        parsed = urlparse(settings.base_url)
        base_host = parsed.hostname  # e.g., "user-001.zeno.blue"

        if base_host and host.endswith(f".{base_host}") and host != base_host:
            # Extract app_id: "my-app.user-001.zeno.blue" → "my-app"
            app_subdomain = host[:-(len(base_host) + 1)]  # +1 for the dot

    if app_subdomain:
        # We need to strip the trailing dot if it exists (some DNS resolvers add it)
        app_id = app_subdomain.strip(".")

        # It's an app request! Proxy it.
        # Check if app exists and is running
        row = db.fetchone("SELECT port, status FROM apps WHERE app_id=?", (app_id,))
        if not row:
             return Response(f"App '{app_id}' not found", status_code=404)
        
        if row["status"] != "running":
             return Response(f"App '{app_id}' is stopped", status_code=503)

        port = int(row["port"])
        # Path for proxying is everything after the domain (request.url.path)
        path = request.url.path
        if path.startswith("/"):
            path = path[1:] # Strip leading slash for target_url construction
            
        target_url = f"http://127.0.0.1:{port}/{path}"
        
        # Rebuild request
        method = request.method
        headers = dict(request.headers)
        headers.pop("host", None)
        body = await request.body()
        
        # Check if this is an SSE request
        accept_header = headers.get("accept", "")
        is_sse = "text/event-stream" in accept_header

        if is_sse:
            # SSE requests need streaming - don't wait for complete response
            async def sse_stream():
                try:
                    async with httpx.AsyncClient(timeout=None) as client:
                        async with client.stream(
                            method,
                            target_url,
                            content=body,
                            headers=headers,
                            params=dict(request.query_params),
                        ) as resp:
                            async for chunk in resp.aiter_bytes():
                                yield chunk
                except httpx.ConnectError:
                    yield b"event: error\ndata: App unavailable\n\n"
                except Exception:
                    pass  # Client disconnected

            return StreamingResponse(
                sse_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                }
            )

        # Regular HTTP request
        async with httpx.AsyncClient(follow_redirects=False, timeout=30.0) as client:
            try:
                resp = await client.request(
                    method,
                    target_url,
                    content=body,
                    headers=headers,
                    params=dict(request.query_params),
                )
            except httpx.ConnectError:
                return Response("App is unavailable (restarting?)", status_code=503)

        # Filter out hop-by-hop headers
        excluded = {"content-encoding", "transfer-encoding", "connection"}
        out_headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded}

        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=out_headers,
        )

    return await call_next(request)


# --- Initialize Services ---

db = DB(settings.db_path)

# Initialize UsageTracker singleton for Internal API (apps using LLM/skills)
from user_container.usage import UsageTracker
UsageTracker.get_instance(db)

runner = Runner()
supervisor = Supervisor(db=db)
skill_loader = SkillLoader() # Load skills from disk

# Initialize admin module with db
admin_module.set_db(db)





# --- Startup / Shutdown ---

@app.on_event("startup")
async def on_startup():
    # Initialize secrets file
    init_secrets_file()

    # Initialize in-process job queue (replaces Redis)
    init_job_queue(db)

    # Start async worker loop (replaces multiprocessing workers)
    asyncio.create_task(_worker_loop())

    # Start job scheduler (A.7)
    job_queue = get_job_queue()
    scheduler = init_scheduler(db, job_queue)
    scheduler.start()

    supervisor.start_monitoring()


@app.on_event("shutdown")
def on_shutdown():
    # Flush Langfuse events before shutdown
    flush_langfuse()

    # Stop scheduler (A.7)
    close_scheduler()


async def _worker_loop():
    """Process jobs from the in-process queue."""
    job_queue = get_job_queue()
    log("[Worker] Async worker loop started")
    while True:
        job_id = await job_queue.dequeue(timeout=5)
        if job_id:
            asyncio.create_task(_execute_job(job_id))


async def _execute_job(job_id: str):
    """Run agent in thread to not block FastAPI event loop."""
    job_queue = get_job_queue()
    job_data = job_queue.get_job(job_id)
    if not job_data:
        log(f"[Worker] Job {job_id} not found in queue")
        return

    job_queue.set_status(job_id, status="running",
                         started_at=datetime.utcnow().isoformat())
    log(f"[Worker] Processing job {job_id}")

    try:
        result = await asyncio.to_thread(
            _run_agent_job, job_id, job_data
        )
        job_queue.set_status(job_id, status="completed",
                             result=result,
                             completed_at=datetime.utcnow().isoformat())
        log(f"[Worker] Job {job_id} completed")
    except Exception as e:
        import traceback
        error_msg = str(e)
        log(f"[Worker] Job {job_id} failed: {error_msg}")
        log(f"[Worker] Traceback: {traceback.format_exc()}")

        status = "cancelled" if "cancelled" in error_msg.lower() else "failed"
        job_queue.set_status(job_id, status=status,
                             error=error_msg,
                             completed_at=datetime.utcnow().isoformat())


def _run_agent_job(job_id: str, job_data: dict) -> str:
    """Sync function that runs in thread."""
    from user_container.agent.agent import Agent
    from user_container.agent.llm_client import JobCancelledException

    agent = Agent(
        skill_loader=skill_loader,
        runner=runner,
        db=db,
    )

    result = agent.run(
        conversation_id=job_data["conversation_id"],
        job_id=job_id,
        user_message=job_data["message"],
        skip_history=job_data.get("skip_history", False),
    )

    if result.get("status") == "success":
        return result.get("summary", "Task completed")
    elif result.get("status") == "cancelled":
        raise JobCancelledException(result.get("summary", "Job cancelled by user"))
    elif result.get("status") == "timeout":
        raise RuntimeError(f"Agent timeout after {result.get('steps', '?')} steps")
    else:
        raise RuntimeError(result.get("error", "Unknown agent error"))

# --- Endpoints ---

@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/setup/status")
async def setup_status():
    """Check if initial setup is complete (API key configured)."""
    has_key = bool(settings.anthropic_api_key or settings.openai_api_key)
    return {
        "configured": has_key,
        "provider": settings.model_provider if has_key else None,
    }


@app.post("/setup")
async def setup_config(payload: dict):
    """
    First-run configuration. Saves API key to local config.
    Expects: {"provider": "anthropic", "api_key": "sk-ant-..."}
    """
    provider = payload.get("provider", "anthropic")
    api_key = payload.get("api_key", "").strip()

    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")
    if provider not in ("anthropic", "openai"):
        raise HTTPException(status_code=400, detail="Provider must be 'anthropic' or 'openai'")

    # Determine config file path
    config_dir = Path(os.environ.get("ZENO_CONFIG_DIR", Path.home() / ".zeno"))
    config_dir.mkdir(parents=True, exist_ok=True)
    env_path = config_dir / ".env"

    # Write .env file
    env_lines = []
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                # Skip existing provider/key lines (we'll rewrite them)
                stripped = line.strip()
                if stripped.startswith(("MODEL_PROVIDER=", "ANTHROPIC_API_KEY=", "OPENAI_API_KEY=")):
                    continue
                env_lines.append(line.rstrip("\n"))

    env_lines.append(f"MODEL_PROVIDER={provider}")
    if provider == "anthropic":
        env_lines.append(f"ANTHROPIC_API_KEY={api_key}")
    else:
        env_lines.append(f"OPENAI_API_KEY={api_key}")

    with open(env_path, "w") as f:
        f.write("\n".join(env_lines) + "\n")

    # Reload settings in-process
    if provider == "anthropic":
        settings.anthropic_api_key = api_key
    else:
        settings.openai_api_key = api_key
    settings.model_provider = provider

    log(f"[Setup] Configured {provider} provider, saved to {env_path}")
    return {"status": "ok", "provider": provider}


@app.get("/api/config")
def get_frontend_config():
    """Return configuration needed by frontend."""
    return {}


@app.get("/user-info")
def get_user_info():
    """Get basic user info (desktop mode)."""
    return {
        "domain": "localhost",
    }


@app.get("/status")
def get_status():
    """Get application status."""
    job_queue = get_job_queue()
    active_jobs = job_queue.get_active_jobs_count()

    return {
        "version": settings.build_version,
        "build_time": settings.build_time,
        "active_jobs": active_jobs,
    }


@app.get("/disk-usage")
def get_disk_usage():
    """
    Get disk usage for the user's storage quota.

    Returns used and total space in bytes, plus human-readable format.
    Storage is mounted at /data (loop device with ext4).
    """
    try:
        stat = os.statvfs("/data")
        total_bytes = stat.f_blocks * stat.f_frsize
        free_bytes = stat.f_bfree * stat.f_frsize
        used_bytes = total_bytes - free_bytes

        def human_readable(size_bytes: int) -> str:
            for unit in ["B", "KB", "MB", "GB"]:
                if size_bytes < 1024:
                    return f"{size_bytes:.1f} {unit}"
                size_bytes /= 1024
            return f"{size_bytes:.1f} TB"

        return {
            "used_bytes": used_bytes,
            "total_bytes": total_bytes,
            "free_bytes": free_bytes,
            "used_percent": round((used_bytes / total_bytes) * 100, 1) if total_bytes > 0 else 0,
            "used_human": human_readable(used_bytes),
            "total_human": human_readable(total_bytes),
        }
    except OSError:
        # Fallback if /data is not mounted (development environment)
        return {
            "used_bytes": 0,
            "total_bytes": 0,
            "free_bytes": 0,
            "used_percent": 0,
            "used_human": "N/A",
            "total_human": "N/A",
        }


@app.get("/conversations")
def list_conversations():
    """List all active (non-archived) conversations with preview."""
    # Get conversations with their latest message timestamp, first user message, and unread count
    rows = db.fetchall("""
        SELECT
            c.id,
            c.created_at,
            c.forked_from,
            c.branch_number,
            c.scheduler_id,
            c.is_scheduler_run,
            c.read_at,
            c.preview as custom_preview,
            (SELECT MAX(m.created_at) FROM messages m WHERE m.conversation_id = c.id) as last_message_at,
            (SELECT MAX(m.created_at) FROM messages m WHERE m.conversation_id = c.id AND m.role = 'user') as last_user_message_at,
            (SELECT m.content FROM messages m WHERE m.conversation_id = c.id AND m.role = 'user' ORDER BY m.id ASC LIMIT 1) as first_message,
            (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id AND m.role = 'assistant' AND (c.read_at IS NULL OR m.created_at > c.read_at)) as unread_count
        FROM conversations c
        WHERE COALESCE(c.is_archived, 0) = 0
        ORDER BY COALESCE((SELECT MAX(m.created_at) FROM messages m WHERE m.conversation_id = c.id AND m.role = 'user'), c.created_at) DESC
    """)

    # Get conversations with active jobs from in-process queue
    job_queue = get_job_queue()
    pending_conversations = set()  # waiting_for_input
    active_conversations = set()   # running or pending
    for job_data in job_queue._job_cache.values():
        status = job_data.get("status")
        conv_id = job_data.get("conversation_id")
        if status == "waiting_for_input":
            pending_conversations.add(conv_id)
        elif status in ("running", "pending"):
            active_conversations.add(conv_id)

    result = []
    for r in rows:
        # Use custom preview if set, otherwise compute from first message
        custom_preview = r.get("custom_preview")
        if custom_preview:
            preview = custom_preview
        else:
            first_msg = r.get("first_message") or ""
            # Truncate to first 50 chars
            preview = first_msg[:50] + "..." if len(first_msg) > 50 else first_msg
        # Add branch suffix for forked conversations
        if r.get("branch_number"):
            preview = f"{preview} - branch (#{r['branch_number']})"
        # Determine if conversation is unread:
        # - read_at is NULL = never opened (scheduled jobs) = unread if has messages
        # - last_message_at > read_at = has new messages since last read = unread
        last_msg_at = r.get("last_message_at")
        read_at = r.get("read_at")
        unread_count = r.get("unread_count", 0) or 0
        is_unread = unread_count > 0
        result.append({
            "id": r["id"],
            "created_at": r["created_at"],
            "last_message_at": last_msg_at,
            "last_user_message_at": r.get("last_user_message_at"),
            "read_at": read_at,
            "is_unread": is_unread,
            "unread_count": unread_count,
            "preview": preview,
            "first_message_preview": (first_msg or "")[:80],
            "has_pending_question": r["id"] in pending_conversations,
            "has_active_job": r["id"] in active_conversations,
            "scheduler_id": r.get("scheduler_id"),
            "is_scheduler_run": bool(r.get("is_scheduler_run"))
        })

    return result


def _strip_internal_blocks(content: str) -> str:
    """Remove internal agent blocks (<thinking>, <plan>, <reflection>) from content."""
    if not content:
        return ""
    result = content
    result = re.sub(r'<thinking>.*?</thinking>\s*', '', result, flags=re.DOTALL)
    result = re.sub(r'<plan>.*?</plan>\s*', '', result, flags=re.DOTALL)
    result = re.sub(r'<reflection>.*?</reflection>\s*', '', result, flags=re.DOTALL)
    return result.strip()


@app.get("/conversations/{conversation_id}/messages")
def get_conversation_messages(conversation_id: str):
    """Get all messages for a conversation."""
    # Check if conversation exists and get read_at
    conv = db.fetchone("SELECT id, read_at FROM conversations WHERE id = ?", (conversation_id,))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = db.fetchall(
        "SELECT id, role, content, metadata, internal, created_at FROM messages WHERE conversation_id = ? ORDER BY id ASC",
        (conversation_id,)
    )

    # Filter to only user and assistant messages with content (exclude internal messages)
    result = []
    for m in messages:
        # Skip internal messages (intermediate tool calls, thinking-only responses)
        if m.get("internal"):
            continue
        if m["role"] in ("user", "assistant") and m.get("content"):
            # Strip internal blocks from assistant messages
            content = m["content"]
            if m["role"] == "assistant":
                content = _strip_internal_blocks(content)
            # Skip if content is empty after stripping
            if not content:
                continue
            msg_data = {
                "id": m["id"],
                "role": m["role"],
                "content": content,
                "created_at": m["created_at"]
            }
            # Include metadata if present (for question messages, etc.)
            if m.get("metadata"):
                try:
                    msg_data["metadata"] = json.loads(m["metadata"])
                except (json.JSONDecodeError, TypeError):
                    pass
            result.append(msg_data)

    return {
        "messages": result,
        "read_at": conv.get("read_at")
    }


@app.post("/conversations/{conversation_id}/fork")
async def fork_conversation(conversation_id: str, payload: dict):
    """Fork a conversation from a specific message.

    Creates a new conversation with all messages up to and including the specified message.
    """
    message_id = payload.get("message_id")
    if message_id is None:
        raise HTTPException(status_code=400, detail="message_id is required")

    new_conv_id = db.fork_conversation(conversation_id, message_id)

    if not new_conv_id:
        raise HTTPException(status_code=404, detail="Conversation or message not found")

    msg_count = db.fetchone(
        "SELECT COUNT(*) as count FROM messages WHERE conversation_id = ?",
        (new_conv_id,)
    )

    log(f"[API] Forked conversation {conversation_id} at msg {message_id} -> {new_conv_id}")

    return {
        "conversation_id": new_conv_id,
        "message_count": msg_count["count"] if msg_count else 0
    }


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation and all its messages."""
    success = db.delete_conversation(conversation_id)

    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")

    log(f"[API] Deleted conversation {conversation_id}")

    return {"ok": True, "conversation_id": conversation_id}


@app.delete("/conversations/{conversation_id}/messages/from/{message_id}")
async def delete_messages_from(conversation_id: str, message_id: int):
    """Delete a message and all messages after it in a conversation."""
    deleted = db.delete_messages_from(conversation_id, message_id)

    if deleted == 0:
        raise HTTPException(status_code=404, detail="Message not found")

    log(f"[API] Deleted {deleted} messages from conversation {conversation_id} starting at message {message_id}")

    return {"ok": True, "deleted_count": deleted}


@app.patch("/conversations/{conversation_id}")
async def rename_conversation(conversation_id: str, data: dict):
    """Rename a conversation (update preview/title)."""
    preview = data.get("preview")
    if not preview or not preview.strip():
        raise HTTPException(status_code=400, detail="preview is required")

    result = db.execute(
        "UPDATE conversations SET preview = ? WHERE id = ?",
        (preview.strip(), conversation_id)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")

    log(f"[API] Renamed conversation {conversation_id} to '{preview.strip()}'")
    return {"ok": True, "conversation_id": conversation_id, "preview": preview.strip()}


@app.get("/conversations/{conversation_id}/cost")
async def get_conversation_cost(conversation_id: str):
    """Get the total cost for a conversation."""
    return db.get_conversation_cost(conversation_id)


@app.post("/conversations/{conversation_id}/archive")
async def archive_conversation(conversation_id: str):
    """Archive a conversation (soft delete)."""
    result = db.execute(
        "UPDATE conversations SET is_archived = 1 WHERE id = ?",
        (conversation_id,)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")
    log(f"[API] Archived conversation {conversation_id}")
    return {"ok": True, "conversation_id": conversation_id}


@app.post("/conversations/{conversation_id}/restore")
async def restore_conversation(conversation_id: str):
    """Restore an archived conversation."""
    result = db.execute(
        "UPDATE conversations SET is_archived = 0 WHERE id = ?",
        (conversation_id,)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")
    log(f"[API] Restored conversation {conversation_id}")
    return {"ok": True, "conversation_id": conversation_id}


@app.post("/conversations/{conversation_id}/read")
async def mark_conversation_read(conversation_id: str):
    """Mark a conversation as read."""
    # Validate UUID format
    try:
        uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")

    now = DB.now()
    result = db.execute(
        "UPDATE conversations SET read_at = ? WHERE id = ?",
        (now, conversation_id)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"ok": True, "conversation_id": conversation_id, "read_at": now}


@app.post("/conversations/{conversation_id}/unread")
async def mark_conversation_unread(conversation_id: str, payload: dict):
    """Mark a conversation as unread from a specific message timestamp.

    Sets read_at to 1 second before the given timestamp so that message
    and all following messages appear as unread.
    """
    # Validate UUID format
    try:
        uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")

    before_timestamp = payload.get("before_timestamp")
    if not before_timestamp:
        raise HTTPException(status_code=400, detail="before_timestamp is required")

    # Parse and subtract 1 second to mark this message as unread
    try:
        dt = datetime.fromisoformat(before_timestamp.replace('Z', '+00:00'))
        # Subtract 1 second
        new_read_at = (dt - timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%S.%f') + 'Z'
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid timestamp format")

    result = db.execute(
        "UPDATE conversations SET read_at = ? WHERE id = ?",
        (new_read_at, conversation_id)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"ok": True, "conversation_id": conversation_id, "read_at": new_read_at}


@app.get("/conversations/archived")
def list_archived_conversations():
    """List all archived conversations."""
    rows = db.fetchall("""
        SELECT
            c.id,
            c.created_at,
            c.forked_from,
            c.branch_number,
            c.preview as custom_preview,
            (SELECT MAX(m.created_at) FROM messages m WHERE m.conversation_id = c.id) as last_message_at,
            (SELECT m.content FROM messages m WHERE m.conversation_id = c.id AND m.role = 'user' ORDER BY m.id ASC LIMIT 1) as first_message
        FROM conversations c
        WHERE c.is_archived = 1
        ORDER BY COALESCE((SELECT MAX(m.created_at) FROM messages m WHERE m.conversation_id = c.id), c.created_at) DESC
    """)

    result = []
    for r in rows:
        # Use custom preview if set, otherwise compute from first message
        custom_preview = r.get("custom_preview")
        if custom_preview:
            preview = custom_preview
        else:
            first_msg = r.get("first_message") or ""
            preview = first_msg[:50] + "..." if len(first_msg) > 50 else first_msg
        if r.get("branch_number"):
            preview = f"{preview} - branch (#{r['branch_number']})"
        result.append({
            "id": r["id"],
            "created_at": r["created_at"],
            "last_message_at": r.get("last_message_at"),
            "preview": preview
        })

    return result


@app.get("/apps")
def list_apps(request: Request):
    """List all created apps with their status."""
    rows = db.fetchall(
        "SELECT app_id, name, port, cwd, status, api_token, created_at FROM apps ORDER BY created_at DESC"
    )

    return [
        {
            **r,
            "alive": supervisor.is_alive(r["app_id"]),
            "url": get_app_url(r["app_id"]),
        }
        for r in rows
    ]


# --- Artifacts Endpoints ---

os.makedirs(settings.artifacts_dir, exist_ok=True)

@app.get("/artifacts")
def list_artifacts(path: str = ""):
    """List artifacts in /workspace/artifacts (supports subdirectories via 'path')."""
    # Prevent directory traversal
    safe_path = os.path.abspath(os.path.join(settings.artifacts_dir, path.lstrip("/")))
    if not safe_path.startswith(os.path.abspath(settings.artifacts_dir)):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not os.path.exists(safe_path):
        raise HTTPException(status_code=404, detail="Path not found")
        
    if not os.path.isdir(safe_path):
        raise HTTPException(status_code=400, detail="Path is not a directory")

    entries = []
    for entry in os.scandir(safe_path):
        # Calculate relative path for download/navigation
        rel_path = os.path.relpath(entry.path, settings.artifacts_dir)
        
        entries.append({
            "name": entry.name,
            "path": rel_path,
            "is_dir": entry.is_dir(),
            "size": entry.stat().st_size if entry.is_file() else 0,
            "mtime": entry.stat().st_mtime,
            "download_url": f"/artifacts/{rel_path}" if entry.is_file() else None
        })
    
    # Sort by directory first, then name
    entries.sort(key=lambda x: (not x["is_dir"], x["name"]))
    return entries


@app.get("/artifacts/search")
def search_artifacts(q: str = ""):
    """Search for files recursively in /workspace/artifacts."""
    if not q or len(q) < 1:
        return []

    query = q.lower()
    results = []

    def search_recursive(dir_path: str):
        """Recursively search directory for files matching query."""
        try:
            for entry in os.scandir(dir_path):
                if entry.is_file():
                    if query in entry.name.lower():
                        rel_path = os.path.relpath(entry.path, settings.artifacts_dir)
                        results.append({
                            "name": entry.name,
                            "path": rel_path,
                            "is_dir": False,
                            "size": entry.stat().st_size,
                            "mtime": entry.stat().st_mtime,
                            "download_url": f"/artifacts/{rel_path}"
                        })
                elif entry.is_dir():
                    search_recursive(entry.path)
        except PermissionError:
            pass

    search_recursive(settings.artifacts_dir)

    # Sort by name and limit results
    results.sort(key=lambda x: x["name"].lower())
    return results[:20]


@app.get("/artifacts/{path:path}/download-zip")
def download_folder_as_zip(path: str):
    """Download a folder as a ZIP archive."""
    import zipfile
    import io

    # Prevent directory traversal
    safe_path = os.path.abspath(os.path.join(settings.artifacts_dir, path))
    if not safe_path.startswith(os.path.abspath(settings.artifacts_dir)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(safe_path):
        raise HTTPException(status_code=404, detail="Path not found")

    if not os.path.isdir(safe_path):
        raise HTTPException(status_code=400, detail="Path is not a directory")

    folder_name = os.path.basename(safe_path)

    def generate_zip():
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(safe_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, safe_path)
                    zf.write(file_path, arc_name)
        buffer.seek(0)
        return buffer.getvalue()

    zip_content = generate_zip()
    encoded_filename = urllib.parse.quote(f"{folder_name}.zip")

    return StreamingResponse(
        iter([zip_content]),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
            "Content-Length": str(len(zip_content))
        }
    )


@app.get("/artifacts/{path:path}")
def download_artifact(path: str, range: str = Header(None)):
    """Download or stream an artifact file with Range request support."""
    safe_path = os.path.abspath(os.path.join(settings.artifacts_dir, path))
    if not safe_path.startswith(os.path.abspath(settings.artifacts_dir)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.isfile(safe_path):
        raise HTTPException(status_code=404, detail="File not found")

    file_size = os.path.getsize(safe_path)
    filename = os.path.basename(safe_path)

    # Detect MIME type
    mime_type, _ = mimetypes.guess_type(safe_path)
    if mime_type is None:
        mime_type = "application/octet-stream"

    # URL-encode filename for Content-Disposition header (RFC 5987)
    from urllib.parse import quote
    encoded_filename = quote(filename)

    # Use inline for streamable media types, attachment for others
    streamable_types = ('video/', 'audio/', 'image/', 'application/pdf')
    disposition = "inline" if any(mime_type.startswith(t) for t in streamable_types) else "attachment"

    # Handle Range requests for video/audio streaming
    if range:
        # Parse Range header: "bytes=start-end"
        range_match = re.match(r'bytes=(\d*)-(\d*)', range)
        if range_match:
            start_str, end_str = range_match.groups()
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else file_size - 1

            # Validate range
            if start >= file_size:
                raise HTTPException(status_code=416, detail="Range not satisfiable")
            end = min(end, file_size - 1)
            content_length = end - start + 1

            def iter_file():
                with open(safe_path, "rb") as f:
                    f.seek(start)
                    remaining = content_length
                    while remaining > 0:
                        chunk_size = min(8192, remaining)
                        data = f.read(chunk_size)
                        if not data:
                            break
                        remaining -= len(data)
                        yield data

            return StreamingResponse(
                iter_file(),
                status_code=206,
                media_type=mime_type,
                headers={
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(content_length),
                    "Content-Disposition": f"{disposition}; filename*=UTF-8''{encoded_filename}"
                }
            )

    # Full file response
    return StreamingResponse(
        open(safe_path, "rb"),
        media_type=mime_type,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Content-Disposition": f"{disposition}; filename*=UTF-8''{encoded_filename}"
        }
    )


MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB


@app.post("/artifacts")
async def upload_artifact(file: UploadFile = File(...), path: str = Form("")):
    """Upload a file to /workspace/artifacts (or subfolder)."""
    # Check file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large (max {MAX_UPLOAD_SIZE // (1024 * 1024)}MB)")

    # Resolve target directory
    target_dir = os.path.abspath(os.path.join(settings.artifacts_dir, path.lstrip("/")))
    if not target_dir.startswith(os.path.abspath(settings.artifacts_dir)):
        raise HTTPException(status_code=403, detail="Access denied")
        
    os.makedirs(target_dir, exist_ok=True)

    # Generate unique filename if file already exists
    base_name, ext = os.path.splitext(file.filename)
    file_path = os.path.join(target_dir, file.filename)
    counter = 1
    while os.path.exists(file_path):
        file_path = os.path.join(target_dir, f"{base_name}_{counter}{ext}")
        counter += 1
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")
        
    return {"ok": True, "path": os.path.relpath(file_path, settings.artifacts_dir)}


@app.delete("/artifacts/{path:path}")
def delete_artifact(path: str):
    """Delete an artifact file or directory."""
    safe_path = os.path.abspath(os.path.join(settings.artifacts_dir, path))
    if not safe_path.startswith(os.path.abspath(settings.artifacts_dir)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(safe_path):
        raise HTTPException(status_code=404, detail="Path not found")

    try:
        if os.path.isdir(safe_path):
            shutil.rmtree(safe_path)
        else:
            os.remove(safe_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {e}")

    return {"ok": True, "path": path}


@app.patch("/artifacts/{path:path}")
async def move_artifact(path: str, request: Request):
    """Move/rename an artifact to a new location."""
    data = await request.json()
    new_path = data.get("new_path")

    if not new_path:
        raise HTTPException(status_code=400, detail="new_path is required")

    # Validate source path
    safe_source = os.path.abspath(os.path.join(settings.artifacts_dir, path))
    if not safe_source.startswith(os.path.abspath(settings.artifacts_dir)):
        raise HTTPException(status_code=403, detail="Access denied")

    # Validate destination path
    safe_dest = os.path.abspath(os.path.join(settings.artifacts_dir, new_path.lstrip("/")))
    if not safe_dest.startswith(os.path.abspath(settings.artifacts_dir)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(safe_source):
        raise HTTPException(status_code=404, detail="Source not found")

    if os.path.exists(safe_dest):
        raise HTTPException(status_code=409, detail="Destination already exists")

    # Ensure destination parent directory exists
    dest_parent = os.path.dirname(safe_dest)
    if not os.path.exists(dest_parent):
        raise HTTPException(status_code=400, detail="Destination folder does not exist")

    try:
        shutil.move(safe_source, safe_dest)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Move failed: {e}")

    return {"ok": True, "old_path": path, "new_path": new_path}


@app.post("/artifacts/directory")
async def create_directory(request: Request):
    """Create a new directory in /workspace/artifacts."""
    data = await request.json()
    path = data.get("path")

    if not path:
        raise HTTPException(status_code=400, detail="path is required")

    # Prevent directory traversal
    safe_path = os.path.abspath(os.path.join(settings.artifacts_dir, path.lstrip("/")))
    if not safe_path.startswith(os.path.abspath(settings.artifacts_dir)):
        raise HTTPException(status_code=403, detail="Access denied")

    if os.path.exists(safe_path):
        raise HTTPException(status_code=409, detail="Path already exists")

    try:
        os.makedirs(safe_path, exist_ok=False)
    except FileExistsError:
        raise HTTPException(status_code=409, detail="Path already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create directory: {e}")

    return {"ok": True, "path": path}


@app.put("/artifacts/content")
async def save_artifact_content(request: Request):
    """Save text content to a file (for Notion-like editor)."""
    data = await request.json()
    path = data.get("path")
    content = data.get("content")

    if not path:
        raise HTTPException(status_code=400, detail="path is required")
    if content is None:
        raise HTTPException(status_code=400, detail="content is required")

    # Prevent directory traversal
    safe_path = os.path.abspath(os.path.join(settings.artifacts_dir, path.lstrip("/")))
    if not safe_path.startswith(os.path.abspath(settings.artifacts_dir)):
        raise HTTPException(status_code=403, detail="Access denied")

    # Ensure parent directory exists
    os.makedirs(os.path.dirname(safe_path), exist_ok=True)

    try:
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Save failed: {e}")

    return {"ok": True, "path": path}


@app.post("/apps/{app_id}/__stop")
def stop_app(app_id: str):
    """Stop a running app."""
    supervisor.stop(app_id)
    db.execute("UPDATE apps SET status=? WHERE app_id=?", ("stopped", app_id))
    return {"ok": True, "app_id": app_id}


@app.post("/apps/{app_id}/__start")
def start_app(app_id: str):
    """Start a stopped app."""
    # We just set status to running in DB, and let supervisor reconcile it.
    db.execute("UPDATE apps SET status=? WHERE app_id=?", ("running", app_id))
    supervisor.reconcile() # Force immediate check
    return {"ok": True, "app_id": app_id}


@app.post("/apps/{app_id}/__restart")
def restart_app(app_id: str):
    """Restart an app."""
    supervisor.stop(app_id)
    db.execute("UPDATE apps SET status=? WHERE app_id=?", ("running", app_id))
    supervisor.reconcile() # Force immediate check
    return {"ok": True, "app_id": app_id}


@app.patch("/apps/{app_id}")
def update_app(app_id: str, data: dict):
    """Update app details (name, cmd, cwd). Auto-restarts if cmd/cwd changed."""
    # Check if app exists
    existing = db.fetchone("SELECT app_id, status FROM apps WHERE app_id=?", (app_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="App not found")

    updated_fields = []
    needs_restart = False

    # Update name if provided
    if "name" in data:
        name = data["name"]
        if name and name.strip():
            db.execute("UPDATE apps SET name=? WHERE app_id=?", (name.strip(), app_id))
            updated_fields.append("name")

    # Update cmd if provided
    if "cmd" in data:
        cmd = data["cmd"]
        if cmd:
            # Store as JSON list (supervisor expects list of strings)
            cmd_json = json.dumps(cmd.split()) if isinstance(cmd, str) else json.dumps(cmd)
            db.execute("UPDATE apps SET cmd=? WHERE app_id=?", (cmd_json, app_id))
            updated_fields.append("cmd")
            needs_restart = True

    # Update cwd if provided
    if "cwd" in data:
        cwd = data["cwd"]
        if cwd:
            cwd_abs = os.path.abspath(cwd)
            if not os.path.exists(cwd_abs):
                raise HTTPException(status_code=400, detail=f"Directory not found: {cwd_abs}")
            db.execute("UPDATE apps SET cwd=? WHERE app_id=?", (cwd_abs, app_id))
            updated_fields.append("cwd")
            needs_restart = True

    if not updated_fields:
        raise HTTPException(status_code=400, detail="No valid fields to update (name, cmd, cwd)")

    # Auto-restart if cmd or cwd changed and app was running
    if needs_restart and existing["status"] == "running":
        supervisor.stop(app_id)
        supervisor.reconcile()

    return {
        "ok": True,
        "app_id": app_id,
        "updated_fields": updated_fields,
        "restarted": needs_restart and existing["status"] == "running"
    }


@app.delete("/apps/{app_id}")
def delete_app(app_id: str):
    """Delete an app (stops it first if running)."""
    # Check if app exists
    existing = db.fetchone("SELECT app_id FROM apps WHERE app_id=?", (app_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="App not found")

    # Stop the app if running
    supervisor.stop(app_id)

    # Delete from database
    db.execute("DELETE FROM apps WHERE app_id=?", (app_id,))
    return {"ok": True, "app_id": app_id}


@app.get("/apps/{app_id}/__logs")
def get_app_logs(app_id: str, lines: int = 100):
    """Get logs from a running app."""
    existing = db.fetchone("SELECT app_id, status FROM apps WHERE app_id=?", (app_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="App not found")

    if existing["status"] != "running":
        return {"app_id": app_id, "logs": "", "line_count": 0, "note": "App is not running"}

    logs = supervisor.tail_logs(app_id, max_lines=lines)
    return {
        "app_id": app_id,
        "logs": logs,
        "line_count": len(logs.split('\n')) if logs else 0
    }


# --- Internal API (for apps) ---

def _verify_localhost(request: Request):
    """Only localhost can call internal API."""
    host = request.client.host if request.client else None
    if host not in ("127.0.0.1", "::1"):
        raise HTTPException(status_code=403, detail="Forbidden - localhost only")


def _get_app_from_token(authorization: str) -> dict:
    """Return app record or raise 401."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = authorization[7:]
    app_record = db.get_app_by_token(token)
    if not app_record:
        raise HTTPException(status_code=401, detail="Invalid token")
    return app_record


@app.get("/internal/skills/list")
async def internal_skills_list(request: Request):
    """List available skills for apps - dynamic discovery."""
    _verify_localhost(request)
    # Token verification optional for list - just localhost check
    return {"skills": internal_skills.list_skills()}


@app.post("/internal/skills/execute")
async def internal_skills_execute(request: Request):
    """Execute a skill script."""
    _verify_localhost(request)
    authorization = request.headers.get("Authorization", "")
    app_record = _get_app_from_token(authorization)

    data = await request.json()
    skill = data.get("skill")
    script = data.get("script")
    args = data.get("args", {})

    if not skill or not script:
        raise HTTPException(status_code=400, detail="skill and script required")

    return internal_skills.execute_skill(
        skill=skill,
        script=script,
        args=args,
        app_id=app_record["app_id"],
        db=db
    )


@app.post("/internal/llm/chat")
async def internal_llm_chat(request: Request):
    """Call LLM for apps."""
    _verify_localhost(request)
    authorization = request.headers.get("Authorization", "")
    app_record = _get_app_from_token(authorization)

    data = await request.json()
    messages = data.get("messages")
    model = data.get("model", "cheap")

    if not messages:
        raise HTTPException(status_code=400, detail="messages required")

    return internal_llm.chat(
        messages=messages,
        model=model,
        app_id=app_record["app_id"],
        db=db
    )


# --- Container Restart ---

RESTART_COOLDOWN_SECONDS = 60
MAX_JOB_WAIT_SECONDS = 30


@app.get("/container/restart-status")
async def get_container_restart_status():
    """
    Get container restart cooldown status.

    Returns: {"cooldown_remaining": <seconds> or 0, "last_restart": <ISO timestamp> or null}
    """
    last_restart = db.fetchone(
        "SELECT value FROM app_state WHERE key = ?",
        ("last_container_restart",)
    )

    if not last_restart:
        return {"cooldown_remaining": 0, "last_restart": None}

    last_time = datetime.fromisoformat(last_restart["value"])
    elapsed = (datetime.utcnow() - last_time).total_seconds()
    remaining = max(0, int(RESTART_COOLDOWN_SECONDS - elapsed))

    return {
        "cooldown_remaining": remaining,
        "last_restart": last_restart["value"]
    }


@app.post("/container/restart")
async def restart_container():
    """
    Restart the container gracefully.

    1. Check cooldown (60s since last restart)
    2. Wait for active jobs to complete (max 30s)
    3. Trigger container restart via os._exit(0)

    Returns: {"status": "restarting", "wait_time": <seconds waited for jobs>}
    """
    # Check cooldown
    last_restart = db.fetchone(
        "SELECT value FROM app_state WHERE key = ?",
        ("last_container_restart",)
    )

    if last_restart:
        last_time = datetime.fromisoformat(last_restart["value"])
        elapsed = (datetime.utcnow() - last_time).total_seconds()
        if elapsed < RESTART_COOLDOWN_SECONDS:
            remaining = int(RESTART_COOLDOWN_SECONDS - elapsed)
            raise HTTPException(
                status_code=429,
                detail=f"Cooldown active. Try again in {remaining} seconds."
            )

    # Wait for active jobs to complete (max 30s)
    wait_start = time.time()

    while time.time() - wait_start < MAX_JOB_WAIT_SECONDS:
        running_jobs = db.fetchall(
            "SELECT id FROM jobs WHERE status IN ('pending', 'running')"
        )
        if not running_jobs:
            break
        await asyncio.sleep(1)

    wait_time = int(time.time() - wait_start)

    # Record restart time
    db.execute(
        """INSERT OR REPLACE INTO app_state (key, value, updated_at)
           VALUES (?, ?, ?)""",
        ("last_container_restart", datetime.utcnow().isoformat(), DB.now())
    )

    # Schedule exit after response is sent
    async def delayed_exit():
        await asyncio.sleep(0.5)  # Allow response to complete
        log("[Restart] Container restart initiated by user")
        # Send SIGTERM to PID 1 (uvicorn --reload watcher) to trigger container restart
        os.kill(1, signal.SIGTERM)

    asyncio.create_task(delayed_exit())

    return {"status": "restarting", "wait_time": wait_time}


@app.post("/chat")
async def chat(payload: dict):
    """
    Chat with the agent (async via job queue).

    Expects: {"message": "...", "conversation_id": "..." (optional)}
    Returns: {"job_id": "...", "conversation_id": "..."}
    """
    message = payload.get("message")
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    try:
        conversation_id = payload.get("conversation_id")
        if not conversation_id:
            # Create a new conversation
            conversation_id = str(uuid.uuid4())
            now = DB.now()
            db.execute(
                "INSERT INTO conversations(id, created_at, read_at) VALUES (?, ?, ?)",
                (conversation_id, now, now),
            )

        # Store user message and get its ID
        db.save_message_from_dict(conversation_id, {"role": "user", "content": message})

        # Get the message ID (last inserted message in this conversation)
        msg_row = db.fetchone(
            "SELECT id FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT 1",
            (conversation_id,)
        )
        message_id = msg_row["id"] if msg_row else None

        # Log user message to console
        log_user_message(message)

        # Create and enqueue job via in-process queue
        job_id = str(uuid.uuid4())
        job_queue = get_job_queue()
        job_queue.create_job(job_id, conversation_id, message)
        job_queue.enqueue(job_id)

        log(f"[API] Created job {job_id} for conversation {conversation_id}")

        return {
            "job_id": job_id,
            "conversation_id": conversation_id,
            "message_id": message_id
        }
    except Exception as e:
        log(f"[API] Error in /chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    since_activity_id: int = None,
    include_detail: bool = False
):
    """
    Get job status and activity log.

    Args:
        job_id: Job identifier
        since_activity_id: Only return activities after this ID (for incremental polling)
        include_detail: Include full detail field (for thinking/planning)
    """
    job_queue = get_job_queue()
    job_data = job_queue.get_job(job_id)

    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")

    import json as _json
    # Parse question_options if present
    question_options = None
    if job_data.get("question_options"):
        try:
            question_options = _json.loads(job_data["question_options"])
        except (_json.JSONDecodeError, TypeError):
            pass

    job_response = {
        "id": job_data.get("id"),
        "conversation_id": job_data.get("conversation_id"),
        "status": job_data.get("status"),
        "result": job_data.get("result") or None,
        "error": job_data.get("error") or None,
        "created_at": job_data.get("created_at"),
        "started_at": job_data.get("started_at") or None,
        "completed_at": job_data.get("completed_at") or None,
        # ask_user support
        "question": job_data.get("question") or None,
        "question_options": question_options,
    }

    # Get activities from SQLite
    activities = db.get_job_activities(
        job_id,
        limit=100,
        since_id=since_activity_id,
        include_detail=include_detail
    )

    # Determine "current" activity (last in-progress operation)
    current = None
    for a in reversed(activities):
        if a.type in ("tool_call", "delegate_start", "llm_call"):
            current = {"type": a.type, "tool_name": a.tool_name, "message": a.message}
            break
        elif a.type in ("tool_result", "delegate_end", "llm_response", "complete"):
            break  # Operation completed, no current activity

    # Get related question suggestions
    suggestions = job_queue.get_suggestions(job_id)

    # Add activities to response
    job_response["activities"] = [
        {
            "id": a.id,
            "timestamp": a.timestamp,
            "type": a.type,
            "message": a.message,
            "detail": a.detail if include_detail else (a.detail[:200] + "..." if a.detail and len(a.detail) > 200 else a.detail),
            "tool_name": a.tool_name,
            "is_error": a.is_error
        }
        for a in activities
    ]
    job_response["current"] = current
    job_response["last_activity_id"] = activities[-1].id if activities else None
    job_response["suggestions"] = suggestions

    return job_response


@app.get("/conversations/{conversation_id}/active-job")
async def get_active_job(conversation_id: str):
    """
    Check if there's an active (pending/running/waiting) job for this conversation.

    Returns:
        {"job_id": "...", "status": "..."} if active job exists
        {"job_id": null} if no active job
    """
    job_queue = get_job_queue()
    active_job = job_queue.get_active_job_for_conversation(conversation_id)

    if active_job:
        return {
            "job_id": active_job.get("id"),
            "status": active_job.get("status")
        }

    return {"job_id": None}


@app.post("/jobs/{job_id}/respond")
async def respond_to_job(job_id: str, payload: dict):
    """
    User responds to ask_user question.

    Expects: {"response": "user's answer"}
    Returns: {"status": "ok"}
    """
    response = payload.get("response")
    if not response:
        raise HTTPException(status_code=400, detail="response is required")

    job_queue = get_job_queue()

    # Verify job exists and is waiting for input
    job_data = job_queue.get_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")

    if job_data.get("status") != "waiting_for_input":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not waiting for input (status: {job_data.get('status')})"
        )

    # Set the response - this will resume the agent
    job_queue.set_response(job_id, response)

    log(f"[API] User responded to job {job_id}: {response[:50]}...")

    return {"status": "ok"}


@app.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """
    Cancel a running or pending job.

    The cancellation is asynchronous - the agent will check the cancellation
    flag at the start of each iteration and stop gracefully.

    Returns: {"status": "cancelling"}
    """
    job_queue = get_job_queue()

    # Verify job exists
    job_data = job_queue.get_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")

    current_status = job_data.get("status")
    if current_status not in ("pending", "running", "waiting_for_input"):
        raise HTTPException(
            status_code=400,
            detail=f"Job cannot be cancelled (status: {current_status})"
        )

    # Set cancellation flag - agent will check this
    job_queue.cancel(job_id)

    log(f"[API] Job {job_id} marked for cancellation")

    return {"status": "cancelling"}


# --- Scheduled Jobs Endpoints (A.7) ---

@app.get("/scheduled-jobs")
async def list_scheduled_jobs():
    """List all scheduled jobs."""
    jobs = db.get_scheduled_jobs()
    return jobs


@app.get("/scheduled-jobs/{job_id}")
async def get_scheduled_job(job_id: str):
    """Get a scheduled job with run history."""
    job = db.get_scheduled_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scheduled job not found")

    # Get run history
    runs = db.get_scheduled_job_runs(job_id, limit=10)
    job["runs"] = runs

    return job


@app.patch("/scheduled-jobs/{job_id}")
async def update_scheduled_job(job_id: str, payload: UpdateScheduledJobRequest):
    """Update a scheduled job (toggle enable/disable, etc.)."""
    job = db.get_scheduled_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scheduled job not found")

    scheduler = get_scheduler()

    # Build updates dict from non-None fields
    updates = {}
    if payload.is_enabled is not None:
        updates["is_enabled"] = payload.is_enabled
        # Enable/disable in scheduler
        if payload.is_enabled:
            scheduler.enable_job(job_id)
        else:
            scheduler.disable_job(job_id)

    if payload.name is not None:
        updates["name"] = payload.name
    if payload.prompt is not None:
        updates["prompt"] = payload.prompt
    if payload.cron_expression is not None:
        updates["cron_expression"] = payload.cron_expression
    if payload.schedule_description is not None:
        updates["schedule_description"] = payload.schedule_description

    # Update in database (scheduler.enable/disable already updates is_enabled)
    if updates and "is_enabled" not in updates:
        db.update_scheduled_job(job_id, updates)

    return {"status": "ok", "job_id": job_id}


@app.delete("/scheduled-jobs/{job_id}")
async def delete_scheduled_job(job_id: str):
    """Delete a scheduled job."""
    job = db.get_scheduled_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scheduled job not found")

    scheduler = get_scheduler()
    scheduler.remove_scheduled_job(job_id)

    return {"status": "ok", "job_id": job_id}


@app.post("/scheduled-jobs/{job_id}/trigger")
async def trigger_scheduled_job(job_id: str):
    """Manually trigger a scheduled job (for testing)."""
    job = db.get_scheduled_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scheduled job not found")

    scheduler = get_scheduler()
    result = scheduler.trigger_job(job_id)

    if not result:
        raise HTTPException(status_code=500, detail="Failed to trigger job")

    created_job_id, conversation_id = result
    return {"status": "ok", "scheduled_job_id": job_id, "job_id": created_job_id, "conversation_id": conversation_id}


@app.get("/scheduled-jobs/{job_id}/runs")
async def get_scheduled_job_runs(job_id: str, limit: int = 20):
    """Get conversations created by a scheduler."""
    job = db.get_scheduled_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scheduled job not found")

    # Get conversations created by this scheduler
    conversations = db.get_scheduler_conversations(job_id, limit)

    # Truncate last_response preview
    for conv in conversations:
        last_resp = conv.get("last_response") or ""
        conv["preview"] = last_resp[:100] + "..." if len(last_resp) > 100 else last_resp

    return {
        "scheduler_id": job_id,
        "scheduler_name": job.get("name"),
        "conversations": conversations
    }


@app.get("/scheduled-jobs/{job_id}/details")
async def get_scheduled_job_details(job_id: str):
    """Get full details for a scheduled job including context and files."""
    import json
    import os

    job = db.get_scheduled_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scheduled job not found")

    # Get run history
    runs = db.get_scheduled_job_runs(job_id, limit=10)
    job["runs"] = runs

    # Get linked conversations
    conversations = db.get_scheduler_conversations(job_id, limit=10)
    job["conversations"] = conversations

    # Parse context_json
    if job.get("context_json"):
        try:
            job["context"] = json.loads(job["context_json"])
        except json.JSONDecodeError:
            job["context"] = None
    else:
        job["context"] = None

    # List files in files_dir if exists
    files_dir = job.get("files_dir")
    if files_dir and os.path.isdir(files_dir):
        try:
            job["files"] = os.listdir(files_dir)
        except Exception:
            job["files"] = []
    else:
        job["files"] = []

    return job


@app.patch("/scheduled-jobs/{job_id}/schedule")
async def update_scheduled_job_schedule(job_id: str, payload: dict):
    """Update the cron schedule of a scheduled job."""
    from user_container.scheduler.cron_utils import parse_cron, get_next_run

    job = db.get_scheduled_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scheduled job not found")

    cron_expression = payload.get("cron_expression")
    schedule_description = payload.get("schedule_description")

    if not cron_expression:
        raise HTTPException(status_code=400, detail="cron_expression is required")

    # Validate CRON expression
    if not parse_cron(cron_expression):
        raise HTTPException(status_code=400, detail=f"Invalid CRON expression: {cron_expression}")

    # Calculate next run time
    next_run = get_next_run(cron_expression)
    next_run_str = next_run.isoformat() if next_run else None

    updates = {
        "cron_expression": cron_expression,
        "next_run_at": next_run_str
    }
    if schedule_description:
        updates["schedule_description"] = schedule_description

    # Update in database
    db.update_scheduled_job(job_id, updates)

    # Re-register with scheduler
    scheduler = get_scheduler()
    updated_job = db.get_scheduled_job(job_id)
    if updated_job and updated_job.get("is_enabled"):
        scheduler._register_job(updated_job)

    log(f"[API] Updated schedule for job {job_id}: {cron_expression}")

    return {"status": "ok", "job_id": job_id, "next_run_at": next_run_str}


# --- User Settings Endpoints ---

@app.get("/settings")
async def get_settings():
    """
    Get all user settings.

    Returns:
        Dict of setting key-value pairs, with defaults applied.
    """
    all_settings = db.get_all_settings()

    # Apply defaults for known settings
    return {
        "model_provider": all_settings.get("model_provider", "anthropic"),
        # Add more settings here as needed
    }


@app.put("/settings")
async def update_settings(payload: dict):
    """
    Update user settings.

    Expects: {"model_provider": "openai"} (or other valid settings)
    Returns: {"status": "ok", "settings": {...}}
    """
    # Validate model_provider if provided
    if "model_provider" in payload:
        provider = payload["model_provider"]
        if provider not in ("anthropic", "openai"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid model_provider: {provider}. Must be 'anthropic' or 'openai'."
            )
        db.set_setting("model_provider", provider)
        log(f"[Settings] Updated model_provider to {provider}")

    # Return updated settings
    return {
        "status": "ok",
        "settings": {
            "model_provider": db.get_setting("model_provider", "anthropic"),
        }
    }


ALLOWED_API_KEYS = {
    "anthropic_api_key": "ANTHROPIC_API_KEY",
    "openai_api_key": "OPENAI_API_KEY",
    "serper_api_key": "SERPER_API_KEY",
}


def _mask_key(key: str) -> str:
    """Mask an API key showing first 6 and last 4 chars."""
    if not key or len(key) < 12:
        return "***"
    return key[:6] + "..." + key[-4:]


@app.get("/settings/api-keys")
async def get_api_keys():
    """Get API key status (configured or not) with masked preview."""
    keys = {}
    for key_name, env_name in ALLOWED_API_KEYS.items():
        value = getattr(settings, key_name, None)
        keys[key_name] = {
            "configured": bool(value),
            "masked": _mask_key(value) if value else None,
        }
    return {"keys": keys}


@app.put("/settings/api-keys")
async def update_api_keys(payload: dict):
    """Save API keys to ~/.zeno/.env and update in-memory settings."""
    # Validate: only accept known key names
    for key_name in payload:
        if key_name not in ALLOWED_API_KEYS:
            raise HTTPException(status_code=400, detail=f"Unknown key: {key_name}")

    # Read existing .env
    config_dir = Path(os.environ.get("ZENO_CONFIG_DIR", Path.home() / ".zeno"))
    config_dir.mkdir(parents=True, exist_ok=True)
    env_path = config_dir / ".env"

    env_var_names_to_update = {ALLOWED_API_KEYS[k] for k in payload}

    env_lines = []
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                stripped = line.strip()
                # Skip lines for keys we're updating
                if any(stripped.startswith(f"{env_name}=") for env_name in env_var_names_to_update):
                    continue
                env_lines.append(line.rstrip("\n"))

    # Add new key values
    for key_name, value in payload.items():
        value = value.strip() if isinstance(value, str) else ""
        env_name = ALLOWED_API_KEYS[key_name]
        if value:
            env_lines.append(f"{env_name}={value}")
            # Update in-memory settings
            setattr(settings, key_name, value)
        else:
            # Empty value = remove key
            setattr(settings, key_name, None)

    with open(env_path, "w") as f:
        f.write("\n".join(env_lines) + "\n")

    log(f"[Settings] Updated API keys: {list(payload.keys())}")
    return {"status": "ok"}


@app.get("/settings/validate-provider")
async def validate_provider(provider: str):
    """
    Validate that API key is configured for the specified provider.

    Query param: ?provider=anthropic or ?provider=openai
    Returns: {"valid": true/false, "error": "message if invalid"}
    """
    from user_container.config import settings as app_settings

    if provider not in ("anthropic", "openai"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider: {provider}. Must be 'anthropic' or 'openai'."
        )

    if provider == "anthropic":
        if not app_settings.anthropic_api_key:
            return {"valid": False, "error": "Anthropic API key is not configured"}
    elif provider == "openai":
        if not app_settings.openai_api_key:
            return {"valid": False, "error": "OpenAI API key is not configured"}

    return {"valid": True}


# --- Admin Panel ---
# Mount admin router (HTTP Basic Auth protected)
app.include_router(admin_module.router)


# --- Frontend Static Files ---
# Serve built frontend (searches multiple locations for native/Docker/bundled mode)

def _find_frontend_dir() -> Path:
    """Find frontend/dist in various locations."""
    candidates = [
        Path(__file__).parent.parent / "frontend" / "dist",  # Running from source (repo root)
        Path("/app/frontend/dist"),  # Docker
    ]
    # PyInstaller bundle
    if getattr(sys, 'frozen', False):
        candidates.insert(0, Path(sys._MEIPASS) / "frontend" / "dist")
    for p in candidates:
        if p.exists():
            return p
    return Path("/app/frontend/dist")  # Fallback (won't exist, mount will be skipped)

FRONTEND_DIR = _find_frontend_dir()

# Only mount if frontend exists (allows running without built frontend during development)
if FRONTEND_DIR.exists():
    # Serve static assets (js, css, etc.)
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    # Serve favicon
    @app.get("/favicon.svg")
    async def favicon():
        favicon_path = FRONTEND_DIR / "favicon.svg"
        if favicon_path.exists():
            return FileResponse(favicon_path)
        raise HTTPException(status_code=404)

    # Catch-all route for SPA - must be LAST
    # Note: This route only handles paths not matched by other routes above
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str, request: Request):
        # API routes are handled above, this is just for SPA routing

        # Try to serve the exact file first (e.g., js, css, images)
        file_path = FRONTEND_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)

        # Otherwise serve index.html for SPA routing
        return FileResponse(FRONTEND_DIR / "index.html")
