"""
LLM Client - Unified interface for LLM providers via LiteLLM + OpenRouter.

All models are accessed through OpenRouter (200+ models with one API key).
Groq is optionally used for fast routing decisions.

Usage:
    client = LLMClient.default()  # Main model from config
    client = LLMClient.cheap()    # Cheap model for routing/compression
    client = LLMClient.custom("openrouter/model", api_key="...")

    response = client.chat(messages, tools)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import json
import os
import time
import random

from user_container.config import settings
from user_container.logger import log_debug, log_error, log as _log
from user_container.observability import log_generation


class JobCancelledException(Exception):
    """Raised when a job is cancelled during LLM call (streaming)."""
    pass


# Retry configuration for rate limits
MAX_RETRIES = 5
BASE_DELAY = 5.0  # seconds (longer start for better spread)
MAX_DELAY = 120.0  # seconds (longer than 60s rate limit window)


# Model output limits (conservative values, not absolute max)
# Claude Sonnet 4.5: max 64K output, we use 16K for safety
# Claude Haiku: max 8K output
# GPT-5.2: max 128K output, we use 32K for safety
MODEL_OUTPUT_LIMITS = {
    # Anthropic models
    "claude-sonnet": 16384,  # Sonnet models (max 64K, use 16K safely)
    "claude-opus": 16384,    # Opus models (max 32K, use 16K safely)
    "claude-haiku": 8192,    # Haiku models (max 8K)
    # OpenAI models
    "gpt-5.2": 32768,        # GPT-5.2 (max 128K, use 32K safely)
    "gpt-5-mini": 16384,     # GPT-5-mini
    "gpt-5": 32768,          # GPT-5
    "gpt-4": 8192,           # GPT-4 variants
    # Default fallback
    "default": 8192
}


def get_output_limit(model: str) -> int:
    """Get appropriate max_tokens for a model based on its capabilities."""
    model_lower = model.lower()
    for prefix, limit in MODEL_OUTPUT_LIMITS.items():
        if prefix != "default" and prefix in model_lower:
            return limit
    return MODEL_OUTPUT_LIMITS["default"]


@dataclass
class LLMResponse:
    """Unified response format from any LLM provider."""
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    usage: Dict[str, int] = field(default_factory=dict)
    thinking: Optional[str] = None  # Extended thinking content (Anthropic only)
    thinking_signature: Optional[str] = None  # Required for thinking blocks in message history
    cost_usd: float = 0.0  # Calculated cost for this request
    reasoning_tokens: int = 0  # Reasoning tokens (OpenAI GPT-5.2+ only)
    truncated: bool = False  # True if response was truncated at max_tokens
    stop_reason: Optional[str] = None  # Why the model stopped (end_turn, max_tokens, tool_use, etc.)

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        thinking_budget: Optional[int] = None,
        reasoning_effort: Optional[str] = None,
        cancellation_check: Optional[Callable[[], bool]] = None
    ) -> LLMResponse:
        """Send chat completion request.

        Args:
            cancellation_check: Optional callable that returns True if job was cancelled.
                               Used with streaming to allow fast cancellation during LLM calls.
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model name being used."""
        pass


class LiteLLMProvider(BaseLLMProvider):
    """Universal LLM provider powered by LiteLLM.

    Supports all providers through LiteLLM's unified interface:
    - Anthropic: model="claude-sonnet-4-5-20250929" (auto-detected)
    - OpenAI: model="gpt-5.2" (auto-detected)
    - Groq: model="groq/llama-3.1-8b-instant"
    - Ollama: model="ollama/llama3"
    - Azure: model="azure/<deployment>"
    - OpenRouter: model="openrouter/<model>"
    """

    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None, provider_name: str = "litellm"):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.provider_name = provider_name

        # Configure LiteLLM globally
        import litellm
        litellm.drop_params = True  # Silently ignore unsupported params per provider

    def get_model_name(self) -> str:
        return self.model

    def _is_anthropic(self) -> bool:
        """Check if current model is Anthropic (for thinking/cache features)."""
        return self.provider_name == "anthropic" or "claude" in self.model.lower()

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        thinking_budget: Optional[int] = None,
        reasoning_effort: Optional[str] = None,
        cancellation_check: Optional[Callable[[], bool]] = None
    ) -> LLMResponse:
        """Send chat completion via LiteLLM."""
        import litellm

        # Prepare messages (adds thinking blocks for Anthropic, cache_control for system)
        is_anthropic = self._is_anthropic()
        include_thinking = bool(thinking_budget) and is_anthropic
        prepared_messages = self._prepare_messages(messages, include_thinking)

        # Build kwargs
        kwargs = {
            "model": self.model,
            "messages": prepared_messages,
            "max_tokens": get_output_limit(self.model),
        }

        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.base_url:
            kwargs["api_base"] = self.base_url

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        # Anthropic extended thinking
        if thinking_budget and is_anthropic:
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
            # Extended thinking requires higher max_tokens
            # Using 16384 buffer to prevent truncation when generating large tool call arguments
            kwargs["max_tokens"] = max(kwargs["max_tokens"], thinking_budget + 16384)

        # OpenAI reasoning effort
        if reasoning_effort and reasoning_effort != "none":
            kwargs["reasoning_effort"] = reasoning_effort

        # Retry loop for rate limits and thinking block errors
        thinking_retry_done = False
        for attempt in range(MAX_RETRIES):
            try:
                if cancellation_check:
                    return self._chat_streaming(kwargs, cancellation_check)
                else:
                    response = litellm.completion(**kwargs)
                    return self._parse_response(response)
            except JobCancelledException:
                raise
            except Exception as e:
                error_str = str(e)
                is_rate_limit = "rate_limit" in error_str or "429" in error_str
                is_thinking_error = "thinking" in error_str.lower() and ("400" in error_str or "invalid" in error_str.lower())
                is_tool_pair_error = "tool_use_id" in error_str and "tool_result" in error_str

                # Handle thinking block or tool pair error - retry without thinking (Anthropic-specific)
                # Tool pair errors can happen when thinking content blocks interfere with
                # LiteLLM's tool_use/tool_result conversion for the Anthropic API
                if (is_thinking_error or is_tool_pair_error) and not thinking_retry_done and is_anthropic:
                    thinking_retry_done = True
                    error_type = "tool pair" if is_tool_pair_error else "thinking block"
                    _log(f"[LiteLLM] {error_type} error, retrying without thinking in history")
                    kwargs["messages"] = self._prepare_messages(messages, include_thinking=False)
                    kwargs.pop("thinking", None)
                    continue

                if is_rate_limit and attempt < MAX_RETRIES - 1:
                    delay = min(BASE_DELAY * (2 ** attempt) + random.uniform(1, 10), MAX_DELAY)
                    _log(f"[RateLimit] Retry {attempt + 1}/{MAX_RETRIES} in {delay:.1f}s")
                    self._sleep_with_cancel_check(delay, cancellation_check)
                    continue

                log_error(f"LLM API error ({self.provider_name}): {e}")
                raise

    def _sleep_with_cancel_check(self, delay: float, cancellation_check: Optional[Callable[[], bool]]):
        """Sleep with periodic cancellation checks."""
        if not cancellation_check:
            time.sleep(delay)
            return
        elapsed = 0.0
        while elapsed < delay:
            if cancellation_check():
                raise JobCancelledException("Cancelled during retry wait")
            time.sleep(0.1)
            elapsed += 0.1

    def _prepare_messages(self, messages: List[Dict[str, Any]], include_thinking: bool) -> List[Dict[str, Any]]:
        """Prepare messages for LiteLLM in OpenAI format.

        Handles:
        - Anthropic system messages: adds cache_control via content blocks
        - Anthropic thinking: converts thinking blocks to content array format
        - Tool pair validation: ensures every tool result has a matching tool_use
        - Strips custom fields (thinking, thinking_signature, internal)
        """
        is_anthropic = self._is_anthropic()
        prepared = []

        for msg in messages:
            role = msg.get("role")

            # System message with cache_control for Anthropic
            if role == "system" and is_anthropic:
                content = msg.get("content", "")
                prepared.append({
                    "role": "system",
                    "content": [{
                        "type": "text",
                        "text": content,
                        "cache_control": {"type": "ephemeral"}
                    }]
                })
                continue

            # Assistant messages with thinking blocks (Anthropic only)
            if role == "assistant" and is_anthropic and include_thinking and msg.get("thinking"):
                content_blocks = []

                # Thinking block (MUST come first - Anthropic requirement)
                thinking = msg["thinking"]
                if isinstance(thinking, dict) and thinking.get("type") == "redacted":
                    thinking_block = {"type": "redacted_thinking", "data": thinking.get("data", "")}
                else:
                    thinking_block = {"type": "thinking", "thinking": thinking}
                if msg.get("thinking_signature"):
                    thinking_block["signature"] = msg["thinking_signature"]
                content_blocks.append(thinking_block)

                # Text content
                if msg.get("content"):
                    content_blocks.append({"type": "text", "text": msg["content"]})

                # Tool use blocks - keep in OpenAI format for LiteLLM to convert
                # (embedding tool_use directly in content blocks can cause LiteLLM
                # conversion issues where tool_use blocks get lost, leading to
                # orphan tool_result errors from the Anthropic API)
                prepared_msg = {"role": "assistant", "content": content_blocks}
                if msg.get("tool_calls"):
                    prepared_msg["tool_calls"] = msg["tool_calls"]

                prepared.append(prepared_msg)
                continue

            # Standard message - strip custom fields, keep OpenAI format
            clean_msg = {k: v for k, v in msg.items() if k not in ("thinking", "thinking_signature", "internal")}
            prepared.append(clean_msg)

        # Validate tool pairs - remove orphan tool results that would cause API errors
        prepared = self._fix_tool_pairs(prepared)

        return prepared

    def _fix_tool_pairs(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fix orphan tool_result messages that have no matching tool_use.

        Anthropic API requires every tool_result to reference a tool_use_id from
        the immediately preceding assistant message. This can break when:
        - Message history is compressed (old assistant messages with tool_calls removed)
        - Messages are truncated or corrupted

        Orphan tool results are converted to user messages with the tool output
        as text content, preserving the information without breaking the API.
        """
        # Build a map: for each tool message index, find the preceding assistant's tool_call_ids
        result = []
        # Track available tool_use_ids from the most recent assistant message
        available_tool_ids = set()

        for msg in messages:
            role = msg.get("role")

            if role == "assistant":
                # Collect tool_call_ids from this assistant message
                available_tool_ids = set()
                tool_calls = msg.get("tool_calls")
                if tool_calls:
                    for tc in tool_calls:
                        tc_id = tc.get("id")
                        if tc_id:
                            available_tool_ids.add(tc_id)
                # Also check content blocks (thinking format)
                content = msg.get("content")
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            block_id = block.get("id")
                            if block_id:
                                available_tool_ids.add(block_id)
                result.append(msg)

            elif role == "tool":
                tool_call_id = msg.get("tool_call_id")
                if tool_call_id and tool_call_id in available_tool_ids:
                    # Valid tool result - keep as-is
                    result.append(msg)
                else:
                    # Orphan tool result - convert to user message
                    tool_content = msg.get("content", "")
                    log_debug(f"[LiteLLM] Fixing orphan tool_result (id={tool_call_id}), converting to user message")
                    result.append({
                        "role": "user",
                        "content": f"[Previous tool output]: {tool_content[:500]}" if tool_content else "[Previous tool output]: (empty)"
                    })
            else:
                # user, system - reset available tool ids on user message
                if role == "user":
                    available_tool_ids = set()
                result.append(msg)

        return result

    def _chat_streaming(self, kwargs: dict, cancellation_check: Callable[[], bool]) -> LLMResponse:
        """Execute streaming chat with cancellation support via worker thread.

        Runs streaming in a separate daemon thread so we can abandon it immediately
        when cancelled. Accumulates chunks manually for reliable content/tool_call
        extraction, and uses stream_chunk_builder for thinking blocks.
        """
        import threading
        import queue as queue_mod
        import litellm

        kwargs["stream"] = True
        kwargs["stream_options"] = {"include_usage": True}

        result_queue = queue_mod.Queue()
        error_queue = queue_mod.Queue()

        def stream_worker():
            try:
                chunks = []
                content = ""
                tool_calls_data = {}
                usage_chunk = None
                finish_reason = None

                for chunk in litellm.completion(**kwargs):
                    chunks.append(chunk)
                    if chunk.choices:
                        choice = chunk.choices[0]
                        delta = choice.delta

                        # Accumulate content
                        if hasattr(delta, 'content') and delta.content:
                            content += delta.content

                        # Accumulate tool calls
                        if hasattr(delta, 'tool_calls') and delta.tool_calls:
                            for tc in delta.tool_calls:
                                idx = getattr(tc, 'index', 0)
                                if idx not in tool_calls_data:
                                    tool_calls_data[idx] = {"id": "", "name": "", "arguments": ""}
                                if tc.id:
                                    tool_calls_data[idx]["id"] = tc.id
                                if tc.function:
                                    if tc.function.name:
                                        tool_calls_data[idx]["name"] = tc.function.name
                                    if tc.function.arguments:
                                        tool_calls_data[idx]["arguments"] += tc.function.arguments

                        # Capture finish reason
                        if choice.finish_reason:
                            finish_reason = choice.finish_reason

                    # Usage (usually in last chunk)
                    if hasattr(chunk, 'usage') and chunk.usage:
                        usage_chunk = chunk.usage

                # Try stream_chunk_builder for complete response (thinking blocks, usage)
                complete_response = None
                try:
                    complete_response = litellm.stream_chunk_builder(chunks, messages=kwargs.get("messages"))
                except Exception:
                    pass

                result_queue.put((content, tool_calls_data, usage_chunk, finish_reason, complete_response))
            except Exception as e:
                error_queue.put(e)

        # Start worker thread (daemon=True so it's abandoned if we cancel)
        worker = threading.Thread(target=stream_worker, daemon=True)
        worker.start()

        # Wait for result with periodic cancellation checks
        while worker.is_alive():
            if cancellation_check():
                log_debug("[LiteLLM] Cancelled - abandoning stream worker thread")
                raise JobCancelledException("Cancelled during LLM streaming")
            worker.join(timeout=0.2)

        # Worker finished - check for errors
        if not error_queue.empty():
            raise error_queue.get()

        content, tool_calls_data, usage_chunk, finish_reason, complete_response = result_queue.get()

        # Build tool_calls list from accumulated data
        tool_calls = []
        for idx in sorted(tool_calls_data.keys()):
            tc = tool_calls_data[idx]
            tool_calls.append({
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": tc["arguments"]
                }
            })

        # Extract thinking blocks from complete response (Anthropic)
        thinking = None
        thinking_signature = None
        if complete_response and complete_response.choices:
            msg = complete_response.choices[0].message
            thinking_blocks = getattr(msg, 'thinking_blocks', None)
            if thinking_blocks:
                for block in thinking_blocks:
                    btype = block.get("type") if isinstance(block, dict) else getattr(block, "type", None)
                    if btype == "thinking":
                        thinking = block.get("thinking", "") if isinstance(block, dict) else getattr(block, "thinking", "")
                        thinking_signature = block.get("signature") if isinstance(block, dict) else getattr(block, "signature", None)
                    elif btype == "redacted_thinking":
                        data = block.get("data", "") if isinstance(block, dict) else getattr(block, "data", "")
                        thinking = {"type": "redacted", "data": data}
                        thinking_signature = block.get("signature") if isinstance(block, dict) else getattr(block, "signature", None)

        # Get usage - prefer complete_response, fall back to chunk usage
        usage_obj = None
        if complete_response and complete_response.usage:
            usage_obj = complete_response.usage
        elif usage_chunk:
            usage_obj = usage_chunk

        # Build usage dict
        usage_dict = self._build_usage_dict(usage_obj)

        # Log truncation warning
        if finish_reason == "length":
            log_debug("[LLM] WARNING: Response truncated at max_tokens limit")

        # Calculate cost
        from user_container.pricing import calculate_cost
        cost = calculate_cost(self.provider_name, self.model, usage_dict)

        # Extract reasoning tokens (OpenAI)
        reasoning_tokens = 0
        if usage_obj:
            output_details = getattr(usage_obj, 'output_tokens_details', None)
            if output_details:
                reasoning_tokens = getattr(output_details, 'reasoning_tokens', 0)

        return LLMResponse(
            content=content if content else None,
            tool_calls=tool_calls if tool_calls else None,
            usage=usage_dict,
            thinking=thinking,
            thinking_signature=thinking_signature,
            cost_usd=cost,
            reasoning_tokens=reasoning_tokens,
            truncated=(finish_reason == "length"),
            stop_reason=finish_reason
        )

    def _parse_response(self, response) -> LLMResponse:
        """Parse LiteLLM ModelResponse to unified LLMResponse format."""
        message = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        # Extract content
        content = message.content

        # Extract tool calls (OpenAI format - LiteLLM normalizes all providers)
        tool_calls = None
        if message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in message.tool_calls
            ]

        # Extract thinking blocks (Anthropic)
        thinking = None
        thinking_signature = None
        thinking_blocks = getattr(message, 'thinking_blocks', None)
        if thinking_blocks:
            for block in thinking_blocks:
                btype = block.get("type") if isinstance(block, dict) else getattr(block, "type", None)
                if btype == "thinking":
                    thinking = block.get("thinking", "") if isinstance(block, dict) else getattr(block, "thinking", "")
                    thinking_signature = block.get("signature") if isinstance(block, dict) else getattr(block, "signature", None)
                elif btype == "redacted_thinking":
                    data = block.get("data", "") if isinstance(block, dict) else getattr(block, "data", "")
                    thinking = {"type": "redacted", "data": data}
                    thinking_signature = block.get("signature") if isinstance(block, dict) else getattr(block, "signature", None)

        # Build usage dict
        usage_dict = self._build_usage_dict(response.usage)

        # Extract reasoning tokens (OpenAI)
        reasoning_tokens = 0
        if response.usage:
            output_details = getattr(response.usage, 'output_tokens_details', None)
            if output_details:
                reasoning_tokens = getattr(output_details, 'reasoning_tokens', 0)

        # Calculate cost
        from user_container.pricing import calculate_cost
        cost = calculate_cost(self.provider_name, self.model, usage_dict)

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            usage=usage_dict,
            thinking=thinking,
            thinking_signature=thinking_signature,
            cost_usd=cost,
            reasoning_tokens=reasoning_tokens,
            truncated=(finish_reason == "length"),
            stop_reason=finish_reason
        )

    def _build_usage_dict(self, usage) -> Dict[str, int]:
        """Build unified usage dict from LiteLLM usage object."""
        if not usage:
            return {"prompt_tokens": 0, "completion_tokens": 0}

        usage_dict = {
            "prompt_tokens": getattr(usage, 'prompt_tokens', 0) or 0,
            "completion_tokens": getattr(usage, 'completion_tokens', 0) or 0
        }

        # Anthropic cache tokens
        cache_creation = getattr(usage, 'cache_creation_input_tokens', 0)
        cache_read = getattr(usage, 'cache_read_input_tokens', 0)
        if cache_creation or cache_read:
            usage_dict["cache_creation_tokens"] = cache_creation or 0
            usage_dict["cache_read_tokens"] = cache_read or 0
            if cache_read and cache_read > 0:
                log_debug(f"[PromptCache] HIT: {cache_read} tokens from cache")
            elif cache_creation and cache_creation > 0:
                log_debug(f"[PromptCache] MISS: {cache_creation} tokens cached for next request")

        # OpenAI cache tokens (different field name)
        if "cache_read_tokens" not in usage_dict:
            prompt_details = getattr(usage, 'prompt_tokens_details', None)
            if prompt_details:
                cached = getattr(prompt_details, 'cached_tokens', 0)
                if cached:
                    usage_dict["cache_read_tokens"] = cached
                    log_debug(f"[Cache] HIT: {cached} tokens from cache")

        return usage_dict


class LLMClient:
    """
    Unified LLM client that wraps different providers.

    Usage:
        client = LLMClient.default()
        response = client.chat(messages, tools)
    """

    def __init__(self, provider: BaseLLMProvider):
        self._provider = provider

    @property
    def model(self) -> str:
        """Return the model name being used."""
        return self._provider.get_model_name()

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        thinking_budget: Optional[int] = None,
        reasoning_effort: Optional[str] = None,
        component: Optional[str] = None,
        job_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        cancellation_check: Optional[Callable[[], bool]] = None
    ) -> LLMResponse:
        """
        Send chat completion request.

        Args:
            messages: List of messages in OpenAI format
            tools: List of tools in OpenAI format (auto-converted for all providers)
            thinking_budget: Token budget for extended thinking (Anthropic only)
            reasoning_effort: Reasoning effort level (OpenAI GPT-5.2+ only): "none", "low", "medium", "high"
            tool_choice: "auto", "none", "required", or specific tool name
            component: Calling component for usage tracking (e.g., "agent", "routing")
            job_id: Job ID for usage tracking
            conversation_id: Conversation ID for usage tracking
            cancellation_check: Optional callable that returns True if job was cancelled.
                               Enables fast cancellation during LLM streaming.

        Returns:
            LLMResponse with content, tool_calls, and usage
        """
        thinking_info = f", thinking={thinking_budget}" if thinking_budget else ""
        reasoning_info = f", reasoning={reasoning_effort}" if reasoning_effort else ""
        log_debug(f"LLM.chat() with {self.model}, {len(messages)} messages, {len(tools) if tools else 0} tools{thinking_info}{reasoning_info}")

        response = self._provider.chat(
            messages, tools, tool_choice, thinking_budget, reasoning_effort,
            cancellation_check=cancellation_check
        )

        # Log to Langfuse (observability)
        cache_read_tokens = response.usage.get("cache_read_tokens", 0)
        reasoning_tokens = response.usage.get("reasoning_tokens", 0)
        log_generation(
            name=f"llm/{component or 'unknown'}",
            model=self.model,
            input_messages=messages,
            output=response.content,
            usage=response.usage,
            cost_usd=response.cost_usd,
            metadata={
                "thinking_budget": thinking_budget,
                "reasoning_effort": reasoning_effort,
                "reasoning_tokens": reasoning_tokens,
                "tool_count": len(tools) if tools else 0,
                "job_id": job_id,
                "conversation_id": conversation_id,
                "cache_hit": cache_read_tokens > 0,
                "cached_tokens": cache_read_tokens,
            }
        )

        # Track usage if component is specified
        if component:
            try:
                from user_container.usage import UsageTracker
                tracker = UsageTracker.get_instance()
                tracker.track(
                    model=self.model,
                    provider=self._provider.provider_name if hasattr(self._provider, 'provider_name') else "litellm",
                    usage=response.usage,
                    cost_usd=response.cost_usd,
                    component=component,
                    job_id=job_id,
                    conversation_id=conversation_id
                )
            except RuntimeError:
                # Tracker not initialized yet (e.g., during startup)
                pass

        return response

    @classmethod
    def default(cls) -> "LLMClient":
        """
        Create client with default (main) model via OpenRouter.

        Settings priority: Database -> Environment -> Default.
        """
        or_settings = cls._get_openrouter_settings()
        if not or_settings["api_key"]:
            raise ValueError("OPENROUTER_API_KEY not set. Configure it in Settings.")
        provider = LiteLLMProvider(
            model=f"openrouter/{or_settings['model']}",
            api_key=or_settings["api_key"],
            provider_name="openrouter"
        )
        return cls(provider)

    @classmethod
    def cheap(cls) -> "LLMClient":
        """
        Create client with cheap model for routing/compression via OpenRouter.
        """
        or_settings = cls._get_openrouter_settings()
        if not or_settings["api_key"]:
            raise ValueError("OPENROUTER_API_KEY not set. Configure it in Settings.")
        model = or_settings["cheap_model"] or or_settings["model"]
        provider = LiteLLMProvider(
            model=f"openrouter/{model}",
            api_key=or_settings["api_key"],
            provider_name="openrouter"
        )
        return cls(provider)

    @classmethod
    def routing(cls) -> "LLMClient":
        """
        Create client optimized for routing decisions.

        Uses Groq (fast TTFT) if available, otherwise falls back to cheap model.
        Controlled by ROUTING_PROVIDER env var:
        - "auto": Use Groq if GROQ_API_KEY is set, else cheap model
        - "groq": Force Groq (error if no API key)
        - "default": Always use cheap model
        """
        routing_provider = settings.routing_provider.lower()

        use_groq = False
        if routing_provider == "groq":
            if not settings.groq_api_key:
                raise ValueError("ROUTING_PROVIDER=groq but GROQ_API_KEY not set")
            use_groq = True
        elif routing_provider == "auto" and settings.groq_api_key:
            use_groq = True

        if use_groq:
            provider = LiteLLMProvider(
                model=f"groq/{settings.groq_routing_model}",
                api_key=settings.groq_api_key,
                provider_name="groq"
            )
            return cls(provider)

        return cls.cheap()  # fallback

    @classmethod
    def custom(cls, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None) -> "LLMClient":
        """Create client with custom model via LiteLLM.

        Args:
            model: LiteLLM model identifier (e.g., "openrouter/anthropic/claude-sonnet-4-5-20250929")
            api_key: Optional API key for the provider
            base_url: Optional base URL for the API endpoint
        """
        provider = LiteLLMProvider(
            model=model,
            api_key=api_key,
            base_url=base_url,
            provider_name="custom"
        )
        return cls(provider)

    @classmethod
    def _get_openrouter_settings(cls) -> dict:
        """Load OpenRouter settings from DB (with config/env fallback)."""
        model = settings.openrouter_model
        cheap_model = settings.openrouter_cheap_model
        api_key = settings.openrouter_api_key

        try:
            from user_container.db.db import DB
            db = DB(settings.db_path)
            model = db.get_setting("openrouter_model") or model
            cheap_model = db.get_setting("openrouter_cheap_model") or cheap_model
            api_key = db.get_setting("openrouter_api_key") or api_key
        except Exception:
            pass

        return {
            "model": model,
            "cheap_model": cheap_model,
            "api_key": api_key,
        }
