"""
Admin panel for debugging and monitoring.

Provides:
- Dashboard with statistics
- Scheduled jobs list
- Conversations list with full message log
- Job activities viewer
"""

import json
import secrets
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from user_container.config import settings
from user_container.db.db import DB

# --- Setup ---

router = APIRouter(prefix="/admin", tags=["admin"])
security = HTTPBasic()

# Templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Database connection (shared with app.py via dependency)
_db: DB = None


def set_db(db: DB):
    """Set the database instance (called from app.py)."""
    global _db
    _db = db


def get_db() -> DB:
    """Get database instance."""
    if _db is None:
        raise RuntimeError("Admin DB not initialized")
    return _db


# --- HTTP Basic Auth ---

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify HTTP Basic Auth credentials for admin panel."""
    if not settings.admin_password:
        raise HTTPException(
            status_code=401,
            detail="Admin panel not configured (ADMIN_PASSWORD not set)",
            headers={"WWW-Authenticate": "Basic"}
        )

    correct_user = secrets.compare_digest(
        credentials.username.encode("utf-8"),
        settings.admin_username.encode("utf-8")
    )
    correct_pass = secrets.compare_digest(
        credentials.password.encode("utf-8"),
        settings.admin_password.encode("utf-8")
    )

    if not (correct_user and correct_pass):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"}
        )


# --- Endpoints ---

@router.get("", response_class=HTMLResponse)
async def admin_dashboard(request: Request, _=Depends(verify_admin)):
    """Admin dashboard with statistics."""
    db = get_db()

    # Get statistics
    stats = {
        "conversations": db.fetchone("SELECT COUNT(*) as count FROM conversations")["count"],
        "messages": db.fetchone("SELECT COUNT(*) as count FROM messages")["count"],
        "jobs_total": db.fetchone("SELECT COUNT(*) as count FROM jobs")["count"],
        "jobs_completed": db.fetchone("SELECT COUNT(*) as count FROM jobs WHERE status='completed'")["count"],
        "jobs_failed": db.fetchone("SELECT COUNT(*) as count FROM jobs WHERE status='failed'")["count"],
        "scheduled_jobs": db.fetchone("SELECT COUNT(*) as count FROM scheduled_jobs")["count"],
    }

    # Calculate success rate
    if stats["jobs_total"] > 0:
        completed = stats["jobs_completed"]
        failed = stats["jobs_failed"]
        total_finished = completed + failed
        stats["success_rate"] = round(completed / total_finished * 100, 1) if total_finished > 0 else 0
    else:
        stats["success_rate"] = 0

    # Average job duration (for completed jobs)
    avg_duration = db.fetchone("""
        SELECT AVG(
            CAST((julianday(completed_at) - julianday(started_at)) * 86400 AS INTEGER)
        ) as avg_seconds
        FROM jobs
        WHERE status='completed' AND started_at IS NOT NULL AND completed_at IS NOT NULL
    """)
    stats["avg_duration"] = round(avg_duration["avg_seconds"] or 0, 1)

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "stats": stats
    })


@router.get("/scheduled-jobs", response_class=HTMLResponse)
async def admin_scheduled_jobs(request: Request, _=Depends(verify_admin)):
    """List scheduled jobs."""
    db = get_db()

    jobs = db.fetchall("""
        SELECT
            id,
            conversation_id,
            name,
            prompt,
            cron_expression,
            schedule_description,
            is_enabled,
            last_run_at,
            next_run_at,
            run_count,
            created_at
        FROM scheduled_jobs
        ORDER BY created_at DESC
    """)

    return templates.TemplateResponse("admin/scheduled_jobs.html", {
        "request": request,
        "jobs": jobs
    })


@router.get("/conversations", response_class=HTMLResponse)
async def admin_conversations(request: Request, _=Depends(verify_admin)):
    """List all conversations."""
    db = get_db()

    conversations = db.fetchall("""
        SELECT
            c.id,
            c.created_at,
            (SELECT MAX(m.created_at) FROM messages m WHERE m.conversation_id = c.id) as last_message_at,
            (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) as message_count,
            (SELECT m.content FROM messages m WHERE m.conversation_id = c.id AND m.role = 'user' ORDER BY m.id ASC LIMIT 1) as first_message,
            (SELECT COALESCE(SUM(cost_usd), 0) FROM usage_log WHERE conversation_id = c.id) as total_cost,
            -- Cost breakdown by component
            (SELECT COALESCE(SUM(cost_usd), 0) FROM usage_log WHERE conversation_id = c.id AND component = 'agent') as agent_cost,
            (SELECT COALESCE(SUM(cost_usd), 0) FROM usage_log WHERE conversation_id = c.id AND component = 'delegate') as delegate_cost,
            (SELECT COALESCE(SUM(cost_usd), 0) FROM usage_log WHERE conversation_id = c.id AND component = 'explore') as explore_cost,
            -- LLM call counts
            (SELECT COUNT(*) FROM usage_log WHERE conversation_id = c.id AND component = 'agent') as agent_calls,
            (SELECT COUNT(*) FROM usage_log WHERE conversation_id = c.id AND component = 'delegate') as delegate_calls,
            (SELECT COUNT(*) FROM usage_log WHERE conversation_id = c.id AND component = 'explore') as explore_calls
        FROM conversations c
        ORDER BY last_message_at DESC
    """)

    return templates.TemplateResponse("admin/conversations.html", {
        "request": request,
        "conversations": conversations
    })


@router.get("/conversations/{conversation_id}", response_class=HTMLResponse)
async def admin_conversation_detail(
    request: Request,
    conversation_id: str,
    _=Depends(verify_admin)
):
    """View full conversation messages (no truncation)."""
    db = get_db()

    # Check conversation exists
    conv = db.fetchone("SELECT id, created_at FROM conversations WHERE id = ?", (conversation_id,))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get ALL messages (no filtering, no truncation)
    messages = db.fetchall("""
        SELECT
            id,
            role,
            content,
            tool_calls,
            tool_call_id,
            thinking,
            internal,
            created_at
        FROM messages
        WHERE conversation_id = ?
        ORDER BY id ASC
    """, (conversation_id,))

    # Parse tool_calls JSON
    for m in messages:
        if m["tool_calls"]:
            try:
                m["tool_calls_parsed"] = json.loads(m["tool_calls"])
            except json.JSONDecodeError:
                m["tool_calls_parsed"] = None
        else:
            m["tool_calls_parsed"] = None

    # Get related jobs
    jobs = db.fetchall("""
        SELECT id, status, created_at, completed_at
        FROM jobs
        WHERE conversation_id = ?
        ORDER BY created_at DESC
    """, (conversation_id,))

    return templates.TemplateResponse("admin/conversation_detail.html", {
        "request": request,
        "conversation": conv,
        "messages": messages,
        "jobs": jobs
    })


@router.get("/jobs/{job_id}", response_class=HTMLResponse)
async def admin_job_detail(request: Request, job_id: str, _=Depends(verify_admin)):
    """View job activities (detailed log)."""
    db = get_db()

    # Get job info
    job = db.fetchone("""
        SELECT
            id,
            conversation_id,
            message,
            status,
            result,
            error,
            created_at,
            started_at,
            completed_at,
            worker_id
        FROM jobs
        WHERE id = ?
    """, (job_id,))

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get ALL activities (no limit, full detail)
    activities = db.fetchall("""
        SELECT
            id,
            timestamp,
            type,
            message,
            detail,
            tool_name,
            is_error
        FROM job_activities
        WHERE job_id = ?
        ORDER BY id ASC
    """, (job_id,))

    return templates.TemplateResponse("admin/job_detail.html", {
        "request": request,
        "job": job,
        "activities": activities
    })


@router.get("/balance", response_class=HTMLResponse)
async def admin_balance(request: Request, _=Depends(verify_admin)):
    """Balance management page."""
    db = get_db()

    # Get current balance
    balance = db.get_balance()

    # Get topup history
    topups = db.get_topups(limit=50)

    # Get usage summary (last 30 days)
    usage_summary = db.get_usage_summary(days=30)

    return templates.TemplateResponse("admin/balance.html", {
        "request": request,
        "balance": balance,
        "topups": topups,
        "usage_summary": usage_summary
    })


@router.post("/balance/topup", response_class=HTMLResponse)
async def admin_balance_topup(request: Request, _=Depends(verify_admin)):
    """Handle topup form submission."""
    db = get_db()

    # Parse form data
    form = await request.form()
    amount = float(form.get("amount", 0))
    note = form.get("note", "").strip() or "Manual topup by admin"

    if amount > 0:
        db.add_topup(amount, note)

    # Redirect back to balance page (PRG pattern)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/admin/balance", status_code=303)


# --- Export Endpoints ---

def _get_full_conversation_data(db: DB, conversation_id: str) -> dict:
    """Get all conversation data for export (messages, jobs, activities)."""
    # Check conversation exists
    conv = db.fetchone("SELECT id, created_at FROM conversations WHERE id = ?", (conversation_id,))
    if not conv:
        return None

    # Get ALL messages
    messages = db.fetchall("""
        SELECT id, role, content, tool_calls, tool_call_id, thinking, internal, created_at
        FROM messages
        WHERE conversation_id = ?
        ORDER BY id ASC
    """, (conversation_id,))

    # Parse tool_calls JSON
    for m in messages:
        if m["tool_calls"]:
            try:
                m["tool_calls_parsed"] = json.loads(m["tool_calls"])
            except json.JSONDecodeError:
                m["tool_calls_parsed"] = None

    # Get all jobs for this conversation
    jobs = db.fetchall("""
        SELECT id, message, status, result, error, created_at, started_at, completed_at, worker_id
        FROM jobs
        WHERE conversation_id = ?
        ORDER BY created_at ASC
    """, (conversation_id,))

    # Get activities and usage for each job
    for job in jobs:
        activities = db.fetchall("""
            SELECT id, timestamp, type, message, detail, tool_name, is_error
            FROM job_activities
            WHERE job_id = ?
            ORDER BY id ASC
        """, (job["id"],))
        job["activities"] = activities

        # Get usage log for this job
        usage = db.fetchall("""
            SELECT model, provider, prompt_tokens, completion_tokens, cost_usd, component, created_at
            FROM usage_log
            WHERE job_id = ?
            ORDER BY created_at ASC
        """, (job["id"],))
        job["usage"] = usage

    # Calculate total usage for conversation
    total_usage = db.fetchone("""
        SELECT
            SUM(prompt_tokens) as total_prompt_tokens,
            SUM(completion_tokens) as total_completion_tokens,
            SUM(cost_usd) as total_cost_usd,
            COUNT(*) as llm_calls
        FROM usage_log
        WHERE conversation_id = ?
    """, (conversation_id,))

    return {
        "conversation": dict(conv),
        "messages": [dict(m) for m in messages],
        "jobs": [dict(j) for j in jobs],
        "total_usage": dict(total_usage) if total_usage else None
    }


@router.get("/conversations/{conversation_id}/export.json")
async def export_conversation_json(conversation_id: str, _=Depends(verify_admin)):
    """Export full conversation data as JSON."""
    from fastapi.responses import Response

    db = get_db()
    data = _get_full_conversation_data(db, conversation_id)

    if not data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    data["exported_at"] = datetime.utcnow().isoformat()

    json_content = json.dumps(data, indent=2, ensure_ascii=False, default=str)

    return Response(
        content=json_content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="conversation_{conversation_id[:8]}.json"'
        }
    )


@router.get("/conversations/{conversation_id}/export.md")
async def export_conversation_md(conversation_id: str, _=Depends(verify_admin)):
    """Export full conversation data as Markdown (for AI analysis)."""
    from fastapi.responses import Response

    db = get_db()
    data = _get_full_conversation_data(db, conversation_id)

    if not data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conv = data["conversation"]
    messages = data["messages"]
    jobs = data["jobs"]
    total_usage = data.get("total_usage")

    lines = []
    lines.append(f"# Conversation Export: {conv['id']}")
    lines.append(f"Created: {conv['created_at']}")
    lines.append(f"Exported: {datetime.utcnow().isoformat()}")
    lines.append("")

    # Messages section
    lines.append(f"## Messages ({len(messages)})")
    lines.append("")

    for i, msg in enumerate(messages, 1):
        role = msg["role"]
        ts = msg["created_at"][:19] if msg["created_at"] else "?"
        internal = " [INTERNAL]" if msg.get("internal") else ""

        lines.append(f"### [{i}] {role}{internal} @ {ts}")
        lines.append("")

        if msg.get("thinking"):
            lines.append("**Thinking:**")
            lines.append("```")
            thinking = msg["thinking"]
            if isinstance(thinking, str) and len(thinking) > 2000:
                thinking = thinking[:2000] + "... [truncated]"
            lines.append(str(thinking))
            lines.append("```")
            lines.append("")

        if msg.get("tool_calls_parsed"):
            lines.append("**Tool calls:**")
            for tc in msg["tool_calls_parsed"]:
                name = tc.get("function", {}).get("name") or tc.get("name", "?")
                args = tc.get("function", {}).get("arguments") or tc.get("arguments", "")
                lines.append(f"- `{name}`")
                if args:
                    lines.append("```json")
                    lines.append(str(args)[:1000])
                    lines.append("```")
            lines.append("")

        if msg.get("tool_call_id"):
            lines.append(f"**Tool call ID:** `{msg['tool_call_id']}`")
            lines.append("")

        if msg.get("content"):
            content = msg["content"]
            if len(content) > 5000:
                content = content[:5000] + "\n\n... [truncated, total " + str(len(msg["content"])) + " chars]"
            lines.append(content)
            lines.append("")

        lines.append("---")
        lines.append("")

    # Jobs section
    lines.append(f"## Jobs ({len(jobs)})")
    lines.append("")

    for job in jobs:
        lines.append(f"### Job: {job['id']}")
        lines.append(f"- **Status:** {job['status']}")
        lines.append(f"- **Created:** {job['created_at']}")
        lines.append(f"- **Started:** {job['started_at'] or '-'}")
        lines.append(f"- **Completed:** {job['completed_at'] or '-'}")
        lines.append(f"- **Worker:** {job['worker_id'] or '-'}")
        lines.append("")

        if job.get("message"):
            lines.append("**User message:**")
            lines.append(f"> {job['message'][:500]}")
            lines.append("")

        if job.get("result"):
            lines.append("**Result:**")
            lines.append("```")
            lines.append(job["result"][:2000])
            lines.append("```")
            lines.append("")

        if job.get("error"):
            lines.append("**Error:**")
            lines.append("```")
            lines.append(job["error"])
            lines.append("```")
            lines.append("")

        activities = job.get("activities", [])
        if activities:
            lines.append(f"#### Activities ({len(activities)})")
            lines.append("")
            lines.append("| # | Type | Tool | Message |")
            lines.append("|---|------|------|---------|")
            for j, a in enumerate(activities, 1):
                atype = a["type"] or ""
                tool = a["tool_name"] or ""
                amsg = (a["message"] or "")[:80].replace("|", "\\|").replace("\n", " ")
                lines.append(f"| {j} | {atype} | {tool} | {amsg} |")
            lines.append("")

            # Full activity details
            lines.append("**Full activity details:**")
            lines.append("")
            for j, a in enumerate(activities, 1):
                atype = a["type"] or "?"
                tool = f" ({a['tool_name']})" if a["tool_name"] else ""
                err = " [ERROR]" if a.get("is_error") else ""
                lines.append(f"##### Activity {j}: {atype}{tool}{err}")
                if a.get("message"):
                    lines.append(f"Message: {a['message']}")
                if a.get("detail"):
                    detail = a["detail"]
                    if len(detail) > 3000:
                        detail = detail[:3000] + "\n... [truncated, total " + str(len(a["detail"])) + " chars]"
                    lines.append("```")
                    lines.append(detail)
                    lines.append("```")
                lines.append("")

        # Job usage
        usage = job.get("usage", [])
        if usage:
            lines.append(f"#### Usage ({len(usage)} LLM calls)")
            lines.append("")
            lines.append("| Model | Provider | Prompt | Completion | Cost |")
            lines.append("|-------|----------|--------|------------|------|")
            for u in usage:
                model = u["model"] or "?"
                provider = u["provider"] or "?"
                prompt = u["prompt_tokens"] or 0
                completion = u["completion_tokens"] or 0
                cost = f"${u['cost_usd']:.4f}" if u["cost_usd"] else "-"
                lines.append(f"| {model} | {provider} | {prompt} | {completion} | {cost} |")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Total usage summary
    if total_usage and total_usage.get("llm_calls"):
        lines.append("## Total Usage Summary")
        lines.append("")
        lines.append(f"- **LLM Calls:** {total_usage['llm_calls']}")
        lines.append(f"- **Prompt Tokens:** {total_usage['total_prompt_tokens'] or 0}")
        lines.append(f"- **Completion Tokens:** {total_usage['total_completion_tokens'] or 0}")
        lines.append(f"- **Total Cost:** ${total_usage['total_cost_usd']:.4f}" if total_usage['total_cost_usd'] else "- **Total Cost:** $0")
        lines.append("")

    md_content = "\n".join(lines)

    return Response(
        content=md_content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="conversation_{conversation_id[:8]}.md"'
        }
    )
