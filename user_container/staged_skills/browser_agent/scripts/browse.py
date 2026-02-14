# /// script
# dependencies = ["browser-use"]
# ///
"""
AI-driven browser automation using browser-use library.

The agent interprets natural language tasks and autonomously navigates,
clicks, fills forms, and extracts data from websites.

Usage:
    uv run scripts/browse.py "<task description>"

Options:
    --model <name>          LLM model to use (default: claude-sonnet-4-20250514)
    --max-steps <n>         Maximum number of actions (default: 25)
    --screenshot <path>     Save final screenshot to path
    --headless              Run browser in headless mode (default: true)
    --no-headless           Show browser window (for debugging)
    --timeout <seconds>     Overall timeout in seconds (default: 300)

Examples:
    uv run scripts/browse.py "Go to google.com and search for 'weather in Warsaw'"

    uv run scripts/browse.py "Log in to example.com with email user@test.com and password secret123, then go to Orders page and list the last 5 orders"

    uv run scripts/browse.py "Open github.com/anthropics and count the number of public repositories"

Environment:
    ANTHROPIC_API_KEY - Required for Claude models
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

# Configure logging to file before importing browser_use
LOG_FILE = "/workspace/browser_agent.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='w'),  # overwrite each run
    ]
)
# Silence console output from browser_use
for logger_name in ['browser_use', 'httpx', 'httpcore', 'playwright', 'asyncio']:
    logging.getLogger(logger_name).handlers = []
    logging.getLogger(logger_name).addHandler(logging.FileHandler(LOG_FILE))
    logging.getLogger(logger_name).setLevel(logging.INFO)


def get_api_key(provider: str) -> str:
    """
    Get API key from secrets file or environment.

    Skills read API keys from /app/secrets.json (created at container startup).
    Falls back to environment variable for development.
    """
    import sys
    secrets_file = Path("/app/secrets.json")
    key_name = f"{provider.upper()}_API_KEY"

    # Debug: print to stderr so it doesn't pollute JSON output
    print(f"DEBUG: Looking for {key_name}", file=sys.stderr)
    print(f"DEBUG: secrets_file exists: {secrets_file.exists()}", file=sys.stderr)
    print(f"DEBUG: current user: {os.getuid()}", file=sys.stderr)

    # Try secrets file first
    if secrets_file.exists():
        try:
            with open(secrets_file) as f:
                secrets = json.load(f)
            print(f"DEBUG: secrets keys: {list(secrets.keys())}", file=sys.stderr)
            key = secrets.get(key_name.lower())
            if key:
                print(f"DEBUG: Found key (length: {len(key)})", file=sys.stderr)
                return key
            else:
                print(f"DEBUG: Key {key_name.lower()} not in secrets", file=sys.stderr)
        except Exception as e:
            print(f"DEBUG: Error reading secrets: {e}", file=sys.stderr)

    # Fallback to environment variable (for development)
    env_key = os.getenv(key_name)
    print(f"DEBUG: env var {key_name}: {'found' if env_key else 'not found'}", file=sys.stderr)
    return env_key


async def browse(
    task: str,
    max_steps: int = 25,
    screenshot_path: str = None,
    headless: bool = True,
    timeout: int = 600,
) -> dict:
    """
    Execute a browser automation task using AI.

    Args:
        task: Natural language description of what to do
        model: LLM model name for the AI agent
        max_steps: Maximum number of browser actions to take
        screenshot_path: Optional path to save final screenshot
        headless: Run browser without visible window
        timeout: Overall timeout in seconds

    Returns:
        dict with status, result, and metadata
    """
    from browser_use import Agent, Browser
    
    model = "claude-sonnet-4-5-20250929"

    # Import the appropriate LLM based on model name
    # browser-use has its own LLM wrappers
    if model.startswith("claude") or model.startswith("anthropic"):
        from browser_use import ChatAnthropic
        api_key = get_api_key("anthropic")
        if not api_key:
            return {"status": "error", "error": "ANTHROPIC_API_KEY not configured", "task": task}
        llm = ChatAnthropic(
            model=model,
            api_key=api_key,
        )
    elif model.startswith("gpt") or model.startswith("openai"):
        from browser_use import ChatOpenAI
        api_key = get_api_key("openai")
        if not api_key:
            return {"status": "error", "error": "OPENAI_API_KEY not configured", "task": task}
        llm = ChatOpenAI(
            model=model,
            api_key=api_key,
        )
    else:
        # Default to Anthropic
        from browser_use import ChatAnthropic
        api_key = get_api_key("anthropic")
        if not api_key:
            return {"status": "error", "error": "ANTHROPIC_API_KEY not configured", "task": task}
        llm = ChatAnthropic(
            model=model,
            api_key=api_key,
        )

    start_time = time.time()
    browser = None

    try:
        # Configure browser with Docker-compatible settings
        # Use 1400x850 viewport to match LLM expected size (avoids resize at each step)
        browser = Browser(
            headless=headless,
            window_size={'width': 1400, 'height': 850},
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
            ],
        )

        # Create the AI agent with cost tracking
        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            calculate_cost=True,
        )

        # Run the agent with timeout
        history = await asyncio.wait_for(
            agent.run(max_steps=max_steps),
            timeout=timeout
        )

        # Get the final result
        final_result = history.final_result() if history else None
        steps_taken = len(history.history) if history and hasattr(history, 'history') else 0

        # Extract token usage from history
        total_input_tokens = 0
        total_output_tokens = 0

        if history and hasattr(history, 'usage') and history.usage:
            usage = history.usage
            total_input_tokens = getattr(usage, 'total_prompt_tokens', 0) or 0
            total_output_tokens = getattr(usage, 'total_completion_tokens', 0) or 0

        # Save screenshot if requested
        screenshot_saved = False
        if screenshot_path:
            try:
                # Get the current page and take screenshot
                if hasattr(browser, 'contexts') and browser.contexts:
                    context = browser.contexts[0]
                    if context.pages:
                        page = context.pages[-1]
                        # Ensure directory exists
                        os.makedirs(os.path.dirname(screenshot_path) or '.', exist_ok=True)
                        await page.screenshot(path=screenshot_path, full_page=True)
                        screenshot_saved = True
            except Exception:
                pass  # Screenshot is optional, don't fail the whole task

        total_time = int((time.time() - start_time) * 1000)

        # Determine provider from model name
        if model.startswith("claude") or model.startswith("anthropic"):
            provider = "anthropic"
        elif model.startswith("gpt") or model.startswith("openai"):
            provider = "openai"
        else:
            provider = "unknown"

        result = {
            "status": "success",
            "task": task,
            "result": final_result,
            "steps_taken": steps_taken,
            "provider": provider,
            "model": model,
            "usage": {
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
            },
            "timing": {
                "total_ms": total_time,
            },
        }

        if screenshot_saved:
            result["screenshot"] = screenshot_path

        return result

    except asyncio.TimeoutError:
        return {
            "status": "error",
            "error": f"Task timed out after {timeout} seconds. Try increasing --timeout or simplifying the task.",
            "task": task,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "task": task,
        }
    finally:
        # Always try to close browser
        if browser:
            try:
                await browser.close()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(
        description="AI-driven browser automation - describe what you want in natural language"
    )
    parser.add_argument(
        "task",
        help="Natural language description of the task to perform"
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=25,
        help="Maximum number of browser actions (default: 25)"
    )
    parser.add_argument(
        "--screenshot", "-s",
        help="Save final screenshot to this path"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run in headless mode (default)"
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Show browser window (for debugging)"
    )
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=600,
        help="Overall timeout in seconds (default: 600)"
    )

    args = parser.parse_args()

    result = asyncio.run(browse(
        task=args.task,
        max_steps=args.max_steps,
        screenshot_path=args.screenshot,
        headless=not args.no_headless,
        timeout=args.timeout,
    ))

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
