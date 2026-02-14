# /// script
# dependencies = ["anthropic", "openai", "pillow"]
# ///
"""
Image Analysis Script

Analyzes images using Vision API (Claude or GPT-4V).
Supports any prompt - from simple descriptions to structured data extraction.

Usage:
    uv run analyze.py --image-path <path> --prompt "<prompt>"

Examples:
    uv run analyze.py --image-path photo.jpg --prompt "What's in this image?"
    uv run analyze.py --image-path invoice.png --prompt "Extract: seller, date, total, items. Return as JSON."
    uv run analyze.py --image-path screenshot.png --prompt "Extract all visible text."
    uv run analyze.py --image-path chart.png --prompt "Extract the data from this chart as CSV."
"""

import argparse
import base64
import json
import os
from pathlib import Path


def get_api_key(provider: str) -> str:
    """
    Get API key from secrets file or environment.

    Skills read API keys from /app/secrets.json (created at container startup).
    Falls back to environment variable for development.
    """
    secrets_file = Path("/app/secrets.json")
    key_name = f"{provider.upper()}_API_KEY"

    # Try secrets file first
    if secrets_file.exists():
        try:
            with open(secrets_file) as f:
                secrets = json.load(f)
            key = secrets.get(key_name.lower())
            if key:
                return key
        except Exception:
            pass

    # Fallback to environment variable (for development)
    return os.getenv(key_name)


def get_image_media_type(path: str) -> str:
    """Get media type from file extension."""
    ext = Path(path).suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return media_types.get(ext, "image/jpeg")


def load_image_as_base64(path: str) -> str:
    """Load image file and return as base64 string."""
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def analyze_with_anthropic(image_path: str, prompt: str) -> dict:
    """Analyze image using Claude Vision API."""
    from anthropic import Anthropic

    api_key = get_api_key("anthropic")
    if not api_key:
        return {"status": "error", "error": "ANTHROPIC_API_KEY not configured"}

    client = Anthropic(api_key=api_key)
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

    image_data = load_image_as_base64(image_path)
    media_type = get_image_media_type(image_path)

    message = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
    )

    return {
        "status": "success",
        "provider": "anthropic",
        "model": model,
        "response": message.content[0].text,
        "usage": {
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
        },
    }


def analyze_with_openai(image_path: str, prompt: str) -> dict:
    """Analyze image using GPT-4 Vision API."""
    from openai import OpenAI

    api_key = get_api_key("openai")
    if not api_key:
        return {"status": "error", "error": "OPENAI_API_KEY not configured"}

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-5.2")

    image_data = load_image_as_base64(image_path)
    media_type = get_image_media_type(image_path)

    response = client.chat.completions.create(
        model=model,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{image_data}",
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
    )

    return {
        "status": "success",
        "provider": "openai",
        "model": model,
        "response": response.choices[0].message.content,
        "usage": {
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
        },
    }


def analyze_image(image_path: str, prompt: str) -> dict:
    """
    Analyze an image using Vision API.

    Args:
        image_path: Path to image file (jpg, png, gif, webp)
        prompt: What to analyze/extract from the image

    Returns:
        dict with status, provider, model, response, and usage
    """
    path = Path(image_path)

    if not path.exists():
        return {"status": "error", "error": f"File not found: {image_path}"}

    # Check file size (Vision APIs have limits ~20MB)
    file_size_mb = path.stat().st_size / (1024 * 1024)
    if file_size_mb > 20:
        return {
            "status": "error",
            "error": f"File too large: {file_size_mb:.1f}MB (max 20MB). Use preprocess.py to resize.",
        }

    # Check supported formats
    supported = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    if path.suffix.lower() not in supported:
        return {
            "status": "error",
            "error": f"Unsupported format: {path.suffix}. Supported: {', '.join(supported)}",
        }

    # Determine provider from environment
    provider = os.getenv("MODEL_PROVIDER", "anthropic")

    try:
        if provider == "anthropic":
            return analyze_with_anthropic(image_path, prompt)
        elif provider == "openai":
            return analyze_with_openai(image_path, prompt)
        else:
            return {"status": "error", "error": f"Unknown provider: {provider}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def main():
    parser = argparse.ArgumentParser(
        description="Analyze images using Vision API (Claude or GPT-4V)"
    )
    parser.add_argument(
        "--image-path", required=True, help="Path to image file (jpg, png, gif, webp)"
    )
    parser.add_argument(
        "--prompt", required=True, help="What to analyze/extract from the image"
    )

    args = parser.parse_args()

    result = analyze_image(args.image_path, args.prompt)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
