# Monitor Integration

How to use Claude Code's Monitor tool with chrome-agent for real-time browser observation.

## How Monitor Works

Claude Code's Monitor tool runs a background script and streams each stdout line as a real-time notification to the agent. The agent keeps working while notifications arrive asynchronously -- no polling, no blocking.

Key behaviors:

- **Each stdout line is one notification.** Lines within 200ms of each other batch into a single notification.
- **`flush=True` is mandatory.** Python buffers stdout by default. Without `flush=True` on every print, events are delayed by seconds or minutes.
- **Too many events auto-stops the monitor.** If the script produces output too fast, the Monitor tool kills it to prevent context overflow. Filter aggressively at the source.
- **Monitor is read-only.** The agent receives notifications but cannot write to the monitored script's stdin. This is the fundamental constraint that shapes the architecture.
- **Persistent mode** runs for the session's lifetime. **Timeout mode** auto-stops after a deadline.

## Architecture: Dual Channel

Because Monitor is read-only, the agent uses two channels:

```mermaid
flowchart TB
    subgraph Agent
        M["Monitor channel (push)\nobserve.py → stdout → notifications"]
        A["Action channel (pull)\nchrome-agent CLI or CDPClient"]
    end

    subgraph Browser["Chrome Browser"]
        CDP1["CDP connection 1\npersistent, events"]
        CDP2["CDP connection 2\nephemeral, commands"]
    end

    M --> CDP1
    A --> CDP2
    CDP1 --> Browser
    CDP2 --> Browser
```

**Monitor channel (push):** A persistent Python script subscribes to CDP events and prints filtered, formatted lines to stdout. The agent receives these as real-time notifications. The script runs for the entire session.

**Action channel (pull):** Separate one-shot `chrome-agent` CLI calls or CDPClient scripts for commands and queries -- navigate, take screenshots, read the DOM, dispatch input events. Each opens its own CDP connection, does its work, and closes.

Both channels connect to the same browser simultaneously. Chrome multiplexes CDP connections -- they don't interfere.

### Why not pipe session mode through Monitor?

`chrome-agent session` reads commands from stdin and writes events to stdout. It would seem natural to run it via Monitor. But Monitor can't write to stdin -- the agent has no way to send commands. Session mode through Monitor would give the agent event observation but no way to act. The dual-channel architecture solves this: Monitor for observation, Bash for action.

## The Observer Script

Chrome-agent includes a ready-to-use observer script at `scripts/observe.py`:

```bash
uv run python scripts/observe.py [--port 9222] [--tier nav|dev|full]
```

**Note:** This script is part of the chrome-agent source repository. It requires the chrome-agent package to be importable (either installed or run from the project directory with `uv run`). If you installed chrome-agent as a tool via `uv tool install`, clone the repo for access to the observer script, or copy the script into your project.

**Startup order matters:** The browser must be running before the observer connects. Launch with `chrome-agent launch` first, then start the observer.

### Tiers

Three verbosity tiers encode filtering decisions so the agent doesn't need to understand CDP event semantics:

**`nav` -- Navigation only (2-3 events per page)**

Subscribes to: `Page.frameNavigated`, `Page.loadEventFired`

Output:
```
[PAGE] Example Domain | https://example.com
[LOADED]
```

Use when: following along with a browsing session, minimal noise.

**`dev` -- Navigation + errors + filtered network (default)**

Adds: `Runtime.consoleAPICalled` (errors/warnings only), `Runtime.exceptionThrown`, `Network.requestWillBeSent` (Document/XHR/Fetch only), `Network.loadingFailed`

Output:
```
[PAGE] My App | http://localhost:3000
[LOADED]
[XHR] POST https://api.example.com/login
[ERR] TypeError: Cannot read properties of null
[EXCEPTION] Unhandled rejection at http://localhost:3000/app.js:42
[NET FAIL] net::ERR_CONNECTION_REFUSED
```

Use when: debugging a web app, watching for errors during development.

**`full` -- Dev + interaction bridge**

Adds: `Runtime.addBinding` + injected DOM listeners for click, scroll, and text selection. Uses JavaScript-side scroll debouncing (300ms) to avoid flooding.

Output:
```
[PAGE] Amazon.com | https://www.amazon.com
[LOADED]
[CLICK] A#nav-link-accountList "Account & Lists"
[SCROLL] y=1200
[SELECT] "Climate Pledge Friendly"
[XHR] GET https://www.amazon.com/api/recommendations
```

Use when: recording user interactions, understanding what a human or agent is clicking/scrolling/selecting.

### Rate limiting

All tiers include a token-bucket rate limiter: max 15 events per 2-second window. Excess events are silently dropped and periodically summarized:

```
[SUPPRESSED] 23 events dropped (rate limited)
```

This prevents Monitor auto-stop on noisy pages like Amazon (200+ network events per page load). The rate limiter drops events at the output level -- suppressed events are genuinely lost, not buffered. The trade-off is acceptable because the suppressed events are noise (the 15th ad-tracking XHR on a page load), not signal.

## Usage Patterns

### Pattern 1: Agent browses with real-time awareness

The agent drives the browser and the monitor provides feedback. The agent doesn't need to explicitly check after each action -- the monitor confirms what happened.

```
Agent starts monitor (see "Starting the Monitor" below)

Agent runs:      chrome-agent Page.navigate '{"url": "https://example.com/login"}'

Monitor reports: [PAGE] Login | https://example.com/login
                 [LOADED]

Agent runs:      chrome-agent Runtime.evaluate '{"expression": "..."}'  (fill form)
Agent runs:      chrome-agent Input.dispatchMouseEvent ...              (click submit)

Monitor reports: [XHR] POST https://api.example.com/auth
                 [PAGE] Dashboard | https://example.com/dashboard
                 [LOADED]

Agent knows:     Login succeeded (saw navigation to dashboard, no errors).
```

Without the monitor, the agent would need to explicitly check the URL and page state after each action. With the monitor, confirmation arrives automatically.

### Pattern 2: Agent observes a human

The human browses. The agent watches via Monitor and answers questions or catches problems.

```
Agent starts monitor with --tier dev

Human clicks:    (navigates to various pages)
Monitor reports: [PAGE] Products | https://myapp.com/products
                 [LOADED]
                 [PAGE] Product Detail | https://myapp.com/products/42
                 [LOADED]
                 [ERR] Failed to load image: 404

Agent responds:  "I see a 404 error loading an image on the product detail page.
                  Let me check which image."
Agent runs:      chrome-agent Runtime.evaluate '{"expression": "..."}'
Agent runs:      chrome-agent Page.captureScreenshot '{"format": "png"}'
```

The monitor is the agent's peripheral vision -- it notices the error without being asked to look.

### Pattern 3: Agent observes a human with full interaction visibility

Same as Pattern 2, but with the `full` tier. The agent sees what the human clicks, scrolls to, and selects.

```
Agent starts monitor with --tier full

Human browses:   (clicks around, scrolls, selects text)
Monitor reports: [PAGE] Amazon.com | https://www.amazon.com
                 [CLICK] INPUT#twotabsearchtextbox
                 [CLICK] INPUT#nav-search-submit-button
                 [PAGE] Search results | https://www.amazon.com/s?k=...
                 [SCROLL] y=800
                 [CLICK] A "Keychron K8 Tenkeyless..."
                 [PAGE] Product | https://www.amazon.com/dp/...
                 [SELECT] "Climate Pledge Friendly"

Agent knows:     The human searched for something, scrolled through results,
                 clicked the Keychron K8, and highlighted "Climate Pledge Friendly."
```

### Pattern 4: Agent observes another agent

Agent A drives the browser. Agent B monitors. This is the multi-agent testing pattern.

```
Agent B starts:  monitor with --tier full

Agent A runs:    chrome-agent Page.navigate '{"url": "http://localhost:3000/checkout"}'

Agent B sees:    [PAGE] Checkout | http://localhost:3000/checkout
                 [LOADED]

Agent A runs:    (locates #email, dispatches Input events to fill it)

Agent B sees:    [CLICK] INPUT#email "test@example.com"
                 [XHR] POST http://localhost:3000/api/validate-email

Agent A runs:    (locates #submit, dispatches click)

Agent B sees:    [CLICK] BUTTON#submit "Place Order"
                 [XHR] POST http://localhost:3000/api/orders
                 [PAGE] Confirmation | http://localhost:3000/order/12345
                 [LOADED]

Agent B knows:   Agent A completed the checkout flow. The order API returned
                 successfully. The confirmation page loaded. No errors.
```

With the `full` tier, Agent B sees Agent A's dispatched input events through the binding bridge. This is a built-in feedback loop: Agent A acts on one CDP connection, Agent B's monitor on another connection reports both the interactions and their consequences. Agent B can verify the complete workflow without any coordination protocol -- it simply watches.

### Pattern 5: Error-triggered investigation

The agent works on code while the monitor watches the browser. When an error appears, the agent investigates.

```
Agent:           (editing source code)
Monitor reports: [EXCEPTION] TypeError: Cannot read properties of null at app.js:42

Agent responds:  "I see an unhandled TypeError at app.js line 42. Let me check."
Agent runs:      chrome-agent Runtime.evaluate '{"expression": "..."}'
Agent runs:      chrome-agent Page.captureScreenshot '{"format": "png"}'
Agent:           (reads the code at line 42, identifies the fix, edits the file)

Monitor reports: [PAGE] My App | http://localhost:3000  (hot reload)
                 [LOADED]
                 (no more errors)

Agent:           "The error is fixed. The page reloaded cleanly."
```

## Push vs Pull

The monitor provides push (events arrive when they happen). One-shot commands provide pull (the agent asks for information when it wants it).

| Need | Channel | Why |
|------|---------|-----|
| Did the page navigate? | Push (monitor) | You don't know when it will happen |
| What URL am I on? | Pull (one-shot) | Instant answer |
| Did an error occur? | Push (monitor) | Errors are unpredictable |
| What does the page look like? | Pull (screenshot) | Snapshots are point-in-time |
| What text is on the page? | Pull (Runtime.evaluate) | DOM state is a snapshot |
| Is the page loaded? | Push (monitor: [LOADED]) | Timing matters |
| Did the API call succeed? | Push (monitor: [XHR]) | You need to know when |
| What did the human click? | Push (monitor: [CLICK], full tier) | You need to know when |

**Heuristic:** If you need to know **when** something happens, use push. If you need to know **what** something is, use pull.

## Starting the Monitor

The agent invokes the Monitor tool in the conversation. The tool takes a shell command, a description, and a persistence setting. Here is what the tool invocation looks like:

For session-length observation:

```
Monitor tool:
  command:     "uv run python scripts/observe.py --tier dev"
  description: "Browser observer (navigation + errors)"
  persistent:  true
```

For time-bounded observation (e.g., watching a specific test run):

```
Monitor tool:
  command:     "uv run python scripts/observe.py --tier dev"
  description: "Watching test run"
  timeout_ms:  300000  (5 minutes)
  persistent:  false
```

The agent receives each stdout line from the observer script as a real-time notification in the conversation. To stop the monitor, use the TaskStop tool with the monitor's task ID.

## Handoff

The agent can switch from observing to acting without stopping the monitor. It simply starts sending commands via one-shot calls or a CDPClient script. The monitor continues running on its own CDP connection, now reporting the consequences of the agent's actions alongside any human activity.

To fully stop observing: use TaskStop with the monitor's task ID. Then the agent operates through action commands only.

## Troubleshooting

**Monitor auto-stops:** The page is generating too many events. Switch to a lower tier (`nav` instead of `dev`). The rate limiter handles most cases, but if `[SUPPRESSED]` lines themselves are too frequent, reduce `max_events` in the observer script.

**No events appearing:** Check that the browser is running (`chrome-agent status`). Check the port matches (`--port`). The observer prints `[OBSERVE] tier=dev port=9222` on startup -- if you don't see this, the script failed to connect. Most common cause: the browser wasn't launched yet. Launch first, then start the observer.

**Events appear delayed:** Ensure all `print()` calls use `flush=True`. The observer script does this. If you write a custom script, every print must flush.

**Binding bridge doesn't work after navigation:** The `full` tier uses `Page.addScriptToEvaluateOnNewDocument` to persist listeners across navigations. If the monitor's CDP connection drops and reconnects, the document script registration is lost. Restart the monitor.
