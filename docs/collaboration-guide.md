# Collaboration Guide

Chrome-agent lets multiple participants -- humans, AI agents, or both -- share one browser in real time. This guide shows you how, starting with the simplest case and building to multi-agent development workflows.

For the underlying protocol mechanics, see [cdp-collaboration-reference.md](cdp-collaboration-reference.md) .

## Key Ideas

Three things to understand before diving in:

**Multiple connections coexist.** Chrome's CDP protocol supports many simultaneous WebSocket connections to the same browser. A monitoring agent, a querying agent, a human using the browser, and DevTools can all operate at the same time without interfering. Events fan out to all subscribers. DOM mutations by one participant are instantly visible to all others.

**CDP sees consequences, not causes.** When you click a link, CDP reports that a navigation started and network requests fired. It does not report the click itself. When you scroll, CDP reports lazy-loaded XHR requests. It does not report the scroll position. CDP tells you what the *browser* is doing. It does not tell you what the *user* is doing. For most development workflows, consequences are enough. When they're not, the gap can be bridged (see "Full Interaction Observation").

**Handoff is informal.** There is no lock, token, or turn-taking protocol. Any participant can act at any time. The agent starts dispatching input events and the human sees them happen in the browser window. The human takes back over by clicking or typing. Chrome handles concurrent input gracefully.

## Quick Start: See What's Happening

Launch a browser and observe it from a separate process.

**Launch the browser:**

```bash
chrome-agent launch
```

A Chrome window opens. Navigate to any page.

**From a separate terminal, check the browser:**

```bash
chrome-agent status
```

```
Browser running on port 9222
  Version: Chrome/146.0.7680.177
  URL:     https://www.google.com
  Title:   Google
```

**Read the page from outside the browser:**

```bash
# Page title
chrome-agent Runtime.evaluate '{"expression": "document.title", "returnByValue": true}'

# Visible text (first 200 chars)
chrome-agent Runtime.evaluate '{"expression": "document.body.innerText.substring(0, 200)", "returnByValue": true}'

# Screenshot
chrome-agent Page.captureScreenshot '{"format": "png"}' > /tmp/screenshot.json
python3 -c "import json, base64; d=json.load(open('/tmp/screenshot.json')); open('/tmp/screenshot.png','wb').write(base64.b64decode(d['data'])); print('Saved /tmp/screenshot.png')"
```

Each command connects to the browser, does one thing, and disconnects. The browser doesn't blink. You're observing it without interfering.

**Watch events in real time:**

Start a persistent session in one terminal, subscribe to navigation events, then navigate the browser by hand in the window:

```bash
# Start session (stays open, reading commands from stdin)
chrome-agent session
```

The session prints a readiness line confirming the connection:

```json
{"ready":true,"ws_url":"ws://localhost:9222/devtools/page/ABC123"}
```

Now type these subscribe commands:

```
+Page.loadEventFired
+Page.frameNavigated
```

Go click around in the browser window. Every time a page loads, the session prints a JSON event line:

```json
{"method":"Page.frameNavigated","params":{"frame":{"url":"https://example.com","title":"Example Domain",...}}}
{"method":"Page.loadEventFired","params":{"timestamp":12345.67}}
```

You're watching the human browse in real time. Press Ctrl+D to end the session.

## How Agents Find and Interact with Elements

When an agent needs to click a button, select text, or fill a form, it follows three steps: **locate, act, verify.** This pattern applies to every interaction scenario below.

### Locate

The agent runs JavaScript to find the element and get its pixel coordinates:

```python
# Find a button
coords = await cdp.send(method="Runtime.evaluate", params={
    "expression": """
    (() => {
        const el = document.querySelector('#submit-button');
        const r = el.getBoundingClientRect();
        return {x: r.x + r.width/2, y: r.y + r.height/2};
    })()
    """,
    "returnByValue": True,
})
pos = coords["result"]["value"]  # {"x": 400, "y": 300}
```

For selecting specific text, a `TreeWalker` locates the text node and a `Range` returns pixel coordinates for the substring:

```python
coords = await cdp.send(method="Runtime.evaluate", params={
    "expression": """
    (() => {
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        while (walker.nextNode()) {
            const node = walker.currentNode;
            if (node.textContent.includes("target text")) {
                const range = document.createRange();
                const idx = node.textContent.indexOf("target text");
                range.setStart(node, idx);
                range.setEnd(node, idx + "target text".length);
                const rect = range.getBoundingClientRect();
                return {
                    startX: rect.left,
                    startY: rect.top + rect.height / 2,
                    endX: rect.right,
                    endY: rect.top + rect.height / 2
                };
            }
        }
        return null;
    })()
    """,
    "returnByValue": True,
})
```

### Act

Dispatch input events at those coordinates. Chrome processes these identically to physical input -- the page's JavaScript sees real events and the human sees the action happen in the browser window.

```python
# Click
await cdp.send(method="Input.dispatchMouseEvent", params={
    "type": "mousePressed", "x": pos["x"], "y": pos["y"],
    "button": "left", "clickCount": 1,
})
await cdp.send(method="Input.dispatchMouseEvent", params={
    "type": "mouseReleased", "x": pos["x"], "y": pos["y"],
    "button": "left", "clickCount": 1,
})
```

```python
# Drag-to-select text
start = coords["result"]["value"]
await cdp.send(method="Input.dispatchMouseEvent", params={
    "type": "mousePressed", "x": start["startX"], "y": start["startY"],
    "button": "left", "clickCount": 1,
})
# Move across in steps (human sees highlight grow)
steps = 5
for i in range(1, steps + 1):
    frac = i / steps
    x = start["startX"] + (start["endX"] - start["startX"]) * frac
    await cdp.send(method="Input.dispatchMouseEvent", params={
        "type": "mouseMoved", "x": int(x), "y": start["startY"], "button": "left",
    })
await cdp.send(method="Input.dispatchMouseEvent", params={
    "type": "mouseReleased", "x": start["endX"], "y": start["endY"],
    "button": "left", "clickCount": 1,
})
```

### Verify

```python
# What was selected?
sel = await cdp.send(method="Runtime.evaluate", params={
    "expression": "window.getSelection().toString()",
    "returnByValue": True,
})
print(f"Selected: {sel['result']['value']}")

# Did the page navigate?
title = await cdp.send(method="Runtime.evaluate", params={
    "expression": "document.title",
    "returnByValue": True,
})

# Was the form filled?
value = await cdp.send(method="Runtime.evaluate", params={
    "expression": "document.querySelector('#email')?.value",
    "returnByValue": True,
})
```

## Scenario 1: You Browse, an Agent Watches

You're exploring a site or testing your web app. An AI agent follows along, catching errors, reading the DOM, answering questions.

### Setup

The agent starts a monitoring script that holds a persistent CDP connection and prints events to stdout. In Claude Code, the Monitor tool streams each line as a real-time notification:

```python
# monitor_browser.py
import asyncio
from chrome_agent.cdp_client import CDPClient, get_ws_url

async def observe():
    ws_url = get_ws_url(port=9222, target_type="page")
    cdp = CDPClient(ws_url=ws_url)
    await cdp.connect()

    await cdp.send(method="Page.enable")
    await cdp.send(method="Network.enable")

    def on_navigate(params):
        frame = params.get("frame", {})
        if not frame.get("parentId"):  # top-level only
            print(f'[PAGE] {frame.get("title", "")} | {frame.get("url", "")}', flush=True)

    def on_request(params):
        req_type = params.get("type", "")
        if req_type in ("Document", "XHR", "Fetch"):
            url = params.get("request", {}).get("url", "")
            print(f"[{req_type}] {url[:120]}", flush=True)

    cdp.on(event="Page.frameNavigated", callback=on_navigate)
    cdp.on(event="Network.requestWillBeSent", callback=on_request)

    print("[MONITOR] Watching -- navigate freely", flush=True)
    while cdp._connected:
        await asyncio.sleep(1)

asyncio.run(observe())
```

While the monitor runs, the agent queries the page on demand via separate one-shot connections:

```python
# Agent reads the page -- separate connection, doesn't interfere with monitor
async with CDPClient(ws_url=ws_url) as cdp:
    title = await cdp.send(method="Runtime.evaluate", params={
        "expression": "document.querySelector('#productTitle')?.textContent.trim()",
        "returnByValue": True,
    })

    screenshot = await cdp.send(method="Page.captureScreenshot", params={"format": "png"})
```

The monitor streams events continuously. DOM queries and screenshots happen on demand. Both are separate CDP connections that coexist with the human's browser usage.

### What the agent sees

- Which pages you visit (URL, title, load timing)
- Network activity (API calls, failed requests -- filtered to Document/XHR/Fetch)
- DOM state at any moment (via `Runtime.evaluate`)
- Visual state at any moment (via screenshots)
- Console output (if subscribed to `Runtime.consoleAPICalled`)

### What the agent doesn't see

Your clicks, scrolling, hovering, typing, or text selection. The agent sees *consequences* of your actions but not the *causes*. For most development workflows, consequences are enough. For full interaction visibility, see "Full Interaction Observation" below.

### What this looks like in practice

During a collaborative Amazon browsing session, a navigation-only monitor saw 2-3 events per page visit (frameNavigated + loadEventFired). Adding network events produced 200+ per page (ads, tracking, lazy-loading, video transcoding). Filtering to Document + XHR/Fetch brought it down to 10-20 meaningful events. Start with navigation only and add network when you need it.

### Handoff

The agent takes over by dispatching input events (locate, act, verify -- described above). The human sees the agent's actions live in the browser. No protocol needed -- the agent just starts acting, the human takes back over by clicking or typing.

## Scenario 2: An Agent Drives, You Watch

You've asked the agent to test a workflow, fill a form, or navigate a multi-step process. You watch the browser window to verify.

### What you see

Everything. The agent dispatches real browser input events. Chrome renders them visually, identically to physical input. You see the cursor move, characters appear in form fields, buttons depress, pages load, text highlight. This is live, not a recording.

### What you don't see

The agent's intent. You see it click a button but not *why*. Two ways to bridge this:

1. **The agent narrates in your conversation.** "I'm clicking the submit button to test form validation."
2. **The agent logs to the browser console.** You watch the console in DevTools (F12):

```python
await cdp.send(method="Runtime.evaluate", params={
    "expression": "console.log('[agent] Clicking submit to test validation')",
})
```

Any participant subscribed to `Runtime.consoleAPICalled` also sees these messages. The console becomes a shared communication channel between humans, agents, and the page itself.

## Scenario 3: Debugging a Web App Together

This is the core development workflow. You're building a web app. Something isn't working. You and an AI agent collaborate to find and fix it.

### Step 1: Launch and point at your dev server

```bash
chrome-agent launch
# Navigate to http://localhost:3000 in the browser window
```

### Step 2: Agent starts monitoring errors

The agent sets up a monitor that watches for problems:

```python
# error_monitor.py
import asyncio
from chrome_agent.cdp_client import CDPClient, get_ws_url

async def watch_errors():
    ws_url = get_ws_url(port=9222, target_type="page")
    cdp = CDPClient(ws_url=ws_url)
    await cdp.connect()

    await cdp.send(method="Runtime.enable")
    await cdp.send(method="Log.enable")
    await cdp.send(method="Network.enable")

    def on_console(params):
        level = params.get("type", "log")
        args = params.get("args", [])
        text = " ".join(a.get("value", a.get("description", "?")) for a in args)
        if level in ("error", "warning"):
            print(f"[{level.upper()}] {text[:200]}", flush=True)

    def on_exception(params):
        details = params.get("exceptionDetails", {})
        text = details.get("text", "")
        url = details.get("url", "")
        line = details.get("lineNumber", "?")
        print(f"[EXCEPTION] {text} at {url}:{line}", flush=True)

    def on_network_fail(params):
        url = params.get("request", {}).get("url", "") if "request" in params else ""
        error = params.get("errorText", "")
        print(f"[NET FAIL] {error}: {url[:120]}", flush=True)

    cdp.on(event="Runtime.consoleAPICalled", callback=on_console)
    cdp.on(event="Runtime.exceptionThrown", callback=on_exception)
    cdp.on(event="Network.loadingFailed", callback=on_network_fail)

    print("[ERROR MONITOR] Watching for errors", flush=True)
    while cdp._connected:
        await asyncio.sleep(1)

asyncio.run(watch_errors())
```

### Step 3: You use the app

Click through the UI, submit forms, trigger the bug. The agent sees every `console.error`, every unhandled exception with stack trace, every failed network request in real time.

### Step 4: Agent investigates

When the agent sees an error, it queries the page to understand the state:

```python
async with CDPClient(ws_url=ws_url) as cdp:
    # Read the error message visible on the page
    error_msg = await cdp.send(method="Runtime.evaluate", params={
        "expression": "document.querySelector('.error-message')?.textContent",
        "returnByValue": True,
    })

    # Check what form values the user entered
    email = await cdp.send(method="Runtime.evaluate", params={
        "expression": "document.querySelector('#email')?.value",
        "returnByValue": True,
    })

    # Take a screenshot showing the error state
    screenshot = await cdp.send(method="Page.captureScreenshot", params={"format": "png"})
```

### Step 5: Agent reproduces the bug

You describe what you did. The agent reproduces it programmatically using locate/act/verify:

```python
async with CDPClient(ws_url=ws_url) as cdp:
    # Navigate to the signup page
    await cdp.send(method="Page.navigate", params={"url": "http://localhost:3000/signup"})
    await asyncio.sleep(2)

    # Fill the email field (with proper event dispatch for React)
    await cdp.send(method="Runtime.evaluate", params={
        "expression": """
        (() => {
            const el = document.querySelector('#email');
            const setter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;
            setter.call(el, 'test@example.com');
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
        })()
        """,
    })

    # Click submit using locate/act pattern
    coords = await cdp.send(method="Runtime.evaluate", params={
        "expression": """
        (() => {
            const el = document.querySelector('#submit');
            const r = el.getBoundingClientRect();
            return {x: r.x + r.width/2, y: r.y + r.height/2};
        })()
        """,
        "returnByValue": True,
    })
    pos = coords["result"]["value"]
    await cdp.send(method="Input.dispatchMouseEvent", params={
        "type": "mousePressed", "x": pos["x"], "y": pos["y"],
        "button": "left", "clickCount": 1,
    })
    await cdp.send(method="Input.dispatchMouseEvent", params={
        "type": "mouseReleased", "x": pos["x"], "y": pos["y"],
        "button": "left", "clickCount": 1,
    })
```

You watch the browser to confirm the agent hits the same bug.

### Step 6: You fix, the agent verifies

You edit the code. Your dev server hot-reloads. The agent re-runs the reproduction steps and confirms the error is gone. This is the development feedback loop: you write code, the agent tests it in the live browser, you iterate.

## Scenario 4: Multiple Agents, No Human

For automated testing, multiple agents operate the same browser headlessly.

```bash
chrome-agent launch --headless
```

Each agent runs its own script with a persistent CDPClient connection:

- **Agent A (actor):** Navigates through critical user flows. Fills forms, clicks buttons, follows links.
- **Agent B (network monitor):** Subscribes to `Network.requestWillBeSent` and `Network.responseReceived`. Records every API call, response time, and status code.
- **Agent C (visual regression):** Takes screenshots at each step via `Page.captureScreenshot`. Compares against baselines.
- **Agent D (error monitor):** Subscribes to `Runtime.exceptionThrown` and `Runtime.consoleAPICalled`. Flags any errors during Agent A's workflow.

All four see the same browser state. When Agent A navigates, Agents B-D observe through their subscriptions. Chrome fans out events to all connections.

For action coordination, designate one agent as the actor. Others observe only. This is a convention, not a lock -- chrome-agent doesn't enforce it because Chrome's multi-client model handles concurrent access gracefully (navigation by one connection sends a clean context-destroyed error to others with pending work, rather than hanging or crashing).

## Anti-Detection: Fingerprint Profiles

Sites like Amazon detect automated browsers and may block or alter behavior. Launch with a fingerprint profile to make the browser appear as a regular desktop browser:

```bash
chrome-agent launch --fingerprint profile.json
```

The profile JSON overrides browser identity signals:

```json
{
    "userAgent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "platform": "Linux x86_64",
    "vendor": "Google Inc.",
    "language": "en-US",
    "timezone": "America/Chicago",
    "viewport": {"width": 1920, "height": 1080}
}
```

This sets the user agent (HTTP header and JavaScript), viewport size, language, timezone, and overrides `navigator.webdriver` (false), `navigator.platform`, `navigator.vendor`, and `window.chrome`. The fingerprint persists across page navigations for the lifetime of the browser.

Without `--fingerprint`, the browser launches with default Chrome settings, which some sites detect as automated.

## Full Interaction Observation

The default CDP events show consequences but not causes. If you need an agent to see exactly what a human does -- every click, scroll, and text selection -- inject DOM event listeners via the binding bridge. This is more advanced; most development workflows don't need it.

### Setup

The observing agent registers a binding and injects listeners:

```python
async def setup_interaction_observer(cdp: CDPClient):
    """Inject DOM event listeners that report to CDP via binding."""

    # Register the binding -- creates a JS function that fires CDP events
    await cdp.send(method="Runtime.addBinding", params={"name": "reportInteraction"})

    # Inject listeners for click, scroll, and selection
    await cdp.send(method="Runtime.evaluate", params={"expression": """
        document.addEventListener('click', (e) => {
            reportInteraction(JSON.stringify({
                type: 'click',
                x: e.clientX,
                y: e.clientY,
                target: e.target.tagName + (e.target.id ? '#' + e.target.id : '')
            }));
        }, true);

        document.addEventListener('scroll', () => {
            reportInteraction(JSON.stringify({
                type: 'scroll',
                y: window.scrollY
            }));
        }, {passive: true});

        document.addEventListener('selectionchange', () => {
            const text = window.getSelection().toString();
            if (text) {
                reportInteraction(JSON.stringify({
                    type: 'selection',
                    text: text
                }));
            }
        });
    """})

    # Listen for the binding events
    def on_interaction(params):
        payload = params.get("payload", "")
        print(f"[INTERACTION] {payload}", flush=True)

    cdp.on(event="Runtime.bindingCalled", callback=on_interaction)
```

Now every click, scroll, and text selection fires a `Runtime.bindingCalled` event with the interaction details.

### Persistence across navigation

The binding function survives page navigations within the same CDP session (Chrome re-injects it into new execution contexts). But the `addEventListener` calls don't -- they're in the old page's JavaScript context. To get listeners on every page:

```python
# Register listeners to auto-inject on every new page
await cdp.send(method="Page.addScriptToEvaluateOnNewDocument", params={"source": """
    document.addEventListener('click', (e) => {
        if (typeof reportInteraction === 'function') {
            reportInteraction(JSON.stringify({
                type: 'click', x: e.clientX, y: e.clientY,
                target: e.target.tagName + (e.target.id ? '#' + e.target.id : '')
            }));
        }
    }, true);
    // ... same for scroll and selectionchange
"""})
```

The `if (typeof reportInteraction === 'function')` guard prevents errors if the binding isn't registered yet.

### Limitations

- **Session-scoped.** If the observing agent's CDP connection drops, the binding stops working on the next navigation. Re-register after reconnecting.
- **Performance.** Skip `mousemove` (fires hundreds of times per second). Use `click` + `scroll` + `selectionchange` for meaningful interactions without noise.

## When Things Go Wrong

### The browser crashes

All CDP connections receive a WebSocket close event. Pending `send()` calls raise `ConnectionError`. The monitor exits. Session mode exits with code 1 and prints "WebSocket disconnected" to stderr. Recovery: `chrome-agent status`, relaunch, reconnect.

### Navigation destroys execution context

When any participant navigates, Chrome destroys the current page's JavaScript execution context. Any other agent with a pending `Runtime.evaluate` receives a context-destroyed error. This is a clean error, not a hang or crash. The connection stays alive and subsequent commands work on the new page.

### Port is already occupied

```
Error: Port 9222 is already in use (Chrome/146.0.7680.177).
Kill the existing browser with: kill $(lsof -ti:9222)
or use a different port with --port.
```

The existing browser is not disturbed. Use `--port 9223` to launch alongside it, or kill the existing process.

### Agent sends a bad CDP command

Invalid commands return a `CDPError` with Chrome's error code and message. The connection stays alive. In session mode, the error appears on stdout and the session continues.

## Tips

- **Start simple.** Use `chrome-agent status` and one-shot `Runtime.evaluate` before setting up monitors. Get comfortable with what you can see.

- **Screenshots are cheap verification.** When in doubt, take a screenshot. Fastest way to confirm agent and human see the same thing.

- **Filter events aggressively.** Start with `Page.frameNavigated` only. Add Network filtered to `Document` and `XHR`/`Fetch` when you need it.

- **Session mode for sustained work.** One-shot commands cost ~350ms each. Session mode: ~0.5ms per command.

- **Multiple connections coexist.** Monitor, query connection, and human share the browser without conflict.

- **The console is a communication channel.** `console.log` from the agent. Human sees it in DevTools. Other agents see it via `Runtime.consoleAPICalled`.

- **Fingerprint for hostile sites.** `--fingerprint profile.json` when sites detect automation.
