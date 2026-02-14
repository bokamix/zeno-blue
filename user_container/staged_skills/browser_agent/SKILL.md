---
name: browser_agent
description: "AI-driven browser automation using natural language. Describe what you want to do (login, click, fill forms, extract data) and the AI agent will figure out how to do it. Perfect for tasks behind login pages, complex interactions, and when you don't know the exact CSS selectors. **VERY SLOW** use only if you really have to."
license: MIT
---

# Browser Agent Skill

AI-powered browser automation that understands natural language. Instead of writing CSS selectors and click sequences, just describe what you want to accomplish.
**IMPORTANT** This is very slow. Only use it if you absolutely have to. Always try the web_fetch tool first.

## Quick Reference

| Script | Purpose | API Cost |
|--------|---------|----------|
| `browse.py` | Execute any browser task via natural language | Yes (LLM calls) |

## Important: Shell Timeout

This skill can take a long time to execute (up to 10 minutes for complex tasks like login + navigation + form submission). **Always set `timeout_s: 600`** when calling this skill via shell tool to avoid premature termination.

## When to Use This

Use Browser Agent when:
- You need to **login to a website** and do something after
- Task requires **complex interactions** (multiple clicks, form filling, navigation)
- You **don't know the exact selectors** and want AI to figure it out
- **Scraping data behind authentication**

For simple scraping without login, consider web_fetch tool (faster, cheaper).

## Usage

```bash
uv run scripts/browse.py "<describe what you want to do>"
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--model` | LLM model to use | claude-sonnet-4-20250514 |
| `--max-steps` | Maximum browser actions | 25 |
| `--screenshot` | Save final screenshot | - |
| `--timeout` | Overall timeout (seconds) | 600 |
| `--no-headless` | Show browser window | false |

## Examples

### Simple Search

```bash
uv run scripts/browse.py "Go to google.com and search for 'best pizza in Warsaw'"
```

### Login and Extract Data

```bash
uv run scripts/browse.py "Log in to example.com with email user@test.com and password secret123, then go to the Orders page and list my last 5 orders with their dates and amounts"
```

### Fill a Form

```bash
uv run scripts/browse.py "Go to contact form on example.com, fill in name 'John Doe', email 'john@test.com', message 'Hello, I have a question about your services', and submit the form"
```

### Check Account Balance

```bash
uv run scripts/browse.py "Log in to mybank.com as user123 with password mypass, navigate to account overview, and tell me the current balance"
```

### Screenshot After Action

```bash
uv run scripts/browse.py "Go to github.com/anthropics and take a screenshot" --screenshot /workspace/github.png
```

### With Different Model

```bash
uv run scripts/browse.py "Search for news about AI" --model gpt-4o
```

## Output

```json
{
  "status": "success",
  "task": "Log in to example.com and check orders",
  "result": "Found 5 orders: 1. Order #123 - $50 - Jan 10, 2. Order #124 - $30 - Jan 8...",
  "steps_taken": 8,
  "timing": {
    "total_ms": 45000
  },
  "screenshot": "/workspace/result.png"
}
```

## How It Works

1. You describe the task in natural language
2. The AI agent sees the current page (DOM structure)
3. It decides what action to take (click, type, scroll, etc.)
4. Executes the action and observes the result
5. Repeats until task is complete or max steps reached
6. Returns the extracted information or confirmation

## Tips for Best Results

### Be Specific About What You Want

```bash
# Good - clear objective
uv run scripts/browse.py "Log in to dashboard.example.com with email admin@test.com password admin123, go to Analytics section, and tell me the total visitors for last week"

# Less good - vague
uv run scripts/browse.py "Check the analytics"
```

### Include Credentials in the Task

```bash
# The agent needs to know login details
uv run scripts/browse.py "Log in using email 'user@example.com' and password 'mypassword', then..."
```

### Specify the Output Format

```bash
# Tell the agent what information you want back
uv run scripts/browse.py "...and list the orders as: order number, date, total amount"
```

### Use Screenshots for Verification

```bash
# Useful for debugging or verification
uv run scripts/browse.py "..." --screenshot /workspace/after_task.png
```

## Limitations

1. **CAPTCHA** - Cannot solve CAPTCHAs automatically
2. **2FA** - Cannot handle two-factor authentication requiring external devices
3. **Cost** - Each step requires LLM inference (more expensive than direct automation)
4. **Speed** - Slower than hardcoded Playwright scripts
5. **Non-deterministic** - May take different paths on different runs

## Troubleshooting

### "Task timed out"

1. Increase timeout: `--timeout 600`
2. Simplify the task into smaller steps
3. The site might be slow or blocking automation

### Agent gets stuck

1. Try with `--no-headless` to see what's happening
2. Rephrase the task more clearly
3. Break complex tasks into simpler ones

### Site blocks the browser

Some sites detect automation. Try:
- Using a different user agent (not yet configurable)
- Running at different times
- The site may simply not allow automation
