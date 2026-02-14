"""
ExploreExecutor - Lightweight executor for codebase exploration.

Similar to DelegateExecutor but specialized for exploration:
- Uses cheap model (Haiku) for cost efficiency
- Only has read-only tools (no write_file, edit_file, shell)
- Returns SUMMARY not raw file contents
- Max 15 steps (exploration can need more than delegate's 10)

The key benefit: exploration results don't pollute main agent's context.
A 50-file exploration becomes one summary message instead of 50 read_file results.
"""

import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Literal, Optional

from user_container.config import settings
from user_container.agent.llm_client import LLMClient, JobCancelledException
from user_container.agent.prompts import EXPLORE_SYSTEM_PROMPT
from user_container.agent.context import get_job_id, get_conversation_id
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
from user_container.observability import create_span


@dataclass
class ExploreResult:
    """Result from an exploration task."""
    status: Literal["success", "error", "timeout"]
    summary: str  # KEY: summary not raw content
    steps: int
    error: Optional[str] = None


class ExploreExecutor:
    """
    Lightweight executor for codebase exploration.

    Used by the explore tool to understand code structure before making changes.
    Returns a SUMMARY of findings rather than raw file contents.
    """

    MAX_STEPS = 15

    # Only read-only tools for exploration
    EXPLORE_TOOLS = [
        "read_file",
        "list_dir",
        "search_in_files",
        "recall_from_chat",
    ]

    def __init__(
        self,
        tools: ToolRegistry,
        db: Optional[DB] = None,
    ):
        """
        Initialize ExploreExecutor.

        Args:
            tools: Tool registry (will be filtered to read-only tools)
            db: Database for activity logging (optional)
        """
        self.llm = LLMClient.cheap()  # Always Haiku
        self.source_tools = tools
        self.tools = self._filter_tools(tools)
        self.db = db

    def _filter_tools(self, source: ToolRegistry) -> ToolRegistry:
        """Create a filtered registry with only read-only tools."""
        filtered = ToolRegistry()
        for tool_name in self.EXPLORE_TOOLS:
            tool = source.get(tool_name)
            if tool:
                filtered.register(
                    name=tool.name,
                    handler=tool.handler,
                    schema=tool.schema,
                    defaults=tool.defaults,
                )
        return filtered

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
                    tool_name="explore",
                    **kwargs
                )

    def execute(
        self,
        question: str,
        paths: Optional[List[str]] = None
    ) -> ExploreResult:
        """
        Execute an exploration task.

        Args:
            question: What to find/understand about the codebase
            paths: Optional specific paths to focus on

        Returns:
            ExploreResult with status and summary of findings
        """
        log_debug(f"[ExploreExecutor] Starting: {question[:80]}...")

        # Emit explore_start activity
        question_preview = question[:60] + "..." if len(question) > 60 else question
        self._emit_activity("explore_start", f"Exploring: {question_preview}")

        # Create Langfuse span to group all explore operations
        explore_span = create_span(
            name="explore",
            input={"question": question, "paths": paths},
            metadata={
                "model": self.llm.model,
                "max_steps": self.MAX_STEPS,
                "job_id": get_job_id(),
                "conversation_id": get_conversation_id(),
            }
        )

        try:
            # Build system prompt
            system_prompt = EXPLORE_SYSTEM_PROMPT

            # Build user content
            user_content = f"Question: {question}"
            if paths:
                user_content += f"\n\nFocus on these paths: {', '.join(paths)}"

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]

            # Execute exploration loop (max 15 steps)
            for step in range(self.MAX_STEPS):
                # Check for cancellation at start of each step
                if self._is_cancelled():
                    log_debug(f"[ExploreExecutor] Cancelled at step {step + 1}")
                    self._emit_activity("explore_end", "Exploration cancelled by user")
                    if explore_span:
                        explore_span.update(output="Cancelled", level="WARNING")
                        explore_span.end()
                    return ExploreResult(
                        status="error",
                        summary="Exploration cancelled by user",
                        steps=step,
                        error="Cancelled"
                    )

                log_debug(f"[ExploreExecutor] Step {step + 1}/{self.MAX_STEPS}")

                # Emit explore_step for steps > 1
                if step > 0:
                    self._emit_activity(
                        "explore_step",
                        f"Exploration step {step + 1}/{self.MAX_STEPS}"
                    )

                log_llm_request(messages, component="ExploreExecutor")

                try:
                    response = self.llm.chat(
                        messages=messages,
                        tools=self.tools.get_openai_specs(),
                        tool_choice="auto",
                        reasoning_effort="none",  # Explore uses cheap model, no reasoning
                        component="explore",
                        job_id=get_job_id(),
                        conversation_id=get_conversation_id(),
                        cancellation_check=self._is_cancelled
                    )
                except JobCancelledException:
                    log_debug(f"[ExploreExecutor] Cancelled during LLM call at step {step + 1}")
                    self._emit_activity("explore_end", "Exploration cancelled during LLM call")
                    if explore_span:
                        explore_span.update(output="Cancelled during LLM call", level="WARNING")
                        explore_span.end()
                    return ExploreResult(
                        status="error",
                        summary="Exploration cancelled by user",
                        steps=step + 1,
                        error="Cancelled during LLM call"
                    )

                log_llm_response(
                    response.content,
                    response.tool_calls,
                    component="ExploreExecutor"
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
                    # Final response = summary
                    summary = self._clean_output(response.content or "No findings")
                    log_debug(f"[ExploreExecutor] Completed in {step + 1} steps")

                    # Emit explore_end activity (success)
                    summary_preview = summary[:100] + "..." if len(summary) > 100 else summary
                    self._emit_activity("explore_end", f"Found: {summary_preview}")

                    # End Langfuse span with success
                    if explore_span:
                        explore_span.update(
                            output=summary,
                            metadata={"steps": step + 1, "status": "success"}
                        )
                        explore_span.end()

                    return ExploreResult(
                        status="success",
                        summary=summary,
                        steps=step + 1
                    )

            # Max steps reached
            log_debug(f"[ExploreExecutor] Timeout after {self.MAX_STEPS} steps")

            # Emit explore_end activity (timeout)
            self._emit_activity(
                "explore_end",
                f"Exploration timeout after {self.MAX_STEPS} steps",
                is_error=True
            )

            # End Langfuse span with timeout
            if explore_span:
                explore_span.update(
                    output=f"Timeout after {self.MAX_STEPS} steps",
                    level="WARNING",
                    metadata={"steps": self.MAX_STEPS, "status": "timeout"}
                )
                explore_span.end()

            return ExploreResult(
                status="timeout",
                summary="Exploration reached maximum steps without completing. Partial findings may be available in the last response.",
                steps=self.MAX_STEPS,
                error=f"Max steps ({self.MAX_STEPS}) exceeded"
            )

        except Exception as e:
            log_error(f"[ExploreExecutor] Error: {e}")

            # Emit explore_end activity (error)
            self._emit_activity(
                "explore_end",
                f"Exploration error: {str(e)[:60]}",
                is_error=True
            )

            # End Langfuse span with error
            if explore_span:
                explore_span.update(
                    output=f"Error: {str(e)}",
                    level="ERROR",
                    metadata={"status": "error", "error": str(e)}
                )
                explore_span.end()

            return ExploreResult(
                status="error",
                summary="",
                steps=0,
                error=str(e)
            )

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
