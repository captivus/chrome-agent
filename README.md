# chrome-agent

A CLI tool for AI agents to observe and interact with Chrome browsers via the Chrome DevTools Protocol (CDP).

Designed as a faster, lower-overhead alternative to browser MCP tools. Each command connects to a running Chrome instance, performs one action, and disconnects. No persistent server, no protocol negotiation, no bloated response formatting.

## Installation

```bash
# Install from PyPI
uv tool install chrome-agent

# Or add as a project dependency
uv add chrome-agent

# Install Playwright's Chromium browser (required once)
uv run playwright install chromium
```

## Quick Start

### Launch and use a browser (drive mode)

```bash
# Launch a browser with CDP enabled
chrome-agent launch &

# Navigate and inspect
chrome-agent navigate "https://example.com"
chrome-agent text
chrome-agent element "h1"
chrome-agent screenshot /tmp/page.png
```

### Observe an existing browser (attach mode)

If your automation code launches Chromium with `--remote-debugging-port=9222`, you can connect to observe it:

```bash
chrome-agent status       # Is the browser running?
chrome-agent url          # What page is it on?
chrome-agent screenshot   # What does it look like?
chrome-agent element "#submit-btn"  # Why can't the code click this?
```

## Commands

```
chrome-agent [--port PORT] <command> [args...]
```

**Observe:** `url`, `screenshot`, `snapshot`, `text`, `html`, `element`, `find`, `value`, `eval`, `cookies`, `tabs`, `wait`

**Navigate:** `navigate`, `back`, `forward`, `reload`

**Interact:** `click`, `clickxy`, `fill`, `type`, `press`, `select`, `check`, `uncheck`, `hover`, `scroll`

**Meta:** `status`, `launch`, `close`, `viewport`, `help`

Run `chrome-agent help` for full command reference.

## For AI Agents

See [INSTRUCTIONS.md](INSTRUCTIONS.md) for comprehensive agent instructions covering:

- Drive mode vs attach mode mental model
- The development feedback loop (write code -> observe browser -> fix code)
- When to observe vs intervene
- Command recipes for common tasks
- Failure modes and recovery

Include the contents of `INSTRUCTIONS.md` in your project's `CLAUDE.md` or agent instructions file.

## Optional: Browser Fingerprinting

For sites that detect automated browsers, launch with a fingerprint profile:

```bash
chrome-agent launch --fingerprint path/to/fingerprint.json
```

The fingerprint JSON should contain:

```json
{
    "userAgent": "Mozilla/5.0 ...",
    "platform": "Linux x86_64",
    "vendor": "Google Inc.",
    "language": "en-US",
    "timezone": "America/Chicago",
    "viewport": {"width": 1920, "height": 1080}
}
```

Without `--fingerprint`, the browser launches with default settings and no anti-detection spoofing.

## Requirements

- Python >= 3.11
- Playwright >= 1.50.0
- Chromium (installed via `playwright install chromium`)
- Linux with xdotool (optional, for virtual desktop pinning)

## License

MIT
