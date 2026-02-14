# /// script
# dependencies = ["playwright"]
# ///
"""
Screenshot Script using Playwright

Capture full-page or element screenshots from web pages.

Usage:
    uv run scripts/screenshot.py <url> <output_path> [options]

Options:
    --selector <css>    Screenshot specific element only
    --wait <selector>   Wait for element before screenshot
    --full-page         Capture entire scrollable page
    --width <px>        Viewport width (default: 1280)
    --height <px>       Viewport height (default: 720)
    --timeout <ms>      Page load timeout (default: 30000)

Examples:
    uv run scripts/screenshot.py "https://example.com" page.png --full-page
    uv run scripts/screenshot.py "https://example.com" mobile.png --width 375 --height 812
    uv run scripts/screenshot.py "https://example.com" header.png --selector "header"
"""

import argparse
import json
import os
import sys
from pathlib import Path


def screenshot(
    url: str,
    output_path: str,
    selector: str = None,
    wait: str = None,
    full_page: bool = False,
    width: int = 1280,
    height: int = 720,
    timeout: int = 30000,
    user_agent: str = None,
    headless: bool = True,
) -> dict:
    """
    Take a screenshot of a web page.

    Args:
        url: URL to screenshot
        output_path: Path to save screenshot
        selector: CSS selector to screenshot specific element
        wait: CSS selector to wait for before screenshot
        full_page: Capture entire scrollable page
        width: Viewport width in pixels
        height: Viewport height in pixels
        timeout: Page load timeout in ms
        user_agent: Custom user agent string
        headless: Run browser in headless mode

    Returns:
        dict with status and screenshot info
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

    # Ensure output directory exists
    output_dir = Path(output_path).parent
    if output_dir and not output_dir.exists():
        output_dir.mkdir(parents=True)

    try:
        with sync_playwright() as p:
            # Launch browser with Docker-compatible settings
            browser = p.chromium.launch(
                headless=headless,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )

            # Create context with viewport size and optional user agent
            context_options = {
                "viewport": {"width": width, "height": height}
            }
            if user_agent:
                context_options["user_agent"] = user_agent

            context = browser.new_context(**context_options)
            page = context.new_page()

            # Navigate to URL
            page.goto(url, timeout=timeout, wait_until="networkidle")

            # Wait for specific selector if specified
            if wait:
                page.wait_for_selector(wait, timeout=timeout)

            # Take screenshot
            screenshot_options = {"path": output_path}

            if selector:
                # Screenshot specific element
                element = page.query_selector(selector)
                if not element:
                    browser.close()
                    return {
                        "status": "error",
                        "error": f"Element not found: {selector}",
                    }
                element.screenshot(**screenshot_options)
            else:
                # Full page or viewport screenshot
                screenshot_options["full_page"] = full_page
                page.screenshot(**screenshot_options)

            browser.close()

            # Get file info
            file_path = Path(output_path)
            file_size_kb = file_path.stat().st_size / 1024

            # Get image dimensions
            try:
                from PIL import Image
                with Image.open(output_path) as img:
                    dimensions = {"width": img.width, "height": img.height}
            except ImportError:
                dimensions = {"width": width, "height": height if not full_page else "full"}

            return {
                "status": "success",
                "url": url,
                "output_path": str(file_path.absolute()),
                "dimensions": dimensions,
                "file_size_kb": round(file_size_kb, 2),
            }

    except PlaywrightTimeout as e:
        return {
            "status": "error",
            "error": f"Timeout: {str(e)}. Try increasing --timeout.",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def main():
    parser = argparse.ArgumentParser(
        description="Take screenshots of web pages"
    )
    parser.add_argument("url", help="URL to screenshot")
    parser.add_argument("output_path", help="Path to save screenshot")
    parser.add_argument(
        "--selector", "-s", help="CSS selector to screenshot specific element"
    )
    parser.add_argument(
        "--wait", "-w", help="CSS selector to wait for before screenshot"
    )
    parser.add_argument(
        "--full-page", "-f", action="store_true", help="Capture entire scrollable page"
    )
    parser.add_argument(
        "--width", type=int, default=1280, help="Viewport width (default: 1280)"
    )
    parser.add_argument(
        "--height", type=int, default=720, help="Viewport height (default: 720)"
    )
    parser.add_argument(
        "--timeout", "-t", type=int, default=30000, help="Page load timeout in ms"
    )
    parser.add_argument(
        "--user-agent", help="Custom user agent string"
    )
    parser.add_argument(
        "--no-headless", action="store_true", help="Show browser window"
    )

    args = parser.parse_args()

    result = screenshot(
        url=args.url,
        output_path=args.output_path,
        selector=args.selector,
        wait=args.wait,
        full_page=args.full_page,
        width=args.width,
        height=args.height,
        timeout=args.timeout,
        user_agent=args.user_agent,
        headless=not args.no_headless,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
