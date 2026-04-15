# chrome-agent

[![PyPI version](https://img.shields.io/pypi/v/chrome-agent)](https://pypi.org/project/chrome-agent/)
[![PyPI downloads](https://img.shields.io/pypi/dm/chrome-agent)](https://pypi.org/project/chrome-agent/)
[![Python versions](https://img.shields.io/pypi/pyversions/chrome-agent)](https://pypi.org/project/chrome-agent/)
[![License](https://img.shields.io/pypi/l/chrome-agent)](https://github.com/captivus/chrome-agent/blob/main/LICENSE)

A CLI tool that gives AI coding agents the ability to observe and interact with Chrome browsers via the Chrome DevTools Protocol.

Multiple agents and humans can share the same browser simultaneously, each with isolated event subscriptions. One agent drives while another observes network traffic. A human browses while an agent watches for errors. Four agents run a coordinated test suite against a single browser. Each participant sees only the events they subscribed to -- no interference.

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
# Launch a browser -- auto-allocates a port and names the instance
chrome-agent launch
# {"name": "myproject-01", "port": 9222, "pid": 58469, "browser_version": "Chrome/147"}

# Check what's running
chrome-agent status
# myproject-01  port 9222
#   [1] 956FD3C2  https://example.com  "Example Domain"

# Read the page title
chrome-agent myproject-01 Runtime.evaluate '{"expression": "document.title", "returnByValue": true}'

# Navigate
chrome-agent myproject-01 Page.navigate '{"url": "https://example.com"}'

# Take a screenshot (returns base64 PNG in JSON)
chrome-agent myproject-01 Page.captureScreenshot '{"format": "png"}'

# Discover available commands
chrome-agent help myproject-01 Page
chrome-agent help myproject-01 Page.navigate
```

## Two Channels

chrome-agent uses a two-channel pattern for browser interaction:

### One-shot mode (commands)

Send a single CDP command. Connects, sends, prints JSON response, disconnects.

```bash
chrome-agent <instance> Domain.method '{"param": "value"}'
```

Good for spot checks, screenshots, quick queries. ~50-80ms per call. If only one instance is running, the instance name can be omitted.

### Attach mode (events)

Persistent connection with isolated event subscriptions. Streams events to stdout as JSON lines.

```bash
chrome-agent attach <instance> +Page.loadEventFired +Network.requestWillBeSent
```

Run it in the background while sending one-shot commands:

```bash
# Background: observe events
chrome-agent attach myproject-01 +Page.loadEventFired +Network.requestWillBeSent > /tmp/events.jsonl &

# Foreground: send commands -- events appear in the attach stream
chrome-agent myproject-01 Page.navigate '{"url": "https://example.com"}'
```

Subscribe to exactly the events you need. Each attach session is isolated -- subscribing to Network events in one session does not affect other sessions.

## Operational Commands

```
chrome-agent launch [--headless] [--fingerprint PATH] [--port PORT]
chrome-agent status [<instance>]
chrome-agent attach <instance> [+Event ...] [--target SPEC] [--url SUBSTRING]
chrome-agent help [<instance>] [Domain | Domain.method]
chrome-agent cleanup
```

| Command | Description |
|---------|-------------|
| `launch` | Find Chrome, launch with CDP enabled. Auto-allocates a port and names the instance from the current directory. |
| `status` | List running instances with their page targets (IDs, URLs, titles). |
| `attach` | Persistent event observation with isolated subscriptions. |
| `help` | Query the browser's protocol schema. Lists domains, commands, events, parameters. |
| `cleanup` | Remove stale instances and their session directories. |

## Interacting with Elements

Agents interact with page elements using a three-step pattern: **locate, act, verify.**

```bash
# Locate -- find element coordinates via JavaScript
chrome-agent myproject-01 Runtime.evaluate '{"expression": "(() => { const r = document.querySelector(\"#submit\").getBoundingClientRect(); return {x: r.x+r.width/2, y: r.y+r.height/2}; })()", "returnByValue": true}'

# Act -- dispatch real input events at those coordinates
chrome-agent myproject-01 Input.dispatchMouseEvent '{"type": "mousePressed", "x": 400, "y": 300, "button": "left", "clickCount": 1}'
chrome-agent myproject-01 Input.dispatchMouseEvent '{"type": "mouseReleased", "x": 400, "y": 300, "button": "left", "clickCount": 1}'

# Verify -- confirm the action worked
chrome-agent myproject-01 Runtime.evaluate '{"expression": "document.title", "returnByValue": true}'
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

See [AGENTS.md](AGENTS.md) for concise agent instructions (the standard for AI agent tool documentation). Covers commands, the two-channel pattern, interaction patterns, and gotchas.

## Collaboration

Multiple participants -- humans, AI agents, or both -- can share a browser simultaneously. Each participant creates an independent CDP session with isolated event subscriptions. One agent enabling Network observation does not flood another agent's event stream.

See [docs/collaboration-guide.md](docs/collaboration-guide.md) for:
- Human-agent collaboration patterns (you browse, agent watches)
- Agent-driven workflows (agent drives, you supervise)
- Multi-agent setups with isolated event subscriptions
- The observation gap (what CDP sees vs what it misses)
- Full interaction observation via the binding bridge

For real-time observation using Claude Code's Monitor tool, see [docs/monitor-integration.md](docs/monitor-integration.md) .

## Requirements

- Python >= 3.11
- Google Chrome or Chromium (system-installed)
- Linux with xdotool (optional, for virtual desktop pinning)

## License

MIT
