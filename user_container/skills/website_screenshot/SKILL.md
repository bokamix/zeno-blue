---
name: website_screenshot
description: "Take screenshots of web pages. Supports full-page capture, specific elements, custom viewport sizes (desktop/mobile), and waiting for dynamic content. Use for visual documentation, monitoring, or capturing page state."
license: MIT
---

# Website Screenshot Skill

Capture screenshots of web pages using headless browser automation.

## Quick Reference

| Script | Purpose | API Cost |
|--------|---------|----------|
| `screenshot.py` | Take full-page or element screenshots | No |

## When to Use This

Use this skill when you need to:
- Capture a **visual snapshot** of a web page
- Screenshot a **specific element** (header, chart, etc.)
- Test **responsive design** (different viewport sizes)
- Document **page state** before/after changes
- Monitor **visual changes** over time

## Usage

```bash
uv run scripts/screenshot.py <url> <output_path> [options]
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--selector <css>` | Screenshot specific element only | - |
| `--wait <selector>` | Wait for element before screenshot | - |
| `--full-page` | Capture entire scrollable page | false |
| `--width <px>` | Viewport width | 1280 |
| `--height <px>` | Viewport height | 720 |
| `--timeout <ms>` | Page load timeout | 30000 |
| `--user-agent` | Custom user agent string | - |
| `--no-headless` | Show browser window (debug) | false |

## Examples

### Full Page Screenshot

```bash
uv run scripts/screenshot.py "https://example.com" /workspace/page.png --full-page
```

### Mobile Viewport

```bash
uv run scripts/screenshot.py "https://example.com" /workspace/mobile.png --width 375 --height 812
```

### Specific Element

```bash
uv run scripts/screenshot.py "https://example.com" /workspace/header.png --selector "header"
```

### Wait for Dynamic Content

```bash
uv run scripts/screenshot.py "https://spa-site.com" /workspace/loaded.png --wait ".content-loaded" --full-page
```

## Output

```json
{
  "status": "success",
  "url": "https://example.com",
  "output_path": "/workspace/page.png",
  "dimensions": {
    "width": 1280,
    "height": 3500
  },
  "file_size_kb": 456.23
}
```

## Common Viewport Sizes

| Device | Width | Height |
|--------|-------|--------|
| Desktop | 1280 | 720 |
| Laptop | 1440 | 900 |
| Tablet | 768 | 1024 |
| iPhone | 375 | 812 |
| Android | 360 | 800 |

## Troubleshooting

### "Timeout waiting for selector"

1. Increase timeout: `--timeout 60000`
2. Check if selector exists on the page
3. Page might need JavaScript - try `--wait` for a specific element

### Blank or incomplete screenshot

1. Use `--wait` for dynamic content
2. Try `--full-page` for scrollable pages
3. Some sites block headless browsers - try custom `--user-agent`
