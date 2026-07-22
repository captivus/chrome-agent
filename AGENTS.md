# chrome-agent

Drive a real Chrome through the Chrome DevTools Protocol (CDP), from the terminal, for AI agents.

Install: `uv tool install chrome-agent` (or `pip install chrome-agent`). Requires Google Chrome or Chromium. One runtime dependency (`websockets`); no Playwright, no browser downloads.

## What it is

Address a Chrome **instance by name**, and send it **any CDP command** or **stream any CDP event**. Two channels:

- **One-shot** (`chrome-agent <inst> Domain.method '{json}'`) — act: send one command, print the result, disconnect (~70 ms).
- **Attach** (`chrome-agent attach <inst> +Event …`) — observe: hold a connection and stream events as JSON lines.

**The full protocol, tracked live.** chrome-agent forwards your `Domain.method` straight to Chrome — nothing is validated against a bundled schema. Any command, event, or domain your installed Chrome supports works, **including protocol surface newer than this build** (e.g. `CrashReportContext` isn't among the bundled bindings, yet `chrome-agent <inst> CrashReportContext.getEntries` returns a normal result over the CLI). So **`help <inst> [Domain[.method]]`, read live from the browser, is the authoritative, version-correct reference** — prefer it over any static list. The typed Python classes are a point-in-time snapshot, not a gate.

**`experimental` ≠ unstable.** Most of the live protocol is flagged experimental (domains carry the flag and their members inherit it), and it's tempting to avoid it — don't. Experimental items break at roughly the same rate as the stable core; what predicts churn is how actively a *domain* is developed, and CDP's busiest domains (Network, Runtime, Page, DOM) are stable-status. The one real experimental signal is **removal/rename**, and even that is rare. Practical posture: **use whatever capability you need regardless of flag; pin the Chrome version you test against; re-verify signatures via `help` on upgrade.**

## Operating a page: sense ⇄ act

An agent does two things in a loop: it **senses** the page and it **acts** on it. **Sensing is the default, continuous mode; acting is the intermittent intervention.** After you act you're sensing again — and that perception is both your confirmation of the act *and* your orientation for the next one. There is no separate "verify" step; **the next sense is the verification.**

**Sense — two channels.** Match the channel to the question:

- **See what the page *says*** — `DOM`, `Accessibility`, `CSS`, `DOMSnapshot`. Structured reads are the primary, high-fidelity channel for content/structure/state. Use a **screenshot** (`Page.captureScreenshot`) for what the page *looks like* — layout, an image, a CAPTCHA; it is the *last resort* for reading content (pixels are lossy, OCR-like).
- **Hear what the page *reports*** — `Network` (what it fetched: requests, responses, bodies), `Runtime` (console output, uncaught exceptions), `Log`, `Audits`.

**Act — trusted operation.** `Input` (mouse/keyboard/touch/gesture events Chrome marks **trusted**), `Page` (navigate, reload, dialogs), `Runtime` (`evaluate`, `callFunctionOn`).

**The discipline:** sense across **more than one channel**, and **never trust an act's return value — trust the next sense.** An action that "succeeded" with no error can still have done nothing; only an observed effect proves it. For an irreversible action (send/submit), the cleanest observed effect is the action surface *disappearing* from the DOM (the compose pane gone), not the button's return. Screenshot before asserting a page "is empty / requires login / is broken." Derive identifiers from data (DOM/state), not from pixels.

**Sense page-readiness before you act.** After `Page.navigate`, wait on an observable condition — `attach +Page.loadEventFired`, or poll `document.readyState === "complete"` (or the target element) via `Runtime.evaluate` in a short retry loop — not a fixed sleep; acting on a half-loaded page reads stale state. Minimal poll: `chrome-agent mysite-01 Runtime.evaluate '{"expression":"document.readyState","returnByValue":true}'` until it returns `"complete"`.

**Most work is sense-dominant.** Four ways to engage a page — only one of them acts:

- **Drive the UI** — locate → act → sense (below).
- **Read what it already loaded** — the DOM, and (when the framework exposes it) its in-memory state, which is more authoritative than the painted DOM.
- **Be the authenticated client** — `Runtime.evaluate` running `fetch()` *inside* the logged-in page inherits its session; call same-origin APIs with zero credential handling.
- **Observe** — `attach` and watch `Network`/`Page`/console events.

### Acting trustworthily

**Two ways to "click," not interchangeable.** A synthetic `element.click()` (via `Runtime.evaluate`) is fabricated in page JS. A trusted `Input.dispatchMouseEvent` enters Chrome's native pipeline at the compositor and reaches what synthetic clicks can't: cross-origin iframes, capture-phase-intercepted overlays, shadow-DOM overlays, UIs that gate on event trust. **Escalation rule:** when a synthetic click *silently no-ops*, escalate to real `Input` events — don't debug selectors or the DOM. Don't over-escalate; plain `click()` is fine on ordinary UIs.

**The drive-the-UI loop (the tactile special case of sense ⇄ act):**

```bash
# Sense -- locate: center coords (use the OUTER element; inner nodes can return {0,0,0,0})
chrome-agent mysite-01 Runtime.evaluate '{"expression":"(()=>{const r=document.querySelector(\"#submit\").getBoundingClientRect();return{x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)};})()","returnByValue":true}'
# Act -- a real click is press + release (trusted)
chrome-agent mysite-01 Input.dispatchMouseEvent '{"type":"mousePressed","x":400,"y":300,"button":"left","clickCount":1}'
chrome-agent mysite-01 Input.dispatchMouseEvent '{"type":"mouseReleased","x":400,"y":300,"button":"left","clickCount":1}'
# Sense again -- confirm via an independent channel
chrome-agent mysite-01 Runtime.evaluate '{"expression":"document.querySelector(\"#result\").textContent","returnByValue":true}'
```

Typing: `Input.insertText '{"text":"..."}'`, `Input.dispatchKeyEvent` (`keyDown`/`keyUp`). React-controlled inputs need the native setter so React sees the change:

```bash
chrome-agent mysite-01 Runtime.evaluate '{"expression":"(()=>{const el=document.querySelector(\"#email\");const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,\"value\").set;set.call(el,\"a@b.com\");el.dispatchEvent(new Event(\"input\",{bubbles:true}));})()"}'
```

## Beyond driving the UI

Often you shouldn't click through the UI at all — these compose standard CDP/JS through the one-shot or attach channel (verify the one you need against your target):

- **Authenticated HTTP client.** `Runtime.evaluate` running `fetch()` *inside* the logged-in page inherits its session — same-origin API calls, zero credential handling. Pass **`awaitPromise:true`** (wait for the promise) and **`returnByValue:true`** (get the JSON, not a handle); without `awaitPromise` it returns before the data resolves.
- **API discovery.** `performance.getEntriesByType("resource")` recovers the backend endpoints the page already called — post-hoc, no live `Network` subscription. After 2–3 guessed endpoints 404, stop guessing and **observe one real request** via `attach +Network.responseReceived` (authoritative filename is in `content-disposition`).
- **Cookie handoff for bulk.** `Network.getCookies '{"urls":["https://host/"]}'` extracts the session into a `Cookie:` header so a faster external client (`curl`) can fan out a large transfer outside the CDP channel.
- **File upload without a dialog.** `DOM.setFileInputFiles` sets file paths on a `<input type=file>` with no OS picker. Identify the input by **`backendNodeId`** — the stable node handle that survives across one-shot calls (`nodeId`/`objectId` go stale between calls).
- **Reach into shadow DOM / cross-origin iframes.** `DOM.getDocument '{"depth":-1,"pierce":true}'` traverses shadow roots and iframes a main-frame `querySelector` can't see; `DOM.getNodeForLocation '{"x":…,"y":…,"includeUserAgentShadowDOM":true}'` returns the node under a coordinate. Trusted `Input` coordinates are **viewport-relative** — Chrome routes the event to whatever target is under them, *including inside a cross-origin iframe*, with no iframe-relative math.
- **Exact-size PDF.** `Page.printToPDF` with explicit `paperWidth`/`paperHeight` (inches) + zero margins + `printBackground:true` (the `--print-to-pdf` CLI flag ignores `@page` size and emits US Letter).

## The two channels (mechanics)

```bash
# Observe: hold a connection, stream subscribed events as JSON lines. Run it in the background.
chrome-agent attach mysite-01 +Page.loadEventFired +Network.requestWillBeSent > /tmp/events.jsonl &
chrome-agent mysite-01 Page.navigate '{"url":"https://example.com"}'
cat /tmp/events.jsonl
```

The attach stream is one JSON object per line — a ready line, then one per event:

```jsonl
{"status": "ready", "sessionId": "C0BEA5F2...", "target": "D71C0575..."}
{"method": "Network.requestWillBeSent", "params": { ... }}
{"method": "Page.loadEventFired", "params": {"timestamp": 27222.68}}
```

Each attach session has **isolated subscriptions** (others don't see yours); add/remove mid-session via stdin (`+Event`/`-Event`). One-shots **can't intercept `Network`** (they detach immediately) — use `attach`, or the Python API, for anything needing a persistent session. CDP observes **consequences** (navigations, network), not **causes** (clicks, scroll, keystrokes). If only one instance is live, the name can be omitted.

## Commands and what they return

Output is JSON on stdout. A one-shot prints the CDP method's **raw result object**, pretty-printed (shapes differ by method — check, don't assume). `launch`/`status` print structured JSON when stdout isn't a TTY. Errors go to **stderr** and exit non-zero, and are self-describing (an unknown instance lists the available ones; a CDP protocol error prints `CDP error <code>: <message>`).

```bash
chrome-agent launch [--port PORT] [--headless] [--fingerprint profile.json] [--no-window-border]
chrome-agent status [<instance>]
chrome-agent attach <instance> [+Event ...] [--target SPEC] [--url SUBSTRING]
chrome-agent stop <instance> [--target SPEC] [--url SUBSTRING]
chrome-agent help [<instance>] [Domain | Domain.method]
chrome-agent cleanup
chrome-agent --version
chrome-agent <instance> Domain.method '{"param": "value"}'
```

- `launch` → `{"name","port","pid","browser_version"}`
- `status` → `[{"name","port","alive","targets":[{"id","full_id","index","url","title"}]}]` — `index` is what `--target N` selects
- `Page.navigate` → `{"frameId","loaderId","isDownload"}`
- `Runtime.evaluate` (`returnByValue:true`) → `{"result":{"type":"string","value":"..."}}` — read **`result.value`** (the value sits under the `result` key)
- `Page.captureScreenshot` → `{"data":"<base64 png>"}` — bytes are at `data`, **not** `result.data`; decode with `… | python3 -c "import sys,json,base64; open('/tmp/s.png','wb').write(base64.b64decode(json.load(sys.stdin)['data']))"` — then view `/tmp/s.png` to actually see the render.

## Targeting tabs

```bash
chrome-agent mysite-01 --target 2 Page.navigate '{"url":"..."}'   # 1-based index
chrome-agent mysite-01 --target 956FD3C2 Runtime.evaluate '{...}' # target-id prefix
chrome-agent mysite-01 --url example.com Runtime.evaluate '{...}' # url substring
```

A one-shot against multiple tabs without a specifier is an error that lists them. **Index gotcha:** `--target N` indices are sorted by stable target id, **not** tab creation/visual order — opening a tab can renumber the others. Prefer `--url` or an id prefix for stability.

## Managing instances

```bash
chrome-agent launch                       # auto port + name (from cwd); isolated profile under /tmp/chrome-agent
chrome-agent launch --headless            # no window (no border, no desktop pinning)
chrome-agent launch --fingerprint p.json  # spoof UA/viewport/lang/TZ via launch flags (also suppresses the marker)
chrome-agent launch -- --some-chrome-flag # everything after -- passes through to Chrome
chrome-agent status                       # all instances + their tabs
chrome-agent stop mysite-01 [--target 2 | --url foo]   # whole browser, or one tab
chrome-agent cleanup                      # drop dead instances + stale session dirs
```

**Instances outlive your task — stopping them is part of the workflow, not optional cleanup.** A launched instance is a full Chrome process that keeps running (and accumulating memory) until stopped. When you're done with an instance you launched: `chrome-agent stop <instance>`, then **verify with `chrome-agent status`** that the instances you started are gone — the stop's return is not the verification; the status read is. If dead instances or stale session dirs linger, `chrome-agent cleanup`. Keep an instance alive only deliberately (e.g. its login session is wanted for later work) — never by omission.

Headed launches are marked (colored border + `🤖 <instance>` title prefix) so a human can tell an agent-driven window from their own; `--no-window-border` disables it. Closing a headed window **auto-retires** its instance from the registry in real time (a transient CDP drop does not); `status` is real-time truth (port-based liveness). On Linux/X11 the window is pinned to the launching terminal's desktop (needs `xdotool`).

**Fingerprint** spoofs user agent, viewport, language, and timezone via Chrome launch flags (no JS injection). It deliberately does **not** patch `navigator.webdriver`/`window.chrome` — an empirical audit (bot.sannysoft.com / CreepJS) found those overrides make Chrome *more* detectable, not less. WebRTC can still leak the real public IP via STUN regardless. Schema + audit: see the README.

## Gotchas

- **Navigation kills context.** A pending `Runtime.evaluate` errors with "context destroyed" when the page navigates. Retry on the new page.
- **One-shot latency** ~70 ms (process startup). For tight loops or event capture, prefer `attach` / a Python driver.
- **Event isolation.** Each `attach` session sees only its own subscriptions.
- **Multiple live instances** disable name auto-selection for **bare one-shot methods** — they error, asking you to specify one. `help` is the exception: it auto-picks any live instance (the protocol schema is identical across them), so it never needs naming.

## Further reading

- [README](README.md) — fingerprint schema, window-border internals, full feature set
- [docs/collaboration-guide.md](docs/collaboration-guide.md) — multi-agent + human-agent workflows, the binding bridge
- [docs/monitor-integration.md](docs/monitor-integration.md) — Claude Code Monitor integration
- **Python API:** `from chrome_agent.cdp_client import CDPClient, get_ws_url` + the generated typed domain classes (`chrome_agent.domains.*`), for driving CDP in-process; `CDPClient.send(method=..., params=...)` reaches any method, bindings or not.
