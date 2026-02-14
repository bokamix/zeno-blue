"""
DelegateExecutor - Lightweight executor for delegated tasks.

A simplified version of SubtaskExecutor designed for:
- Fast execution of atomic, self-contained tasks
- Always uses cheap model (Haiku)
- Max 10 steps (no long-running tasks)
- No planning or reflection - just execute
"""

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

from user_container.config import settings
from user_container.agent.llm_client import LLMClient, JobCancelledException
from user_container.agent.prompts import DELEGATE_SYSTEM_PROMPT
from user_container.agent.skill_loader import SkillLoader
from user_container.agent.skill_router import SkillRouter
from user_container.agent.context import get_job_id, get_conversation_id
from user_container.usage.skill_tracker import track_skill_usage
from user_container.tools.registry import ToolRegistry
from user_container.db.db import DB
from user_container.jobs.queue import get_job_queue
from user_container.logger import (
    log_debug,
    log_error,
    log_tool_call,
    log_tool_result,
    log_llm_request,
    log_llm_response,
)


@dataclass
class DelegateResult:
    """Result from a delegated task execution."""
    status: Literal["success", "error", "timeout"]
    output: str
    steps: int
    error: Optional[str] = None


class DelegateExecutor:
    """
    Lightweight executor for delegated tasks.

    Used by the delegate_task tool to run atomic, self-contained tasks
    with a fast, cheap model. Does not include delegate_task in its
    own tool registry to prevent recursion.
    """

    MAX_STEPS = 10

    def __init__(
        self,
        tools: ToolRegistry,
        skill_loader: SkillLoader,
        db: Optional[DB] = None,
    ):
        """
        Initialize DelegateExecutor.

        Args:
            tools: Tool registry (should NOT include delegate_task)
            skill_loader: For loading skill prompts
            db: Database for activity logging (optional)
        """
        self.llm = LLMClient.cheap()  # Always Haiku
        self.tools = tools
        self.skill_loader = skill_loader
        self.skill_router = SkillRouter()
        self.db = db

    def _is_cancelled(self) -> bool:
        """Check if current job was cancelled by user."""
        job_id = get_job_id()
        if not job_id:
            return False
        try:
            job_queue = get_job_queue()
            return job_queue.is_cancelled(job_id)
        except Exception:
            return False

    def _emit_activity(self, activity_type: str, message: str, **kwargs):
        """Emit activity if db and job_id are available."""
        if self.db:
            job_id = get_job_id()
            if job_id:
                self.db.add_job_activity(
                    job_id, activity_type, message,
                    tool_name="delegate_task",
                    **kwargs
                )

    def execute(self, task: str, context: str = "") -> DelegateResult:
        """
        Execute an atomic task.

        No planning, no reflection - just BASE_SYSTEM_PROMPT + tools + skills.
        Runs for max 10 steps.

        Args:
            task: Clear description of what to do
            context: Optional context (URLs, file paths, data)

        Returns:
            DelegateResult with status, output, and step count
        """
        log_debug(f"[DelegateExecutor] Starting task: {task[:80]}...")

        # Emit delegate_start activity
        task_preview = task[:60] + "..." if len(task) > 60 else task
        self._emit_activity("delegate_start", f"Sub-agent: {task_preview}")

        try:
            # 1. Route skills based on task
            available_skills = self.skill_loader.list_available_skills()
            selected_skills, _ = self.skill_router.route(
                [{"role": "user", "content": task}],
                available_skills,
                {}  # Fresh start - no active skills
            )
            log_debug(f"[DelegateExecutor] Skills: {selected_skills}")

            # 2. Build simple system prompt (no planning/reflection)
            skill_prompts = self.skill_loader.get_skill_prompts(selected_skills)
            system_prompt = self._build_system_prompt(skill_prompts)

            # 3. Build messages
            user_content = f"Task: {task}"
            if context:
                user_content += f"\n\nContext: {context}"

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]

            # 4. Execute loop (max 10 steps)
            for step in range(self.MAX_STEPS):
                # Check for cancellation at start of each step
                if self._is_cancelled():
                    log_debug(f"[DelegateExecutor] Cancelled at step {step + 1}")
                    self._emit_activity("delegate_end", "✗ Sub-agent cancelled by user")
                    return DelegateResult(
                        status="error",
                        output="Task cancelled by user",
                        steps=step,
                        error="Cancelled"
                    )

                log_debug(f"[DelegateExecutor] Step {step + 1}/{self.MAX_STEPS}")

                # Emit delegate_step for steps > 1
                if step > 0:
                    self._emit_activity("delegate_step", f"Sub-agent step {step + 1}/{self.MAX_STEPS}")

                log_llm_request(messages, component="DelegateExecutor")

                try:
                    response = self.llm.chat(
                        messages=messages,
                        tools=self.tools.get_openai_specs(),
                        tool_choice="auto",
                        reasoning_effort="none",  # Delegate tasks use cheap model, no reasoning
                        component="delegate",
                        job_id=get_job_id(),
                        conversation_id=get_conversation_id(),
                        cancellation_check=self._is_cancelled  # Enable fast cancellation
                    )
                except JobCancelledException:
                    log_debug(f"[DelegateExecutor] Cancelled during LLM call at step {step + 1}")
                    self._emit_activity("delegate_end", "✗ Sub-agent cancelled during LLM call")
                    return DelegateResult(
                        status="error",
                        output="Task cancelled by user",
                        steps=step + 1,
                        error="Cancelled during LLM call"
                    )

                log_llm_response(
                    response.content,
                    response.tool_calls,
                    component="DelegateExecutor"
                )

                if response.has_tool_calls:
                    # Execute tools, append results
                    results = self._execute_tools(response.tool_calls)

                    # Add assistant message
                    assistant_msg = {"role": "assistant", "tool_calls": response.tool_calls}
                    if response.content:
                        assistant_msg["content"] = response.content
                    messages.append(assistant_msg)

                    # Add tool results
                    for r in results:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": r["tool_call_id"],
                            "content": r["content"]
                        })
                else:
                    # Final response
                    output = self._clean_output(response.content or "Done")
                    log_debug(f"[DelegateExecutor] Completed in {step + 1} steps")

                    # Emit delegate_end activity (success)
                    output_preview = output[:80] + "..." if len(output) > 80 else output
                    self._emit_activity("delegate_end", f"✓ Sub-agent: {output_preview}")

                    return DelegateResult(
                        status="success",
                        output=output,
                        steps=step + 1
                    )

            # Max steps reached
            log_debug(f"[DelegateExecutor] Timeout after {self.MAX_STEPS} steps")

            # Emit delegate_end activity (timeout)
            self._emit_activity("delegate_end", f"✗ Sub-agent timeout after {self.MAX_STEPS} steps", is_error=True)

            return DelegateResult(
                status="timeout",
                output="Task reached maximum steps without completion",
                steps=self.MAX_STEPS,
                error=f"Max steps ({self.MAX_STEPS}) exceeded"
            )

        except Exception as e:
            log_error(f"[DelegateExecutor] Error: {e}")

            # Emit delegate_end activity (error)
            self._emit_activity("delegate_end", f"✗ Sub-agent error: {str(e)[:60]}", is_error=True)

            return DelegateResult(
                status="error",
                output="",
                steps=0,
                error=str(e)
            )

    def _build_system_prompt(self, skill_prompts: str) -> str:
        """Build simple system prompt without planning/reflection."""
        from datetime import datetime

        base = DELEGATE_SYSTEM_PROMPT.format(skills_dir=settings.skills_dir)

        # Add current date context
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        day_of_week = datetime.now().strftime("%A")
        base = f"{base}\n\n## CURRENT DATE\nToday is {day_of_week}, {current_date}."

        if skill_prompts:
            base = f"{base}\n\n# LOADED SKILLS\n{skill_prompts}"

        return base

    def _execute_tools(self, tool_calls: List) -> List[Dict[str, Any]]:
        """Execute a list of tool calls."""
        results = []

        for call in tool_calls:
            # Handle both object and dict formats
            if isinstance(call, dict):
                tool_name = call["function"]["name"]
                args_str = call["function"]["arguments"]
                call_id = call["id"]
            else:
                tool_name = call.function.name
                args_str = call.function.arguments
                call_id = call.id

            try:
                args = json.loads(args_str)
            except json.JSONDecodeError:
                args = {"raw": args_str}

            log_tool_call(tool_name, args)

            is_error = False
            try:
                output = self.tools.call(tool_name, args)
                result_str = json.dumps(output, default=str)

                # Track skill API usage if present in output
                track_skill_usage(
                    tool_name=tool_name,
                    args=args,
                    output=output,
                    job_id=get_job_id(),
                    conversation_id=get_conversation_id()
                )
            except Exception as e:
                result_str = f"Error: {str(e)}"
                is_error = True

            log_tool_result(tool_name, result_str, is_error=is_error)

            results.append({
                "tool_call_id": call_id,
                "content": result_str
            })

        return results

    def _clean_output(self, content: str) -> str:
        """Clean output - remove thinking blocks, trim whitespace."""
        if not content:
            return ""

        # Remove thinking blocks
        content = re.sub(r'<thinking>.*?</thinking>\s*', '', content, flags=re.DOTALL)

        return content.strip()
