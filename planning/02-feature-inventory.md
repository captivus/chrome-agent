# Feature Inventory

> *This document is a complete, categorized list of every discrete feature needed for this iteration, extracted systematically from the Master Project Specification. It bridges the gap between the vision (what the system does as a whole) and the specifications (what each piece does individually). Each feature is an independently meaningful, independently implementable capability -- something a user would recognize as a thing the system does.*

## 1. Project Reference

**Source:** `planning/01-master-project-specification.md`

## 2. Summary

**Total features:** 8

**Categories:** 4

**Complexity breakdown:** 2 small, 2 medium, 4 large

**Cross-cutting constraint:** This iteration replaces the existing Playwright-based implementation with a direct CDP implementation. The Playwright dependency is removed entirely. This is a consequence of implementing all features on raw CDP, not a feature in itself.

## 3. Categories

### Protocol Client

**Abbreviation:** CDP

**Description:** The core CDP WebSocket client and session management. Features in this category handle connecting to Chrome, sending commands, receiving events, and maintaining persistent sessions.

### Browser Management

**Abbreviation:** BRW

**Description:** Launching, discovering, and managing Chrome browser processes. Features in this category handle finding the Chrome binary, starting it with the right flags, checking status, and managing fingerprint profiles.

### Code Generation

**Abbreviation:** GEN

**Description:** Build-time tooling that generates typed Python code from the CDP protocol schema. Distinct from the runtime protocol client -- this category produces source files, not runtime behavior.

### Command-Line Interface

**Abbreviation:** CLI

**Description:** The CLI entry points that expose CDP client and browser management capabilities to agents and developers. Features in this category handle argument parsing, output formatting, and the session stdin/stdout protocol.

## 4. Master Feature Table

| Feature ID | Name | Description | Complexity |
|------------|------|-------------|------------|
| CDP-01 | CDP WebSocket Client | Connect to Chrome via WebSocket, send commands, receive responses, subscribe to events, handle errors and disconnection | Large |
| CDP-02 | Session Mode | Persistent stdin/stdout protocol over a single WebSocket connection, supporting commands, responses, and event streaming via Monitor | Large |
| CDP-03 | Protocol Discovery | Query the browser's protocol schema endpoint and present domain, command, and event information in a readable format | Small |
| GEN-01 | Typed Protocol Bindings | Auto-generate typed Python classes and methods from the CDP protocol schema, providing one class per domain, one method per command, and typed dataclasses for all CDP types | Large |
| BRW-01 | Browser Launch | Start a Chrome browser with --remote-debugging-port via subprocess, including binary discovery, process lifecycle management, and clean shutdown | Large |
| BRW-02 | Browser Status | Check whether a browser is listening on a CDP port and report version, page URL, and title | Small |
| BRW-03 | Fingerprint Profiles | Apply anti-detection configuration to launched browsers -- user agent, viewport, locale, timezone, platform spoofing via CDP and launch flags | Medium |
| CLI-01 | One-Shot Commands | Parse Domain.method and JSON params from CLI arguments, connect, send, print response, disconnect. Also route operational commands (launch, status, session, help) | Medium |

## 5. Feature Details

### CDP-01: CDP WebSocket Client

**What it does:** Connects to a Chrome browser's CDP WebSocket endpoint, sends commands, awaits responses, and dispatches events to registered callbacks. This is the foundation that all other features build on. It is also the primary importable Python interface -- agents and developers can use it directly as a library (`from chrome_agent import CDPClient`) to build CDP interactions in their own scripts.

**Inputs:** WebSocket URL (obtained from Chrome's `/json` endpoint), CDP method name, optional JSON parameters.

**Outputs:** JSON response from Chrome for commands. Event callback invocation for subscribed events.

**Behavioral details:**
- Connects to both page and browser targets
- Correlates commands to responses by message ID
- Supports CDP session multiplexing (sessionId routing for multi-target interactions)
- Propagates CDP errors as Python exceptions
- Handles WebSocket disconnection cleanly (propagates to pending commands, shuts down)
- Supports `async with` context manager for lifecycle management
- Errors in the receive loop must not silently die
- Multi-client support is inherent to CDP -- Chrome natively handles multiple simultaneous WebSocket connections to the same target, with events fanning out to all connected clients. This is not something chrome-agent builds; it is a property of the protocol that chrome-agent must not interfere with

**Complexity:** Large -- session multiplexing, async lifecycle management, error propagation from the receive loop, and the foundation role (everything else depends on this) make this more than a simple client.

**Traceability:** Essential Functionality Workflow 1 (Launch and Control), Technical Context (external systems, user interaction model -- Python library)

### CDP-02: Session Mode

**What it does:** Maintains a persistent WebSocket connection to Chrome and exposes a stdin/stdout protocol for sending CDP commands and receiving responses and events. This is the primary interface for agents doing multi-step browser work. Designed for reactive event streaming via Claude Code's Monitor tool -- the agent is woken up when browser events fire rather than polling.

**Inputs:** CDP port number. Commands on stdin. Event subscription/unsubscription commands on stdin.

**Outputs:** CDP responses and events on stdout (one JSON message per line). Readiness signal on stdout when the connection is established. Error information on stderr.

**Behavioral details:**
- Persistent connection eliminates per-command overhead for multi-step workflows
- Forwards CDP's native message format (responses and events are distinguishable by their JSON structure)
- Signals readiness so the caller knows when commands can be sent
- Malformed input produces an error response, not a crash
- Browser disconnection exits cleanly with error information
- EOF on stdin triggers clean shutdown
- Output is unbuffered and single-line for Monitor integration
- Handles SIGTERM gracefully (Monitor may terminate the process)

**Complexity:** Large -- the stdin/stdout protocol, event delivery, error handling, readiness signaling, Monitor integration, and clean shutdown under various failure modes make this the most complex feature.

**Traceability:** Essential Functionality Workflow 1 (Launch and Control), Workflow 4 (React to Browser Events), Workflow 3 (Collaborate)

### CDP-03: Protocol Discovery

**What it does:** Queries the browser's `/json/protocol` HTTP endpoint and presents CDP domain, command, event, and type information in a readable format. This is how agents learn what the browser can do.

**Inputs:** CDP port number. Optional domain name or `Domain.method` name to filter output.

**Outputs:** Formatted text output listing domains, commands with their parameters and return types, events with their parameters, and descriptions.

**Behavioral details:**
- Supports progressive drill-down: list all domains, list commands in a domain, show details for a specific command
- Queries the browser's protocol schema endpoint via HTTP (no WebSocket needed)
- Fails with a clear error if no browser is running on the specified port

**Complexity:** Small -- HTTP GET, JSON parsing, text formatting. The protocol schema is well-structured and the formatting is straightforward.

**Traceability:** Essential Functionality Workflow 2 (Discover Protocol Capabilities), Key Workflows Workflow 2

### GEN-01: Typed Protocol Bindings

**What it does:** Auto-generates typed Python modules from the CDP protocol schema. Each CDP domain becomes a Python class, each command becomes a typed method, each CDP type becomes a typed data structure. The generated code is both a usable API and a discoverability mechanism -- agents can read the function signatures to know what commands exist and what parameters they accept.

**Inputs:** The CDP protocol schema, sourced from either the browser's protocol schema endpoint or the PDL files in the devtools-protocol repository.

**Outputs:** Python source files -- one module per CDP domain -- containing typed classes and methods that delegate to CDP-01's generic `send()` interface.

**Behavioral details:**
- Generates from the protocol schema, which is a machine-readable specification of every command, event, type, and parameter
- Generated code delegates to CDP-01 -- it is a typed layer over the generic client, not a separate implementation
- Re-running the generator against a newer browser version produces updated bindings
- The generated modules are the primary importable library API for Python consumers

**Complexity:** Large -- the generation is mechanical text transformation, but handling all CDP type variations and producing clean, idiomatic Python across 50 domains and 500+ methods requires thoroughness.

**Traceability:** Essential Functionality Workflow 2 (Discover Protocol Capabilities), Technical Context (user interaction model -- Python library, agents need to discover commands)

### BRW-01: Browser Launch

**What it does:** Starts a Chrome/Chromium browser with `--remote-debugging-port` enabled, managing the subprocess lifecycle. Finds the browser binary on the system, starts it with appropriate flags, and waits for the CDP port to become available.

**Inputs:** Port number (default 9222), optional fingerprint profile path, optional headless flag, optional window management preferences.

**Outputs:** A running Chrome process with CDP enabled on the specified port. Confirmation message with browser version.

**Behavioral details:**
- Discovers the Chrome/Chromium binary on the system (platform-specific search paths)
- Launches with remote debugging enabled and waits for the CDP port to become available before returning
- Optionally applies a fingerprint profile (via BRW-03) after launch
- Fire-and-forget: the browser continues running after chrome-agent exits
- Supports headless mode
- Optionally manages window placement (platform-specific, best-effort)
- Fails with a helpful error if Chrome is not found, listing searched paths

**Complexity:** Large -- browser binary discovery across platforms, subprocess management, port readiness polling, integration with fingerprint profiles, and window management. Highest-risk feature due to platform-specific behavior.

**Traceability:** Essential Functionality Workflow 1 (Launch and Control), Key Workflows Workflow 1 step 1

### BRW-02: Browser Status

**What it does:** Checks whether a browser is listening on a CDP port and reports basic information.

**Inputs:** Port number (default 9222).

**Outputs:** Whether the port is active, browser version, current page URL and title.

**Behavioral details:**
- Uses stdlib only (socket check + `/json/version` + `/json` HTTP requests) -- no WebSocket, no async
- Reports "No browser running on port N" if the port is not active
- Reports browser version, first page's URL and title if active

**Complexity:** Small -- socket check and two HTTP requests. This feature already exists in the current codebase and works well.

**Traceability:** Key Workflows Workflow 1 (status checking before session)

### BRW-03: Fingerprint Profiles

**What it does:** Applies anti-detection configuration to a launched browser to make it appear as a real desktop browser rather than an automated instance.

**Inputs:** A JSON fingerprint profile file specifying user agent, viewport dimensions, locale, timezone, platform, and vendor.

**Outputs:** The browser's JavaScript environment reflects the spoofed values. Navigator properties, `window.chrome`, and the `webdriver` flag are overridden.

**Behavioral details:**
- Injects anti-detection scripts that run before any page scripts
- Overrides browser fingerprint signals (webdriver flag, platform, vendor, chrome object)
- Sets viewport, user agent, locale, and timezone
- Profile is defined as a JSON file with a documented schema
- Applied after browser launch, before the browser is used for any navigation

**Complexity:** Medium -- the individual overrides are straightforward, but the init script must run before any page loads, which requires careful sequencing with the browser launch.

**Traceability:** Essential Functionality Workflow 1 (Launch and Control -- "optionally with anti-detection fingerprinting")

### CLI-01: One-Shot Commands

**What it does:** Parses command-line arguments, routes to the appropriate action (operational command or CDP method), and handles output formatting. This is the CLI entry point.

**Inputs:** Command-line arguments: either an operational command (`launch`, `status`, `session`, `help`) or a `Domain.method` with optional JSON params.

**Outputs:** Printed output to stdout (command results, status information, help text). Exit code (0 for success, non-zero for errors).

**Behavioral details:**
- Distinguishes CDP method calls from operational commands and routes accordingly
- One-shot CDP commands create a connection, send one command, print the response, and disconnect
- Attaching to a running browser (discovering targets, selecting which to connect to) is part of the connection path for both one-shot and session modes
- Operational commands (launch, status, session, help, cleanup) route to their respective features
- Malformed input produces clear error messages
- One-shot mode has higher per-command overhead than session mode, making it suitable for single operations rather than multi-step workflows

**Complexity:** Medium -- argument parsing and routing is straightforward, but the one-shot CDP path requires connection management and error handling.

**Traceability:** Technical Context (user interaction model), Essential Functionality all workflows
