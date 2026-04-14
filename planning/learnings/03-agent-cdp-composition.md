# Agent CDP Composition

## Question

Can agents compose raw CDP commands from protocol documentation alone, without pre-built abstractions or convenience wrappers? If agents can read PDL docs and produce working CDP scripts, then chrome-agent does not need to provide high-level commands -- it only needs to provide CDP transport and protocol documentation.

## Experiment

Four agents were each given a different CDP task, a minimal WebSocket client, and access to PDL protocol definitions. No pre-built interaction helpers, no examples of CDP usage, no convenience commands. Each agent had to discover the right CDP commands, compose them correctly, and produce a working script.

### Agent A: Form Fill

**Script:** `./03-agent-composition-form.py`

**Task:** Navigate to a test page, fill form inputs, click submit, verify results, then scroll to and click an off-screen button.

**CDP commands composed:**
- `DOM.getDocument`, `DOM.querySelector` -- element lookup via DOM tree
- `DOM.focus` -- focus input elements
- `DOM.getBoxModel` -- get element coordinates for clicking
- `DOM.scrollIntoViewIfNeeded` -- scroll off-screen elements into view
- `Input.insertText` -- bulk text insertion
- `Input.dispatchMouseEvent` -- mouse click sequence (move, press, release)
- `Runtime.evaluate` -- read back text content for verification
- `Page.enable`, `Page.loadEventFired` -- wait for navigation

**Result:** All steps passed. Form filled, submitted, verified. Far button scrolled into view and clicked.

**Token cost:** ~32K tokens

### Agent B: Network Capture

**Script:** `./03-agent-composition-network.py`

**Task:** Enable network monitoring, navigate to example.com, capture all requests/responses during page load, print URL/method/status/size for each.

**CDP commands composed:**
- `Network.enable`, `Network.disable` -- domain lifecycle
- `Network.requestWillBeSent` (event) -- capture request URL and method
- `Network.responseReceived` (event) -- capture response status
- `Network.loadingFinished` (event) -- capture response size
- `Page.navigate`, `Page.loadEventFired` -- navigation + load detection

**Result:** All network requests captured with method, status code, MIME type, and encoded data length.

**Token cost:** ~24K tokens

### Agent C: Accessibility and Performance

**Script:** `./03-agent-composition-ax-perf.py`

**Task:** Get the full accessibility tree, collect performance metrics, and take a DOM snapshot with layout information.

**CDP commands composed:**
- `Accessibility.enable`, `Accessibility.getFullAXTree` -- full accessibility tree with roles, names, ignored nodes
- `Performance.enable`, `Performance.getMetrics` -- all performance counters
- `DOMSnapshot.captureSnapshot` -- DOM snapshot with computed styles, bounding rects, paint order

**Result:** Accessibility tree enumerated (roles, named nodes). All performance metrics collected. DOM snapshot captured with layout bounds and node type breakdown.

**Token cost:** ~26K tokens

### Agent D: Screencast and Emulation

**Script:** `./03-agent-composition-screencast.py`

**Task:** Set device emulation (iPhone 12 Pro), navigate to a page, capture screencast frames, save a frame as JPEG, get layout metrics, then reset emulation.

**CDP commands composed:**
- `Emulation.setDeviceMetricsOverride` -- device emulation (width, height, scale, mobile)
- `Emulation.clearDeviceMetricsOverride` -- reset to defaults
- `Page.startScreencast`, `Page.stopScreencast` -- continuous frame capture
- `Page.screencastFrame` (event) -- receive frames with metadata
- `Page.screencastFrameAck` -- acknowledge frames to receive the next one
- `Page.getLayoutMetrics` -- CSS layout/visual viewport and content size
- `Runtime.evaluate` -- inject DOM mutations to trigger repaints for screencast frames

**Result:** Three screencast frames captured, first frame saved as JPEG. Layout metrics retrieved. Emulation set and cleared.

**Token cost:** ~28K tokens

## Observations

All four agents succeeded on their first attempt. Each agent:

1. Read the relevant PDL domain definitions
2. Identified the correct CDP commands and events
3. Composed them in the right order with correct parameters
4. Handled event-driven patterns (listeners registered before triggering actions)
5. Produced clean, working scripts

The agents did not need pre-built abstractions. They composed CDP commands the same way a developer would -- by reading the protocol docs. This is notable because the CDP protocol has over 100 domains and thousands of commands. The agents navigated this surface area without guidance.

Token costs ranged from 24K to 32K, with the form-fill task (Agent A) being the most expensive because it involved the most steps and verification.

The WebSocket client was shared across all agents (~50 lines). Everything else -- the domain-specific logic -- was composed from scratch.

## Conclusion

Agents can compose CDP commands from protocol documentation alone. They do not need pre-built convenience commands or abstraction layers to interact with a browser. Given a WebSocket transport and PDL docs, agents discover and use the right CDP commands for arbitrary browser automation tasks.

This means chrome-agent's role is to provide:
1. CDP WebSocket transport (connect to a browser)
2. Protocol documentation (PDL or equivalent reference)
3. Observation tools (screenshot, text extraction, accessibility tree)

It does not need to provide high-level commands like `click`, `fill`, `waitForSelector`, etc. These commands duplicate what agents can compose from CDP primitives.

**Design decision:** Remove convenience commands from chrome-agent. The tool provides transport and observation; agents compose interactions from CDP.

## Cross-references

- Experiments 3-4 (`01-interaction-primitives-from-cdp.md`, `02-waiting-from-cdp.md`) prove the CDP primitives are sufficient
- Token cost analysis (`04-token-cost-analysis.md`) quantifies the cost tradeoffs of different CDP approaches
