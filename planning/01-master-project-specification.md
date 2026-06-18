# Master Project Specification

> *This document captures the vision for what you're building in this iteration -- who it's for, what's in scope, and how users will interact with it. The methodology is designed to be applied iteratively: define a make-it-work version, execute it through the full Planning Phase and Implementation Loop, then repeat to layer on complexity. This specification scopes one pass through the methodology. It is the sole input to Feature Extraction; every feature must trace back to something in this document.*

## 1. Project Purpose

**Problem:**

chrome-agent v0.3.0 delivers full CDP access to Chrome browsers through a CLI tool and Python library. The core protocol capabilities work -- agents can send any CDP command, subscribe to any event, launch browsers, and connect multiple clients to the same browser. However, the CLI surface was designed before real-world usage patterns were understood. Deploying chrome-agent against complex sites (Meetup, Eventbrite, aroundchicago.tech) revealed more natural and ergonomic ways to provide these capabilities:

- Agents naturally fall into a **two-channel interaction pattern** -- observing events on a persistent connection while sending commands independently -- but the current `session` command tries to be both an event listener and a command interface on a single stream. This mixes event notifications with command responses, making it difficult to use on noisy pages.
- When multiple participants (agents, humans, tools) share a browser, one participant's event subscriptions are visible to all others on the same connection. This causes **event flooding** -- subscribing to network events on a page like Meetup produces hundreds of ad-tracking events that drown useful signals for every participant.
- Managing browsers by **port number** doesn't scale past one or two instances. When running benchmarks or scraping multiple sites concurrently, users must manually track which port maps to which browser.

The capabilities exist. The access patterns need to match how agents and humans actually work.

**Who experiences it:**

AI agents (primarily Claude Code agents) that need to observe, interact with, and control web browsers as part of automated workflows -- web scraping, testing, monitoring, form filling, data extraction, and browser-based task automation. Also developers building applications that deploy multiple agents against shared browser sessions.

**What success looks like for this iteration:**

An agent can launch a named browser instance, attach to it for event observation, send commands independently via one-shot, and do both concurrently without interference. A second agent or human can attach to the same browser with isolated event subscriptions -- each participant sees only the events they subscribed to. Browsers are identified by name, not port number.

## 2. Essential Functionality

**Workflow 1: Launch and Manage Browser Instances**

An agent launches a Chrome browser and gets back a named handle (derived from the working directory). The agent uses this name for all subsequent interactions. Multiple browser instances coexist, each with its own name and auto-allocated port. The agent can check what instances are running and what pages are open in each.

**Workflow 2: Attach to Observe Browser Events**

An agent attaches to a running browser instance, creating a persistent connection with event subscriptions. The agent specifies which events to observe. Events stream to stdout as the browser operates -- page navigations, network requests, console errors, or any other CDP event the agent subscribes to. This runs concurrently with command execution (Workflow 3). The attachment lives until the agent detaches.

**Workflow 3: Send Commands to a Browser**

An agent sends a single CDP command to a named browser instance and gets the response back directly. This is the command-response workhorse -- navigate, evaluate JavaScript, take screenshots, dispatch input events. Each command is an independent invocation with no persistent state. This runs concurrently with event observation (Workflow 2).

**Workflow 4: Collaborate on a Shared Browser**

Multiple participants (agents, humans, tools) independently attach to the same browser instance. Each participant has isolated event subscriptions -- one participant enabling network event observation does not flood another participant with those events. Commands from any participant affect the shared browser state (navigation, DOM changes), and those effects are visible to all participants through their own event subscriptions.

## 3. Scope Boundaries

### Now (This Iteration)

- Named browser instances with auto-allocated ports and a discoverable registry
- `attach` command for persistent event observation with per-participant subscription isolation
- One-shot commands routed by instance name
- `status` command showing all running instances with their page targets (target IDs, URLs, titles)
- Replacement of the `session` command with `attach`
- Subsumption of the standalone observer script (`scripts/observe.py`) into `attach` -- the observer's event streaming functionality becomes a native capability of the attach command rather than a separate script
- Event subscription isolation between participants sharing a browser
- Target identification within a browser instance (by target ID, index, or URL)

### Not (Out of Scope)

- Event filtering logic inside chrome-agent -- users subscribe to the events they want and filter downstream. chrome-agent passes through what CDP delivers for subscribed events without being opinionated about what matters.
- A separate `send` command -- one-shot commands already provide ephemeral command-response interaction, and adding `send` as a distinct verb would create a redundant path with no capability difference.
- Coordination or locking between concurrent participants -- applications decide their own collaboration model
- Convenience/abstraction commands (click, fill, screenshot) -- agents compose CDP commands directly

### Next (Future Iterations)

- Filtering patterns if common ones emerge from real-world use -- the current "subscribe to what you want" approach may prove insufficient for some use cases, but we don't have enough data to be opinionated yet
- Batch mode for one-shot commands (amortizing Python startup across multiple commands without entering interactive mode)

## 4. Technical Context

**Platform:**

Python CLI tool, distributed via PyPI, installed with `uv tool install chrome-agent` or `pip install chrome-agent`. Runs on Linux, macOS, and Windows.

**User interaction model:**

Two complementary modes that work concurrently:

1. *Attach mode*: A long-running process that holds a persistent connection to a browser instance and streams subscribed events to stdout. Designed to run as a background process -- under Claude Code's Monitor tool for push notifications, or redirected to a file for pull-based reading. The agent subscribes to specific events and receives only those. This is the observation channel.

2. *One-shot mode*: A single CLI invocation that sends one CDP command and returns the response on stdout. Each invocation is independent -- no persistent state, no event subscriptions. This is the command channel.

Both modes address browsers by instance name rather than port number. Both can target specific pages within a multi-tab browser by target ID, numeric index, or URL.

Additionally, the Python library (`CDPClient` and typed domain classes) remains available for agents that need to write scripts with custom logic -- for example, subscribing to network events, navigating, collecting results, and returning them all in one script execution.

**External systems and integrations:**

- Chrome/Chromium browser -- the system being controlled via CDP. Must be installed on the system.
- Chrome DevTools Protocol -- the WebSocket-based JSON-RPC protocol that Chrome exposes on its debugging port.
- Chrome's HTTP endpoints for target discovery and protocol schema.
- Claude Code's Monitor tool -- for reactive event streaming from attach mode. Not required -- attach mode works as a background process with stdout redirected to a file for agents without Monitor.
- Instance registry -- a local registry (under `/tmp/chrome-agent/`) mapping instance names to ports, PIDs, and metadata. Managed by chrome-agent, not an external system.

**Constraints:**

- Single runtime dependency (`websockets`) -- minimizing install size and complexity remains a core design goal.
- Must work with any Chrome/Chromium version that supports CDP.
- One-shot commands must remain fast -- Python startup dominates latency (~50-80ms) and this is acceptable. The architecture must not add meaningful overhead beyond this baseline.
- Event subscription isolation between participants is a hard requirement, not a nice-to-have. The flooding problem observed on Meetup (hundreds of ad-tracking events drowning useful signals) makes shared subscriptions unusable in practice.

## 5. Key Workflows

### Workflow 1: Launch and Manage Browser Instances

**Goal:** An agent gets a browser running and can identify and discover it by name across the session's lifetime.

**Steps:**

1. Agent launches a browser from a working directory. chrome-agent auto-allocates a port, derives an instance name from the directory basename (e.g., `aroundchicago.tech-01`), and registers it.
2. chrome-agent returns the instance name, port, and PID -- as structured JSON when not in a TTY, as formatted text for humans.
3. Agent uses the instance name for all subsequent commands (`attach`, one-shot, `status`).
4. Agent can launch additional instances from the same or different directories. Each gets a unique name with an auto-incremented suffix.
5. Agent checks what's running via `status`, which lists all registered instances with their page targets -- target IDs, URLs, and titles.
6. `cleanup` removes stale registry entries for instances whose Chrome processes have died.

**Expected outcome:** One or more named browser instances are running and discoverable. The agent never needs to track port numbers manually.

**Error paths:**

- Chrome binary not found on the system.
- All ports in the scanning range are occupied.
- Agent references an instance name that doesn't exist or whose browser has died -- clear error with guidance.
- Registry is stale (Chrome process died without cleanup) -- `status` should detect and report dead instances rather than showing them as healthy.

### Workflow 2: Attach to Observe Browser Events

**Goal:** An agent establishes a persistent connection to a browser instance for event observation, running concurrently with independent command execution.

**Steps:**

1. Agent starts `attach` with an instance name and a list of event subscriptions (e.g., `+Page.loadEventFired +Network.requestWillBeSent`).
2. chrome-agent connects to the browser, creates a session with isolated event subscriptions, and begins streaming subscribed events to stdout as JSON lines.
3. The agent (or Monitor, or a file redirect) reads events from stdout.
4. Meanwhile, the agent sends one-shot commands (Workflow 3) independently. Events caused by those commands (e.g., network requests from a navigation) appear on the attach stream.
5. The agent can modify subscriptions during the session via stdin (`+Event` to subscribe, `-Event` to unsubscribe).
6. The agent detaches by closing the process (Ctrl+D, signal, or process exit). The browser and page are unaffected.

**Expected outcome:** The agent has a real-time stream of browser events scoped to exactly what it subscribed to. Command execution happens independently through one-shot without interfering with event observation.

**Error paths:**

- Browser instance has died since launch -- clear error on attach attempt.
- Specified page target doesn't exist or is ambiguous -- error with the available targets listed.
- Browser crashes mid-attachment -- the attach process exits with error information.
- Agent subscribes to a very high-volume event stream -- chrome-agent passes events through without filtering; downstream handling is the agent's responsibility.

### Workflow 3: Send Commands to a Browser

**Goal:** An agent sends a single CDP command to a named browser instance and gets the response.

**Steps:**

1. Agent invokes a one-shot command with the instance name, CDP method, and parameters.
2. chrome-agent resolves the instance name to a port, connects, creates a temporary session, sends the command, and returns the response as JSON on stdout.
3. The connection is closed. No state persists between invocations.

**Expected outcome:** The agent has the CDP response as structured JSON, ready to parse and act on. If an attach session (Workflow 2) is running concurrently, it receives any events triggered by this command.

**Error paths:**

- Instance name not found or browser has died.
- Specified page target doesn't exist or is ambiguous.
- CDP command returns an error (malformed params, unsupported method) -- the error is printed as JSON on stdout with a non-zero exit code.
- Page navigates while command is in flight (context destroyed) -- CDP error propagated to the agent.

### Workflow 4: Collaborate on a Shared Browser

**Goal:** Multiple participants independently observe and interact with the same browser without interfering with each other's event subscriptions.

**Steps:**

1. One participant launches a browser instance (or it's already running).
2. Each participant discovers the instance via `status`.
3. Each participant attaches independently, subscribing to their own events.
4. Participants send one-shot commands independently. Navigation by one participant triggers events on other participants' attach streams (for events they've subscribed to).
5. Participants can target the same page or different pages (tabs) within the browser. Target IDs (stable across navigations) identify specific tabs unambiguously.
6. One participant detaching does not affect other participants' connections or subscriptions.

**Expected outcome:** Multiple participants coexist on the same browser instance, each with isolated event subscriptions. No coordination protocol is needed -- instance discovery via `status` and independent attach/one-shot connections are sufficient.

**Error paths:**

- Two participants navigate the same tab simultaneously -- CDP handles this (last navigation wins), but both participants' pending commands on the navigated-away page may receive context-destroyed errors.
- A participant's attach process dies -- other participants are unaffected.
- The browser crashes -- all participants receive disconnection errors.

---

# Iteration 3 Increment

> *This section layers a third pass onto the vision above. Sections 1-5 describe the Iteration 2 scope (named instances + the two-channel pattern); this increment adds window distinction, instance lifecycle, and a fingerprint correction, driven by real-world use after Iteration 2 shipped.*

## I3.1 Project Purpose (increment)

Running agents against real sites alongside a human's own browsing surfaced three problems Iteration 2 didn't address:

- **Window confusion.** On a shared desktop, an agent-driven Chrome window is indistinguishable from the user's own Chrome windows. The user cannot tell at a glance which window the agent is operating, and agent windows pop onto whatever virtual desktop the user is working on.
- **Fingerprinting was counterproductive.** The Iteration 1 fingerprint feature (BRW-03) injected JavaScript navigator overrides to evade bot detection. An empirical detection audit found these overrides are each independently detectable and make the browser *more* detectable, not less -- they flip `bot.sannysoft.com`'s WebDriver test from pass to fail and raise CreepJS's headless score. A plain CDP-attached Chrome is already cleaner than the "hardened" one.
- **The registry drifted from reality.** Stale instance entries lingered after a browser closed, requiring manual `cleanup`. Worse, Chrome installs that fork the real browser into a different process (snap, the `chromium-browser` wrapper, self-relaunch) were misreported as dead immediately after a successful launch, because liveness was a PID-only check.

## I3.2 Essential Functionality (increment)

**Workflow 5: Tell agent windows apart.** Every headed browser an agent launches is visually marked -- a colored border + a corner badge naming the instance, and a title prefix (`🤖 <instance> — <page title>`) so it stands out in the taskbar / Alt-Tab while still showing the page's own title. The color is stable per instance, so multiple agent windows are distinguishable from each other as well as from the user's Chrome. On by default for headed launches; disabled with `--no-window-border`; suppressed under `--fingerprint` (the marker is page-observable) and `--headless` (no window). Agent windows also pin to the launching terminal's virtual desktop, out of the user's way.

**Workflow 6: The registry mirrors reality.** When an agent-launched window is closed (by the user, a crash, or shutdown), its instance is automatically removed from the registry and its session directory cleaned up -- no command to run. Liveness reflects whether the browser's CDP endpoint is actually reachable, not just whether the launched PID survives, so wrapper/snap-launched browsers are reported correctly. A *dropped CDP connection alone* does not retire an instance -- a host suspend/resume can sever the connection while the browser keeps running -- so the supervisor confirms the browser is truly gone (its CDP port stopped listening) before retiring, and reconnects to resume otherwise. `launch` also prunes any stale entries as a fallback.

**Fingerprint correction.** Fingerprint profiles now spoof only what can be set cleanly at launch (user agent, viewport, language, timezone) via Chrome flags, with no JavaScript injection. The detectable navigator overrides were removed.

## I3.3 Scope Boundaries (increment)

### Now (Iteration 3)

- Window border + badge + title prefix marking agent-launched windows, with a stable per-instance color (BRW-06)
- Per-instance supervisor that auto-retires an instance from the registry when its browser closes (BRW-07)
- Port-based instance liveness (fixes wrapper/snap "launched but reported dead")
- Launch-time pruning of stale registry entries and orphaned session directories
- Fingerprint hardening: launch-flag spoofs only, JS navigator overrides removed (BRW-03 update)
- `--version` / `-V` flag (CLI-01 update)

### Not (Out of Scope)

- WebRTC real-IP-leak mitigation -- it requires proxy support to be meaningful (the IP-handling policy flag alone is a no-op without a proxy) and is documented as a known limitation, not addressed here.
- Cross-OS platform spoofing -- WebGL/font signals leak the real OS regardless; a profile's platform should match the host.
- An OS-level window frame (true window-manager border) -- the marker is in-page; on GNOME/Mutter there is no cheap per-window border, and an in-page marker is detection-safe and cross-platform.

### Next (Future Iterations)

- Proxy support, and with it WebRTC IP-handling so the real IP does not leak around a proxy.
- An optional page-independent window marker (e.g. an external overlay) for marking `chrome://` / blank pages where in-page injection cannot reach.

## I3.4 Key Workflow: Window marking and auto-retirement

**Goal:** An agent's browser window is identifiable and the registry stays truthful with no manual upkeep.

**Steps:**

1. Agent launches a headed browser. chrome-agent spawns a detached per-instance supervisor that holds a CDP connection to the browser.
2. The supervisor marks every tab (current and future) with the instance's border + badge and keeps the title prefixed -- unless suppressed by `--no-window-border`, `--fingerprint`, or `--headless`.
3. The user visually identifies the agent window by its colored border and badge, on the launching terminal's desktop.
4. When the supervisor's CDP connection drops, it checks whether the browser is truly gone -- the CDP port stops listening within a short grace window. If gone (the window was closed), it removes the instance from the registry and deletes the session directory, then exits. If the port is still up (a transient drop), it reconnects and resumes supervising (re-installing the border on the live tabs).
5. A later `status` reflects only what is actually running; a later `launch` additionally prunes any stale entries left by abnormal exits.

**Error paths:**

- The CDP connection drops transiently (host suspend/resume, a network blip) while the browser keeps running -- the supervisor sees the port is still up and reconnects rather than retiring the live instance.
- The supervisor process is killed while the browser lives -- the entry persists until the next launch-time prune or manual `cleanup`; port-based liveness ensures a live browser is never wrongly pruned.
- A fingerprint profile is active -- the in-page marker is suppressed to avoid a page-observable footprint on bot-defended sites.
