"""
web_fetch tool - Fetch content from URLs.

Simple HTTP fetch with HTML stripping for reading web pages,
articles, documentation, etc.
"""

from typing import Any, Dict

import httpx
from bs4 import BeautifulSoup

from user_container.tools.registry import ToolSchema, make_parameters


# Security: Max response size before parsing (prevents memory exhaustion)
MAX_RESPONSE_SIZE = 5 * 1024 * 1024  # 5MB max


WEB_FETCH_SCHEMA = ToolSchema(
    name="web_fetch",
    description="""Fetch content from a URL and return as text.

Returns: Page content as plain text (HTML stripped).
Use for: Reading articles, documentation, web pages.

NOTE: For complex scraping (JS rendering, pagination), use shell with a Python script instead.""",
    parameters=make_parameters(
        properties={
            "url": {
                "type": "string",
                "description": "URL to fetch"
            },
            "max_length": {
                "type": ["integer", "null"],
                "description": "Max characters to return (default: 10000)"
            }
        },
        required=["url"]
    )
)


def web_fetch(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch URL content and strip HTML.

    Args (via dict):
        url: URL to fetch
        max_length: Max characters to return (default 10000)

    Returns:
        Dict with status, content, url, length
    """
    url = args.get("url", "")
    max_length = args.get("max_length") or 10000

    if not url:
        return {"status": "error", "error": "URL is required"}

    try:
        # Fetch with reasonable timeout and follow redirects
        response = httpx.get(
            url,
            timeout=30,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; ZENO/1.0)"
            }
        )
        response.raise_for_status()

        # Security: Check response size before parsing (prevents memory exhaustion)
        response_size = len(response.content)
        if response_size > MAX_RESPONSE_SIZE:
            max_mb = MAX_RESPONSE_SIZE // (1024 * 1024)
            return {
                "status": "error",
                "url": url,
                "error": f"Response too large: {response_size // (1024*1024)}MB (max {max_mb}MB)"
            }

        # Parse HTML and strip unwanted elements
        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove script, style, nav, footer, header, aside
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript']):
            tag.decompose()

        # Get text content
        text = soup.get_text(separator='\n', strip=True)

        # Clean up multiple newlines
        import re
        text = re.sub(r'\n{3,}', '\n\n', text)

        original_length = len(text)

        # Truncate if needed
        if len(text) > max_length:
            text = text[:max_length] + f"\n\n[Truncated - showing {max_length} of {original_length} chars]"

        return {
            "status": "success",
            "url": url,
            "content": text,
            "length": len(text),
            "original_length": original_length
        }

    except httpx.TimeoutException:
        return {"status": "error", "url": url, "error": "Request timed out (30s)"}
    except httpx.HTTPStatusError as e:
        return {"status": "error", "url": url, "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        return {"status": "error", "url": url, "error": str(e)}
