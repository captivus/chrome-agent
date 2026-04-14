# Raw WebSocket CDP Client

**Script:** `./02-raw-websocket-client.py`

## The Question

Experiment 01 showed that Playwright's CDPSession provides full CDP access in attach mode, but it also exposed an uncomfortable dependency: Playwright's entire installation footprint for what amounts to a `send()`/`on()` wrapper over a WebSocket. The question for this experiment was: how hard is it to build a minimal CDP client directly on WebSockets, with no Playwright dependency at all? Specifically:

- Can we connect directly to Chrome's CDP WebSocket endpoint?
- How much code does a functional CDP client require?
- Can it handle both command-response correlation and event subscriptions?
- Is the latency comparable to or better than the Playwright path?

## What the Script Does

The script implements a `MinimalCDPClient` class (~30 lines of core logic) that connects to Chrome's CDP WebSocket endpoint using the `websockets` library. The class provides three methods:

- **`connect()`** -- opens the WebSocket and starts a background receive loop.
- **`send(method, params)`** -- assigns a monotonically increasing message ID, sends JSON over the WebSocket, and returns a `Future` that resolves when Chrome's response (matched by ID) arrives.
- **`on(event, callback)`** -- registers callbacks for CDP events, dispatched by the receive loop when unsolicited messages arrive.

A helper function `get_ws_url()` demonstrates target discovery -- hitting Chrome's `/json` or `/json/version` HTTP endpoints to obtain the WebSocket debugger URL for either a page target or the browser target.

The script then runs five tests using this client:

1. **Navigation** -- sends `Page.navigate` with a URL and measures latency.
2. **Screenshot** -- sends `Page.captureScreenshot` and writes the decoded PNG to disk.
3. **Screencast** -- starts screencast, triggers visual changes via `Runtime.evaluate` (changing background color), collects and ACKs frames.
4. **Performance metrics** -- enables the Performance domain and retrieves metrics.
5. **JavaScript evaluation** -- sends `Runtime.evaluate` to read `document.title` and measures round-trip time.

## Observations

All five tests passed. Key findings:

- **The client is trivially small.** The entire `MinimalCDPClient` class is ~40 lines including error handling. The protocol is straightforward JSON-over-WebSocket with integer ID correlation for request-response and a `method` field for events.
- **No Playwright needed.** Every capability tested in Experiment 01 via Playwright's CDPSession worked identically via raw WebSocket -- navigation, screenshots, screencast, performance metrics, JS evaluation.
- **Target discovery is simple.** Chrome exposes `/json` (list of page targets with their WebSocket URLs) and `/json/version` (browser-level WebSocket URL) as plain HTTP endpoints. No special handshake is needed.
- **Latency was comparable or better.** Without Playwright's abstraction layer in the path, command round-trips went directly to Chrome. Screenshot and JS evaluation timings were in line with or faster than the Playwright CDPSession path from Experiment 01.
- **The `max_size` parameter matters.** Screenshots and screencast frames can be large (multi-megabyte base64-encoded images). The WebSocket connection needs `max_size=50MB` or similar to avoid truncation errors on large payloads.

## Conclusions

**A raw WebSocket CDP client is viable and preferable for chrome-agent's use case.** The implementation is minimal, the protocol is well-structured for async Python, and eliminating Playwright removes a heavy dependency that provided no value beyond what 40 lines of WebSocket code can do.

This experiment directly informed the CDP-01 specification:

- **Architecture decision:** chrome-agent's foundation is a raw WebSocket CDP client, not a Playwright wrapper. Playwright remains available as an optional integration but is not required.
- **`MinimalCDPClient` as prototype:** The class structure from this experiment -- `connect()`, `send()`, `on()`, background receive loop with ID correlation -- became the skeleton for the production `CDPClient` class specified in CDP-01.
- **Target discovery pattern:** The `get_ws_url()` helper demonstrated the two-endpoint pattern (page vs. browser targets) that the spec captures in its connection logic.
- **Message size configuration:** The `max_size=50MB` setting for the WebSocket connection was carried into the spec based on the screenshot payload sizes observed here.

## Cross-References

- **Experiment 01** (`01-playwright-cdp-session.md`) -- the predecessor that motivated this experiment by showing CDPSession works but comes with unnecessary dependency weight
- **CDP-01 spec** (`CDP-01-cdp-websocket-client.md`) -- the specification that codifies this experiment's findings into a production design
