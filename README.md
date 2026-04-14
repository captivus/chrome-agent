# chrome-agent

[![PyPI version](https://img.shields.io/pypi/v/chrome-agent)](https://pypi.org/project/chrome-agent/)
[![PyPI downloads](https://img.shields.io/pypi/dm/chrome-agent)](https://pypi.org/project/chrome-agent/)
[![Python versions](https://img.shields.io/pypi/pyversions/chrome-agent)](https://pypi.org/project/chrome-agent/)
[![License](https://img.shields.io/pypi/l/chrome-agent)](https://github.com/captivus/chrome-agent/blob/main/LICENSE)

A CLI tool that gives AI coding agents the ability to observe and interact with Chrome browsers via the Chrome DevTools Protocol.

Multiple agents and humans can share the same browser simultaneously. One agent drives while another observes. A human browses while an agent watches for errors. Four agents run a coordinated test suite against a single browser. The protocol supports all of it natively.

## Why this exists

AI coding agents need to see and interact with browsers -- to test their code, debug automation, inspect page state. The standard approach (browser MCP tools) uses a persistent server with protocol negotiation and verbose response formatting. `chrome-agent` takes a different approach: direct access to Chrome's DevTools Protocol with no abstraction layer.

This means full CDP protocol access -- every command, every event, every domain Chrome exposes. Not a curated subset of capabilities, but the complete protocol. Agents compose interactions from CDP primitives the same way DevTools does.

## Installation

```bash
uv tool install chrome-agent
```

Or add to a project:

```bash
uv add chrome-agent
```

Requires Google Chrome or Chromium installed on the system. No Playwright, no browser downloads.

## Quick Start

```bash
# Launch a browser
chrome-agent launch

# Check it's running
chrome-agent status

# Read the page title
chrome-agent Runtime.evaluate '{"expression": "document.title", "returnByValue": true}'

# Navigate
chrome-agent Page.navigate '{"url": "https://example.com"}'

# Take a screenshot (returns base64 PNG in JSON)
chrome-agent Page.captureScreenshot '{"format": "png"}'

# Discover available commands
chrome-agent help Page
chrome-agent help Page.navigate
```

## Two Modes

### One-shot mode

Send a single CDP command. Connects, sends, prints JSON response, disconnects.

```bash
chrome-agent [--port PORT] Domain.method '{"param": "value"}'
```

Good for spot checks, screenshots, quick queries. ~350ms per call.

### Session mode

Persistent CDP connection via stdin/stdout. Send commands, subscribe to events, get real-time notifications.

```bash
chrome-agent session [--port PORT]
```

Session protocol:
```
+Page.loadEventFired              # subscribe to event
+Page.frameNavigated              # subscribe to another
Page.navigate {"url": "https://example.com"}   # send command
-Page.loadEventFired              # unsubscribe
```

Responses and events are JSON lines on stdout. ~0.5ms per command.

## Operational Commands

```
chrome-agent launch [--headless] [--fingerprint PATH] [--port PORT]
chrome-agent status [--port PORT]
chrome-agent session [--port PORT]
chrome-agent help [Domain | Domain.method]
chrome-agent cleanup
```

| Command | Description |
|---------|-------------|
| `launch` | Find Chrome, launch with CDP enabled. Refuses if port is occupied. |
| `status` | Check if a browser is running on the CDP port. |
| `session` | Start a persistent CDP session (stdin/stdout). |
| `help` | Query the browser's protocol schema. Lists domains, commands, events, parameters. |
| `cleanup` | Remove stale session directories from previous launches. |

## Interacting with Elements

Agents interact with page elements using a three-step pattern: **locate, act, verify.**

```bash
# Locate -- find element coordinates via JavaScript
chrome-agent Runtime.evaluate '{"expression": "(() => { const r = document.querySelector(\"#submit\").getBoundingClientRect(); return {x: r.x+r.width/2, y: r.y+r.height/2}; })()", "returnByValue": true}'

# Act -- dispatch real input events at those coordinates
chrome-agent Input.dispatchMouseEvent '{"type": "mousePressed", "x": 400, "y": 300, "button": "left", "clickCount": 1}'
chrome-agent Input.dispatchMouseEvent '{"type": "mouseReleased", "x": 400, "y": 300, "button": "left", "clickCount": 1}'

# Verify -- confirm the action worked
chrome-agent Runtime.evaluate '{"expression": "document.title", "returnByValue": true}'
```

Chrome processes dispatched input events identically to physical input. A human watching the browser sees the cursor move, buttons depress, text highlight, and pages load in real time.

## Python API

```python
from chrome_agent.cdp_client import CDPClient, get_ws_url
from chrome_agent.domains.page import Page
from chrome_agent.domains.runtime import Runtime

async with CDPClient(ws_url=get_ws_url(port=9222)) as cdp:
    page = Page(client=cdp)
    runtime = Runtime(client=cdp)

    await page.navigate(url="https://example.com")
    result = await runtime.evaluate(expression="document.title", return_by_value=True)
    print(result["result"]["value"])
```

54 typed domain classes with snake_case methods generated from Chrome's protocol schema.

## Browser Fingerprinting

For sites that detect automated browsers, launch with a fingerprint profile:

```bash
chrome-agent launch --fingerprint profile.json
```

```json
{
    "userAgent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 ...",
    "platform": "Linux x86_64",
    "vendor": "Google Inc.",
    "language": "en-US",
    "timezone": "America/Chicago",
    "viewport": {"width": 1920, "height": 1080}
}
```

Overrides user agent (HTTP header and JavaScript), viewport, language, timezone, `navigator.webdriver`, `navigator.platform`, `navigator.vendor`, and `window.chrome`. Persists across page navigations.

## For AI Agents

See [AGENTS.md](AGENTS.md) for concise agent instructions (the standard for AI agent tool documentation). Covers commands, session protocol, interaction patterns, and gotchas.

## Collaboration

Multiple participants -- humans, AI agents, or both -- can share a browser simultaneously. Chrome's CDP multiplexes connections: events fan out to all subscribers, DOM mutations are cross-visible, and concurrent access is handled gracefully.

See [docs/collaboration-guide.md](docs/collaboration-guide.md) for:
- Human-agent collaboration patterns (you browse, agent watches)
- Agent-driven workflows (agent drives, you supervise)
- Multi-agent setups (actor + observers)
- The observation gap (what CDP sees vs what it misses)
- Full interaction observation via the binding bridge

For real-time observation using Claude Code's Monitor tool, see [docs/monitor-integration.md](docs/monitor-integration.md) . Includes a ready-to-use observer script with three verbosity tiers and rate limiting for noisy pages.

## Requirements

- Python >= 3.11
- Google Chrome or Chromium (system-installed)
- Linux with xdotool (optional, for virtual desktop pinning)

## License

MIT
