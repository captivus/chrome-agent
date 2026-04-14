# Playwright CDPSession in Attach Mode

**Script:** `./01-playwright-cdp-session.py`

## The Question

chrome-agent connects to an already-running Chrome instance via `connect_over_cdp`. Playwright exposes a `CDPSession` object that lets you send raw CDP commands alongside Playwright's own high-level API. Before committing to any architecture, we needed to answer: does `CDPSession` actually work in attach mode, and can it access the full breadth of CDP -- including domains Playwright doesn't wrap (screencast, performance metrics, network interception at the protocol level)?

A secondary question was latency. If raw CDP commands through Playwright's `CDPSession` add meaningful overhead compared to Playwright's own methods, that would matter for the real-time observation use case.

## What the Script Does

The script connects to Chrome on `localhost:9222` using Playwright's `connect_over_cdp`, obtains the first page from the existing browser context, and then creates a `CDPSession` from that page. It runs five tests:

1. **CDPSession creation** -- calls `page.context.new_cdp_session(page)` to verify this works in attach mode (not just launch mode).
2. **Raw `Page.captureScreenshot` vs Playwright's `page.screenshot()`** -- sends the CDP command directly through the session and compares timing against Playwright's built-in method.
3. **`Page.startScreencast`** -- enables screencast frame streaming, triggers visual changes via scrolling, collects frames, and ACKs each one. This is a CDP-only feature with no Playwright equivalent.
4. **`Performance.getMetrics`** -- enables the Performance domain and retrieves browser performance counters. Another CDP-only domain.
5. **`Network.enable` + event capture** -- enables the Network domain, navigates to trigger requests, and captures `Network.requestWillBeSent` events via callback registration.

## Observations

All five tests passed:

- `CDPSession` creation works in attach mode without issues.
- `Page.captureScreenshot` via CDP returned valid PNG image data. Latency was comparable to Playwright's own screenshot method -- no significant overhead from the CDPSession wrapper.
- Screencast frames were received and ACKed successfully. The event subscription model (`cdp.on("Page.screencastFrame", callback)`) works as expected.
- `Performance.getMetrics` returned the full set of Chrome performance counters (Documents, Nodes, JSEventListeners, LayoutCount, etc.).
- Network domain events were captured via the CDPSession callback mechanism.

## Conclusions

**Playwright's CDPSession works in attach mode and provides full CDP access.** There is no domain restriction -- anything available over the raw protocol is accessible through `cdp.send(method, params)`.

However, this experiment also revealed the cost of using CDPSession: it requires Playwright as a dependency. Playwright brings a large installation footprint (browser binaries, platform-specific drivers) even though chrome-agent never uses Playwright to launch browsers. The CDPSession API is also a thin wrapper -- it provides `send()` and `on()`, which is essentially what a raw WebSocket client provides. This raised the question: if we only need `send()` and `on()`, do we need Playwright at all?

This directly motivated **Experiment 02** -- building a raw WebSocket CDP client to see if the Playwright dependency could be eliminated entirely.

## Cross-References

- **Experiment 02** (`02-raw-websocket-client.md`) -- the follow-up that tested a Playwright-free approach
- **CDP-01 spec** (`CDP-01-cdp-websocket-client.md`) -- the resulting specification for the raw WebSocket client that became chrome-agent's foundation
