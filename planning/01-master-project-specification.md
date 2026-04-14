# Master Project Specification

> *This document captures the vision for what you're building in this iteration -- who it's for, what's in scope, and how users will interact with it. The methodology is designed to be applied iteratively: define a make-it-work version, execute it through the full Planning Phase and Implementation Loop, then repeat to layer on complexity. This specification scopes one pass through the methodology. It is the sole input to Feature Extraction; every feature must trace back to something in this document.*

## 1. Project Purpose

**Problem:**

AI agents need full, fast, granular browser control -- and the current options don't deliver. MCP-based browser control implementations are slow and don't provide fine-grained enough control over the browser. Playwright and similar abstraction layers expose only a curated subset of what the browser can actually do, locking agents out of capabilities like screencast, network interception, performance tracing, and dozens of other CDP domains. Both approaches also bundle heavy dependencies (Node.js subprocesses, ~200MB bundled Chromium). And none of them provide a way for multiple agents -- or an agent and a human -- to collaborate in the same browser session. chrome-agent exists today (PyPI v0.2.1) but is built on Playwright, inheriting its limitations. This iteration replaces the Playwright foundation with a direct CDP implementation -- a breaking change that trades the curated convenience command interface for full protocol access.

**Who experiences it:**

AI agents (primarily Claude Code agents) that need to observe, interact with, and control web browsers as part of automated workflows -- web scraping, testing, monitoring, form filling, data extraction, and browser-based task automation. Also developers building applications that deploy multiple agents against shared browser sessions.

**What success looks like for this iteration:**

An agent can start a session with a browser and interact with it through the full Chrome DevTools Protocol -- any command, any event, any domain -- through both a CLI tool and an importable Python library.

## 2. Essential Functionality

**Workflow 1: Launch and Control a Browser**

An agent checks whether a browser is already running, launches one if needed (optionally with anti-detection fingerprinting), or attaches to an already-running browser. The agent sends CDP commands and receives responses through a persistent session. When done, the agent closes the session.

**Workflow 2: Discover Protocol Capabilities**

An agent queries the connected browser to discover what CDP domains, commands, and events are available -- including parameter names, types, descriptions, and return values. Typed Python bindings generated from the protocol schema make commands discoverable through function signatures. The agent uses this information to compose operations.

**Workflow 3: Collaborate on a Shared Browser**

Multiple agents (or a human and an agent) connect to the same browser simultaneously. Each agent has its own session with an independent connection. They observe the same page state, receive the same events, and can send commands independently. Coordination between agents is the responsibility of the application, not chrome-agent.

**Workflow 4: React to Browser Events**

An agent subscribes to CDP events and is notified reactively when they fire -- not by polling. Session mode integrates with Claude Code's Monitor tool so that CDP events stream as real-time notifications. Quiet periods consume zero tokens.

## 3. Scope Boundaries

### Now (This Iteration)

- CDP client that can send any command and subscribe to any event across all 50 domains
- Session mode with persistent connection for multi-step workflows
- One-shot mode for single CDP commands
- Browser launch with remote debugging enabled (subprocess management, binary discovery)
- Browser attach to an already-running browser on a CDP port
- Typed Python bindings auto-generated from the protocol schema, serving both library consumers and agents as a discoverability mechanism
- Protocol discovery via the browser's protocol schema endpoint
- Status checking (is a browser running on a given port)
- Multi-client support (multiple sessions to the same browser)
- Fingerprint/anti-detection profiles for launched browsers
- Integration with Claude Code's Monitor tool for reactive event streaming
- Removal of the Playwright dependency

### Not (Out of Scope)

- Coordination or locking between concurrent clients -- applications decide their own collaboration model
- Convenience/abstraction commands (click, fill, screenshot) -- agents compose CDP commands directly
- Firefox, Edge, or other browser support -- this is a Chrome DevTools Protocol client, not a cross-browser automation framework
- Proxy configuration or network routing -- agents can configure this through CDP's Network domain directly
- Target/tab management abstractions -- agents use CDP's Target domain directly to create, list, and switch between targets
- Authentication or credential management abstractions -- agents use CDP's WebAuthn, FedCm, or cookie manipulation directly

### Next (Future Iterations)

- Nothing deferred at this time

## 4. Technical Context

**Platform:**

Python CLI tool, distributed via PyPI, installed with `uv tool install chrome-agent` or `pip install chrome-agent`. Runs on Linux, macOS, and Windows.

**User interaction model:**

Two interfaces:

1. *CLI tool*: One-shot commands for single operations, a persistent session mode for multi-step workflows and event streaming, and operational commands for browser management and protocol discovery. Session mode is designed to integrate with Claude Code's Monitor tool for reactive, event-driven browser control.

2. *Python library*: Importable modules for agents and developers writing Python scripts. Typed domain classes (auto-generated from the protocol schema) provide IDE autocomplete and make CDP commands discoverable through function signatures. An agent writing a script can import and use chrome-agent's CDP client and typed bindings directly.

**External systems and integrations:**

- Chrome/Chromium browser -- the system being controlled via CDP. Must be installed on the system (chrome-agent does not bundle a browser).
- Chrome DevTools Protocol -- the WebSocket-based JSON-RPC protocol that Chrome exposes on its debugging port.
- Chrome's HTTP endpoints for target discovery and protocol schema.
- Chrome DevTools Protocol Definition Language (PDL) files -- machine-readable protocol specifications published by Google in the devtools-protocol repository. These define every domain, command, event, type, and parameter in the protocol and serve as the input for typed binding generation and test suite derivation.
- Claude Code's Monitor tool -- for reactive event streaming from session mode.

**Constraints:**

- Single runtime dependency (`websockets`) -- minimizing install size and complexity is a core design goal. The current Playwright dependency brings ~200MB of bundled Chromium plus a Node.js subprocess.
- Must work with any Chrome/Chromium version that supports CDP -- chrome-agent is a protocol client, not pinned to a browser version.
- Session mode must have low per-command latency for multi-step workflows.
- Chrome must be installed on the system. Browser binary discovery is platform-specific.

## 5. Key Workflows

### Workflow 1: Launch and Control a Browser

**Goal:** An agent gets a browser running with CDP enabled and interacts with it through the full protocol.

**Steps:**

1. Agent checks whether a browser is already running on the target port.
2. If not, agent launches a browser with CDP enabled, optionally with a fingerprint profile for anti-detection.
3. Agent opens a persistent session.
3. Agent sends CDP commands and reads responses.
4. Agent optionally subscribes to events and receives them reactively.
5. Agent closes the session when done. The browser remains running for other agents or the human.

**Expected outcome:** The agent has sent and received CDP commands successfully through a persistent session.

**Error paths:**

- Chrome binary not found on the system.
- Requested port already in use by another process.
- Browser crashes mid-session.
- Malformed command input.

### Workflow 2: Discover Protocol Capabilities

**Goal:** An agent learns what CDP commands are available on the connected browser.

**Steps:**

1. Agent queries for available CDP domains.
2. Agent drills into a specific domain to see its commands, events, and types.
3. Agent inspects a specific command's parameters and return values.

**Expected outcome:** The agent has enough information to compose CDP commands correctly.

**Error paths:**

- No browser running to query.

### Workflow 3: Collaborate on a Shared Browser

**Goal:** Multiple agents share the same browser, each observing and interacting independently.

**Steps:**

1. A browser is running with CDP enabled.
2. Multiple agents each open their own session to the same browser.
3. Both agents send commands and receive events independently.
4. State mutations from one agent are immediately visible to the other.

**Expected outcome:** Both agents connected and operational. Events fan out to both. Navigation by one produces clean errors (not hangs) in the other's pending operations.

**Error paths:**

- Same as Workflow 1 -- collaboration uses the same session mechanism.

### Workflow 4: React to Browser Events

**Goal:** An agent monitors browser activity reactively without polling.

**Steps:**

1. Agent opens a session and subscribes to CDP events (e.g., network requests, page loads, console messages).
2. Events stream as real-time notifications via Monitor integration.
3. Agent is woken up only when events fire. Quiet periods consume zero tokens.
4. Agent reacts to events -- inspects content, takes action, or continues waiting.

**Expected outcome:** The agent receives browser events in real time without polling overhead.

**Error paths:**

- Browser crashes or navigates away, breaking event subscriptions.
