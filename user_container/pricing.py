"""
Pricing module - calculates costs from LLM usage.
"""
import json
from pathlib import Path
from typing import Dict, Optional

from user_container.logger import log

_PRICES: Optional[Dict] = None


def load_prices() -> Dict:
    """Load prices from costs.json (cached in memory)."""
    global _PRICES
    if _PRICES is None:
        path = Path(__file__).parent / "costs.json"
        with open(path) as f:
            _PRICES = json.load(f)
    return _PRICES


def calculate_cost(
    provider: str,
    model: str,
    usage: Dict[str, int]
) -> float:
    """
    Calculate cost in USD from usage dict.

    Args:
        provider: "anthropic", "openai", or "groq"
        model: Model name (e.g., "claude-sonnet-4-5-20250929")
        usage: Dict with prompt_tokens, completion_tokens,
               optionally cache_creation_tokens, cache_read_tokens

    Returns:
        Cost in USD (float)
    """
    prices_data = load_prices()
    fallback = prices_data.get("fallback", {"input_per_million": 10.0, "output_per_million": 30.0})

    # Try to find model-specific pricing
    provider_prices = prices_data.get("prices", {}).get(provider, {})
    model_prices = provider_prices.get(model)

    if not model_prices:
        log(f"[Pricing] Unknown model {provider}/{model}, using fallback pricing")
        model_prices = fallback

    # Calculate base costs
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)

    input_cost = prompt_tokens * model_prices.get("input_per_million", fallback["input_per_million"]) / 1_000_000
    output_cost = completion_tokens * model_prices.get("output_per_million", fallback["output_per_million"]) / 1_000_000

    # Anthropic cache pricing (if applicable)
    cache_write_cost = 0.0
    cache_read_cost = 0.0
    if "cache_write_per_million" in model_prices:
        cache_creation = usage.get("cache_creation_tokens", 0)
        cache_read = usage.get("cache_read_tokens", 0)
        cache_write_cost = cache_creation * model_prices["cache_write_per_million"] / 1_000_000
        cache_read_cost = cache_read * model_prices["cache_read_per_million"] / 1_000_000

    total = input_cost + output_cost + cache_write_cost + cache_read_cost
    return total


def calculate_cost_duration(
    provider: str,
    model: str,
    duration_seconds: float
) -> float:
    """
    Calculate cost in USD from audio/video duration.

    Used for APIs like OpenAI Whisper that charge per minute of audio
    instead of per token.

    Args:
        provider: "openai" (Whisper), etc.
        model: Model name (e.g., "gpt-4o-transcribe")
        duration_seconds: Duration in seconds

    Returns:
        Cost in USD (float)
    """
    prices_data = load_prices()
    fallback_per_minute = 0.01  # Conservative fallback

    provider_prices = prices_data.get("prices", {}).get(provider, {})
    model_prices = provider_prices.get(model, {})

    per_minute = model_prices.get("per_minute", fallback_per_minute)

    duration_minutes = duration_seconds / 60.0
    return duration_minutes * per_minute
