# chrome-agent

CLI tool for AI agents to observe and interact with Chrome browsers via CDP.

Install: `uv tool install chrome-agent` (or `pip install chrome-agent`). Requires Chrome/Chromium installed on the system.

## Quick Reference

```bash
chrome-agent launch [--port PORT] [--headless] [--fingerprint profile.json]
chrome-agent status [<instance>]
chrome-agent attach <instance> [+Event ...] [--target SPEC] [--url SUBSTRING]
chrome-agent help [<instance>] [Domain | Domain.method]
chrome-agent stop <instance>
chrome-agent cleanup
chrome-agent <instance> Domain.method '{"param": "value"}'
```

## Two Channels

chrome-agent uses a two-channel pattern for browser interaction:

**Observe (attach):** `chrome-agent attach mysite-01 +Page.loadEventFired +Network.requestWillBeSent` holds a persistent connection and streams subscribed events to stdout as JSON lines. Run it in the background (with `&`, under Monitor, or redirected to a file). Each attach session has isolated event subscriptions -- other participants don't see your subscriptions, and you don't see theirs.

**Act (one-shot):** `chrome-agent mysite-01 Runtime.evaluate '{"expression": "document.title", "returnByValue": true}'` connects, sends one CDP command, prints the JSON response, and disconnects. ~50-80ms per call (Python startup dominates). Use for navigation, evaluation, screenshots, input dispatch -- any command-response interaction.

Both channels address browsers by **instance name**, not port number. Launch creates a named instance; all subsequent commands use that name.

## Launching and Managing Browsers

```bash
# Launch -- auto-allocates a port, names the instance from the current directory
chrome-agent launch
# Output: {"name": "myproject-01", "port": 9222, "pid": 58469, "browser_version": "Chrome/147"}

# Launch with specific port
chrome-agent launch --port 9500

# See what's running
chrome-agent status
# aroundchicago.tech-01  port 9222
#   [1] 956FD3C2  https://www.meetup.com/find/...  "Find Events | Meetup"
#
# kindle2markdown-01     port 9223
#   [1] F9G0H1I2  about:blank

# See a specific instance
chrome-agent status mysite-01

# Stop a browser gracefully (sends CDP Browser.close)
chrome-agent stop mysite-01

# Clean up dead instances
chrome-agent cleanup
```

## Common Operations

```bash
# Read page title
chrome-agent mysite-01 Runtime.evaluate '{"expression": "document.title", "returnByValue": true}'

# Read visible text
chrome-agent mysite-01 Runtime.evaluate '{"expression": "document.body.innerText.substring(0, 500)", "returnByValue": true}'

# Navigate
chrome-agent mysite-01 Page.navigate '{"url": "https://example.com"}'

# Take screenshot (returns base64 PNG in JSON)
chrome-agent mysite-01 Page.captureScreenshot '{"format": "png"}'

# Decode and save a screenshot
chrome-agent mysite-01 Page.captureScreenshot '{"format": "png"}' | python3 -c "import sys,json,base64; d=json.load(sys.stdin); open('/tmp/screenshot.png','wb').write(base64.b64decode(d['data']))"

# Evaluate JavaScript
chrome-agent mysite-01 Runtime.evaluate '{"expression": "document.querySelector(\"#price\")?.textContent", "returnByValue": true}'

# Query protocol -- discover available commands
chrome-agent help mysite-01 Page
chrome-agent help mysite-01 Page.navigate
```

If only one instance is running, you can omit the instance name for one-shot commands:

```bash
chrome-agent Page.navigate '{"url": "https://example.com"}'
```

## Interacting with Elements

Pattern: **locate, act, verify.**

```bash
# Locate -- get pixel coordinates via JS
chrome-agent mysite-01 Runtime.evaluate '{"expression": "(() => { const r = document.querySelector(\"#btn\").getBoundingClientRect(); return {x: r.x+r.width/2, y: r.y+r.height/2}; })()", "returnByValue": true}'

# Act -- dispatch real input events at those coordinates
chrome-agent mysite-01 Input.dispatchMouseEvent '{"type": "mousePressed", "x": 400, "y": 300, "button": "left", "clickCount": 1}'
chrome-agent mysite-01 Input.dispatchMouseEvent '{"type": "mouseReleased", "x": 400, "y": 300, "button": "left", "clickCount": 1}'

# Verify
chrome-agent mysite-01 Runtime.evaluate '{"expression": "document.title", "returnByValue": true}'
```

For filling form fields (React-compatible):
```bash
chrome-agent mysite-01 Runtime.evaluate '{"expression": "(() => { const el = document.querySelector(\"#email\"); const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, \"value\").set; set.call(el, \"test@example.com\"); el.dispatchEvent(new Event(\"input\", {bubbles:true})); })()"}'
```

## Observing a Browser

Use `attach` to stream events. Run it in the background while you send commands:

```bash
# Start event observation in background
chrome-agent attach mysite-01 +Page.loadEventFired +Network.requestWillBeSent > /tmp/events.jsonl &

# Send commands -- events caused by these appear in the attach stream
chrome-agent mysite-01 Page.navigate '{"url": "https://example.com"}'

# Read the captured events
cat /tmp/events.jsonl
# {"status": "ready", "sessionId": "42A165B16155FB", "target": "F980DEDB623E4B"}
# {"method": "Network.requestWillBeSent", "params": {"request": {"url": "https://example.com/"}...}}
# {"method": "Page.loadEventFired", "params": {"timestamp": 22932.859519}}
```

Modify subscriptions during the session by writing to stdin:
```bash
# If running interactively (not backgrounded):
+Network.responseReceived    # subscribe to additional event
-Network.requestWillBeSent   # unsubscribe
```

Multiple attach sessions can coexist on the same browser. Each has isolated subscriptions -- one agent enabling Network events does not flood another agent's event stream.

## Target Specifiers

When a browser has multiple tabs, specify which one to target:

```bash
# By numeric index (from status output)
chrome-agent mysite-01 --target 2 Page.navigate '{"url": "..."}'

# By target ID prefix (from status output)
chrome-agent mysite-01 --target 956FD3C2 Runtime.evaluate '{"expression": "document.title"}'

# By URL substring
chrome-agent mysite-01 --url meetup.com Runtime.evaluate '{"expression": "document.title"}'
```

When there's only one tab, no specifier is needed.

## What You Can and Cannot See

CDP events show **consequences** (pages loading, network requests, DOM mutations) but not **causes** (clicks, scrolling, typing, text selection). If you need to observe user interactions, inject DOM listeners via `Runtime.addBinding`. See `docs/collaboration-guide.md` for details.

## Key Gotchas

- **Instance naming.** `chrome-agent launch` creates a named instance from the current directory basename. Use `chrome-agent status` to see what's running.
- **One-shot overhead.** Each CLI invocation costs ~50-80ms (Python startup dominates). For multi-step workflows with event observation, use `attach` in the background and one-shot for commands.
- **Navigation kills context.** If someone navigates while you have a pending `Runtime.evaluate`, you get a context-destroyed error. Retry on the new page.
- **Fingerprint for hostile sites.** Use `--fingerprint profile.json` to override user agent, viewport, timezone, and anti-detection signals.
- **Event isolation.** Each `attach` session has its own event subscriptions. Subscribing to Network events in one session does not affect other sessions.

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
- `docs/monitor-integration.md` -- Claude Code Monitor integration, dual-channel pattern
- `docs/cdp-collaboration-reference.md` -- CDP protocol mechanics, event catalog, binding bridge
