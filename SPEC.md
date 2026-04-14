> **RETIRED** -- This document was the working draft created during initial design exploration. The authoritative planning artifacts are now in `planning/`:
> - Master Project Specification: `planning/01-master-project-specification.md`
> - Feature Inventory: `planning/02-feature-inventory.md`
> - Feature Specifications: `planning/03-specs/`
>
> This file is preserved as a historical record of the design process.

# chrome-agent: Specification (Historical)

## What chrome-agent is

chrome-agent is two things:

1. **A Python implementation of the Chrome DevTools Protocol.** It exposes the full CDP surface -- every command, every event, every type across all domains. An agent or developer using chrome-agent has access to everything Chrome can do through its debugging protocol. No capabilities are filtered, curated, or abstracted away.

2. **A collaborative browser control model.** chrome-agent can launch a browser or attach to a running one. Multiple agents, or a human and an agent, can share the same browser session. This attach/collaborate mode is the novel value that chrome-agent provides beyond being a CDP implementation.

## Why this matters

AI agents need full browser control. Current tools either expose a curated subset of browser capabilities (limiting what agents can do) or require heavy dependencies that bundle their own browser engines. chrome-agent takes a different approach: implement the protocol directly, expose it completely, and let the agent compose operations from the protocol primitives.

## Architecture

### Layer 1: CDP Client

A WebSocket-based client that can send any CDP command and subscribe to any CDP event. This is the foundation -- built on the `websockets` library.

The client provides:
- `send(method, params)` -- send a command, await the response
- `on(event, callback)` -- subscribe to an event
- Connection management (connect to page or browser targets)
- Error handling (CDP error codes, connection failures, WebSocket disconnection)
- Proper async lifecycle (`async with` context manager)
- Connection resilience (error propagation from the receive loop, clean shutdown)

The client must handle protocol mechanics that vary across domains:
- **Session multiplexing**: `Target.attachToTarget` returns a `sessionId` that must be included in subsequent messages for that target. This is how you interact with iframes, service workers, or specific tabs from a single WebSocket connection.
- **Error codes**: CDP errors are structured (`{code, message}`) and must be propagated as exceptions, not silently dropped.
- **Binary data**: Some commands (e.g., `IO.read`) return binary data that needs appropriate handling.

### Layer 2: Protocol Coverage

The Chrome DevTools Protocol defines 50 domains with approximately 518 commands and events. chrome-agent supports all of them through the generic `send()` interface. The protocol definition is the specification -- if CDP defines it, chrome-agent can call it.

The 50 domains span:

| Category | Domains | Examples |
|---|---|---|
| Page & Navigation | Page, Target | Navigate, lifecycle events, screencast, dialogs |
| DOM & Content | DOM, DOMSnapshot, CSS, Accessibility | Element operations, snapshots, styles, AX tree |
| Input | Input | Mouse, keyboard, touch, drag events |
| JavaScript | Runtime | Evaluate, await promises, object inspection |
| Network | Network, Fetch | Request/response capture, interception, throttling |
| Performance | Performance, Tracing, PerformanceTimeline | Metrics, traces, profiling |
| Emulation | Emulation, DeviceOrientation | Viewport, device, geolocation, timezone |
| Storage | Storage, DOMStorage, IndexedDB, CacheStorage | Cookies, localStorage, databases |
| Media | Media, WebAudio | Media inspection, audio graphs |
| Browser | Browser, SystemInfo, Log | Window management, system info, console logs |
| Overlay | Overlay | Visual highlighting, debug overlays |
| Security | Security | Certificate and security state |
| Workers | ServiceWorker, BackgroundService | Service worker management |
| Debugging | DOMDebugger, EventBreakpoints, Inspector | Breakpoints, inspection |
| Auth & Identity | WebAuthn, FedCm, Autofill | Authentication, credentials |
| Device Emulation | BluetoothEmulation, SmartCardEmulation | Hardware emulation |
| Other | PWA, Cast, Extensions, IO, LayerTree, Memory, Preload, Tethering, WebMCP, DeviceAccess, FileSystem, HeadlessExperimental, CrashReportContext | Specialized capabilities |

### Protocol Versioning

CDP has stable and experimental domains. Experimental commands can change without notice between Chrome releases (e.g., `Page.startScreencast` is experimental). chrome-agent does not pin to a Chrome version -- it is a protocol client, not a browser. The generic `send()` interface works regardless of protocol version. If a command exists in the connected browser, chrome-agent can call it.

### Layer 3: Connection & Browser Management

#### Targets

CDP exposes multiple target types, each with its own WebSocket endpoint:

- **Page targets** (`/devtools/page/...`) -- for Page, DOM, Input, Runtime, and most other domains
- **Browser targets** (`/devtools/browser/...`) -- for Target, Browser, and browser-level operations
- **Service worker targets**, **iframe targets**, etc. -- accessible via `Target.attachToTarget` with session multiplexing

The `/json` endpoint returns a snapshot of available targets. For tracking target lifecycle (pages opening and closing, `window.open`, `target=_blank`), clients subscribe to `Target.targetCreated` and `Target.targetDestroyed` events on the browser target.

#### Operational Modes

**Launch mode**: Start a Chrome browser with `--remote-debugging-port`, managing the process lifecycle. This requires:
- **Browser binary discovery**: Locating Chrome/Chromium on the system. This is platform-specific (Linux, macOS, Windows paths differ).
- **Process lifecycle management**: Starting Chrome via `subprocess`, monitoring the process, clean shutdown.
- **Fingerprint profiles**: Anti-detection configuration via `Page.addScriptToEvaluateOnNewDocument` and launch flags.
- **Window management**: Platform-specific (X11 on Linux, etc.).

**Attach mode**: Connect to an already-running browser on a CDP port. Multiple clients can attach simultaneously.

#### Multi-Client Behavior

CDP natively supports multiple simultaneous WebSocket connections to the same page target. Each connection operates independently. The protocol behavior, verified experimentally (experiment 7):

- **Events fan out**: All connected clients receive events for domains they have enabled. In testing, two clients received identical lifecycle events in the same order.
- **Commands execute independently**: Any client can send any command at any time. Both clients can enable the same domains (e.g., `DOM.enable`) without conflict.
- **State is shared**: Mutations from one client (navigation, DOM changes, emulation settings) are visible to all clients immediately.
- **Navigation affects all clients**: When one client navigates, other clients' pending operations on the old page fail with a clean error ("Inspected target navigated or closed"). Both clients remain functional after the disruption.
- **No built-in coordination**: CDP provides no locking or conflict resolution between clients. This is the standard behavior of any shared mutable resource.

chrome-agent does not impose a coordination model. The application using chrome-agent decides how its agents coordinate, based on the collaboration patterns relevant to its use case.

### Layer 4: CLI Interface

The CLI has three modes of operation:

#### One-shot commands

For operational tasks that don't require session persistence:

```
chrome-agent launch [--port 9222] [--fingerprint profile.json] [--headless]
chrome-agent status [--port 9222]
```

#### Protocol discovery

The `help` command queries the connected browser's `/json/protocol` endpoint, which serves the complete protocol schema for that browser version -- every domain, command, event, parameter, return type, and description.

```
chrome-agent help                    # list all domains with descriptions
chrome-agent help Page               # list all commands and events in the Page domain
chrome-agent help Page.navigate      # show parameters, return types, and description
```

This means discoverability is always accurate for the connected browser. If Chrome adds a new command, `chrome-agent help` reflects it immediately without a chrome-agent release. No PDL files need to be shipped, no documentation needs to be generated at build time.

The `help` command works without a session -- it makes a single HTTP request to the browser's `/json/protocol` endpoint and exits.

#### Session mode

For CDP protocol interaction. The `session` command starts a persistent process that maintains a WebSocket connection to the browser. Communication is line-based over stdin/stdout:

```
chrome-agent session [--port 9222]
```

**Sending commands**: Write a line to stdin -- method name, space, optional JSON params:
```
Page.navigate {"url": "https://example.com"}
```

**Receiving responses**: Read a JSON line from stdout:
```
{"frameId": "ABC123", "loaderId": "DEF456"}
```

**Subscribing to events**: Write a line prefixed with `+`:
```
+Network.requestWillBeSent
```

**Receiving events**: Events arrive on stdout prefixed with `!`:
```
!Network.requestWillBeSent {"requestId": "1", "request": {"url": "..."}}
```

**Ending the session**: Close stdin. The process exits, the WebSocket closes.

The session process lives exactly as long as the caller needs it. No daemon to manage, no socket files to clean up. An agent starts a session when it needs to do browser work and closes it when it's done.

**Performance**: Per-command latency in session mode is ~0.5ms for lightweight commands (vs ~350ms per CLI invocation in one-shot mode). This is the difference between a 7-step operation taking 10ms vs 2.5 seconds.

#### Collaborative use

Multiple sessions can connect to the same browser simultaneously. Each session opens its own WebSocket connection:

```
Agent A starts:   chrome-agent session --port 9222   -> WebSocket #1
Agent B starts:   chrome-agent session --port 9222   -> WebSocket #2
Human has DevTools open                              -> WebSocket #3
```

Chrome handles the multiplexing natively. Each client sends commands and receives events independently. There is no chrome-agent-level coordination -- applications decide how their agents share the browser.

#### CLI command format

The CLI uses the CDP method name as the command. If the first argument contains a dot, it is a raw CDP method:

```
chrome-agent Page.navigate '{"url": "https://example.com"}'
chrome-agent Page.captureScreenshot '{"format": "png"}'
chrome-agent Runtime.evaluate '{"expression": "document.title", "returnByValue": true}'
```

This is the one-shot mode -- each invocation creates a new connection, sends one command, prints the result, and exits. It is convenient for single operations but incurs ~350ms of overhead per call. For multi-step workflows, use session mode.

The operational commands (`launch`, `status`, `session`, `help`) are the only non-CDP commands. Everything else is a CDP method call.

## What we are replacing and why

The current implementation uses Playwright as an abstraction layer over CDP. We are replacing it with a direct CDP implementation because:

1. **Playwright limits protocol access.** It exposes a curated subset of CDP. Features like screencast, tracing, performance metrics, network interception at the protocol level, and dozens of other domains are inaccessible through Playwright's API.

2. **The interaction layer is buildable from CDP primitives.** Experiments proved that click, fill, type, scroll, and wait operations can be composed from CDP primitives. CDP natively provides `DOM.scrollIntoViewIfNeeded`, `DOM.getBoxModel`, `DOM.getNodeForLocation` (hit testing), `DOM.focus`, `Input.dispatchMouseEvent`, `Input.insertText`, and `Runtime.evaluate` with `awaitPromise` for MutationObserver-based waiting. The happy-path implementation is approximately 120 lines; production quality will be larger to handle edge cases (iframes, shadow DOM, animation settling, stale node references).

3. **The dependency cost is disproportionate.** Playwright brings a Node.js subprocess, a bundled Chromium binary (~200MB), and significant install weight. chrome-agent needs only the `websockets` library.

4. **AI agents can compose CDP commands directly.** Experiments with four independent agents showed that given CDP documentation (PDL files), agents successfully compose multi-step operations across DOM, Input, Network, Accessibility, Performance, Emulation, and Page domains -- without pre-built abstractions or guidance on composition patterns. Token cost is equivalent to using pre-built CLI commands (~17-18K tokens for a 7-step form interaction task).

5. **Convenience commands are unnecessary.** The current CLI exposes curated commands (`click`, `fill`, `screenshot`, etc.) that compose multiple CDP calls. These are being removed. The CDP protocol methods are the interface. Agents compose operations directly from protocol primitives, which gives them full flexibility without limiting them to pre-built abstractions.

## The Protocol Definition Language (PDL)

Google defines the CDP protocol using Protocol Definition Language files. These are machine-readable, fully typed specifications of every command, event, parameter, return type, and enumeration. The PDL files serve as:

- **The specification** for chrome-agent's protocol coverage
- **The source of truth** for the test suite
- **A potential input** for code generation of typed Python bindings

Each PDL domain defines three constructs:
- **Commands** -- request-response operations (send parameters, get a result)
- **Events** -- subscription-based notifications (enable a domain, receive callbacks)
- **Types** -- data structures (the shapes of objects that commands and events use)

The PDL files live in the Chrome DevTools Protocol repository and are updated with each Chrome release.

## Test Strategy

### Principle: The PDL implies the test suite

The protocol definition is the specification. The test suite is derived from the specification.

### Protocol-level tests

Two levels of rigor, driven by what's practical:

**Core domains** (Page, DOM, Input, Runtime, Network, Accessibility, Performance, Emulation, Fetch, Target, CSS, Log, DOMSnapshot, Overlay, Browser -- approximately 15 domains): Full test coverage. For each command: send with valid parameters, verify the response matches the PDL's return type, test parameter variations, test error cases. For each event: enable the domain, trigger the condition, verify the event arrives. This produces approximately 100-150 tests.

**Remaining domains** (~35 domains): Smoke tests. Verify the domain can be enabled and basic commands execute without error. Many of these domains require specific browser state to test meaningfully (ServiceWorker needs a registered SW, WebAuthn needs a virtual authenticator, BluetoothEmulation is platform-specific). Full test infrastructure for every domain is not justified upfront -- it should be built as the domains are used.

### Behavioral tests

Higher-level tests that verify composed operations work correctly:
- Click works on visible, off-screen (auto-scroll), and obscured elements
- Fill replaces existing values, works on text/password/textarea/contenteditable
- Navigation triggers lifecycle events, back/forward works, click-triggered navigation
- Waiting detects dynamically inserted elements, visibility changes, timeouts
- Screencast captures frames, acknowledges them, stops cleanly
- Network capture correlates requests, responses, and completion events
- Emulation changes viewport, device metrics, resets cleanly

### Session and multi-client tests

- Session mode maintains a persistent connection across multiple commands
- Multiple sessions can connect to the same browser simultaneously
- Events fan out to all connected sessions
- Mutations from one session are visible to others
- Navigation by one session produces clean errors (not hangs) in others

### Test infrastructure

- Tests run against a real browser with CDP enabled (not mocked)
- Test fixture pages cover edge cases (hidden elements, overlays, delayed insertion, scroll targets, forms)
- Tests are implementation-agnostic -- they test behavior through the CDP client, not internal APIs

## Migration Plan

The migration from Playwright to direct CDP is incremental.

### Phase 1: CDP client as standalone module

Build the production-quality CDP client alongside the existing Playwright code. The client is a new module with no dependency on Playwright. It can be tested independently against a manually-launched browser. The `websockets` library is added as a dependency alongside Playwright during transition.

**Done when**: The CDP client passes its own unit tests (connect, send commands, subscribe to events, handle errors, clean shutdown).

### Phase 2: Browser launcher without Playwright

Replace `browser.py` with direct Chrome subprocess management. This is the highest-risk phase because it involves:
- Browser binary discovery across platforms
- Process lifecycle management
- Reimplementing fingerprint/anti-detection via `Page.addScriptToEvaluateOnNewDocument` (replacing Playwright's `add_init_script`)
- Persistent context semantics (replacing Playwright's `launch_persistent_context`)

**Done when**: `chrome-agent launch` starts a browser using subprocess, and `chrome-agent status` can connect to it.

### Phase 3: Session mode

Implement the stdin/stdout session mode. This is the primary interface for CDP protocol interaction.

**Done when**: `chrome-agent session` connects to a browser, accepts commands on stdin, returns responses on stdout, handles events, and exits cleanly on EOF. Multiple sessions can connect to the same browser.

### Phase 4: CLI with raw CDP commands

Replace the curated command set (`click`, `fill`, `screenshot`, etc.) with the `Domain.method` pattern for one-shot use. The operational commands (`launch`, `status`, `session`) remain.

**Done when**: `chrome-agent Page.captureScreenshot '{"format": "png"}'` works in one-shot mode.

### Phase 5: Remove Playwright dependency

Remove `playwright` from `pyproject.toml`. Remove all Playwright imports. The `websockets` library is now the only browser-communication dependency.

**Done when**: `uv pip install chrome-agent` no longer pulls in Playwright, and all tests pass.

## Experimental Evidence

The following experiments validated the design decisions in this specification. All experiment code is in the `experiments/` directory.

### Experiment 1: Playwright CDPSession in attach mode
- Confirmed that Playwright's `CDPSession` works in attach mode
- Raw CDP commands (captureScreenshot, startScreencast, Performance.getMetrics, Network.enable) all work through CDPSession
- Established that Playwright is not a barrier to raw CDP access, but also not necessary for it

### Experiment 2: Raw WebSocket CDP client
- Built a minimal CDP client (~40 lines) over WebSocket
- Confirmed all CDP operations work without Playwright
- Discovered the page-vs-browser target distinction

### Experiment 3: Interaction primitives from raw CDP
- Built click, fill, type, press from CDP primitives
- All 7 test scenarios passed: button click, form fill, character-by-character typing, hidden element detection, obscured element hit-testing, off-screen auto-scroll click, checkbox toggle
- Key CDP commands: DOM.scrollIntoViewIfNeeded, DOM.getContentQuads, DOM.getNodeForLocation, DOM.focus, Input.dispatchMouseEvent, Input.insertText

### Experiment 4: Waiting from raw CDP
- Built event-driven waiting using Page.lifecycleEvent and Runtime.evaluate with awaitPromise + MutationObserver
- All 6 test scenarios passed: page load events (DOMContentLoaded, load, networkIdle), delayed element detection (500ms and 1500ms), click-triggered navigation, timeout handling, visibility change detection
- Event-driven approach reacts within <1ms of DOM insertion (vs ~30ms latency with polling)

### Experiment 5: Agent CDP composition
- Four independent agents given CDP tasks with only PDL documentation and a WebSocket client
- Agent A: Form fill + click (DOM, Input, Runtime) -- 32K tokens, 24 tool uses, 159s
- Agent B: Network capture (Network, Page) -- 24K tokens, 14 tool uses, 82s
- Agent C: Accessibility + Performance + DOMSnapshot -- 26K tokens, 8 tool uses, 60s
- Agent D: Emulation + Screencast (Emulation, Page) -- 28K tokens, 13 tool uses, 94s
- All four succeeded without guidance on composition patterns

### Experiment 6: Token cost comparison
- Same 7-step task (screenshot, fill x2, click x2, verify, screenshot)
- CLI abstraction: 17,187 tokens, 12 tool calls, 62s
- Raw CDP script: 18,418 tokens, 6 tool calls, 50s
- No meaningful token cost penalty for raw CDP; script approach is faster due to fewer subprocess invocations

### Experiment 7: Multi-client collaboration
- Two CDP clients connected simultaneously to the same page WebSocket URL
- Both clients operational: sent commands, received responses
- Events fan out identically: both received the same 14 lifecycle events in the same order
- Cross-client mutation visibility: Client A changed document.title, Client B read it immediately
- Both clients enabled DOM domain simultaneously without conflict
- Navigation by Client A caused Client B's pending promise to fail with clean error ("Inspected target navigated or closed")
- Both clients remained functional after the disruption

### Experiment 8: Session persistence approaches
- UNIX socket daemon: 1.3x speedup over fresh connections (modest, WebSocket overhead is small)
- stdin/stdout REPL: 2.1x speedup over fresh connections, 5x for lightweight commands
- Real per-invocation CLI overhead measured at ~350ms (Python startup + imports + Playwright + connection)
- Session mode reduces per-command latency to ~0.5ms -- a 700x improvement over one-shot CLI invocations
- REPL model is simpler (~130 lines), requires no daemon management, and fits naturally with subprocess-based tool usage
