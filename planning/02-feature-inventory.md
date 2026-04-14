# Feature Inventory

> *This document is a complete, categorized list of every discrete feature needed for this iteration, extracted systematically from the Master Project Specification. It bridges the gap between the vision (what the system does as a whole) and the specifications (what each piece does individually). Each feature is an independently meaningful, independently implementable capability -- something a user would recognize as a thing the system does. Behaviors of a feature (how it reports progress, handles errors, recovers from interruption, writes output) are captured in the feature's description, not as separate features. The Master Feature Table provides the at-a-glance summary; the Feature Details section captures the full behavioral picture of each feature as surfaced during extraction. The methodology is applied iteratively -- this inventory covers one pass through the Planning Phase, scoping the make-it-work version. Every feature listed here must trace back to the Master Project Specification; if it can't, it either doesn't belong or the specification needs updating. Features at this stage are not yet atomic -- some will need splitting during Step 3 (Iterative Specification Development) when their full complexity becomes apparent. This is a complete list, not a final one.*

## 1. Project Reference

**Source:** `planning/01-master-project-specification.md`

## 2. Summary

**Iteration 1 (v0.3.0):** 8 features across 4 categories (2 small, 2 medium, 4 large). Delivered the CDP-native foundation: WebSocket client, session mode, browser launch, protocol discovery, typed bindings, fingerprint profiles, browser status, and one-shot CLI commands. All implemented and released.

**Iteration 2 (this iteration):** 3 new features across 2 existing categories (1 small, 1 medium, 1 large). Reshapes the CLI surface around named instances and a two-channel interaction pattern (attach for events, one-shot for commands) with event subscription isolation between participants.

**Cross-cutting change:** All existing commands that accept `--port` (launch, status, help, one-shot) adapt to address browsers by instance name. This is a behavioral update to each command driven by the Instance Registry feature, not a separate feature per command.

**Superseded features:** CDP-02 (Session Mode) is superseded by Attach Mode. BRW-02 (Browser Status) is superseded by Instance Status.

**Combined totals:** 11 features, 4 categories, 3 small, 3 medium, 5 large

## 3. Categories

### Protocol Client

**Abbreviation:** CDP

**Description:** The core CDP WebSocket client and session management. Features in this category handle connecting to Chrome, sending commands, receiving events, and maintaining persistent sessions.

### Browser Management

**Abbreviation:** BRW

**Description:** Launching, discovering, and managing Chrome browser processes and instances. Features in this category handle finding the Chrome binary, starting it with the right flags, checking status, managing fingerprint profiles, and managing the instance lifecycle (naming, registration, discovery).

### Code Generation

**Abbreviation:** GEN

**Description:** Build-time tooling that generates typed Python code from the CDP protocol schema. Distinct from the runtime protocol client -- this category produces source files, not runtime behavior.

### Command-Line Interface

**Abbreviation:** CLI

**Description:** The CLI entry points that expose CDP client and browser management capabilities to agents and developers. Features in this category handle argument parsing, output formatting, and the session stdin/stdout protocol.

## 4. Master Feature Table

### Iteration 1 (v0.3.0) -- implemented

| Feature ID | Name | Description | Complexity |
|------------|------|-------------|------------|
| CDP-01 | CDP WebSocket Client | Connect to Chrome via WebSocket, send commands, receive responses, subscribe to events, handle errors and disconnection | Large |
| CDP-02 | Session Mode | Persistent stdin/stdout protocol over a single WebSocket connection, supporting commands, responses, and event streaming via Monitor. **Superseded by CDP-04 (Attach Mode) in iteration 2.** | Large |
| CDP-03 | Protocol Discovery | Query the browser's protocol schema endpoint and present domain, command, and event information in a readable format | Small |
| GEN-01 | Typed Protocol Bindings | Auto-generate typed Python classes and methods from the CDP protocol schema, providing one class per domain, one method per command, and typed dataclasses for all CDP types | Large |
| BRW-01 | Browser Launch | Start a Chrome browser with --remote-debugging-port via subprocess, including binary discovery, process lifecycle management, and clean shutdown | Large |
| BRW-02 | Browser Status | Check whether a browser is listening on a CDP port and report version, page URL, and title. **Superseded by BRW-05 (Instance Status) in iteration 2.** | Small |
| BRW-03 | Fingerprint Profiles | Apply anti-detection configuration to launched browsers -- user agent, viewport, locale, timezone, platform spoofing via CDP and launch flags | Medium |
| CLI-01 | One-Shot Commands | Parse Domain.method and JSON params from CLI arguments, connect, send, print response, disconnect. Also route operational commands (launch, status, session, help) | Medium |

### Iteration 2 (this iteration) -- new features

| Feature ID | Name | Description | Complexity |
|------------|------|-------------|------------|
| BRW-04 | Instance Registry | Manage named browser instances: auto-allocate ports, derive names from directory basenames, store name-to-port-to-PID mappings, support lookup by name, detect and clean up stale entries | Medium |
| CDP-04 | Attach Mode | Persistent connection to a named browser instance for event observation with isolated subscriptions. Replaces Session Mode. Streams subscribed events to stdout as JSON lines. | Large |
| BRW-05 | Instance Status | List all registered browser instances with their page targets. Enrich registry data with live browser state: liveness, target IDs, URLs, and titles. Replaces Browser Status. | Small |

## 5. Feature Details

### Iteration 1 (v0.3.0) -- implemented

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

> **Superseded by CDP-04 (Attach Mode) in iteration 2.** Session Mode mixed events and command responses on a single stdout stream and used page-level connections with shared event subscriptions. Attach Mode replaces it with isolated event subscriptions and a design focused on event observation running concurrently with independent one-shot command execution.

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

- **Iteration 2 update:** Accepts an instance name (resolved via BRW-04 Instance Registry) instead of a port number, consistent with the instance-name routing used by all other commands.

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
- **Iteration 2 update:** Integrates with BRW-04 (Instance Registry) for auto-port allocation, instance naming, registration, and structured JSON output. `--port` remains available as an override for users who need a specific port (e.g., matching a firewall rule, or connecting to a Chrome launched externally). The core launch mechanics (binary discovery, subprocess management, port readiness) are unchanged.

**Complexity:** Large -- browser binary discovery across platforms, subprocess management, port readiness polling, integration with fingerprint profiles, and window management. Highest-risk feature due to platform-specific behavior.

**Traceability:** Essential Functionality Workflow 1 (Launch and Control), Key Workflows Workflow 1 step 1

### BRW-02: Browser Status

> **Superseded by BRW-05 (Instance Status) in iteration 2.** Browser Status checked a single port. Instance Status lists all registered instances with enriched page target information.

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
- **Iteration 2 update:** One-shot commands accept an instance name as the first argument (e.g., `chrome-agent mysite-01 Runtime.evaluate '...'`) and resolve it via BRW-04 (Instance Registry). Target specifier support added (target ID prefix, numeric index, or URL substring) for multi-tab instances. `session` route replaced by `attach` route. Creates isolated sessions for commands.

**Complexity:** Medium -- argument parsing and routing is straightforward, but the one-shot CDP path requires connection management and error handling.

**Traceability:** Technical Context (user interaction model), Essential Functionality all workflows

### Iteration 2 (this iteration) -- new features

### BRW-04: Instance Registry

**What it does:** Manages named browser instances -- the infrastructure that maps human-readable names to browser processes. Provides port auto-allocation, name derivation, registration, lookup, and stale entry cleanup. This is the foundation that all instance-name-based commands depend on.

**Inputs:** For registration: working directory path (for name derivation), optional port override. For lookup: instance name. For cleanup: no input (scans registry for dead entries).

**Outputs:** For registration: instance name, allocated port, PID. For lookup: port, PID, and metadata for the named instance. For cleanup: removal of stale entries. Structured JSON output for programmatic consumers, formatted text for humans.

**Behavioral details:**
- Auto-allocates ports by scanning from a base port (default 9222) upward, checking each for availability
- Derives instance names from the current working directory basename, lowercased, with special characters stripped. Auto-increments a numeric suffix (`-01`, `-02`) when an instance with the same base name already exists
- Stores registry data under `/tmp/chrome-agent/` -- name-to-port-to-PID mappings with launch timestamps
- Lookup by name returns port and PID; errors with a clear message if the instance name is not found
- Stale entry detection checks PID liveness -- if the Chrome process has died, the entry is stale
- Cleanup removes stale entries and their associated session directories
- Used by launch (registration), attach (lookup), one-shot (lookup), status (enumeration), help (lookup), and cleanup (pruning)

**Complexity:** Medium -- the individual operations (port scanning, name derivation, JSON file I/O, PID checks) are straightforward, but the registry is the foundation that every other command depends on, and concurrent access considerations (multiple chrome-agent invocations reading/writing the registry) add complexity.

**Traceability:** Essential Functionality Workflow 1 (Launch and Manage Browser Instances), Key Workflows Workflow 1 (steps 1-6), Scope Boundaries Now ("Named browser instances with auto-allocated ports and a discoverable registry"), Technical Context (instance registry as local mechanism)

### CDP-04: Attach Mode

**What it does:** Creates a persistent connection to a named browser instance for event observation with isolated event subscriptions. This is the observation channel in chrome-agent's two-channel interaction pattern. The agent attaches, subscribes to events, and receives them as a JSON line stream on stdout -- running concurrently with independent one-shot command execution. Replaces CDP-02 (Session Mode).

**Inputs:** Instance name (resolved via BRW-04 registry). Optional target specifier (target ID prefix, numeric index, or URL substring) for multi-tab instances. Event subscriptions specified as CLI arguments at launch (e.g., `+Page.loadEventFired +Network.requestWillBeSent`) and/or via stdin during the session.

**Outputs:** Subscribed CDP events on stdout as JSON lines (one message per line, unbuffered). Readiness signal on stdout when the connection is established and subscriptions are active.

**Behavioral details:**
- Connects to the browser and creates a session with isolated event subscriptions -- other participants' subscriptions are invisible to this session, and this session's subscriptions are invisible to others
- Per-event selectivity: subscribing to a specific event (e.g., `+Network.requestWillBeSent`) auto-enables the parent CDP domain but only forwards the subscribed event, not all events in that domain
- Event subscriptions can be specified as CLI arguments at launch and modified via stdin during the session (`+Event` to subscribe, `-Event` to unsubscribe)
- Designed to run as a background process: under Claude Code's Monitor tool (push notifications), redirected to a file (`> /tmp/events.jsonl`), or with `&` in a shell
- Events caused by other participants' actions (e.g., a one-shot navigation) appear on the attach stream for subscribed event types
- Target identification: when the instance has multiple page targets, the user specifies which to attach to. Default to the only target when unambiguous. Error with available targets listed when ambiguous or not found.
- Detachment: the session is destroyed when the process exits (Ctrl+D, signal, or parent process termination). The browser and page are unaffected.
- Handles SIGTERM gracefully for Monitor integration (Monitor may terminate the process)
- Errors with clear messages for: dead instance, ambiguous target, browser crash mid-session
- Output format is Monitor-compatible: unbuffered, one JSON object per line, no interleaved binary data

**Complexity:** Large -- isolated session creation, event subscription management (CLI args + stdin protocol), per-event selectivity on top of CDP domain-level enabling, target identification with ambiguity handling, concurrent operation with one-shot commands, signal handling, and clean shutdown under various failure modes. The most complex feature in this iteration.

**Traceability:** Essential Functionality Workflow 2 (Attach to Observe Browser Events), Workflow 4 (Collaborate on a Shared Browser), Key Workflows Workflow 2 (all steps), Workflow 4 (steps 3-6), Scope Boundaries Now ("attach command for persistent event observation with per-participant subscription isolation", "Event subscription isolation between participants sharing a browser"), Technical Context (user interaction model -- attach mode)

### BRW-05: Instance Status

**What it does:** Lists all registered browser instances with their page targets, enriching registry data with live browser state. This is how agents and humans discover what's running and identify specific page targets for attach or one-shot commands. Replaces BRW-02 (Browser Status).

**Inputs:** Optional instance name to show details for a specific instance. No input lists all instances.

**Outputs:** For each instance: name, port, alive/dead status. For each page target within an alive instance: target ID (truncated for readability), numeric index, URL, and title. Structured JSON output for programmatic consumers, formatted text for humans.

**Behavioral details:**
- Reads the instance registry (BRW-04) for all registered instances
- For each instance, checks whether the Chrome process is still alive (PID liveness check and/or port check)
- For each alive instance, queries Chrome's `/json` endpoint to enumerate page targets
- Displays target IDs truncated to 8 characters (sufficient for disambiguation), with numeric indexes for shorthand reference
- Dead instances are reported as dead rather than silently omitted -- helps the user understand stale state and prompts cleanup
- Accepts an optional instance name to filter output to a single instance
- Used by agents to discover target IDs before issuing attach or one-shot commands

**Complexity:** Small -- reads the registry, checks PID/port liveness, makes HTTP requests to `/json`, and formats output. All operations are well-understood and synchronous. The logic is straightforward enumeration and formatting.

**Traceability:** Essential Functionality Workflow 1 (Launch and Manage Browser Instances), Workflow 4 (Collaborate on a Shared Browser), Key Workflows Workflow 1 (step 5), Workflow 4 (step 2), Scope Boundaries Now ("status command showing all running instances with their page targets")
