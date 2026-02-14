"""
LLM Client - Unified interface for multiple LLM providers.

Supports:
- Anthropic (Claude)
- OpenAI (GPT)

Usage:
    client = LLMClient.default()  # Main model from config
    client = LLMClient.cheap()    # Cheap model for routing/compression

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


def get_effective_model_provider() -> str:
    """
    Get the effective model provider, checking database setting first.

    Priority:
    1. Database setting (user_settings.model_provider)
    2. Environment variable (MODEL_PROVIDER)
    3. Default ("anthropic")

    Returns:
        Provider name: "anthropic" or "openai"
    """
    try:
        from user_container.db.db import DB
        db = DB(settings.db_path)
        db_provider = db.get_setting("model_provider")
        if db_provider:
            return db_provider.lower()
    except Exception:
        # Database not available or error - fall back to config
        pass

    return settings.model_provider.lower()


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


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: str, model: str):
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

        self.model = model
        self.provider_name = "anthropic"

    def get_model_name(self) -> str:
        return self.model

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        thinking_budget: Optional[int] = None,
        reasoning_effort: Optional[str] = None,  # ignored for Anthropic
        cancellation_check: Optional[Callable[[], bool]] = None
    ) -> LLMResponse:
        """Send chat completion to Anthropic using streaming for cancellation support."""
        # Separate system message from conversation
        system_content = ""
        conversation = []

        # Determine if we should include thinking blocks
        # When thinking is disabled, we MUST strip thinking blocks from history
        # (Anthropic API rejects thinking blocks in history when thinking is disabled)
        include_thinking = bool(thinking_budget)

        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                conversation.append(self._convert_message_to_anthropic(msg, include_thinking=include_thinking))

        # Build request kwargs
        kwargs = {
            "model": self.model,
            "max_tokens": get_output_limit(self.model),
            "messages": conversation,
        }

        if system_content:
            # Use cache_control for system prompt (prompt caching)
            kwargs["system"] = [
                {
                    "type": "text",
                    "text": system_content,
                    "cache_control": {"type": "ephemeral"}
                }
            ]

        if tools:
            kwargs["tools"] = self._convert_tools_to_anthropic(tools)
            kwargs["tool_choice"] = self._convert_tool_choice(tool_choice)

        # Extended thinking (Anthropic-specific)
        if thinking_budget:
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": thinking_budget
            }
            # Extended thinking requires higher max_tokens
            # Using 16384 buffer to prevent truncation when generating large tool call arguments
            # (e.g., write_file with large content). 4096 was too tight and caused infinite loops
            # when the model's output was truncated mid-tool-call.
            kwargs["max_tokens"] = max(kwargs["max_tokens"], thinking_budget + 16384)

        # Retry loop for rate limits and thinking block errors
        thinking_retry_done = False  # Track if we already retried without thinking
        for attempt in range(MAX_RETRIES):
            try:
                # Use streaming if cancellation_check is provided (allows fast cancellation)
                if cancellation_check:
                    return self._chat_streaming(kwargs, cancellation_check)
                else:
                    # Fallback to non-streaming for backwards compatibility
                    response = self.client.messages.create(**kwargs)
                    return self._parse_response(response)
            except JobCancelledException:
                # Re-raise cancellation without retry
                raise
            except Exception as e:
                error_str = str(e)
                is_rate_limit = "rate_limit" in error_str or "429" in error_str
                is_thinking_error = "thinking" in error_str.lower() and "400" in error_str

                # Handle thinking block order error - retry without thinking
                if is_thinking_error and not thinking_retry_done:
                    thinking_retry_done = True
                    _log("[AnthropicProvider] Thinking block error, retrying without thinking in history")
                    # Rebuild conversation without thinking blocks
                    new_conversation = []
                    for msg in messages:
                        if msg["role"] != "system":
                            new_conversation.append(self._convert_message_to_anthropic(msg, include_thinking=False))
                    kwargs["messages"] = new_conversation
                    # Remove thinking from request too (graceful degradation)
                    kwargs.pop("thinking", None)
                    continue

                if is_rate_limit and attempt < MAX_RETRIES - 1:
                    delay = min(BASE_DELAY * (2 ** attempt) + random.uniform(1, 10), MAX_DELAY)
                    _log(f"[RateLimit] Retry {attempt + 1}/{MAX_RETRIES} in {delay:.1f}s")
                    # Interruptible sleep - check cancellation every 0.1s
                    self._sleep_with_cancel_check(delay, cancellation_check)
                    continue

                log_error(f"Anthropic API error: {e}")
                raise

    def _sleep_with_cancel_check(self, delay: float, cancellation_check: Optional[Callable[[], bool]]):
        """Sleep with periodic cancellation checks."""
        if not cancellation_check:
            time.sleep(delay)
            return

        # Sleep in 0.1s increments, checking for cancellation
        elapsed = 0.0
        while elapsed < delay:
            if cancellation_check():
                raise JobCancelledException("Cancelled during retry wait")
            time.sleep(0.1)
            elapsed += 0.1

    def _chat_streaming(self, kwargs: dict, cancellation_check: Callable[[], bool]) -> LLMResponse:
        """Execute chat with streaming, checking for cancellation.

        Runs streaming in a separate thread so we can abandon it immediately
        when cancelled (stream.close() doesn't interrupt blocking HTTP reads).
        """
        import threading
        import queue

        result_queue = queue.Queue()
        error_queue = queue.Queue()

        def stream_worker():
            """Worker thread that performs the actual streaming."""
            try:
                content_blocks = []
                current_block = None
                usage_info = None

                with self.client.messages.stream(**kwargs) as stream:
                    for event in stream:
                        # Process streaming events to build content blocks
                        event_type = getattr(event, 'type', None)

                        if event_type == 'content_block_start':
                            block = getattr(event, 'content_block', None)
                            if block:
                                block_type = getattr(block, 'type', None)
                                if block_type == 'thinking':
                                    current_block = {'type': 'thinking', 'thinking': '', 'signature': None}
                                elif block_type == 'text':
                                    current_block = {'type': 'text', 'text': ''}
                                elif block_type == 'tool_use':
                                    current_block = {
                                        'type': 'tool_use',
                                        'id': getattr(block, 'id', ''),
                                        'name': getattr(block, 'name', ''),
                                        'input': ''
                                    }
                                elif block_type == 'redacted_thinking':
                                    current_block = {
                                        'type': 'redacted_thinking',
                                        'data': getattr(block, 'data', '')
                                    }

                        elif event_type == 'content_block_delta':
                            delta = getattr(event, 'delta', None)
                            if delta and current_block:
                                delta_type = getattr(delta, 'type', None)
                                if delta_type == 'thinking_delta':
                                    current_block['thinking'] += getattr(delta, 'thinking', '')
                                elif delta_type == 'text_delta':
                                    current_block['text'] += getattr(delta, 'text', '')
                                elif delta_type == 'input_json_delta':
                                    current_block['input'] += getattr(delta, 'partial_json', '')
                                elif delta_type == 'signature_delta':
                                    current_block['signature'] = getattr(delta, 'signature', None)

                        elif event_type == 'content_block_stop':
                            if current_block:
                                content_blocks.append(current_block)
                                current_block = None

                    # Get final message for usage info and stop_reason
                    final_message = stream.get_final_message()
                    usage_info = final_message.usage if final_message else None
                    stop_reason = final_message.stop_reason if final_message else None

                result_queue.put((content_blocks, usage_info, stop_reason))
            except Exception as e:
                error_queue.put(e)

        # Start worker thread (daemon=True so it's abandoned if we cancel)
        worker = threading.Thread(target=stream_worker, daemon=True)
        worker.start()

        # Wait for result with periodic cancellation checks
        while worker.is_alive():
            if cancellation_check():
                log_debug("[AnthropicProvider] Cancelled - abandoning stream worker thread")
                raise JobCancelledException("Cancelled during LLM streaming")
            worker.join(timeout=0.2)  # Check every 200ms

        # Worker finished - check for errors
        if not error_queue.empty():
            raise error_queue.get()

        # Get result
        content_blocks, usage_info, stop_reason = result_queue.get()

        # Check for truncation
        if stop_reason == "max_tokens":
            log_debug("[LLM] WARNING: Response truncated at max_tokens limit")

        return self._parse_streamed_response(content_blocks, usage_info, stop_reason)

    def _convert_message_to_anthropic(self, msg: Dict[str, Any], include_thinking: bool = True) -> Dict[str, Any]:
        """Convert OpenAI message format to Anthropic format.

        Args:
            msg: Message in OpenAI format
            include_thinking: If False, strip thinking blocks from history.
                              Required when thinking is disabled in current request.
        """
        role = msg["role"]

        # Tool results come as role="tool" in OpenAI format
        if role == "tool":
            return {
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": msg.get("tool_call_id"),
                    "content": msg.get("content", "")
                }]
            }

        # Assistant messages (may have thinking, tool_calls, or just content)
        if role == "assistant":
            # Only include thinking if enabled for current request
            has_thinking = msg.get("thinking") if include_thinking else None
            has_tool_calls = msg.get("tool_calls")
            has_content = msg.get("content")

            # If we have thinking or tool_calls, we need content blocks
            if has_thinking or has_tool_calls:
                content_blocks = []

                # Thinking MUST come first (Anthropic requirement)
                if has_thinking:
                    # Check if this is redacted thinking (stored as dict with type="redacted")
                    if isinstance(has_thinking, dict) and has_thinking.get("type") == "redacted":
                        # Redacted thinking - must send back as redacted_thinking block
                        thinking_block = {
                            "type": "redacted_thinking",
                            "data": has_thinking.get("data", "")
                        }
                    else:
                        # Normal thinking
                        thinking_block = {
                            "type": "thinking",
                            "thinking": msg["thinking"]
                        }
                    # Signature is required when sending thinking blocks back to API
                    if msg.get("thinking_signature"):
                        thinking_block["signature"] = msg["thinking_signature"]
                    content_blocks.append(thinking_block)

                # Add text content if present
                if has_content:
                    content_blocks.append({
                        "type": "text",
                        "text": msg["content"]
                    })

                # Add tool use blocks
                if has_tool_calls:
                    for tc in msg["tool_calls"]:
                        func = tc.get("function", {})
                        args = func.get("arguments", "{}")
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except json.JSONDecodeError:
                                args = {}

                        content_blocks.append({
                            "type": "tool_use",
                            "id": tc.get("id"),
                            "name": func.get("name"),
                            "input": args
                        })

                # Defensive: ensure thinking blocks are first (Anthropic requirement)
                if content_blocks and len(content_blocks) > 1:
                    thinking_types = ("thinking", "redacted_thinking")
                    if content_blocks[0].get("type") not in thinking_types:
                        has_thinking = any(b.get("type") in thinking_types for b in content_blocks)
                        if has_thinking:
                            content_blocks.sort(key=lambda b: 0 if b.get("type") in thinking_types else 1)

                return {"role": "assistant", "content": content_blocks}

            # Simple assistant message (no thinking, no tools)
            return {"role": "assistant", "content": has_content or ""}

        # Regular user messages
        return {
            "role": role if role != "tool" else "user",
            "content": msg.get("content", "")
        }

    def _convert_tools_to_anthropic(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert OpenAI tool format to Anthropic format."""
        anthropic_tools = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool["function"]
                anthropic_tools.append({
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {"type": "object", "properties": {}})
                })
        return anthropic_tools

    def _convert_tool_choice(self, tool_choice: str) -> Dict[str, Any]:
        """Convert OpenAI tool_choice to Anthropic format."""
        if tool_choice == "none":
            return {"type": "none"}
        elif tool_choice == "auto":
            return {"type": "auto"}
        elif tool_choice == "required":
            return {"type": "any"}
        else:
            # Specific tool name
            return {"type": "tool", "name": tool_choice}

    def _parse_response(self, response) -> LLMResponse:
        """Parse Anthropic response to unified format."""
        content = None
        thinking = None
        thinking_signature = None
        tool_calls = []
        stop_reason = response.stop_reason  # Capture stop_reason

        for block in response.content:
            if block.type == "thinking":
                # Extended thinking block (Anthropic-specific)
                thinking = block.thinking
                thinking_signature = getattr(block, 'signature', None)
            elif block.type == "redacted_thinking":
                # Redacted thinking block - Anthropic encrypts thinking in some cases
                # Must be preserved and sent back as-is to the API
                thinking = {"type": "redacted", "data": getattr(block, 'data', '')}
                thinking_signature = getattr(block, 'signature', None)
            elif block.type == "text":
                content = block.text
            elif block.type == "tool_use":
                # Convert to OpenAI-compatible tool call format
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input)
                    }
                })

        # Build usage dict with cache info if available
        usage = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens
        }

        # Add cache info if present (prompt caching)
        cache_creation = getattr(response.usage, 'cache_creation_input_tokens', 0)
        cache_read = getattr(response.usage, 'cache_read_input_tokens', 0)
        if cache_creation or cache_read:
            usage["cache_creation_tokens"] = cache_creation
            usage["cache_read_tokens"] = cache_read
            # Log cache hit/miss
            if cache_read > 0:
                log_debug(f"[PromptCache] HIT: {cache_read} tokens from cache")
            elif cache_creation > 0:
                log_debug(f"[PromptCache] MISS: {cache_creation} tokens cached for next request")

        # Calculate cost
        from user_container.pricing import calculate_cost
        cost = calculate_cost("anthropic", self.model, usage)

        return LLMResponse(
            content=content,
            tool_calls=tool_calls if tool_calls else None,
            usage=usage,
            thinking=thinking,
            thinking_signature=thinking_signature,
            cost_usd=cost,
            stop_reason=stop_reason
        )

    def _parse_streamed_response(self, content_blocks: List[dict], usage, stop_reason: str = None) -> LLMResponse:
        """Parse streamed content blocks to unified format."""
        content = None
        thinking = None
        thinking_signature = None
        tool_calls = []

        for block in content_blocks:
            block_type = block.get('type')
            if block_type == 'thinking':
                thinking = block.get('thinking', '')
                thinking_signature = block.get('signature')
            elif block_type == 'redacted_thinking':
                thinking = {"type": "redacted", "data": block.get('data', '')}
                thinking_signature = block.get('signature')
            elif block_type == 'text':
                content = block.get('text', '')
            elif block_type == 'tool_use':
                # Parse JSON input string to dict
                input_str = block.get('input', '{}')
                try:
                    input_dict = json.loads(input_str) if isinstance(input_str, str) else input_str
                except json.JSONDecodeError:
                    input_dict = {}

                tool_calls.append({
                    "id": block.get('id', ''),
                    "type": "function",
                    "function": {
                        "name": block.get('name', ''),
                        "arguments": json.dumps(input_dict)
                    }
                })

        # Build usage dict
        usage_dict = {
            "prompt_tokens": getattr(usage, 'input_tokens', 0) if usage else 0,
            "completion_tokens": getattr(usage, 'output_tokens', 0) if usage else 0
        }

        # Add cache info if present
        if usage:
            cache_creation = getattr(usage, 'cache_creation_input_tokens', 0)
            cache_read = getattr(usage, 'cache_read_input_tokens', 0)
            if cache_creation or cache_read:
                usage_dict["cache_creation_tokens"] = cache_creation
                usage_dict["cache_read_tokens"] = cache_read
                if cache_read > 0:
                    log_debug(f"[PromptCache] HIT: {cache_read} tokens from cache")
                elif cache_creation > 0:
                    log_debug(f"[PromptCache] MISS: {cache_creation} tokens cached for next request")

        # Calculate cost
        from user_container.pricing import calculate_cost
        cost = calculate_cost("anthropic", self.model, usage_dict)

        return LLMResponse(
            content=content,
            tool_calls=tool_calls if tool_calls else None,
            usage=usage_dict,
            thinking=thinking,
            thinking_signature=thinking_signature,
            cost_usd=cost,
            truncated=(stop_reason == "max_tokens")
        )


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider (also works with OpenAI-compatible APIs like Groq).

    Supports both Chat Completions API (legacy) and Responses API (GPT-5.2+).
    The Responses API is used when:
    - Model is gpt-5.2 or newer
    - reasoning_effort is specified
    """

    # Models that support/require Responses API
    RESPONSES_API_MODELS = {"gpt-5.2", "gpt-5.2-codex"}

    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None):
        try:
            from openai import OpenAI
            kwargs = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            self.client = OpenAI(**kwargs)
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

        self.model = model
        self.base_url = base_url
        # Detect provider from base_url
        if base_url and "groq" in base_url:
            self.provider_name = "groq"
        else:
            self.provider_name = "openai"

    def get_model_name(self) -> str:
        return self.model

    def _should_use_responses_api(self) -> bool:
        """Check if we should use Responses API for this model."""
        # Don't use Responses API for non-OpenAI providers (Groq, etc.)
        if self.provider_name != "openai":
            return False
        # Check if model supports Responses API
        return self.model in self.RESPONSES_API_MODELS

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        thinking_budget: Optional[int] = None,  # ignored for OpenAI
        reasoning_effort: Optional[str] = None,
        cancellation_check: Optional[Callable[[], bool]] = None
    ) -> LLMResponse:
        """Send chat completion to OpenAI.

        Args:
            messages: Conversation messages
            tools: Available tools
            tool_choice: "auto", "none", "required", or tool name
            thinking_budget: Ignored (Anthropic-specific)
            reasoning_effort: "none", "low", "medium", "high" (GPT-5.2+ only)
            cancellation_check: Optional callable that returns True if job was cancelled
        """
        if self._should_use_responses_api():
            return self._chat_responses_api(messages, tools, tool_choice, reasoning_effort, cancellation_check)
        else:
            return self._chat_completions_api(messages, tools, tool_choice, cancellation_check)

    def _chat_completions_api(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        cancellation_check: Optional[Callable[[], bool]] = None
    ) -> LLMResponse:
        """Send chat completion using Chat Completions API (legacy)."""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "max_tokens": get_output_limit(self.model),
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        # Retry loop for rate limits
        for attempt in range(MAX_RETRIES):
            try:
                # Use streaming if cancellation_check is provided
                if cancellation_check:
                    return self._chat_completions_streaming(kwargs, cancellation_check)
                else:
                    response = self.client.chat.completions.create(**kwargs)
                    return self._parse_completions_response(response)
            except JobCancelledException:
                # Re-raise cancellation without retry
                raise
            except Exception as e:
                error_str = str(e)
                is_rate_limit = "rate_limit" in error_str or "429" in error_str

                if is_rate_limit and attempt < MAX_RETRIES - 1:
                    delay = min(BASE_DELAY * (2 ** attempt) + random.uniform(1, 10), MAX_DELAY)
                    _log(f"[RateLimit] Retry {attempt + 1}/{MAX_RETRIES} in {delay:.1f}s")
                    self._sleep_with_cancel_check(delay, cancellation_check)
                    continue

                log_error(f"OpenAI API error: {e}")
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

    def _chat_completions_streaming(
        self,
        kwargs: dict,
        cancellation_check: Callable[[], bool]
    ) -> LLMResponse:
        """Execute chat with streaming, checking for cancellation.

        Runs streaming in a separate thread so we can abandon it immediately when cancelled.
        """
        import threading
        import queue

        kwargs["stream"] = True
        kwargs["stream_options"] = {"include_usage": True}

        result_queue = queue.Queue()
        error_queue = queue.Queue()

        def stream_worker():
            """Worker thread that performs the actual streaming."""
            try:
                content = ""
                tool_calls_data = {}
                usage = None

                with self.client.chat.completions.create(**kwargs) as stream:
                    for chunk in stream:
                        if chunk.choices:
                            delta = chunk.choices[0].delta
                            if delta.content:
                                content += delta.content
                            if delta.tool_calls:
                                for tc in delta.tool_calls:
                                    idx = tc.index
                                    if idx not in tool_calls_data:
                                        tool_calls_data[idx] = {
                                            "id": tc.id or "",
                                            "name": tc.function.name if tc.function else "",
                                            "arguments": ""
                                        }
                                    if tc.id:
                                        tool_calls_data[idx]["id"] = tc.id
                                    if tc.function:
                                        if tc.function.name:
                                            tool_calls_data[idx]["name"] = tc.function.name
                                        if tc.function.arguments:
                                            tool_calls_data[idx]["arguments"] += tc.function.arguments
                        if chunk.usage:
                            usage = chunk.usage

                result_queue.put((content, tool_calls_data, usage))
            except Exception as e:
                error_queue.put(e)

        # Start worker thread (daemon=True so it's abandoned if we cancel)
        worker = threading.Thread(target=stream_worker, daemon=True)
        worker.start()

        # Wait for result with periodic cancellation checks
        while worker.is_alive():
            if cancellation_check():
                log_debug("[OpenAIProvider] Cancelled - abandoning stream worker thread")
                raise JobCancelledException("Cancelled during LLM streaming")
            worker.join(timeout=0.2)

        # Worker finished - check for errors
        if not error_queue.empty():
            raise error_queue.get()

        # Get result
        content, tool_calls_data, usage = result_queue.get()

        # Build tool_calls list
        tool_calls = []
        for idx in sorted(tool_calls_data.keys()):
            tc_data = tool_calls_data[idx]
            tool_calls.append({
                "id": tc_data["id"],
                "type": "function",
                "function": {
                    "name": tc_data["name"],
                    "arguments": tc_data["arguments"]
                }
            })

        # Build usage dict
        usage_dict = {
            "prompt_tokens": getattr(usage, 'prompt_tokens', 0) if usage else 0,
            "completion_tokens": getattr(usage, 'completion_tokens', 0) if usage else 0
        }

        # Extract cached tokens if present
        if usage:
            prompt_details = getattr(usage, 'prompt_tokens_details', None)
            if prompt_details:
                cached = getattr(prompt_details, 'cached_tokens', 0)
                if cached:
                    usage_dict["cache_read_tokens"] = cached

        # Calculate cost
        from user_container.pricing import calculate_cost
        cost = calculate_cost(self.provider_name, self.model, usage_dict)

        return LLMResponse(
            content=content if content else None,
            tool_calls=tool_calls if tool_calls else None,
            usage=usage_dict,
            cost_usd=cost
        )

    def _chat_responses_api(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        reasoning_effort: Optional[str] = None,
        cancellation_check: Optional[Callable[[], bool]] = None
    ) -> LLMResponse:
        """Send chat completion using Responses API (GPT-5.2+)."""
        # Convert messages to Responses API format
        input_items = self._convert_messages_to_responses_api(messages)

        kwargs = {
            "model": self.model,
            "input": input_items,
            "max_output_tokens": get_output_limit(self.model),
        }

        # Add reasoning if specified (GPT-5.2 default is "none")
        if reasoning_effort and reasoning_effort != "none":
            kwargs["reasoning"] = {"effort": reasoning_effort}
            log_debug(f"[OpenAI] Using reasoning_effort={reasoning_effort}")

        # Convert and add tools
        if tools:
            kwargs["tools"] = self._convert_tools_to_responses_api(tools)
            # Responses API uses different tool_choice format
            if tool_choice == "required":
                kwargs["tool_choice"] = "required"
            elif tool_choice == "none":
                kwargs["tool_choice"] = "none"
            # "auto" is default, no need to specify

        # Retry loop for rate limits
        for attempt in range(MAX_RETRIES):
            try:
                # Use streaming if cancellation_check is provided
                if cancellation_check:
                    return self._chat_responses_streaming(kwargs, cancellation_check)
                else:
                    response = self.client.responses.create(**kwargs)
                    return self._parse_responses_api_response(response)
            except JobCancelledException:
                # Re-raise cancellation without retry
                raise
            except Exception as e:
                error_str = str(e)
                is_rate_limit = "rate_limit" in error_str or "429" in error_str

                if is_rate_limit and attempt < MAX_RETRIES - 1:
                    delay = min(BASE_DELAY * (2 ** attempt) + random.uniform(1, 10), MAX_DELAY)
                    _log(f"[RateLimit] Retry {attempt + 1}/{MAX_RETRIES} in {delay:.1f}s")
                    self._sleep_with_cancel_check(delay, cancellation_check)
                    continue

                log_error(f"OpenAI Responses API error: {e}")
                raise

    def _chat_responses_streaming(
        self,
        kwargs: dict,
        cancellation_check: Callable[[], bool]
    ) -> LLMResponse:
        """Execute Responses API with streaming, checking for cancellation.

        Runs streaming in a separate thread so we can abandon it immediately when cancelled.
        """
        import threading
        import queue

        kwargs["stream"] = True

        result_queue = queue.Queue()
        error_queue = queue.Queue()

        def stream_worker():
            """Worker thread that performs the actual streaming."""
            try:
                content = None
                tool_calls = []
                usage = None
                current_function_call = None

                with self.client.responses.create(**kwargs) as stream:
                    for event in stream:
                        event_type = getattr(event, 'type', None)

                        if event_type == 'response.output_item.added':
                            item = getattr(event, 'item', None)
                            if item:
                                item_type = getattr(item, 'type', None)
                                if item_type == 'function_call':
                                    current_function_call = {
                                        "call_id": getattr(item, 'call_id', ''),
                                        "name": getattr(item, 'name', ''),
                                        "arguments": ""
                                    }

                        elif event_type == 'response.function_call_arguments.delta':
                            if current_function_call:
                                delta = getattr(event, 'delta', '')
                                current_function_call["arguments"] += delta

                        elif event_type == 'response.output_item.done':
                            item = getattr(event, 'item', None)
                            if item:
                                item_type = getattr(item, 'type', None)
                                if item_type == 'message':
                                    for content_part in getattr(item, 'content', []):
                                        if getattr(content_part, 'type', None) == "output_text":
                                            content = getattr(content_part, 'text', '')
                                elif item_type == 'function_call' and current_function_call:
                                    tool_calls.append({
                                        "id": current_function_call["call_id"],
                                        "type": "function",
                                        "function": {
                                            "name": current_function_call["name"],
                                            "arguments": current_function_call["arguments"]
                                        }
                                    })
                                    current_function_call = None

                        elif event_type == 'response.done':
                            response = getattr(event, 'response', None)
                            if response:
                                usage = getattr(response, 'usage', None)

                result_queue.put((content, tool_calls, usage))
            except Exception as e:
                error_queue.put(e)

        # Start worker thread (daemon=True so it's abandoned if we cancel)
        worker = threading.Thread(target=stream_worker, daemon=True)
        worker.start()

        # Wait for result with periodic cancellation checks
        while worker.is_alive():
            if cancellation_check():
                log_debug("[OpenAIProvider] Cancelled - abandoning Responses API stream worker")
                raise JobCancelledException("Cancelled during LLM streaming")
            worker.join(timeout=0.2)

        # Worker finished - check for errors
        if not error_queue.empty():
            raise error_queue.get()

        # Get result
        content, tool_calls, usage = result_queue.get()

        # Build usage dict
        usage_dict = {
            "prompt_tokens": getattr(usage, 'input_tokens', 0) if usage else 0,
            "completion_tokens": getattr(usage, 'output_tokens', 0) if usage else 0
        }

        # Extract cached tokens if present
        reasoning_tokens = 0
        if usage:
            input_details = getattr(usage, 'input_tokens_details', None)
            if input_details:
                cached = getattr(input_details, 'cached_tokens', 0)
                if cached:
                    usage_dict["cache_read_tokens"] = cached

            output_details = getattr(usage, 'output_tokens_details', None)
            if output_details:
                reasoning_tokens = getattr(output_details, 'reasoning_tokens', 0)

        # Calculate cost
        from user_container.pricing import calculate_cost
        cost = calculate_cost(self.provider_name, self.model, usage_dict)

        return LLMResponse(
            content=content,
            tool_calls=tool_calls if tool_calls else None,
            usage=usage_dict,
            cost_usd=cost,
            reasoning_tokens=reasoning_tokens
        )

    def _convert_messages_to_responses_api(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert Chat Completions messages to Responses API input format.

        Responses API uses a different format:
        - System/user/assistant messages: {"role": "...", "content": "..."}
        - Function calls: {"type": "function_call", "name": "...", "arguments": "...", "call_id": "..."}
        - Function results: {"type": "function_call_output", "call_id": "...", "output": "..."}

        Key difference: tool_calls are NOT part of assistant messages, they're separate items.
        """
        input_items = []

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")

            if role == "system":
                input_items.append({
                    "role": "system",
                    "content": content
                })
            elif role == "user":
                input_items.append({
                    "role": "user",
                    "content": content
                })
            elif role == "assistant":
                # Handle assistant messages (may have tool_calls)
                if msg.get("tool_calls"):
                    # First, add assistant message with content (if any)
                    if content:
                        input_items.append({
                            "role": "assistant",
                            "content": content
                        })

                    # Then add each tool call as a separate function_call item
                    for tc in msg["tool_calls"]:
                        func = tc.get("function", {})
                        input_items.append({
                            "type": "function_call",
                            "name": func.get("name"),
                            "arguments": func.get("arguments", "{}"),
                            "call_id": tc.get("id")
                        })
                else:
                    # Simple assistant message
                    input_items.append({
                        "role": "assistant",
                        "content": content or ""
                    })
            elif role == "tool":
                # Tool result - Responses API uses function_call_output
                input_items.append({
                    "type": "function_call_output",
                    "call_id": msg.get("tool_call_id"),
                    "output": content
                })

        return input_items

    def _convert_tools_to_responses_api(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert tools to Responses API format.

        Chat Completions format:
        {"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}

        Responses API format:
        {"type": "function", "name": "...", "description": "...", "parameters": {...}}
        """
        converted = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool.get("function", {})
                converted.append({
                    "type": "function",
                    "name": func.get("name"),
                    "description": func.get("description", ""),
                    "parameters": func.get("parameters", {"type": "object", "properties": {}})
                })
            else:
                # Pass through non-function tools as-is
                converted.append(tool)
        return converted

    def _parse_completions_response(self, response) -> LLMResponse:
        """Parse Chat Completions API response to unified format."""
        msg = response.choices[0].message

        tool_calls = None
        if msg.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in msg.tool_calls
            ]

        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens
        }

        # Extract cached tokens if present (OpenAI prompt caching)
        prompt_details = getattr(response.usage, 'prompt_tokens_details', None)
        if prompt_details:
            cached = getattr(prompt_details, 'cached_tokens', 0)
            if cached:
                usage["cache_read_tokens"] = cached
                log_debug(f"[OpenAI] Cache hit: {cached} tokens")

        # Calculate cost
        from user_container.pricing import calculate_cost
        cost = calculate_cost(self.provider_name, self.model, usage)

        return LLMResponse(
            content=msg.content,
            tool_calls=tool_calls,
            usage=usage,
            cost_usd=cost
        )

    def _parse_responses_api_response(self, response) -> LLMResponse:
        """Parse Responses API response to unified format.

        Responses API returns:
        - response.output: List of output items (text, tool_calls, etc.)
        - response.usage: Usage info with reasoning_tokens
        """
        content = None
        tool_calls = []
        reasoning_tokens = 0

        # Parse output items
        for item in response.output:
            item_type = getattr(item, 'type', None)

            if item_type == "message":
                # Text content
                for content_part in getattr(item, 'content', []):
                    if getattr(content_part, 'type', None) == "output_text":
                        content = getattr(content_part, 'text', '')
            elif item_type == "function_call":
                # Tool call
                tool_calls.append({
                    "id": getattr(item, 'call_id', ''),
                    "type": "function",
                    "function": {
                        "name": getattr(item, 'name', ''),
                        "arguments": getattr(item, 'arguments', '{}')
                    }
                })

        # Build usage dict
        usage = {
            "prompt_tokens": getattr(response.usage, 'input_tokens', 0),
            "completion_tokens": getattr(response.usage, 'output_tokens', 0)
        }

        # Extract cached tokens if present (OpenAI prompt caching)
        input_details = getattr(response.usage, 'input_tokens_details', None)
        if input_details:
            cached = getattr(input_details, 'cached_tokens', 0)
            if cached:
                usage["cache_read_tokens"] = cached
                log_debug(f"[OpenAI] Cache hit: {cached} tokens")

        # Extract reasoning tokens if present
        reasoning_tokens = 0
        output_details = getattr(response.usage, 'output_tokens_details', None)
        if output_details:
            reasoning_tokens = getattr(output_details, 'reasoning_tokens', 0)
            if reasoning_tokens > 0:
                log_debug(f"[OpenAI] Reasoning tokens: {reasoning_tokens}")

        # Calculate cost
        from user_container.pricing import calculate_cost
        cost = calculate_cost(self.provider_name, self.model, usage)

        return LLMResponse(
            content=content,
            tool_calls=tool_calls if tool_calls else None,
            usage=usage,
            cost_usd=cost,
            reasoning_tokens=reasoning_tokens
        )


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
            tools: List of tools in OpenAI format (auto-converted for Anthropic)
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
                    provider=self._provider.provider_name if hasattr(self._provider, 'provider_name') else "anthropic",
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
        Create client with default (main) model from config.

        Provider selection priority:
        1. Database setting (user_settings.model_provider)
        2. MODEL_PROVIDER env var
        3. Default ("anthropic")

        Models:
        - "anthropic" -> Claude (ANTHROPIC_MODEL)
        - "openai" -> GPT (OPENAI_MODEL)
        """
        provider_name = get_effective_model_provider()

        if provider_name == "anthropic":
            if not settings.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            provider = AnthropicProvider(
                api_key=settings.anthropic_api_key,
                model=settings.anthropic_model
            )
        elif provider_name == "openai":
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY not set")
            provider = OpenAIProvider(
                api_key=settings.openai_api_key,
                model=settings.openai_model
            )
        else:
            raise ValueError(f"Unknown MODEL_PROVIDER: {provider_name}")

        return cls(provider)

    @classmethod
    def cheap(cls) -> "LLMClient":
        """
        Create client with cheap model for routing/compression.

        Provider selection priority:
        1. Database setting (user_settings.model_provider)
        2. MODEL_PROVIDER env var
        3. Default ("anthropic")

        Models:
        - anthropic -> ANTHROPIC_CHEAP_MODEL (default: claude-3-5-haiku-20241022)
        - openai -> OPENAI_CHEAP_MODEL (default: gpt-5-mini)
        """
        provider_name = get_effective_model_provider()

        if provider_name == "anthropic":
            if not settings.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            provider = AnthropicProvider(
                api_key=settings.anthropic_api_key,
                model=settings.anthropic_cheap_model
            )
        elif provider_name == "openai":
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY not set")
            provider = OpenAIProvider(
                api_key=settings.openai_api_key,
                model=settings.openai_cheap_model
            )
        else:
            raise ValueError(f"Unknown MODEL_PROVIDER: {provider_name}")

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
            provider = OpenAIProvider(
                api_key=settings.groq_api_key,
                model=settings.groq_routing_model,
                base_url="https://api.groq.com/openai/v1"
            )
            return cls(provider)

        return cls.cheap()  # fallback

    @classmethod
    def with_model(cls, provider: str, model: str) -> "LLMClient":
        """
        Create client with specific provider and model.

        Args:
            provider: "anthropic" or "openai"
            model: Model name (e.g., "claude-sonnet-4-20250514", "gpt-4o")
        """
        if provider == "anthropic":
            if not settings.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            llm_provider = AnthropicProvider(
                api_key=settings.anthropic_api_key,
                model=model
            )
        elif provider == "openai":
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY not set")
            llm_provider = OpenAIProvider(
                api_key=settings.openai_api_key,
                model=model
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")

        return cls(llm_provider)
