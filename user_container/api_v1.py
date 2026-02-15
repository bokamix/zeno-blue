"""External API router for ZENO.

Provides a clean REST API at /api/v1/ for external integrations.
Requires Bearer token authentication (ZENO API key).

Endpoints:
  POST   /api/v1/chat                        - Send a message
  GET    /api/v1/jobs/{job_id}                - Poll job status
  POST   /api/v1/jobs/{job_id}/cancel         - Cancel a job
  GET    /api/v1/conversations                - List conversations
  GET    /api/v1/conversations/{id}/messages   - Get messages
"""

import re
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from user_container.config import settings
from user_container.db.db import DB
from user_container.logger import log

router = APIRouter(prefix="/api/v1", tags=["external-api"])


def _get_db():
    """Lazy import to avoid circular dependency."""
    from user_container.app import db
    return db


def _get_job_queue():
    from user_container.jobs.queue import get_job_queue
    return get_job_queue()


def _envelope(data: dict, request: Request = None) -> dict:
    """Wrap response in standard envelope."""
    return {
        "data": data,
        "meta": {
            "request_id": str(uuid.uuid4())[:8],
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    }


def _strip_internal_blocks(content: str) -> str:
    """Remove internal agent blocks from content."""
    if not content:
        return ""
    result = content
    result = re.sub(r'<thinking>.*?</thinking>\s*', '', result, flags=re.DOTALL)
    result = re.sub(r'<plan>.*?</plan>\s*', '', result, flags=re.DOTALL)
    result = re.sub(r'<reflection>.*?</reflection>\s*', '', result, flags=re.DOTALL)
    return result.strip()


@router.post("/chat")
async def api_chat(payload: dict, request: Request):
    """Send a message to the agent.

    Body:
        message: str (required)
        conversation_id: str (optional - reuse existing conversation)
        headless: bool (optional - auto-respond to ask_user prompts)
        ask_user_default: str (optional - default response for headless mode)
    """
    db = _get_db()
    job_queue = _get_job_queue()

    message = payload.get("message")
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    conversation_id = payload.get("conversation_id")
    headless = payload.get("headless", False)
    ask_user_default = payload.get("ask_user_default", "proceed")

    try:
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            now = DB.now()
            db.execute(
                "INSERT INTO conversations(id, created_at, read_at) VALUES (?, ?, ?)",
                (conversation_id, now, now),
            )

        # Store user message
        db.save_message_from_dict(conversation_id, {"role": "user", "content": message})

        # Create and enqueue job
        job_id = str(uuid.uuid4())
        job_queue.create_job(
            job_id, conversation_id, message,
            headless=headless,
            ask_user_default=ask_user_default,
        )
        job_queue.enqueue(job_id)

        log(f"[API/v1] Created job {job_id} (headless={headless})")

        return _envelope({
            "job_id": job_id,
            "conversation_id": conversation_id,
        }, request)

    except Exception as e:
        log(f"[API/v1] Error in /chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}")
async def api_get_job(job_id: str, request: Request):
    """Get job status."""
    db = _get_db()
    job_queue = _get_job_queue()

    job_data = job_queue.get_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")

    result = {
        "id": job_data.get("id"),
        "conversation_id": job_data.get("conversation_id"),
        "status": job_data.get("status"),
        "result": job_data.get("result") or None,
        "error": job_data.get("error") or None,
        "created_at": job_data.get("created_at"),
        "started_at": job_data.get("started_at") or None,
        "completed_at": job_data.get("completed_at") or None,
    }

    return _envelope(result, request)


@router.post("/jobs/{job_id}/cancel")
async def api_cancel_job(job_id: str, request: Request):
    """Cancel a running job."""
    job_queue = _get_job_queue()

    job_data = job_queue.get_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")

    current_status = job_data.get("status")
    if current_status not in ("pending", "running", "waiting_for_input"):
        raise HTTPException(
            status_code=400,
            detail=f"Job cannot be cancelled (status: {current_status})"
        )

    job_queue.cancel(job_id)
    log(f"[API/v1] Job {job_id} marked for cancellation")

    return _envelope({"status": "cancelling"}, request)


@router.get("/conversations")
async def api_list_conversations(request: Request):
    """List conversations."""
    db = _get_db()

    rows = db.fetchall("""
        SELECT
            c.id,
            c.created_at,
            c.preview as custom_preview,
            (SELECT MAX(m.created_at) FROM messages m WHERE m.conversation_id = c.id) as last_message_at,
            (SELECT m.content FROM messages m WHERE m.conversation_id = c.id AND m.role = 'user' ORDER BY m.id ASC LIMIT 1) as first_message
        FROM conversations c
        WHERE COALESCE(c.is_archived, 0) = 0
        ORDER BY COALESCE((SELECT MAX(m.created_at) FROM messages m WHERE m.conversation_id = c.id), c.created_at) DESC
        LIMIT 50
    """)

    conversations = []
    for r in rows:
        preview = r.get("custom_preview") or (r.get("first_message") or "")[:80]
        conversations.append({
            "id": r["id"],
            "created_at": r["created_at"],
            "last_message_at": r.get("last_message_at"),
            "preview": preview,
        })

    return _envelope({"conversations": conversations}, request)


@router.get("/conversations/{conversation_id}/messages")
async def api_get_messages(conversation_id: str, request: Request):
    """Get messages for a conversation."""
    import json

    db = _get_db()

    conv = db.fetchone("SELECT id FROM conversations WHERE id = ?", (conversation_id,))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = db.fetchall(
        "SELECT id, role, content, metadata, internal, created_at FROM messages WHERE conversation_id = ? ORDER BY id ASC",
        (conversation_id,)
    )

    result = []
    for m in messages:
        if m.get("internal"):
            continue
        if m["role"] in ("user", "assistant") and m.get("content"):
            content = m["content"]
            if m["role"] == "assistant":
                content = _strip_internal_blocks(content)
            if not content:
                continue
            msg_data = {
                "id": m["id"],
                "role": m["role"],
                "content": content,
                "created_at": m["created_at"],
            }
            if m.get("metadata"):
                try:
                    msg_data["metadata"] = json.loads(m["metadata"])
                except (json.JSONDecodeError, TypeError):
                    pass
            result.append(msg_data)

    return _envelope({"messages": result}, request)
