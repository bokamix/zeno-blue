"""
Rich-based logging for the agent module.
Provides clean, colorful output for agent execution.
"""

import json
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.table import Table

from user_container.config import settings

console = Console()


def log_user_message(content: str):
    """Log user message."""
    console.print()
    console.print(Panel(
        content,
        title="[bold blue]User[/bold blue]",
        border_style="blue",
        padding=(0, 1)
    ))


def log_agent_start(conversation_id: str, active_skills: Dict[str, int]):
    """Log agent starting."""
    skills_str = ", ".join(f"{k}(TTL={v})" for k, v in active_skills.items()) if active_skills else "none"
    console.print()
    console.print(f"[dim]─── Agent started ─── conversation: {conversation_id[:8]}... ─── skills: {skills_str} ───[/dim]")


def log_step(step: int, max_steps: int):
    """Log step number."""
    if settings.debug:
        console.print(f"[dim]Step {step}/{max_steps}[/dim]")


def log_skills_change(action: str, skill: str, ttl: Optional[int] = None):
    """Log skill changes (add/drop/expire)."""
    if action == "add":
        console.print(f"  [green]+ skill:[/green] [bold]{skill}[/bold] [dim](TTL={ttl})[/dim]")
    elif action == "drop":
        console.print(f"  [red]- skill:[/red] [bold]{skill}[/bold] [dim](dropped)[/dim]")
    elif action == "expire":
        console.print(f"  [yellow]⏱ skill:[/yellow] [bold]{skill}[/bold] [dim](expired)[/dim]")


def log_tool_call(tool_name: str, args: Dict[str, Any]):
    """Log a tool call with formatted arguments."""
    console.print()
    console.print(f"  [yellow]▶ {tool_name}[/yellow]")

    # Format args nicely
    if args:
        try:
            args_json = json.dumps(args, indent=2, ensure_ascii=False)
            if len(args_json) > 500:
                # Truncate long args
                args_json = args_json[:500] + "\n    ... (truncated)"
            console.print(Syntax(args_json, "json", theme="monokai", padding=1, word_wrap=True))
        except:
            console.print(f"    [dim]{args}[/dim]")


def log_tool_result(tool_name: str, result: str, is_error: bool = False):
    """Log tool result."""
    style = "red" if is_error else "green"
    icon = "✗" if is_error else "✓"

    # Parse and format if JSON
    try:
        result_obj = json.loads(result)
        result_formatted = json.dumps(result_obj, indent=2, ensure_ascii=False)
        if len(result_formatted) > 800:
            result_formatted = result_formatted[:800] + "\n  ... (truncated)"
        console.print(f"  [{style}]{icon}[/{style}] [dim]result:[/dim]")
        console.print(Syntax(result_formatted, "json", theme="monokai", padding=1, word_wrap=True))
    except:
        # Not JSON, show as text
        result_short = result[:500] + "..." if len(result) > 500 else result
        console.print(f"  [{style}]{icon}[/{style}] [dim]{result_short}[/dim]")


def log_assistant_response(content: str):
    """Log final assistant response."""
    console.print()
    console.print(Panel(
        content,
        title="[bold green]Assistant[/bold green]",
        border_style="green",
        padding=(0, 1)
    ))


def log_thinking(content: str):
    """Log thinking (only in debug mode)."""
    if settings.debug and content:
        console.print()
        console.print(Panel(
            content,
            title="[bold magenta]Thinking[/bold magenta]",
            border_style="magenta",
            padding=(0, 1)
        ))


def log_error(message: str):
    """Log error message."""
    console.print(f"[bold red]Error:[/bold red] {message}")


def log_debug(message: str):
    """Log debug message (only in debug mode)."""
    if settings.debug:
        console.print(f"[dim]{message}[/dim]")


# Legacy compatibility - old _log calls route here
def log(msg: str, debug_only: bool = False):
    """Legacy log function for backwards compatibility."""
    if debug_only and not settings.debug:
        return

    # Parse old-style messages and route to appropriate new functions
    if "[SkillRouter] Adding skill:" in msg:
        # Extract skill name
        parts = msg.split("Adding skill: ")
        if len(parts) > 1:
            skill_info = parts[1]
            skill_name = skill_info.split(" ")[0]
            log_skills_change("add", skill_name, settings.skill_ttl)
            return
    elif "[SkillRouter] Dropping skill:" in msg:
        parts = msg.split("Dropping skill: ")
        if len(parts) > 1:
            skill_name = parts[1].strip()
            log_skills_change("drop", skill_name)
            return
    elif "[SkillRouter] Skill expired:" in msg:
        parts = msg.split("Skill expired: ")
        if len(parts) > 1:
            skill_name = parts[1].strip()
            log_skills_change("expire", skill_name)
            return

    # Default: just print with dim style for debug
    if debug_only:
        console.print(f"[dim]{msg}[/dim]")
    else:
        console.print(msg)


def log_llm_request(messages: List[Dict[str, Any]], component: str = "Agent"):
    """Log LLM request summary (only in debug mode).

    Shows only NEW messages since last assistant response to avoid repetition.
    Full details are logged separately by log_tool_call, log_tool_result, etc.
    """
    if not settings.debug:
        return

    # Find messages since last assistant response (these are the "new" ones)
    # Work backwards to find last assistant message
    last_assistant_idx = -1
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("role") == "assistant":
            last_assistant_idx = i
            break

    # New messages = everything after last assistant (tool results going back)
    # If no assistant yet, show last user message
    if last_assistant_idx >= 0:
        new_messages = messages[last_assistant_idx + 1:]
    else:
        # First call - find user message(s)
        new_messages = [m for m in messages if m.get("role") == "user"][-1:] if messages else []

    # Count by role for summary
    role_counts = {}
    for msg in messages:
        role = msg.get("role", "unknown")
        role_counts[role] = role_counts.get(role, 0) + 1

    counts_str = ", ".join(f"{r}:{c}" for r, c in role_counts.items())

    console.print()
    console.print(f"[bold cyan]─── LLM Request ({component}) ─── {len(messages)} msgs ({counts_str}) ───[/bold cyan]")

    # Show only new messages (if any)
    if new_messages:
        console.print(f"[dim]New since last response ({len(new_messages)}):[/dim]")
        for msg in new_messages:
            _log_single_message(msg)
    else:
        console.print(f"[dim]No new messages (continuing conversation)[/dim]")


def _log_single_message(msg: Dict[str, Any]):
    """Helper to log a single message."""
    role = msg.get("role", "unknown")
    content = msg.get("content", "")

    # Color by role
    role_colors = {
        "system": "magenta",
        "user": "blue",
        "assistant": "green",
        "tool": "yellow",
    }
    role_color = role_colors.get(role, "white")

    # Truncate content for display
    max_len = 300 if role == "tool" else 500
    if content and len(content) > max_len:
        content = content[:max_len] + "..."

    console.print(f"  [{role_color}]{role}:[/{role_color}] {content if content else '[empty]'}")

    # Show tool_call_id for tool messages
    if msg.get("tool_call_id"):
        console.print(f"    [dim]tool_call_id: {msg['tool_call_id'][:20]}...[/dim]")

    # Show tool_calls if present
    if msg.get("tool_calls"):
        for tc in msg["tool_calls"]:
            if isinstance(tc, dict):
                name = tc.get("function", {}).get("name", "?")
            else:
                name = tc.function.name
            console.print(f"    [yellow]→ tool_call: {name}[/yellow]")


def log_llm_response(content: Optional[str], tool_calls: Optional[List] = None, component: str = "Agent"):
    """Log LLM response (only in debug mode)."""
    if not settings.debug:
        return

    console.print()
    console.print(f"[bold cyan]─── LLM Response ({component}) ───[/bold cyan]")

    if content:
        # Truncate for readability
        display = content[:1000] + "..." if len(content) > 1000 else content
        console.print(f"[green]content:[/green] {display}")

    if tool_calls:
        console.print(f"[yellow]tool_calls: {len(tool_calls)} call(s)[/yellow]")
        for tc in tool_calls:
            if isinstance(tc, dict):
                name = tc.get("function", {}).get("name", "?")
                args = tc.get("function", {}).get("arguments", "")
            else:
                name = tc.function.name
                args = tc.function.arguments

            # Pretty print args
            try:
                args_obj = json.loads(args)
                args_display = json.dumps(args_obj, indent=2)[:200]
            except:
                args_display = args[:200]

            console.print(f"  [yellow]→ {name}[/yellow]({args_display}{'...' if len(args) > 200 else ''})")
