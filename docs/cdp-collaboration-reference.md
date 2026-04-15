# Collaboration Model

Chrome-agent enables multiple participants -- humans, AI agents, or any combination -- to share a single browser. This document explains how collaboration works, what each participant can see and do, how they coordinate, and how to choose the right collaboration pattern for your use case.

## How It Works

Chrome's DevTools Protocol (CDP) supports multiple simultaneous WebSocket connections to the same browser. Each connection can independently send commands and subscribe to events. There is no built-in concept of ownership, locking, or turns -- all participants operate on the same shared page at the same time.

This is not a limitation. It is the design. Chrome handles concurrent access gracefully at the protocol level:

- **DOM mutations are immediately cross-visible.** If Agent A changes `document.title`, Agent B sees the change on its next `Runtime.evaluate`. There is no synchronization delay -- both operate on the same V8 execution context.
- **Navigation by one participant affects all others.** If the human navigates, all connected agents see the new page. If an agent navigates, the human sees it in the browser window. Pending JavaScript evaluations in other connections receive a context-destroyed error (not a hang or crash).
- **Each connection has independent message state.** Message ID namespaces and binding registrations are per-connection.

Event subscription behavior depends on which connection model is used. See the next section.

## Connection Models and Event Isolation

CDP offers two WebSocket endpoints, and the choice between them fundamentally affects how event subscriptions interact across participants.

### Page-level WebSocket (`/devtools/page/<ID>`)

Multiple clients connect directly to a page target. Each gets its own WebSocket, but **event domain subscriptions are shared across all connections to the same page.** If any client calls `Network.enable`, all clients connected to that page receive network events -- even if they never subscribed. This is Chrome's original multi-client model, designed for DevTools coexistence.

This model is simple but creates coupling. A network observer agent that enables the Network domain causes every other connected agent to receive hundreds of network events per page load. There is no way for one client to opt out of domains another client enabled.

### Browser-level WebSocket (`/devtools/browser/<ID>`) + `Target.attachToTarget`

A single WebSocket connects to the browser process itself. To interact with a page, the client calls `Target.attachToTarget` with `flatten: true`, which creates an isolated CDP session scoped to that target. Each session has its own domain subscriptions, independent of every other session -- even sessions attached to the same page.

**This is the model chrome-agent uses.** Both `attach` mode and one-shot commands connect to the browser-level WebSocket and create isolated sessions via `Target.attachToTarget`. The practical consequence:

- Agent A enables `Network` in its session. Agent B's session receives zero network events.
- Agent B enables `Page` in its session. Agent A's session is unaffected.
- Each participant controls exactly which events it receives. No cross-talk.

This isolation is per-session, not per-connection. A single browser-level WebSocket can multiplex many sessions (each with its own `sessionId`), and each session's subscriptions are independent.

### Why this matters for collaboration

With page-level connections, adding an observer agent has side effects -- it changes the event stream other agents see. With browser-level connections and `Target.attachToTarget`, observers are invisible to each other. You can attach a network observer, a DOM mutation watcher, and a screenshot agent to the same page without any of them interfering with the others' event streams.

## Participants

A participant is anything that holds a CDP connection to the browser. Participants fall into two roles: **actors** (sending commands that change the browser state) and **observers** (watching what happens without changing it). Any participant can play either role, and roles can shift during a session.

### Human

The human interacts through the browser's GUI -- clicking, typing, scrolling, selecting text. The human is always an actor. The human's actions produce real browser input events that the page's JavaScript sees, but CDP does not report them (see "The Observation Gap" below).

### AI Agent (attach mode)

An agent running `chrome-agent attach <instance> +Event.name` holds a persistent connection with an isolated CDP session. It can subscribe to events, and dynamically add or remove subscriptions at runtime by writing `+Event.name` or `-Event.name` to stdin. Its event subscriptions do not affect other participants. Multiple agents can each run their own attach session against the same browser instance, each with independent subscriptions.

### AI Agent (one-shot mode)

An agent running individual `chrome-agent <instance> Domain.method '{...}'` commands connects, creates a temporary isolated session via `Target.attachToTarget`, sends one command, prints the response, and disconnects. Connection overhead is ~50-80ms. Useful for spot checks, commands, and queries -- not for continuous event observation.

### DevTools

Chrome's built-in DevTools is just another CDP client. If a human opens DevTools while agents are connected, all coexist. DevTools uses page-level connections internally, so its domain subscriptions are shared with other page-level clients -- but not with chrome-agent's browser-level sessions. DevTools' network panel, console, and element inspector work normally alongside agent connections.

## The Observation Gap

CDP has two layers, and understanding the boundary between them is essential for collaboration.

### Layer 1: CDP Events (what Chrome broadcasts)

CDP events are the browser engine's own account of what is happening. They cover:

| Domain | What you observe | Key events |
|--------|-----------------|------------|
| **Page** | Navigation, page lifecycle, dialogs, downloads | `frameNavigated`, `loadEventFired`, `domContentEventFired`, `javascriptDialogOpening` |
| **Network** | All HTTP traffic -- requests, responses, WebSocket | `requestWillBeSent`, `responseReceived`, `loadingFinished`, `loadingFailed` |
| **DOM** | Structural mutations -- nodes added/removed, attributes changed | `childNodeInserted`, `childNodeRemoved`, `attributeModified` |
| **Runtime** | Console output, exceptions, execution contexts | `consoleAPICalled`, `exceptionThrown` |
| **Log** | Browser log messages | `entryAdded` |

### Layer 2: DOM Events (what the page's JavaScript sees)

The page's JavaScript environment fires events for every user interaction: `click`, `mousemove`, `keydown`, `scroll`, `selectionchange`, `input`, `focus`, `blur`, `touchstart`, and hundreds more. These events exist only inside the page -- CDP has no built-in mechanism to subscribe to them.

### The gap

**CDP observes consequences. It does not observe causes.**

When a human clicks a link, CDP reports that a navigation started (`Page.frameNavigated`) and network requests fired (`Network.requestWillBeSent`). It does not report the click itself. When a human scrolls, CDP reports lazy-loaded XHR requests. It does not report the scroll position. When a human selects text, CDP reports nothing at all.

The Input domain has exactly one event (`Input.dragIntercepted`, experimental) and it is for intercepting, not observing. CDP was designed for DevTools, which *controls* the browser. It was not designed for observing a human user's interactions.

| A participant does this | CDP observers see | CDP observers miss |
|------------------------|-------------------|-------------------|
| Clicks a link | Navigation, network requests | The click, mouse coordinates |
| Types in a form | Nothing (until form submission triggers XHR) | Keystrokes, input values, focus |
| Scrolls the page | XHR from lazy-loading | Scroll position, direction |
| Selects text | Nothing | Selected text, selection range |
| Hovers over an element | Nothing (unless hover triggers a request) | Hover target, mouse position |
| Dispatches CDP input events | Nothing (CDP is command-only for Input) | The dispatched events themselves |

The last row is critical for agent-to-agent collaboration: **when an agent dispatches mouse or keyboard events via `Input.dispatchMouseEvent` or `Input.dispatchKeyEvent`, other CDP observers do not see those events.** The page's JavaScript sees them (they are real browser input), but CDP does not broadcast "an input event was dispatched." An observing agent is blind to another agent's input actions unless the bridge is set up.

### Bridging the gap

Two mechanisms connect the layers:

**Pull model: `Runtime.evaluate`.** Any participant can run JavaScript in the page at any time to read the current state -- scroll position, selected text, focused element, form values, DOM content. This is a snapshot, not a stream. You ask, the page answers.

**Push model: `Runtime.addBinding`.** A participant registers a named JavaScript function via CDP. When page JavaScript calls that function, CDP fires a `Runtime.bindingCalled` event to the registering session. Combine this with injected DOM event listeners to get real-time notification of user interactions:

```javascript
// Register on CDP side: Runtime.addBinding(name="reportEvent")
// Then inject into the page:
document.addEventListener('click', (e) => {
    reportEvent(JSON.stringify({
        type: 'click', x: e.clientX, y: e.clientY,
        target: e.target.tagName + (e.target.id ? '#' + e.target.id : '')
    }));
}, true);

document.addEventListener('scroll', () => {
    reportEvent(JSON.stringify({type: 'scroll', y: window.scrollY}));
}, {passive: true});

document.addEventListener('selectionchange', () => {
    const text = window.getSelection().toString();
    if (text) reportEvent(JSON.stringify({type: 'selection', text: text}));
});
```

Bindings are tied to the CDP session that registered them. The JS function survives page navigations within the session and even lingers in the current execution context after the session disconnects (though the CDP event pipe breaks). Re-registering on a new connection restores everything. For reliable observation, maintain a long-lived connection (attach mode).

## Collaboration Patterns

### Pattern 1: Human drives, agent observes

The human browses. The agent watches via CDP events (navigations, network) and periodically takes screenshots or reads the DOM to stay synchronized.

**Setup:** One `chrome-agent attach <instance> +Page.frameNavigated +Page.loadEventFired` for the observer agent. Optionally add `+Network.requestWillBeSent` filtered to `Document` and `XHR`/`Fetch` types.

**What the agent sees:** Which pages the human visits, when they load, what API calls the page makes. The agent can take screenshots, read page text, query DOM elements, and check form values at any time via `Runtime.evaluate`.

**What the agent misses:** Clicks, scrolling, typing, text selection, hover. To see these, inject DOM event listeners via the binding bridge (adds overhead and requires persistent connection).

**Handoff:** The agent can take over by dispatching input events (`Input.dispatchMouseEvent`, `Input.dispatchKeyEvent`). The human sees the agent's actions in the browser window in real time. No coordination protocol is needed -- the agent just starts acting.

### Pattern 2: Agent drives, human observes

The agent navigates, fills forms, clicks buttons, takes screenshots. The human watches the browser window to verify the agent is doing the right thing.

**Setup:** One `chrome-agent attach <instance>` for the driving agent, plus one-shot commands for actions. The human simply watches the browser window.

**What the human sees:** Every navigation, every form fill, every click -- because the agent dispatches real input events that Chrome renders visually.

**What the human misses:** The agent's intent. The agent knows why it clicked a button; the human only sees the click. Consider having the agent log its intent to the console (`Runtime.evaluate` with `console.log`) so the human can see it in DevTools.

### Pattern 3: Multiple agents, specialized roles

Several agents connect simultaneously, each with a different job. Because chrome-agent uses browser-level connections with isolated sessions, each agent's event subscriptions are independent -- adding an observer does not change what other agents receive.

**Example setup:**
- **Agent A (actor):** Navigates, fills forms, clicks. Uses `Input.dispatch*` for human-like interactions.
- **Agent B (network observer):** `chrome-agent attach <instance> +Network.requestWillBeSent +Network.responseReceived`. Captures all HTTP traffic during Agent A's interactions. Agent A sees none of these network events.
- **Agent C (visual observer):** Takes periodic screenshots via `chrome-agent <instance> Page.captureScreenshot`. Creates temporary isolated sessions per invocation.
- **Agent D (interaction observer):** Registers `Runtime.addBinding` and injects DOM event listeners. Sees every click, scroll, and selection from Agent A's dispatched events.

**Coordination:** No explicit coordination is needed for observation. Each agent's session has isolated subscriptions, so agents cannot interfere with each other's event streams.

For action coordination -- preventing two agents from navigating simultaneously -- use a shared signal. The simplest approach is a convention: only one agent is the designated actor at any time. The actor navigates and interacts; all others observe. Actor designation can be managed outside chrome-agent (e.g., via a shared file, environment variable, or orchestrator process).

### Pattern 4: Agent-to-agent with no human

The same as Pattern 3, but no browser window is needed. Launch with `chrome-agent launch --headless`. Agents interact, observe, and coordinate entirely through CDP. Verification is through screenshots (visual), DOM queries (structural), and network capture (behavioral) rather than a human watching a window.

### Choosing a pattern

| Use case | Pattern | Participants |
|----------|---------|-------------|
| Human browses, agent provides commentary or assistance | 1 | Human + 1 agent |
| Agent automates a workflow, human supervises | 2 | 1 agent + human |
| Agent explores a website, second agent records network traffic | 3 | 2+ agents |
| Automated testing with observation | 4 | 2+ agents, headless |
| Human and agent take turns interacting | 1 ↔ 2 | Human + 1 agent |
| Multiple agents with different objectives on the same page | 3 | N agents |

## Filtering CDP Events

A real-world page generates hundreds of CDP events per page load. Amazon produces 200+ network requests per page (ad tracking, analytics, lazy-loading, video transcoding). Subscribing to all events drowns meaningful signals in noise.

With isolated sessions, event filtering is straightforward: each agent subscribes only to the events it needs, and those subscriptions affect nobody else. But filtering within your own stream is still important for managing volume.

### Filtering by use case

**Navigation only (lightest):** Subscribe to `Page.frameNavigated`, `Page.loadEventFired`, `Page.domContentEventFired`. Skip everything else.

**Navigation + meaningful network:** Add `Network.requestWillBeSent`, but filter by the `type` field. Keep `Document` (page navigations) and `XHR`/`Fetch` (API calls). Discard `Image`, `Stylesheet`, `Script`, `Font`, `Ping`.

**Console and errors:** Subscribe to `Runtime.consoleAPICalled`, `Runtime.exceptionThrown`, `Log.entryAdded`. Quietest and most useful for development.

**DOM mutations:** Subscribe to `DOM.childNodeInserted`, `DOM.childNodeRemoved`, `DOM.attributeModified`. Warning: this is a firehose on complex pages. Filter by node ID or subtree.

**Full interaction (via binding bridge):** Inject listeners for `click`, `scroll`, `selectionchange`, `keydown`. Throttle or debounce mouse-move events.

### Filtering by signal-to-noise

On Amazon, a navigation observer sees:
- 1-2 `Page.frameNavigated` events (the actual navigation)
- 1 `Page.loadEventFired` (page fully loaded)
- 200+ `Network.requestWillBeSent` events (ads, tracking, lazy-loading)

The navigation events are the signal. The network events are noise unless you specifically need them. Start with the lightest subscription set and add domains only when you need them.

## How Agents Interact with Page Elements

An agent that needs to click a button, select text, or fill a form follows a three-step pattern: **locate, act, verify.**

### Locate

The agent uses `Runtime.evaluate` to run JavaScript that finds the target element and returns its pixel coordinates:

```javascript
// Find an element by selector and return its position
(() => {
    const el = document.querySelector('#submit-button');
    const rect = el.getBoundingClientRect();
    return {x: rect.x + rect.width/2, y: rect.y + rect.height/2};
})()
```

For text selection, a `TreeWalker` locates the text node and a `Range` returns the precise pixel coordinates of the substring:

```javascript
(() => {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
        const node = walker.currentNode;
        if (node.textContent.includes("target text")) {
            const range = document.createRange();
            const start = node.textContent.indexOf("target text");
            range.setStart(node, start);
            range.setEnd(node, start + "target text".length);
            const rect = range.getBoundingClientRect();
            return {startX: rect.left, startY: rect.top + rect.height/2,
                    endX: rect.right, endY: rect.top + rect.height/2};
        }
    }
    return null;
})()
```

### Act

The agent dispatches input events at the coordinates. Chrome processes these identically to physical input -- the page's JavaScript sees real `mousedown`, `mousemove`, `mouseup`, `click`, `keydown` events.

```python
# Click
await cdp.send("Input.dispatchMouseEvent", {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1})
await cdp.send("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1})

# Drag-to-select text
await cdp.send("Input.dispatchMouseEvent", {"type": "mousePressed", "x": start_x, "y": start_y, "button": "left", "clickCount": 1})
for x in intermediate_points:
    await cdp.send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y, "button": "left"})
await cdp.send("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": end_x, "y": end_y, "button": "left", "clickCount": 1})
```

### Verify

The agent confirms the action produced the expected result:

```python
# Verify text was selected
selection = await cdp.send("Runtime.evaluate", {
    "expression": "window.getSelection().toString()", "returnByValue": True
})

# Verify navigation occurred
title = await cdp.send("Runtime.evaluate", {
    "expression": "document.title", "returnByValue": True
})

# Verify form was filled
value = await cdp.send("Runtime.evaluate", {
    "expression": "document.querySelector('#email').value", "returnByValue": True
})
```

Other observers (agents with bindings, or a human watching the screen) see the actions happen in real time during the Act step. The Verify step is for the acting agent's own confirmation.

## Protocol Reference

This document describes the CDP protocol as implemented by Chrome 147. Event availability may differ across Chrome versions. Query the live protocol:

```bash
chrome-agent help                     # list all domains
chrome-agent help Page                # list Page domain events and commands
chrome-agent help Page.loadEventFired # details for a specific event
```

The protocol schema is served by the browser at `http://localhost:<port>/json/protocol` and is always accurate for the connected browser version.
