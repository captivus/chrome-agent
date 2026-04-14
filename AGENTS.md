# chrome-agent

CLI tool for AI agents to observe and interact with Chrome browsers via CDP.

## Quick Reference

```bash
chrome-agent launch [--headless] [--fingerprint profile.json] [--port PORT]
chrome-agent status [--port PORT]
chrome-agent session [--port PORT]
chrome-agent help [Domain | Domain.method]
chrome-agent cleanup
chrome-agent [--port PORT] Domain.method '{"param": "value"}'
```

## Two Modes

**One-shot:** `chrome-agent Domain.method '{"params": ...}'` connects, sends one CDP command, prints JSON, disconnects. ~350ms per call. Good for spot checks.

**Session:** `chrome-agent session` holds a persistent CDP connection. Send commands on stdin, read responses and events on stdout as JSON lines. ~0.5ms per command. Use for sustained work.

Session protocol:
```
+Domain.eventName          subscribe to event (auto-enables domain)
-Domain.eventName          unsubscribe
Domain.method {"params"}   send command
```

## Common Operations

```bash
# Check browser status
chrome-agent status

# Read page title
chrome-agent Runtime.evaluate '{"expression": "document.title", "returnByValue": true}'

# Read visible text
chrome-agent Runtime.evaluate '{"expression": "document.body.innerText.substring(0, 500)", "returnByValue": true}'

# Navigate
chrome-agent Page.navigate '{"url": "https://example.com"}'

# Take screenshot (returns base64 PNG in JSON)
chrome-agent Page.captureScreenshot '{"format": "png"}'

# Evaluate JavaScript
chrome-agent Runtime.evaluate '{"expression": "document.querySelector(\"#price\")?.textContent", "returnByValue": true}'

# Query protocol -- discover available commands
chrome-agent help Page
chrome-agent help Page.navigate
```

## Interacting with Elements

Pattern: **locate, act, verify.**

```bash
# Locate -- get pixel coordinates via JS
chrome-agent Runtime.evaluate '{"expression": "(() => { const r = document.querySelector(\"#btn\").getBoundingClientRect(); return {x: r.x+r.width/2, y: r.y+r.height/2}; })()", "returnByValue": true}'

# Act -- dispatch real input events at those coordinates
chrome-agent Input.dispatchMouseEvent '{"type": "mousePressed", "x": 400, "y": 300, "button": "left", "clickCount": 1}'
chrome-agent Input.dispatchMouseEvent '{"type": "mouseReleased", "x": 400, "y": 300, "button": "left", "clickCount": 1}'

# Verify
chrome-agent Runtime.evaluate '{"expression": "document.title", "returnByValue": true}'
```

For filling form fields (React-compatible):
```bash
chrome-agent Runtime.evaluate '{"expression": "(() => { const el = document.querySelector(\"#email\"); const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, \"value\").set; set.call(el, \"test@example.com\"); el.dispatchEvent(new Event(\"input\", {bubbles:true})); })()"}'
```

## Observing a Browser

Use the observer script with Claude Code's Monitor tool for real-time event notifications:

```bash
# Three tiers: nav (navigation only), dev (+ errors + network), full (+ clicks/scrolls/selection)
uv run python scripts/observe.py --tier dev
```

The observer streams filtered events as `[TAG] content` lines:
```
[PAGE] Example Domain | https://example.com
[LOADED]
[XHR] POST https://api.example.com/login
[ERR] TypeError: Cannot read properties of null
```

Multiple CDP connections coexist. The observer, query connections, and a human all share the browser without conflict. See `docs/monitor-integration.md` for the full Monitor integration guide.

## What You Can and Cannot See

CDP events show **consequences** (pages loading, network requests, DOM mutations) but not **causes** (clicks, scrolling, typing, text selection). If you need to observe user interactions, inject DOM listeners via `Runtime.addBinding`. See `docs/collaboration-guide.md` for details.

## Key Gotchas

- **Port conflicts.** `chrome-agent launch` refuses if the port is occupied. Use `--port N` or kill the existing process.
- **One-shot overhead.** Each CLI invocation costs ~350ms. For multi-step workflows, use session mode or the Python CDPClient directly.
- **Navigation kills context.** If someone navigates while you have a pending `Runtime.evaluate`, you get a context-destroyed error. Retry on the new page.
- **Fingerprint for hostile sites.** Use `--fingerprint profile.json` to override user agent, viewport, timezone, and anti-detection signals.

## Python API

```python
from chrome_agent.cdp_client import CDPClient, get_ws_url
from chrome_agent.domains.page import Page
from chrome_agent.domains.runtime import Runtime

ws_url = get_ws_url(port=9222, target_type="page")
async with CDPClient(ws_url=ws_url) as cdp:
    page = Page(client=cdp)
    runtime = Runtime(client=cdp)
    await page.navigate(url="https://example.com")
    result = await runtime.evaluate(expression="document.title", return_by_value=True)
```

54 typed domain classes with snake_case methods. `chrome-agent help` discovers available commands from the live browser.

## Further Reading

- `docs/collaboration-guide.md` -- human-agent collaboration patterns, multi-agent workflows
- `docs/monitor-integration.md` -- Claude Code Monitor integration, observer script, push vs pull
- `docs/cdp-collaboration-reference.md` -- CDP protocol mechanics, event catalog, binding bridge
