"""
Agent module - Autonomous agent with dynamic skill loading.

This module provides the main Agent class that:
1. Uses a Skill Router to select relevant skills per turn
2. Executes tasks using Tools
3. Supports <thinking> for internal reasoning
"""

import hashlib
import json
import random
import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from user_container.config import settings
from user_container.db.db import DB
from user_container.runner.runner import Runner
from user_container.agent.skill_loader import SkillLoader
from user_container.agent.skill_router import SkillRouter
from user_container.agent.routing import RoutingAgent, RoutingDecision
from user_container.agent.llm_client import LLMClient, JobCancelledException
from user_container.agent.prompts import BASE_SYSTEM_PROMPT
from user_container.agent.planned_executor import (
    should_add_planning,
    should_add_reflection,
    get_planning_injection,
    get_reflection_injection,
    log_plan,
    log_reflection,
)
from user_container.agent.loop_detector import (
    detect_loop, get_anti_loop_prompt, get_force_progress_prompt,
    get_research_synthesis_prompt, get_total_limit_prompt, TOOL_LIMITS
)
from collections import defaultdict
from user_container.agent.context_manager import ContextManager, get_context_stats
from user_container.agent.conversation_summarizer import (
    ConversationSummarizer,
    build_context_header,
)
from user_container.logger import (
    log_agent_start,
    log_step,
    log_tool_call,
    log_tool_result,
    log_assistant_response,
    log_thinking,
    log_error,
    log_debug,
    log_llm_request,
    log_llm_response,
)
from user_container.tools.registry import ToolRegistry
from user_container.agent.delegate_executor import DelegateExecutor
from user_container.agent.explore_executor import ExploreExecutor
from user_container.agent.context import set_job_id, set_conversation_id, get_job_id, get_conversation_id
from user_container.usage.skill_tracker import track_skill_usage
from user_container.jobs.queue import get_job_queue
from user_container.observability import start_trace, end_trace, add_trace_tags, log_generation
from user_container.agent.suggestion_generator import SuggestionGenerator
from user_container.agent.progress_estimator import ProgressEstimator

# Tools
from user_container.tools.shell import make_shell_tool, SHELL_SCHEMA
from user_container.tools.files import (
    write_file, read_file, list_dir, edit_file,
    WRITE_FILE_SCHEMA, READ_FILE_SCHEMA, LIST_DIR_SCHEMA, EDIT_FILE_SCHEMA,
    READ_FILE_DEFAULTS, LIST_DIR_DEFAULTS, EDIT_FILE_DEFAULTS,
)
from user_container.tools.search_tools import (
    search_in_files,
    make_recall_from_chat_tool,
    SEARCH_IN_FILES_SCHEMA, SEARCH_IN_FILES_DEFAULTS,
    RECALL_FROM_CHAT_SCHEMA, RECALL_FROM_CHAT_DEFAULTS,
)
from user_container.tools.delegate import make_delegate_task_tool, DELEGATE_TASK_SCHEMA
from user_container.tools.explore import make_explore_tool, EXPLORE_SCHEMA
from user_container.tools.web_fetch import web_fetch, WEB_FETCH_SCHEMA
from user_container.tools.web_search import make_web_search_tool, WEB_SEARCH_SCHEMA
from user_container.tools.ask_user import make_ask_user_tool, ASK_USER_SCHEMA
from user_container.tools.schedule import (
    make_create_scheduled_job_tool, CREATE_SCHEDULED_JOB_SCHEMA,
    make_list_scheduled_jobs_tool, LIST_SCHEDULED_JOBS_SCHEMA,
    make_update_scheduled_job_tool, UPDATE_SCHEDULED_JOB_SCHEMA,
)


class Agent:
    """
    Autonomous Agent that executes tasks with dynamic skill loading.
    """

    def __init__(
        self,
        skill_loader: SkillLoader,
        runner: Runner,
        db: DB,
    ):
        self.skill_loader = skill_loader
        self.runner = runner
        self.db = db
        self._current_job_id = None  # For fast cancellation checks

        self.max_steps = settings.agent_max_steps

        # Initialize LLM Client (supports Anthropic and OpenAI)
        self.llm = LLMClient.default()

        # Initialize Skill Router
        self.skill_router = SkillRouter()

        # Initialize Routing Agent (decides execution strategy)
        self.routing_agent = RoutingAgent()

        # Initialize Context Manager (handles compression for long tasks)
        self.context_manager = ContextManager()

        # Initialize Conversation Summarizer (hierarchical memory)
        self.summarizer = ConversationSummarizer(db=db)

        # Initialize Tools (two registries - main + delegate)
        self.tools = ToolRegistry()
        self.delegate_tools = ToolRegistry()  # For DelegateExecutor (no delegate_task)
        self._register_tools()

        # Initialize DelegateExecutor with its own tools (no recursion)
        self.delegate_executor = DelegateExecutor(
            tools=self.delegate_tools,
            skill_loader=self.skill_loader,
            db=self.db  # For activity logging
        )

        # Register delegate_task to main tools AFTER executor is created
        self.tools.register(
            name="delegate_task",
            handler=make_delegate_task_tool(self.delegate_executor),
            schema=DELEGATE_TASK_SCHEMA
        )

        # Initialize ExploreExecutor for codebase exploration
        # Uses delegate_tools (read-only subset) and cheap model
        self.explore_executor = ExploreExecutor(
            tools=self.delegate_tools,
            db=self.db  # For activity logging
        )

        # Register explore tool to main tools
        self.tools.register(
            name="explore",
            handler=make_explore_tool(self.explore_executor),
            schema=EXPLORE_SCHEMA
        )

        # Initialize Suggestion Generator (for "Related Questions" feature)
        self.suggestion_generator = SuggestionGenerator()

        # Initialize Progress Estimator (for "Fake Progress Steps" feature)
        self.progress_estimator = ProgressEstimator()

    def _is_cancelled(self) -> bool:
        """Fast check if current job was cancelled by user."""
        if not self._current_job_id:
            return False
        try:
            job_queue = get_job_queue()
            return job_queue.is_cancelled(self._current_job_id)
        except Exception as e:
            if not hasattr(self, '_cancel_check_error_logged'):
                log_error(f"[Agent] CRITICAL: Cannot check cancellation status: {e}")
                self._cancel_check_error_logged = True
            return False

    def _handle_cancellation(self, step_count: int, start_time: float = None) -> Dict[str, Any]:
        """Handle job cancellation and return appropriate response."""
        elapsed_time = time.time() - start_time if start_time else 0
        log_debug(f"[Agent] Cancelled after {elapsed_time:.2f}s ({step_count} steps)")
        if self._current_job_id:
            self.db.add_job_activity(self._current_job_id, "cancelled", f"Execution cancelled by user ({elapsed_time:.1f}s)")
        end_trace(
            output="Cancelled by user",
            status="cancelled",
            metadata={"steps": step_count, "elapsed_seconds": round(elapsed_time, 2)},
            tags=["status:cancelled"],
        )
        return {
            "status": "cancelled",
            "summary": "Wykonanie zatrzymane przez użytkownika",
            "steps": step_count,
            "elapsed_seconds": round(elapsed_time, 2)
        }

    def _register_tools(self):
        """Register available tools to both main and delegate registries."""
        shell_handler = make_shell_tool(self.runner, self.db)

        # Register to BOTH registries (delegate tools = main tools - delegate_task)
        for registry in [self.tools, self.delegate_tools]:
            # Shell
            registry.register(
                name="shell",
                handler=shell_handler,
                schema=SHELL_SCHEMA
            )

            # File System
            registry.register("read_file", read_file, READ_FILE_SCHEMA, READ_FILE_DEFAULTS)
            registry.register("write_file", write_file, WRITE_FILE_SCHEMA)
            registry.register("edit_file", edit_file, EDIT_FILE_SCHEMA, EDIT_FILE_DEFAULTS)
            registry.register("list_dir", list_dir, LIST_DIR_SCHEMA, LIST_DIR_DEFAULTS)

            # Search
            registry.register(
                name="search_in_files",
                handler=search_in_files,
                schema=SEARCH_IN_FILES_SCHEMA,
                defaults=SEARCH_IN_FILES_DEFAULTS
            )

            # Recall from current chat
            registry.register(
                name="recall_from_chat",
                handler=make_recall_from_chat_tool(self.db),
                schema=RECALL_FROM_CHAT_SCHEMA,
                defaults=RECALL_FROM_CHAT_DEFAULTS
            )

            # Web
            registry.register("web_fetch", web_fetch, WEB_FETCH_SCHEMA)
            registry.register(
                name="web_search",
                handler=make_web_search_tool(settings.serper_api_key),
                schema=WEB_SEARCH_SCHEMA
            )

            # Scheduler - list_scheduled_jobs (always available)
            registry.register(
                name="list_scheduled_jobs",
                handler=make_list_scheduled_jobs_tool(self.db),
                schema=LIST_SCHEDULED_JOBS_SCHEMA
            )

        # delegate_task ONLY in main registry (prevents recursion in DelegateExecutor)
        # Note: delegate_executor is created AFTER this, so we register the tool later
        # This is handled in __init__ after DelegateExecutor creation

    def run(
        self,
        conversation_id: str,
        job_id: str = None,
        user_message: str = None,
        skip_history: bool = False
    ) -> Dict[str, Any]:
        """
        Main execution loop.

        Args:
            conversation_id: The conversation ID to continue
            job_id: Optional job ID (for orchestrated execution)
            user_message: Optional user message (for orchestrated execution)
            skip_history: If True, don't load conversation history (for scheduled jobs)

        Returns:
            Dict with status and summary
        """
        if not self.llm:
            return {"status": "error", "error": "LLM client not configured"}

        # Start timing for debug
        start_time = time.time()

        # Set context for nested components (DelegateExecutor, etc.)
        set_job_id(job_id)
        set_conversation_id(conversation_id)
        self._current_job_id = job_id  # For fast cancellation checks
        self._cancel_check_error_logged = False  # Reset for new job

        # Start Langfuse trace for observability
        start_trace(
            name="agent_run",
            session_id=conversation_id,
            metadata={
                "job_id": job_id,
                "skip_history": skip_history,
                "model": self.llm.model if self.llm else None,
            },
            input=user_message,
        )

        # Load persisted active skills from DB
        active_skills = self.db.get_active_skills(conversation_id)
        log_agent_start(conversation_id, active_skills)

        # Route the request to determine execution strategy
        # This happens once at the start based on the user's latest message
        routing_decision = self._route_request(
            conversation_id,
            user_message=user_message,
            skip_history=skip_history
        )

        # Emit routing activity
        if job_id:
            depth_names = {0: "direct", 1: "standard", 2: "complex"}
            self.db.add_job_activity(
                job_id, "routing",
                f"depth={routing_decision.depth} ({depth_names.get(routing_decision.depth, '?')})"
            )

            # Emit quick acknowledgment as thinking_stream for immediate user feedback
            if routing_decision.depth > 0:
                ack_messages = {
                    1: "Working on this for you...",
                    2: "This is a complex task. Let me think through it carefully..."
                }
                self.db.add_job_activity(
                    job_id,
                    "thinking_stream",
                    ack_messages.get(routing_decision.depth, "Processing..."),
                    detail=ack_messages.get(routing_decision.depth)
                )

                # Generate related questions in background (Perplexity-style)
                threading.Thread(
                    target=self._generate_suggestions_async,
                    args=(job_id, user_message),
                    daemon=True
                ).start()

                # Generate and emit fake progress steps in background
                threading.Thread(
                    target=self._emit_progress_steps_async,
                    args=(job_id, user_message),
                    daemon=True
                ).start()

        # Get thinking budget based on depth (extended thinking for complex tasks)
        thinking_budget = self._get_thinking_budget(routing_decision.depth)
        # Get reasoning effort for OpenAI GPT-5.2+
        reasoning_effort = self._get_reasoning_effort(routing_decision.depth)

        # Add dynamic tags based on routing decision
        depth_tags = {
            0: ["depth:direct", "task:simple"],
            1: ["depth:standard", "task:multi-step"],
            2: ["depth:complex", "task:large-scope"],
        }
        thinking_tag = f"thinking:{'enabled' if thinking_budget else 'disabled'}"
        model_tag = f"model:{self.llm.model}" if self.llm else "model:unknown"

        add_trace_tags([
            *depth_tags.get(routing_decision.depth, []),
            thinking_tag,
            model_tag,
        ])

        # Register ask_user tool if job_id is available
        # This tool needs job_id to store questions and poll for responses
        # Also needs db to save question/response to conversation history
        if job_id:
            job_queue = get_job_queue()
            self.tools.register(
                name="ask_user",
                handler=make_ask_user_tool(job_id, job_queue, db=self.db),
                schema=ASK_USER_SCHEMA
            )
            log_debug(f"[Agent] Registered ask_user tool for job {job_id}")

            # Register scheduler tools (A.7 Job Scheduler)
            # These tools need scheduler and/or db
            try:
                from user_container.scheduler.scheduler import get_scheduler
                scheduler = get_scheduler()
                self.tools.register(
                    name="create_scheduled_job",
                    handler=make_create_scheduled_job_tool(scheduler, conversation_id),
                    schema=CREATE_SCHEDULED_JOB_SCHEMA
                )
                self.tools.register(
                    name="update_scheduled_job",
                    handler=make_update_scheduled_job_tool(scheduler, self.db),
                    schema=UPDATE_SCHEDULED_JOB_SCHEMA
                )
                log_debug(f"[Agent] Registered scheduler tools for conversation {conversation_id}")
            except RuntimeError:
                # Scheduler not initialized (e.g., during tests)
                log_debug("[Agent] Scheduler not available, skipping scheduler tools")

        # Track consecutive truncations to prevent infinite loops
        consecutive_truncations = 0
        MAX_CONSECUTIVE_TRUNCATIONS = 3

        # Track if we just executed tools - helps differentiate between
        # "model finished task" vs "model is stuck" when getting empty response
        just_executed_tools = False

        # Persistent loop state - survives context compression
        # This is the key fix: counters persist even when history is compressed
        loop_state = {
            "last_tool_signature": None,
            "consecutive_same_tool": 0,
            "tool_results_hash": None,
            "consecutive_same_result": 0,
            "recovery_attempts": 0,  # Track soft recovery attempts
            "tool_counts": defaultdict(int),  # Per-tool usage counters
            "tool_cache": {},  # {cache_key: result_preview} for duplicate detection
            "research_file_created": False,  # Track if research file was created
        }

        # Soft recovery thresholds (inject prompt, continue)
        SOFT_RECOVERY_THRESHOLD = 3        # Same tool 3x → inject recovery prompt
        SAME_RESULT_THRESHOLD = 2          # Same result 2x → inject force progress prompt
        TOOL_ONLY_SOFT_THRESHOLD = 5       # 5 tool-only → nudge

        # Hard stop thresholds (only after soft recovery fails)
        MAX_RECOVERY_ATTEMPTS = 3          # 3 failed recoveries → stop
        TOOL_ONLY_HARD_THRESHOLD = 15      # 15 tool-only → stop
        ABSOLUTE_MAX_SAME_TOOL = 10        # Safety net: 10x same tool → stop

        # Track consecutive responses with tool calls but no text content
        consecutive_tool_only_responses = 0
        total_tool_only_responses = 0  # Total (not reset) for absolute limit

        # Research artifact settings (Faza 3)
        INFO_TOOLS = ["web_search", "web_fetch"]
        RESEARCH_DIR = "/workspace/.research"
        RESEARCH_THRESHOLD = 3  # Start saving to file after N calls

        # For scheduled jobs: track message count at start to filter old history
        initial_message_count = 0
        if skip_history:
            # Count existing messages so we can filter them out later
            initial_message_count = len(self.db.get_conversation_history(conversation_id))
            log_debug(f"Scheduled job: will skip first {initial_message_count} messages from history")

        # Standard execution loop (same for all depths)
        step_count = 0
        while step_count < self.max_steps:
            step_count += 1
            log_step(step_count, self.max_steps)

            # Check if job was cancelled by user (checkpoint 1: start of step)
            if self._is_cancelled():
                return self._handle_cancellation(step_count, start_time)

            # Emit step activity
            if job_id:
                self.db.add_job_activity(job_id, "step", f"Step {step_count}/{self.max_steps}")

            # 1. Build conversation context using hierarchical memory
            # Approach: summary + full history with intelligent compression
            # Old messages (>5 exchanges) are compressed to one-line summaries
            # New messages (last 5 exchanges) are kept full
            if skip_history:
                # Scheduled jobs: minimal context, just the prompt
                history = [{"role": "user", "content": user_message}] if user_message else []
                context_header = None
                log_debug(f"History: scheduled job, {len(history)} messages")
            else:
                # Get or generate conversation summary (for long conversations)
                summary = self.summarizer.get_or_update_summary_sync(conversation_id)

                # Get total message count for context header
                total_messages = self.db.count_messages(conversation_id)

                # Get conversation history with intelligent compression
                # - Old messages (>5 exchanges ago): compressed to one-line summaries
                # - New messages (last 5 exchanges): kept full
                # This preserves ALL messages (no orphan tool_results) while reducing tokens
                history = self.db.get_conversation_history(
                    conversation_id,
                    compress_old=True,
                    recent_exchanges=5
                )

                # Build context header if we have summary
                visible_count = len(history)
                if summary:
                    context_header = build_context_header(total_messages, visible_count, summary)
                else:
                    context_header = None

                log_debug(f"History: {len(history)} messages (total={total_messages}, with compression)")

            # 2. Route to skills based on history
            available_skills = self.skill_loader.list_available_skills()
            selected_skills, active_skills = self.skill_router.route(
                history, available_skills, active_skills
            )
            log_debug(f"Selected skills: {selected_skills}")

            # Persist updated active skills
            self.db.save_active_skills(conversation_id, active_skills)

            # 3. Build system prompt with loaded skills (and planning if depth >= 1)
            skill_prompts = self.skill_loader.get_skill_prompts(selected_skills)
            system_prompt = self._build_system_prompt(
                skill_prompts,
                depth=routing_decision.depth,
                step_count=step_count
            )
            log_debug(f"System prompt length: {len(system_prompt)} chars")

            # 4. Build messages for LLM (with context header if available)
            messages = self._build_messages(system_prompt, history, context_header)

            # 4.5. Inject reflection prompt if needed (depth >= 1, every N steps)
            if should_add_reflection(routing_decision.depth, step_count):
                reflection_msg = {"role": "user", "content": get_reflection_injection()}
                messages.append(reflection_msg)
                log_debug(f"[PlannedExecution] Injecting reflection prompt at step {step_count}")

            # 4.6. Loop detection (all depths) - inject anti-loop prompt if stuck
            loop_result = detect_loop(history, threshold=3)
            if loop_result.detected:
                log_debug(f"[LoopDetection] Detected: {loop_result.tool_name} x{loop_result.repetitions}")
                anti_loop_msg = {"role": "user", "content": get_anti_loop_prompt()}
                messages.append(anti_loop_msg)

                if job_id:
                    self.db.add_job_activity(
                        job_id, "loop_detected",
                        f"Repeated {loop_result.tool_name} x{loop_result.repetitions}, injecting anti-loop prompt"
                    )

            log_debug(f"Total messages: {len(messages)}")

            # 4.7. Auto-compress context if needed (for long-running tasks)
            messages, was_compressed = self.context_manager.compress(messages)
            if was_compressed:
                log_debug(f"[ContextManager] Compressed to {len(messages)} messages")

            # Check if job was cancelled by user (checkpoint 2: before LLM call)
            if self._is_cancelled():
                return self._handle_cancellation(step_count, start_time)

            # 5. Call LLM (with extended thinking for complex tasks)
            if job_id:
                # Log LLM call with parameters
                llm_params = {
                    "model": self.llm.model,
                    "messages_count": len(messages),
                    "thinking_budget": thinking_budget,
                    "reasoning_effort": reasoning_effort,
                    "max_tokens": max(8192, (thinking_budget or 0) + 4096) if thinking_budget else 8192,
                    "tools_count": len(self.tools.get_openai_specs()) if self.tools else 0
                }
                reasoning_info = f", reasoning={reasoning_effort}" if reasoning_effort and reasoning_effort != "none" else ""
                self.db.add_job_activity(
                    job_id, "llm_call",
                    f"Calling {self.llm.model} with {len(messages)} messages" + (f", thinking={thinking_budget}" if thinking_budget else "") + reasoning_info,
                    detail=json.dumps(llm_params, indent=2)
                )

            try:
                response = self._call_llm(messages, thinking_budget=thinking_budget, reasoning_effort=reasoning_effort)
            except JobCancelledException:
                # Fast cancellation during LLM streaming
                return self._handle_cancellation(step_count, start_time)

            # Detect potential truncation (output cut off at max_tokens)
            if response.get("stop_reason") == "max_tokens" and response.get("tool_calls"):
                log_debug("[Agent] WARNING: Response truncated (max_tokens) with tool calls - arguments may be incomplete")
                if job_id:
                    self.db.add_job_activity(
                        job_id, "warning",
                        "Response truncated (max_tokens reached) - tool arguments may be incomplete"
                    )

            # Check if job was cancelled by user (checkpoint 3: after LLM call)
            if self._is_cancelled():
                return self._handle_cancellation(step_count, start_time)

            # 6. Handle Response
            content = response.get("content", "")
            has_tool_calls = bool(response.get("tool_calls"))

            # Emit llm_response activity
            if job_id:
                tool_info = f", {len(response.get('tool_calls', []))} tools" if has_tool_calls else ""
                content_preview = (content[:60] + "...") if content and len(content) > 60 else (content or "[no content]")
                self.db.add_job_activity(job_id, "llm_response", f"{content_preview}{tool_info}")

            # Check if this is thinking-only (no tool calls, content is only <thinking>)
            # Also treat as thinking-only if we have extended thinking but no content
            is_thinking_only = self._is_thinking_only(content) if content else False
            ext_thinking = response.get("thinking")
            ext_thinking_signature = response.get("thinking_signature")
            has_ext_thinking_only = bool(ext_thinking) and not content and not has_tool_calls
            is_thinking_only = is_thinking_only or has_ext_thinking_only

            # Log thinking if present (extract from content)
            if content:
                thinking_content = self._extract_thinking(content)
                if thinking_content:
                    log_thinking(thinking_content)
                    # Emit thinking activity (from <thinking> tags)
                    if job_id:
                        self.db.add_job_activity(
                            job_id, "thinking",
                            f"Thinking ({len(thinking_content)} chars)",
                            detail=thinking_content
                        )

                # Log plan/reflection if present (for depth >= 1)
                if routing_decision.depth >= 1:
                    log_plan(content)
                    log_reflection(content)

                    # Emit planning activity if <plan> tag is present
                    if job_id and "<plan>" in content:
                        plan_match = re.search(r'<plan>(.*?)</plan>', content, re.DOTALL)
                        if plan_match:
                            self.db.add_job_activity(
                                job_id, "planning",
                                "Created execution plan",
                                detail=plan_match.group(1).strip()
                            )

                    # Emit reflection activity if <reflection> tag is present
                    if job_id and "<reflection>" in content:
                        reflection_match = re.search(r'<reflection>(.*?)</reflection>', content, re.DOTALL)
                        if reflection_match:
                            self.db.add_job_activity(
                                job_id, "reflection",
                                "Self-reflection",
                                detail=reflection_match.group(1).strip()
                            )

            # Log extended thinking if present (already extracted earlier for is_thinking_only check)
            if ext_thinking:
                log_debug(f"[ExtendedThinking] {len(ext_thinking)} chars")
                log_thinking(ext_thinking)  # Log extended thinking content

                # Log extended thinking to Langfuse
                log_generation(
                    name="llm/thinking",
                    model=self.llm.model,
                    input_messages=[],
                    output=ext_thinking[:10000],  # Truncate if very long
                    metadata={"type": "extended_thinking", "full_length": len(ext_thinking)}
                )

                # Emit extended thinking activity
                if job_id:
                    self.db.add_job_activity(
                        job_id, "thinking",
                        f"Extended thinking ({len(ext_thinking)} chars)",
                        detail=ext_thinking
                    )

                    # Emit thinking_stream for UI display (truncated for readability)
                    display_thinking = ext_thinking[:300] + "..." if len(ext_thinking) > 300 else ext_thinking
                    self.db.add_job_activity(
                        job_id,
                        "thinking_stream",
                        "Analyzing approach...",
                        detail=display_thinking
                    )

            if has_tool_calls:
                # Check if response was truncated - tool_calls JSON might be corrupted
                was_truncated = response.get("truncated", False)
                if was_truncated:
                    log_debug("[Agent] WARNING: Tool calls may be corrupted due to truncation")
                    if job_id:
                        self.db.add_job_activity(
                            job_id, "warning",
                            "Tool calls may be incomplete due to response truncation"
                        )
                    # Validate tool_calls JSON before execution
                    valid_tool_calls = []
                    for tc in response["tool_calls"]:
                        try:
                            args_str = tc["function"]["arguments"] if isinstance(tc, dict) else tc.function.arguments
                            json.loads(args_str)  # Validate JSON
                            valid_tool_calls.append(tc)
                        except (json.JSONDecodeError, KeyError) as e:
                            log_error(f"[Agent] Skipping corrupted tool_call: {e}")
                            if job_id:
                                self.db.add_job_activity(
                                    job_id, "error",
                                    f"Skipped corrupted tool call: {e}",
                                    is_error=True
                                )
                    if not valid_tool_calls:
                        # All tool calls were corrupted - treat as empty response
                        log_debug("[Agent] All tool calls corrupted, treating as empty response")
                        consecutive_truncations += 1
                        if consecutive_truncations >= MAX_CONSECUTIVE_TRUNCATIONS:
                            return {
                                "status": "error",
                                "error": "Model responses keep getting truncated. Try simplifying the task.",
                                "steps": step_count
                            }
                        self._save_message(conversation_id, "assistant",
                                           content="[Tool calls corrupted, retrying...]",
                                           internal=True)
                        continue
                    response["tool_calls"] = valid_tool_calls

                # Check if job was cancelled by user (checkpoint 4: before tool execution)
                if self._is_cancelled():
                    return self._handle_cancellation(step_count, start_time)

                # Emit thinking_stream before tool execution
                if job_id:
                    tool_calls_list = response["tool_calls"]
                    tool_names = [
                        tc.get("function", {}).get("name", "tool") if isinstance(tc, dict)
                        else getattr(getattr(tc, "function", None), "name", "tool")
                        for tc in tool_calls_list[:3]
                    ]
                    tool_count = len(tool_calls_list)
                    self.db.add_job_activity(
                        job_id,
                        "thinking_stream",
                        f"Running: {', '.join(tool_names)}{'...' if tool_count > 3 else ''}",
                        detail=f"Executing {tool_count} tool(s) to complete the task"
                    )

                # Execute tools and continue loop
                results = self._execute_tool_calls(response["tool_calls"], job_id=job_id)

                # Check if cancelled during tool execution - don't save partial results
                # (would break tool_use/tool_result pairs)
                if self._is_cancelled():
                    return self._handle_cancellation(step_count, start_time)

                # === PER-TOOL LIMIT TRACKING (Faza 1) ===
                # Count tool usage and check limits BEFORE loop detection
                for idx, call in enumerate(response["tool_calls"]):
                    if isinstance(call, dict):
                        call_tool_name = call["function"]["name"]
                        call_tool_args = call["function"]["arguments"]
                    else:
                        call_tool_name = call.function.name
                        call_tool_args = call.function.arguments

                    # Increment counters
                    loop_state["tool_counts"][call_tool_name] += 1
                    loop_state["tool_counts"]["_total"] += 1

                    tool_count_now = loop_state["tool_counts"][call_tool_name]
                    total_count_now = loop_state["tool_counts"]["_total"]

                    # Check per-tool limit
                    tool_limit = TOOL_LIMITS.get(call_tool_name, 50)
                    if tool_count_now >= tool_limit:
                        log_debug(f"[Agent] TOOL LIMIT: {call_tool_name} reached {tool_count_now}/{tool_limit}")
                        if job_id:
                            self.db.add_job_activity(
                                job_id, "tool_limit",
                                f"Tool limit reached: {call_tool_name} x{tool_count_now}"
                            )
                        synthesis_prompt = get_research_synthesis_prompt(call_tool_name, tool_count_now)
                        self._save_message(conversation_id, "user", content=synthesis_prompt, internal=True)

                    # Check total limit
                    if total_count_now >= TOOL_LIMITS["_total"]:
                        log_debug(f"[Agent] TOTAL TOOL LIMIT: {total_count_now}/{TOOL_LIMITS['_total']}")
                        if job_id:
                            self.db.add_job_activity(
                                job_id, "tool_limit",
                                f"Total tool limit reached: {total_count_now}"
                            )
                        self._save_message(conversation_id, "user", content=get_total_limit_prompt(), internal=True)

                    # === TOOL RESULT CACHING (Faza 2) ===
                    # Build cache key and check for duplicates
                    args_hash = hashlib.md5(call_tool_args.encode()).hexdigest()[:8]
                    cache_key = f"{call_tool_name}:{args_hash}"

                    if cache_key in loop_state["tool_cache"]:
                        cached_preview = loop_state["tool_cache"][cache_key]
                        log_debug(f"[Agent] DUPLICATE TOOL CALL: {call_tool_name} with same args")
                        if job_id:
                            self.db.add_job_activity(
                                job_id, "duplicate_tool",
                                f"Duplicate call: {call_tool_name}"
                            )
                        # Note: We still executed it, but warn the agent
                        # Warning will be appended after all tool tracking

                    # Cache the result
                    if idx < len(results):
                        result_content = results[idx]["content"]
                        result_preview = result_content[:300] + "..." if len(result_content) > 300 else result_content
                        loop_state["tool_cache"][cache_key] = result_preview

                    # === RESEARCH ARTIFACT FILES (Faza 3) ===
                    # For info tools (web_search, web_fetch), save findings to file
                    if call_tool_name in INFO_TOOLS and idx < len(results):
                        tool_count_for_research = loop_state["tool_counts"][call_tool_name]

                        if tool_count_for_research >= RESEARCH_THRESHOLD:
                            # Extract and save findings
                            result_content = results[idx]["content"]
                            findings = self._extract_findings(call_tool_name, result_content)

                            # Parse args to get query/url
                            try:
                                args_dict = json.loads(call_tool_args)
                                query = args_dict.get("query", args_dict.get("url", "unknown"))
                            except:
                                query = "unknown"

                            research_file = self._save_to_research_file(
                                conversation_id, call_tool_name, query, findings
                            )

                            # Notify agent about research file (only on first save)
                            if not loop_state["research_file_created"]:
                                loop_state["research_file_created"] = True
                                info_msg = f"""📝 RESEARCH MODE ACTIVATED

Your research findings are being saved to: {research_file}

If context gets compressed, you can read this file to recall your findings.
Continue with your research - findings will be automatically saved."""
                                self._save_message(conversation_id, "user", content=info_msg, internal=True)
                                log_debug(f"[Agent] Research mode activated: {research_file}")
                                if job_id:
                                    self.db.add_job_activity(
                                        job_id, "research_mode",
                                        f"Research findings being saved to {research_file}"
                                    )
                # === END PER-TOOL LIMIT TRACKING ===

                # === PERSISTENT LOOP DETECTION (survives context compression) ===
                # Track tool signatures for repetition detection
                tool_calls_list = response["tool_calls"]
                if tool_calls_list:
                    first_call = tool_calls_list[0]
                    if isinstance(first_call, dict):
                        tc_name = first_call["function"]["name"]
                        tc_args = first_call["function"]["arguments"]
                    else:
                        tc_name = first_call.function.name
                        tc_args = first_call.function.arguments

                    current_sig = f"{tc_name}:{tc_args}"

                    if current_sig == loop_state["last_tool_signature"]:
                        loop_state["consecutive_same_tool"] += 1
                    else:
                        loop_state["consecutive_same_tool"] = 0
                        loop_state["last_tool_signature"] = current_sig

                    # SOFT RECOVERY: Inject recovery prompt with results
                    if loop_state["consecutive_same_tool"] >= SOFT_RECOVERY_THRESHOLD:
                        last_result = results[0]["content"] if results else "unknown"
                        # Truncate result for readability
                        result_preview = last_result[:500] + "..." if len(last_result) > 500 else last_result

                        recovery_prompt = f"""🚨 LOOP RECOVERY MODE ACTIVATED

You called `{tc_name}` {loop_state["consecutive_same_tool"]+1} times with SAME arguments.

HERE IS YOUR RESULT (use it now):
```
{result_preview}
```

YOUR NEXT ACTION MUST BE DIFFERENT. Options:
1. Use shell to create/move/copy files based on this result
2. Use write_file/edit_file to modify files
3. Tell the user the result if that's all they needed

DO NOT call `{tc_name}` again with the same arguments."""

                        log_debug(f"[Agent] SOFT RECOVERY: {tc_name} x{loop_state['consecutive_same_tool']+1}, injecting recovery prompt")
                        if job_id:
                            self.db.add_job_activity(
                                job_id, "loop_recovery",
                                f"Soft recovery: {tc_name} x{loop_state['consecutive_same_tool']+1} - injecting prompt with results"
                            )

                        self._save_message(conversation_id, "user", content=recovery_prompt, internal=True)

                        # Reset counter after injection (give model another chance)
                        loop_state["consecutive_same_tool"] = 0
                        loop_state["recovery_attempts"] = loop_state.get("recovery_attempts", 0) + 1

                    # HARD STOP: Only after multiple failed recovery attempts OR absolute max
                    total_same_tool = loop_state["consecutive_same_tool"] + (loop_state.get("recovery_attempts", 0) * SOFT_RECOVERY_THRESHOLD)
                    if loop_state.get("recovery_attempts", 0) >= MAX_RECOVERY_ATTEMPTS:
                        log_error(f"[Agent] LOOP HARD STOP: Failed {MAX_RECOVERY_ATTEMPTS} soft recoveries for {tc_name}")
                        if job_id:
                            self.db.add_job_activity(
                                job_id, "loop_hard_stop",
                                f"ABORTED: {MAX_RECOVERY_ATTEMPTS} recovery attempts failed for {tc_name}",
                                is_error=True
                            )
                        end_trace(
                            output=f"Loop detected: {tc_name} - {MAX_RECOVERY_ATTEMPTS} recovery attempts failed",
                            status="error",
                            metadata={"tool": tc_name, "recovery_attempts": loop_state.get("recovery_attempts", 0)},
                            tags=["status:error", "reason:loop_detected"],
                        )
                        return {
                            "status": "error",
                            "error": f"Agent stuck: Tried {MAX_RECOVERY_ATTEMPTS} times to recover from repeated `{tc_name}` calls. Please rephrase your request.",
                            "steps": step_count
                        }

                    # Safety net: Absolute max same tool (catches edge cases)
                    if total_same_tool >= ABSOLUTE_MAX_SAME_TOOL:
                        log_error(f"[Agent] SAFETY STOP: {tc_name} called {total_same_tool}x total")
                        if job_id:
                            self.db.add_job_activity(
                                job_id, "loop_hard_stop",
                                f"ABORTED: Safety limit - {tc_name} x{total_same_tool}",
                                is_error=True
                            )
                        end_trace(
                            output=f"Safety stop: {tc_name} repeated {total_same_tool} times total",
                            status="error",
                            metadata={"tool": tc_name, "total_repetitions": total_same_tool},
                            tags=["status:error", "reason:loop_detected"],
                        )
                        return {
                            "status": "error",
                            "error": f"Agent stuck: `{tc_name}` called {total_same_tool} times. Please try a simpler request.",
                            "steps": step_count
                        }

                # Track identical results (hash-based)
                if results:
                    results_str = json.dumps([r["content"] for r in results], sort_keys=True)
                    result_hash = hashlib.md5(results_str.encode()).hexdigest()[:8]

                    if result_hash == loop_state["tool_results_hash"]:
                        loop_state["consecutive_same_result"] += 1
                    else:
                        loop_state["consecutive_same_result"] = 0
                        loop_state["tool_results_hash"] = result_hash

                    # Inject STRONG prompt when same results detected (soft recovery)
                    if loop_state["consecutive_same_result"] >= SAME_RESULT_THRESHOLD:
                        log_debug(f"[Agent] Same result detected {loop_state['consecutive_same_result']+1}x, injecting force progress prompt")
                        if job_id:
                            self.db.add_job_activity(
                                job_id, "loop_warning",
                                f"Same tool results {loop_state['consecutive_same_result']+1}x - forcing progress"
                            )
                        # Save a system message to force the model to change behavior
                        self._save_message(conversation_id, "user",
                                           content=get_force_progress_prompt(),
                                           internal=True)

                # Track tool-only responses (no text content with tools)
                if not content:
                    consecutive_tool_only_responses += 1
                    total_tool_only_responses += 1  # Total never resets
                else:
                    consecutive_tool_only_responses = 0  # Only reset consecutive

                # SOFT NUDGE: Remind model to respond to user (every 5 tool calls)
                if consecutive_tool_only_responses >= TOOL_ONLY_SOFT_THRESHOLD:
                    if consecutive_tool_only_responses % 5 == 0:  # Every 5 tool calls
                        nudge_prompt = """You have been executing tools without responding to the user.

Please either:
1. Complete your current task and respond with the result
2. If you need more information, ask the user
3. If you're stuck, explain what's blocking you

Your next message should include text for the user, not just tool calls."""

                        log_debug(f"[Agent] TOOL-ONLY NUDGE: {consecutive_tool_only_responses} tool calls without text")
                        if job_id:
                            self.db.add_job_activity(
                                job_id, "loop_warning",
                                f"Nudge: {consecutive_tool_only_responses} tool calls without response"
                            )
                        self._save_message(conversation_id, "user", content=nudge_prompt, internal=True)

                # HARD STOP: Only after many tool-only responses (absolute limit)
                if consecutive_tool_only_responses >= TOOL_ONLY_HARD_THRESHOLD:
                    log_error(f"[Agent] TOOL-ONLY HARD STOP: {consecutive_tool_only_responses} consecutive tool calls without text")
                    if job_id:
                        self.db.add_job_activity(
                            job_id, "loop_hard_stop",
                            f"ABORTED: {consecutive_tool_only_responses} consecutive tool calls without text response",
                            is_error=True
                        )
                    end_trace(
                        output="Agent stuck: consecutive tool calls without text",
                        status="error",
                        metadata={"consecutive_tool_only": consecutive_tool_only_responses},
                        tags=["status:error", "reason:tool_only_loop"],
                    )
                    return {
                        "status": "error",
                        "error": f"Agent stuck: {consecutive_tool_only_responses} consecutive tool calls without producing a response. Please try a simpler request.",
                        "steps": step_count
                    }
                # === END PERSISTENT LOOP DETECTION ===

                # Save assistant message with tool calls (internal - not shown in chat)
                self._save_message(conversation_id, "assistant",
                                   content=content if content else None,
                                   tool_calls=response["tool_calls"],
                                   thinking=ext_thinking,
                                   thinking_signature=ext_thinking_signature,
                                   internal=True)

                # Save tool results (internal - not shown in chat)
                for res in results:
                    self._save_message(conversation_id, "tool",
                                       content=res["content"],
                                       tool_call_id=res["tool_call_id"],
                                       internal=True)

                # Successfully executed tools - reset truncation counter
                consecutive_truncations = 0
                just_executed_tools = True  # Mark that we just ran tools

            elif is_thinking_only:
                # Thinking-only response - save and continue loop (internal)
                self._save_message(conversation_id, "assistant", content=content,
                                   thinking=ext_thinking,
                                   thinking_signature=ext_thinking_signature,
                                   internal=True)
                # Valid thinking response - reset counters
                consecutive_truncations = 0
                just_executed_tools = False
                # Continue to next iteration (don't return)

            else:
                # Check if response was truncated
                was_truncated = response.get("truncated", False)

                # Check if response is completely empty
                if not content and not has_tool_calls and not ext_thinking:
                    # If we just executed tools and got empty response (not truncated),
                    # the model likely finished the task - return default message
                    if just_executed_tools and not was_truncated:
                        log_debug("[Agent] Empty response after tool execution - task complete")
                        content = "Done."  # Provide completion message
                        consecutive_truncations = 0
                        just_executed_tools = False
                    else:
                        # Empty response without prior tools, or truncated - retry
                        consecutive_truncations += 1
                        log_debug(f"[Agent] Empty response detected (truncation #{consecutive_truncations}), continuing loop")

                        # Prevent infinite truncation loops
                        if consecutive_truncations >= MAX_CONSECUTIVE_TRUNCATIONS:
                            log_error(f"[Agent] Too many consecutive truncations ({consecutive_truncations}), aborting")
                            if job_id:
                                self.db.add_job_activity(
                                    job_id, "error",
                                    f"Aborted: {consecutive_truncations} consecutive empty responses",
                                    is_error=True
                                )
                            end_trace(
                                output="Aborted due to repeated truncations",
                                status="error",
                                metadata={"consecutive_truncations": consecutive_truncations},
                                tags=["status:error", "reason:truncation_loop"],
                            )
                            return {
                                "status": "error",
                                "error": "Model keeps generating incomplete responses. Try simplifying the task.",
                                "steps": step_count
                            }

                        if job_id:
                            self.db.add_job_activity(
                                job_id, "warning",
                                f"Empty response #{consecutive_truncations} - retrying"
                            )
                        # Save empty marker and continue (don't return)
                        self._save_message(conversation_id, "assistant",
                                           content="[Response incomplete, continuing...]",
                                           internal=True)
                        continue
                else:
                    # Got a real response, reset counters
                    consecutive_truncations = 0
                    just_executed_tools = False

                # If content was truncated but not empty, warn the user
                if was_truncated and content:
                    log_debug("[Agent] Response was truncated but has content - delivering partial response")
                    if job_id:
                        self.db.add_job_activity(
                            job_id, "warning",
                            "Response was truncated - content may be incomplete"
                        )

                # Final text response - return to user (NOT internal)
                visible_content = self._strip_thinking(content)

                # Save full response (with thinking) to DB for context
                self._save_message(conversation_id, "assistant", content=content,
                                   thinking=ext_thinking,
                                   thinking_signature=ext_thinking_signature)

                # Log final response
                log_assistant_response(visible_content)

                # Get context stats for response
                context_stats = get_context_stats(messages)

                # Calculate elapsed time
                elapsed_time = time.time() - start_time
                log_debug(f"[Agent] Completed in {elapsed_time:.2f}s ({step_count} steps)")

                # Emit complete activity
                if job_id:
                    self.db.add_job_activity(
                        job_id, "complete",
                        f"Completed in {step_count} steps ({elapsed_time:.1f}s)"
                    )

                end_trace(
                    output=visible_content,
                    status="success",
                    metadata={"steps": step_count},
                    tags=["status:success"],
                )
                return {
                    "status": "success",
                    "summary": visible_content,
                    "context_usage_percent": context_stats["usage_percent"],
                    "steps": step_count,
                    "elapsed_seconds": round(elapsed_time, 2)
                }

        # Calculate elapsed time for timeout
        elapsed_time = time.time() - start_time
        log_debug(f"[Agent] Timeout after {elapsed_time:.2f}s ({step_count} steps)")

        # Emit timeout activity
        if job_id:
            self.db.add_job_activity(
                job_id, "error",
                f"Timeout - max steps ({self.max_steps}) reached ({elapsed_time:.1f}s)",
                is_error=True
            )

        end_trace(
            output="Max steps reached",
            status="timeout",
            metadata={"steps": step_count, "max_steps": self.max_steps, "elapsed_seconds": round(elapsed_time, 2)},
            tags=["status:timeout"],
        )
        return {"status": "timeout", "summary": "Max steps reached", "steps": step_count, "elapsed_seconds": round(elapsed_time, 2)}

    def _build_system_prompt(self, skill_prompts: str, depth: int = 0, step_count: int = 0) -> str:
        """Build full system prompt with loaded skills and planning injection."""
        from datetime import datetime

        # Substitute path placeholders
        base = BASE_SYSTEM_PROMPT.format(
            skills_dir=settings.skills_dir,
            workspace_dir=settings.workspace_dir
        )

        # Add current date context
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        day_of_week = datetime.now().strftime("%A")
        base = f"{base}\n\n## CURRENT DATE\nToday is {day_of_week}, {current_date}. Use this for any date-related tasks."

        # Add custom user instructions if set
        custom_prompt = self.db.get_setting("custom_system_prompt", "")
        if custom_prompt.strip():
            base = f"{base}\n\n## USER INSTRUCTIONS\n{custom_prompt.strip()}"

        # Add skills if present
        if skill_prompts:
            base = f"{base}\n\n# LOADED SKILLS\n{skill_prompts}"

        # Add planning prompt for depth >= 1 on first step
        if should_add_planning(depth, step_count):
            base = f"{base}{get_planning_injection()}"
            log_debug("[PlannedExecution] Injecting planning prompt")

        return base

    def _build_messages(
        self,
        system_prompt: str,
        history: List[Dict[str, Any]],
        context_header: str = None
    ) -> List[Dict[str, Any]]:
        """Build message list for LLM.

        Structure when context_header is provided:
        1. System prompt
        2. Context header (as user message) - conversation metadata + summary
        3. Recent conversation history

        Args:
            system_prompt: The system prompt
            history: Recent conversation messages
            context_header: Optional context header with summary and metadata
        """
        messages = [{"role": "system", "content": system_prompt}]

        # Add context header if provided (injected before history)
        if context_header:
            messages.append({"role": "user", "content": context_header})
            # Add a brief assistant acknowledgment to maintain proper turn structure
            messages.append({"role": "assistant", "content": "I understand the context. Let me continue."})

        messages.extend(history)
        return messages

    def _get_thinking_budget(self, depth: int) -> Optional[int]:
        """Return thinking budget tokens based on task complexity (Anthropic)."""
        if depth == 0:
            return None  # no extended thinking
        elif depth == 1:
            return 5000  # standard thinking
        else:  # depth == 2
            return 15000  # deep thinking for complex tasks

    def _get_reasoning_effort(self, depth: int) -> Optional[str]:
        """Return reasoning effort level based on task complexity (OpenAI GPT-5.2+).

        Mapping:
        - depth 0: "none" (no reasoning, fastest)
        - depth 1: "medium" (standard reasoning)
        - depth 2: "high" (deep reasoning for complex tasks)

        If OPENAI_REASONING_EFFORT is set to a specific value (not "auto"),
        that value is used regardless of depth.
        """
        # Check if user has set a specific effort level
        configured_effort = settings.openai_reasoning_effort
        if configured_effort and configured_effort != "auto":
            return configured_effort

        # Auto-map from depth
        if depth == 0:
            return "none"
        elif depth == 1:
            return "medium"
        else:  # depth == 2
            return "high"

    def _call_llm(
        self,
        messages: List[Dict[str, Any]],
        thinking_budget: Optional[int] = None,
        reasoning_effort: Optional[str] = None
    ) -> Dict[str, Any]:
        """Call LLM via unified client with streaming for fast cancellation."""
        try:
            log_debug(f"Calling LLM ({self.llm.model})...")
            log_llm_request(messages, component="Agent")

            response = self.llm.chat(
                messages=messages,
                tools=self.tools.get_openai_specs(),
                tool_choice="auto",
                thinking_budget=thinking_budget,
                reasoning_effort=reasoning_effort,
                component="agent",
                job_id=get_job_id(),
                conversation_id=get_conversation_id(),
                cancellation_check=self._is_cancelled  # Enable fast cancellation during streaming
            )

            log_llm_response(response.content, response.tool_calls, component="Agent")

            if response.has_tool_calls:
                log_debug(f"LLM returned {len(response.tool_calls)} tool calls")
            else:
                log_debug("LLM returned text response")

            # Log warning if response was truncated
            if response.truncated:
                log_debug("[Agent] WARNING: LLM response was truncated at max_tokens")

            return {
                "content": response.content,
                "tool_calls": response.tool_calls,
                "thinking": response.thinking,  # Extended thinking (Anthropic only)
                "thinking_signature": response.thinking_signature,  # Required for message history
                "truncated": response.truncated  # True if response was truncated at max_tokens
            }
        except JobCancelledException:
            # Re-raise to be caught by the main loop
            raise
        except Exception as e:
            log_error(f"LLM Error: {e}")
            return {"content": f"Error: {e}"}

    def _execute_tool_calls(self, tool_calls: List[Any], job_id: str = None) -> List[Dict[str, Any]]:
        """
        Execute a list of tool calls.

        delegate_task calls run in parallel via ThreadPoolExecutor.
        Other tools run sequentially.
        """
        # Separate delegate_task from other calls
        delegate_calls = []
        other_calls = []

        for call in tool_calls:
            tool_name = call["function"]["name"] if isinstance(call, dict) else call.function.name
            if tool_name == "delegate_task":
                delegate_calls.append(call)
            else:
                other_calls.append(call)

        results = []

        # Execute non-delegate tools sequentially (with cancel check between each)
        for call in other_calls:
            # Check for cancellation before each tool (faster cancel)
            if self._is_cancelled():
                log_debug(f"[Agent] Cancelled during tool execution, {len(results)} tools completed")
                break
            result = self._execute_single_tool(call, job_id=job_id)
            results.append(result)

        # Execute delegate_task calls in parallel (if not cancelled)
        if delegate_calls and not self._is_cancelled():
            log_debug(f"[Agent] Running {len(delegate_calls)} delegate_task(s) in parallel")
            with ThreadPoolExecutor(max_workers=len(delegate_calls)) as executor:
                # Submit all delegate tasks
                future_to_call = {
                    executor.submit(self._execute_single_tool, call, job_id): call
                    for call in delegate_calls
                }

                # Collect results as they complete
                for future in as_completed(future_to_call):
                    result = future.result()
                    results.append(result)

        return results

    def _validate_tool_args(self, tool_name: str, args: Dict[str, Any]) -> Optional[str]:
        """Validate tool arguments against schema, return error message if invalid.

        This catches truncation issues (missing required params) BEFORE execution,
        preventing confusing errors in tool handlers and breaking infinite loops.
        """
        tool = self.tools.get(tool_name)
        if not tool:
            return None  # Unknown tool, let registry handle it

        schema = tool.schema
        if not schema or not schema.parameters:
            return None

        required = schema.parameters.get("required", [])
        properties = schema.parameters.get("properties", {})

        # Check for missing required parameters
        missing = []
        for param in required:
            if param not in args or args.get(param) is None:
                missing.append(param)

        if missing:
            return f"Missing required parameter(s): {', '.join(missing)}"

        return None

    def _execute_single_tool(self, call: Any, job_id: str = None) -> Dict[str, Any]:
        """Execute a single tool call and return the result."""
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

        # Log the tool call with formatted args
        log_tool_call(tool_name, args)

        # Emit tool_call activity
        args_summary = str(args)[:100]
        if job_id:
            self.db.add_job_activity(
                job_id, "tool_call",
                f"{tool_name}({args_summary})",
                tool_name=tool_name
            )

        is_error = False

        # Pre-execution validation: catch truncation issues early
        validation_error = self._validate_tool_args(tool_name, args)
        if validation_error:
            result_str = (
                f"Error: {validation_error}. "
                f"This may be caused by response truncation (max_tokens reached). "
                f"Try: 1) Generate smaller content, 2) Split into multiple files, "
                f"3) Use edit_file to build incrementally."
            )
            is_error = True
            log_debug(f"[Agent] Tool validation failed: {tool_name} - {validation_error}")
        else:
            try:
                output = self.tools.call(tool_name, args)
                result_str = json.dumps(output, default=str)

                # Track skill API usage if present in output
                track_skill_usage(
                    tool_name=tool_name,
                    args=args,
                    output=output,
                    job_id=job_id,
                    conversation_id=get_conversation_id()
                )
            except Exception as e:
                result_str = f"Error executing {tool_name}: {str(e)}"
                is_error = True

        # Log the tool result
        log_tool_result(tool_name, result_str, is_error=is_error)

        # Emit tool_result activity
        result_summary = result_str[:200] if len(result_str) > 200 else result_str
        if job_id:
            self.db.add_job_activity(
                job_id, "tool_result",
                result_summary,
                tool_name=tool_name,
                is_error=is_error
            )

        return {
            "tool_call_id": call_id,
            "content": result_str
        }

    def _save_message(self, conversation_id: str, role: str, content: str = None,
                      tool_calls: List = None, tool_call_id: str = None,
                      thinking: str = None, thinking_signature: str = None,
                      internal: bool = False):
        """Save message to database.

        Args:
            internal: If True, message is internal (not shown to user in chat).
                     Used for intermediate assistant messages before tool calls.
        """
        msg = {"role": role}
        if content:
            msg["content"] = content
        if tool_calls:
            msg["tool_calls"] = tool_calls
        if tool_call_id:
            msg["tool_call_id"] = tool_call_id
        if thinking:
            msg["thinking"] = thinking  # Extended thinking (Anthropic only)
        if thinking_signature:
            msg["thinking_signature"] = thinking_signature  # Required for thinking blocks
        if internal:
            msg["internal"] = True

        self.db.save_message_from_dict(conversation_id, msg)

    def _strip_thinking(self, content: str) -> str:
        """Remove internal blocks (<thinking>, <plan>, <reflection>) from content.

        These blocks contain agent reasoning that should not be shown to users.
        """
        if not content:
            return ""
        result = content
        result = re.sub(r'<thinking>.*?</thinking>\s*', '', result, flags=re.DOTALL)
        result = re.sub(r'<plan>.*?</plan>\s*', '', result, flags=re.DOTALL)
        result = re.sub(r'<reflection>.*?</reflection>\s*', '', result, flags=re.DOTALL)
        return result.strip()

    def _extract_thinking(self, content: str) -> str:
        """Extract content from <thinking> blocks."""
        if not content:
            return ""
        matches = re.findall(r'<thinking>(.*?)</thinking>', content, flags=re.DOTALL)
        return "\n".join(m.strip() for m in matches)

    def _is_thinking_only(self, content: str) -> bool:
        """Check if content contains only <thinking> blocks with no other text."""
        if not content:
            return False
        # Strip thinking and see if anything remains
        stripped = self._strip_thinking(content)
        return len(stripped) == 0 and '<thinking>' in content

    def _extract_findings(self, tool_name: str, result_content: str) -> str:
        """Extract key findings from tool result for research file."""
        try:
            data = json.loads(result_content)

            if tool_name == "web_search" and isinstance(data, dict) and "results" in data:
                # Extract from web search results
                findings = []
                for r in data.get("results", [])[:5]:
                    title = r.get("title", "")
                    snippet = r.get("snippet", "")
                    url = r.get("url", "")
                    if title or snippet:
                        findings.append(f"- **{title}**: {snippet}")
                        if url:
                            findings.append(f"  Source: {url}")
                return "\n".join(findings) if findings else result_content[:500]

            elif tool_name == "web_fetch":
                # Extract content from web fetch
                content = data.get("content", "") if isinstance(data, dict) else str(data)
                return content[:800] if len(content) > 800 else content

        except (json.JSONDecodeError, TypeError, KeyError):
            pass

        # Fallback: return truncated raw content
        return result_content[:500] if len(result_content) > 500 else result_content

    def _save_to_research_file(
        self,
        conversation_id: str,
        tool_name: str,
        query: str,
        findings: str
    ) -> str:
        """Append findings to research file and return the file path."""
        import os
        from datetime import datetime

        research_dir = "/workspace/.research"
        os.makedirs(research_dir, exist_ok=True)

        # Use conversation ID prefix for unique file per conversation
        research_file = f"{research_dir}/{conversation_id[:8]}_notes.md"
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Create header if file is new
        if not os.path.exists(research_file):
            header = f"# Research Notes\nConversation: {conversation_id[:8]}\n\n"
            with open(research_file, "w") as f:
                f.write(header)

        # Append findings
        with open(research_file, "a") as f:
            f.write(f"\n## {tool_name}: {query[:50]}{'...' if len(query) > 50 else ''} ({timestamp})\n")
            f.write(findings)
            f.write("\n")

        return research_file

    def _route_request(
        self,
        conversation_id: str,
        user_message: str = None,
        skip_history: bool = False
    ) -> RoutingDecision:
        """
        Route the current request to determine execution strategy.

        Extracts the latest user message and runs it through the RoutingAgent
        to classify complexity (depth 0/1/2).

        Args:
            conversation_id: The conversation ID
            user_message: Optional user message (if provided, skip extracting from history)
            skip_history: If True, don't load history (for scheduled jobs)

        Note: Currently only logs the decision. Actual branching to different
        executors (PlannedExecutor, OrchestratedExecutor) will be added in B.3/B.5.
        """
        if skip_history:
            # Scheduled jobs - route based on provided message, no history context
            history = []
            if not user_message:
                log_debug("[Routing] No user message for scheduled job, using default routing")
                return RoutingDecision.default()
        else:
            history = self.db.get_conversation_history(conversation_id)

            # Find the latest user message if not provided
            if not user_message:
                for i in range(len(history) - 1, -1, -1):
                    msg = history[i]
                    if msg.get("role") == "user" and msg.get("content"):
                        user_message = msg["content"]
                        break

            if not user_message:
                log_debug("[Routing] No user message found, using default routing")
                return RoutingDecision.default()

        # Run routing
        decision = self.routing_agent.route(user_message, history)

        # Log the decision (visible in normal logs, not just debug)
        depth_names = {0: "direct", 1: "standard", 2: "complex"}
        log_debug(f"[Routing] depth={decision.depth} ({depth_names.get(decision.depth, '?')})")

        return decision

    def _generate_suggestions_async(self, job_id: str, user_message: str) -> None:
        """
        Generate related question suggestions in background thread.

        Called for depth > 0 tasks to show Perplexity-style "Related Questions"
        while the agent is working.
        """
        try:
            # Small delay to not block agent start
            time.sleep(0.5)

            suggestions = self.suggestion_generator.generate(user_message)
            if suggestions:
                job_queue = get_job_queue()
                job_queue.set_suggestions(job_id, suggestions)
                log_debug(f"[Suggestions] Saved {len(suggestions)} for job {job_id}")
            else:
                log_debug(f"[Suggestions] Empty result for job {job_id}")
        except Exception as e:
            from user_container.logger import log
            log(f"[Suggestions] ERROR for job {job_id}: {e}")

    def _emit_progress_steps_async(self, job_id: str, user_message: str) -> None:
        """
        Generate and emit fake progress steps in background thread.

        Called for depth > 0 tasks to show estimated progress steps
        while the agent is working. Steps are emitted with delays
        to create a typewriter effect in the UI.

        NOTE: These are ESTIMATES, not real progress tracking.
        """
        try:
            # Small delay before starting
            time.sleep(0.3)

            # Check if job was cancelled before generating
            if self._is_cancelled():
                return

            # Generate estimated steps
            steps = self.progress_estimator.generate(user_message)
            if not steps:
                log_debug(f"[ProgressSteps] No steps generated for job {job_id}")
                return

            log_debug(f"[ProgressSteps] Emitting {len(steps)} steps for job {job_id}")

            # Emit steps with delay (typewriter effect)
            for i, step in enumerate(steps):
                # Check if job was cancelled
                if self._is_cancelled():
                    log_debug(f"[ProgressSteps] Cancelled at step {i+1}")
                    break

                # Emit as progress_step activity
                self.db.add_job_activity(
                    job_id,
                    "progress_step",
                    step,
                    detail=f"Step {i+1} of {len(steps)}"
                )

                # Delay between steps (3-5s for slower visual progression)
                delay = 3.0 + random.random() * 2.0
                time.sleep(delay)

        except Exception as e:
            log_debug(f"[ProgressSteps] Error: {e}")
