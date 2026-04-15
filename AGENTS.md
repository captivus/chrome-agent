# chrome-agent

CLI tool for AI agents to observe and interact with Chrome browsers via CDP.

Install: `uv tool install chrome-agent` (or `pip install chrome-agent`). Requires Chrome/Chromium on the system.

## Quick Reference

```bash
chrome-agent launch [--port PORT] [--headless] [--fingerprint profile.json]
chrome-agent status [<instance>]
chrome-agent attach <instance> [+Event ...] [--target SPEC] [--url SUBSTRING]
chrome-agent stop <instance> [--target SPEC] [--url SUBSTRING]
chrome-agent help [<instance>] [Domain | Domain.method]
chrome-agent cleanup
chrome-agent <instance> Domain.method '{"param": "value"}'
```

## Two Channels

**Observe (attach):** `chrome-agent attach mysite-01 +Page.loadEventFired +Network.requestWillBeSent` holds a persistent connection and streams subscribed events to stdout as JSON lines. Run it in the background while you send commands:

```bash
chrome-agent attach mysite-01 +Page.loadEventFired +Network.requestWillBeSent > /tmp/events.jsonl &
chrome-agent mysite-01 Page.navigate '{"url": "https://example.com"}'
cat /tmp/events.jsonl  # events from the navigation appear here
```

Each attach session has isolated subscriptions -- other participants don't see yours, you don't see theirs. Modify subscriptions during the session via stdin (`+Event` to subscribe, `-Event` to unsubscribe).

**Act (one-shot):** `chrome-agent mysite-01 Domain.method '{"params"}'` connects, sends one CDP command, prints JSON, disconnects. ~50-80ms per call. If only one instance is running, the instance name can be omitted.

Both channels address browsers by **instance name**, not port number.

## Managing Browsers

```bash
# Launch -- auto-allocates a port, names the instance from the current directory
chrome-agent launch
# {"name": "myproject-01", "port": 9222, "pid": 58469, "browser_version": "Chrome/147"}

chrome-agent launch --port 9500         # specific port
chrome-agent launch --headless          # headless mode
chrome-agent launch --fingerprint p.json  # anti-detection

chrome-agent status                     # list all instances with page targets
chrome-agent status mysite-01           # one instance

chrome-agent stop mysite-01             # stop entire browser (Browser.close)
chrome-agent stop mysite-01 --target 2  # close just one tab (Target.closeTarget)
chrome-agent stop mysite-01 --url foo   # close tab matching URL

chrome-agent cleanup                    # remove dead instances
```

## Common Operations

```bash
chrome-agent mysite-01 Runtime.evaluate '{"expression": "document.title", "returnByValue": true}'
chrome-agent mysite-01 Runtime.evaluate '{"expression": "document.body.innerText.substring(0, 500)", "returnByValue": true}'
chrome-agent mysite-01 Page.navigate '{"url": "https://example.com"}'
chrome-agent mysite-01 Page.captureScreenshot '{"format": "png"}'

# Save a screenshot to file
chrome-agent mysite-01 Page.captureScreenshot '{"format": "png"}' | python3 -c "import sys,json,base64; d=json.load(sys.stdin); open('/tmp/screenshot.png','wb').write(base64.b64decode(d['data']))"

# Discover available commands
chrome-agent help mysite-01 Page
chrome-agent help mysite-01 Page.navigate
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

## Target Specifiers

When a browser has multiple tabs, specify which one to target:

```bash
chrome-agent mysite-01 --target 2 Page.navigate '{"url": "..."}'          # by index
chrome-agent mysite-01 --target 956FD3C2 Runtime.evaluate '{"expression": "..."}'  # by ID prefix
chrome-agent mysite-01 --url meetup.com Runtime.evaluate '{"expression": "..."}'   # by URL
```

When there's only one tab, no specifier is needed.

## Key Gotchas

- **Instance naming.** `chrome-agent launch` names the instance from the current directory basename. Use `status` to see what's running.
- **One-shot overhead.** ~50-80ms per call (Python startup). Use `attach` in background for event observation.
- **Navigation kills context.** Pending `Runtime.evaluate` gets a context-destroyed error when someone navigates. Retry on the new page.
- **Event isolation.** Each `attach` session has its own subscriptions. No cross-talk between participants.
- **CDP sees consequences, not causes.** Events show pages loading and network requests, not clicks or scrolling. See [docs/collaboration-guide.md](docs/collaboration-guide.md) for the binding bridge workaround.

## Further Reading

- [docs/collaboration-guide.md](docs/collaboration-guide.md) -- multi-agent workflows, human-agent patterns
- [docs/monitor-integration.md](docs/monitor-integration.md) -- Claude Code Monitor integration
- [docs/cdp-collaboration-reference.md](docs/cdp-collaboration-reference.md) -- CDP protocol mechanics, binding bridge
