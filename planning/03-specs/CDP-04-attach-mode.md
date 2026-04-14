# Feature Specification

> *This document is the complete definition of a single atomic feature -- what to build, how to validate it, what to observe during implementation, what it depends on, and (once implementation begins) its implementation history.*

## 1. Feature ID and Name

CDP-04: Attach Mode

## 2. User Story

As an AI agent, I want to attach to a running Chrome browser instance and observe browser events in real time on a persistent connection, so that I can see what's happening (page loads, network requests, errors) while sending commands independently through one-shot mode.

## 3. Implementation Contract

### Level 1 -- Plain English

This feature creates a persistent connection to a named browser instance for event observation with isolated event subscriptions. It replaces CDP-02 (Session Mode).

The agent runs `chrome-agent attach <instance-name>` with optional event subscriptions as arguments (e.g., `+Page.loadEventFired +Network.requestWillBeSent`). The command resolves the instance name to a port via the Instance Registry (BRW-04), connects to the browser-level WebSocket endpoint, creates a CDP session on a specific page target using `Target.attachToTarget` with `flatten: true`, subscribes to the specified events, and streams them to stdout as JSON lines.

Event subscriptions are isolated -- other participants connected to the same browser don't see this session's subscriptions, and this session doesn't see theirs. This is the core property that differentiates attach mode from the old session mode.

Per-event selectivity is supported: subscribing to `+Network.requestWillBeSent` auto-enables the Network domain on the CDP session but only forwards `requestWillBeSent` events, not all Network events. This is the same mechanism the existing session mode uses via its `+`/`-` protocol.

The agent can modify subscriptions during the session via stdin (`+Event` to subscribe, `-Event` to unsubscribe).

The attach process is designed to run as a background process: under Claude Code's Monitor tool, redirected to a file, or with `&` in a shell. Events caused by other participants' actions (e.g., a one-shot command navigating the page) appear on the attach stream for subscribed event types.

When the instance has multiple page targets (tabs), the agent specifies which to attach to using a target specifier: a target ID prefix (e.g., `--target 956FD3C2`), a numeric index (e.g., `--target 1`), or a URL substring (e.g., `--url meetup.com`). When there's only one page target, no specifier is needed. Ambiguous or missing targets produce an error listing the available targets.

Detachment happens when the process exits (Ctrl+D, signal, or parent process termination). The CDP session is destroyed, event subscriptions die, and the browser and page are unaffected.

### Level 2 -- Logic Flow (INPUT / LOGIC / OUTPUT)

**INPUT:**

- `instance_name`: string -- resolved via BRW-04 registry to get port
- `subscriptions`: list of strings -- event names to subscribe to at launch (e.g., ["Page.loadEventFired", "Network.requestWillBeSent"])
- `target_spec`: string or None -- target ID prefix, numeric index, or URL substring. None = default to only target.
- `target_by`: "id" | "index" | "url" -- how to interpret target_spec. Inferred from the flag used (--target vs --url).

**LOGIC:**

```
run_attach(instance_name, subscriptions, target_spec, target_by):
    // Phase 1: Resolve instance to port
    info = registry.lookup(instance_name)  // raises InstanceNotFoundError
    port = info.port

    // Phase 2: Connect to browser-level WebSocket
    browser_ws_url = get_ws_url(port=port, target_type="browser")
    cdp = CDPClient(ws_url=browser_ws_url)
    await cdp.connect()

    // Phase 3: Resolve page target
    targets = await cdp.send(method="Target.getTargets")
    page_targets = [t for t in targets["targetInfos"] if t["type"] == "page"]

    if len(page_targets) == 0:
        raise NoPageError("No page targets in instance {instance_name}")

    target_id = resolve_target(page_targets, target_spec, target_by)

    // Phase 4: Create isolated CDP session
    // The target may have been destroyed between getTargets and attach
    // (e.g., user closed the tab). Guard against this race.
    try:
        result = await cdp.send(
            method="Target.attachToTarget",
            params={"targetId": target_id, "flatten": True}
        )
    except (CDPError, Exception) as e:
        raise TargetNotFoundError(
            f"Failed to attach to target {target_id[:16]}: {e}",
            page_targets
        )
    session_id = result["sessionId"]

    // Phase 5: Set up event subscriptions
    // Track which domains are enabled and which events are subscribed
    enabled_domains = set()
    subscribed_events = set()
    event_handlers = {}  // tracks handlers by event name for later removal

    // Define event emitter helper for stdout streaming (used by subscribe_event)
    def emit_event(method, params):
        line = json.dumps({"method": method, "params": params})
        print(line, flush=True)

    // Phase 6: Subscribe to initial events
    // Event handlers are registered per-event in subscribe_event via
    // cdp.on(event=..., callback=..., session_id=...). No catch-all needed.
    for event_name in subscriptions:
        await subscribe_event(cdp, session_id, event_name, enabled_domains, subscribed_events)

    // Phase 7: Signal readiness
    print(json.dumps({"status": "ready", "sessionId": session_id[:16],
                       "target": target_id[:16]}), flush=True)

    // Phase 8: Read stdin for subscription changes, run until EOF/signal
    // Run stdin loop and connection monitor concurrently -- exit on whichever
    // completes first (EOF/signal or WebSocket drop).
    setup_signal_handlers()  // SIGTERM -> clean shutdown

    async def stdin_loop():
        try:
            async for line in async_stdin_reader():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("+"):
                    event_name = line[1:]
                    await subscribe_event(cdp, session_id, event_name,
                                          enabled_domains, subscribed_events)
                elif line.startswith("-"):
                    event_name = line[1:]
                    unsubscribe_event(cdp, session_id, event_name, subscribed_events)
                    // Note: we do NOT disable the domain -- other events may still need it
                else:
                    // Not a subscription command -- ignore or log warning
                    print(json.dumps({"warning": f"Unknown command: {line}"}), flush=True)
        except (EOFError, asyncio.CancelledError):
            pass

    async def monitor_connection():
        while cdp._connected:
            await asyncio.sleep(0.5)
        // Connection lost -- notify and exit
        print(json.dumps({"error": "Browser disconnected"}), flush=True)

    stdin_task = asyncio.create_task(stdin_loop())
    monitor_task = asyncio.create_task(monitor_connection())
    done, pending = await asyncio.wait(
        [stdin_task, monitor_task], return_when=asyncio.FIRST_COMPLETED
    )
    for task in pending:
        task.cancel()
    // Determine exit reason
    connection_lost = monitor_task in done

    // Phase 9: Clean shutdown
    // Connection may already be dead (e.g., browser crashed), so guard the detach
    try:
        await cdp.send(method="Target.detachFromTarget",
                       params={"sessionId": session_id})
    except (ConnectionError, Exception):
        pass  // Connection already dead
    await cdp.close()


subscribe_event(cdp, session_id, event_name, enabled_domains, subscribed_events):
    // Auto-enable the parent domain if not already enabled
    domain = event_name.split(".")[0]
    if domain not in enabled_domains:
        await cdp.send(method=f"{domain}.enable", session_id=session_id)
        enabled_domains.add(domain)
    subscribed_events.add(event_name)
    // Register per-event handler on CDPClient
    handler = lambda params: emit_event(event_name, params)
    event_handlers[event_name] = handler  // track for later removal
    cdp.on(event=event_name, callback=handler, session_id=session_id)


unsubscribe_event(cdp, session_id, event_name, subscribed_events):
    subscribed_events.discard(event_name)
    // Deregister the per-event handler from CDPClient
    // Note: CDPClient.off() only accepts (event, callback) -- no session_id parameter.
    // Session filtering was applied at registration time via cdp.on() and is stored
    // internally by CDPClient; off() matches by callback reference to remove the entry.
    handler = event_handlers.pop(event_name, None)
    if handler is not None:
        cdp.off(event=event_name, callback=handler)


resolve_target(page_targets, target_spec, target_by) -> str:
    if target_spec is None:
        if len(page_targets) == 1:
            return page_targets[0]["targetId"]
        else:
            raise AmbiguousTargetError(page_targets)

    if target_by == "index":
        index = int(target_spec) - 1  // 1-based
        if 0 <= index < len(page_targets):
            return page_targets[index]["targetId"]
        raise TargetNotFoundError(f"Index {target_spec} out of range", page_targets)

    elif target_by == "id":
        matches = [t for t in page_targets if t["targetId"].startswith(target_spec)]
        if len(matches) == 1:
            return matches[0]["targetId"]
        elif len(matches) == 0:
            raise TargetNotFoundError(f"No target matching ID prefix '{target_spec}'", page_targets)
        else:
            raise AmbiguousTargetError(matches)

    elif target_by == "url":
        matches = [t for t in page_targets if target_spec in t["url"]]
        if len(matches) == 1:
            return matches[0]["targetId"]
        elif len(matches) == 0:
            raise TargetNotFoundError(f"No target matching URL '{target_spec}'", page_targets)
        else:
            raise AmbiguousTargetError(matches)
```

**OUTPUT:**

- stdout: JSON lines, one per message, unbuffered. Four types of messages:
  - Readiness signal: `{"status": "ready", "sessionId": "...", "target": "..."}`
  - Events: `{"method": "Network.requestWillBeSent", "params": {...}}`
  - Errors: `{"error": "Browser disconnected"}`
  - Warnings: `{"warning": "Unknown command: ..."}`
- stderr: error messages (instance not found, target errors, connection failures)
- Exit code: 0 for clean shutdown (EOF, SIGTERM), 1 for errors

### Level 3 -- Formal Interfaces

```python
class NoPageError(Exception):
    """No page targets available in the browser instance."""
    def __init__(self, instance_name: str):
        super().__init__(f"No page targets in instance '{instance_name}'")


class AmbiguousTargetError(Exception):
    """Multiple page targets match the specifier."""
    def __init__(self, targets: list[dict]):
        self.targets = targets
        lines = [f"  [{i+1}] {t['targetId'][:8]}  {t['url'][:60]}  \"{t.get('title', '')}\"" 
                 for i, t in enumerate(targets)]
        listing = "\n".join(lines)
        super().__init__(
            f"Multiple page targets found. Specify one:\n{listing}"
        )


class TargetNotFoundError(Exception):
    """No page target matches the specifier."""
    def __init__(self, message: str, targets: list[dict]):
        self.targets = targets
        lines = [f"  [{i+1}] {t['targetId'][:8]}  {t['url'][:60]}  \"{t.get('title', '')}\"" 
                 for i, t in enumerate(targets)]
        listing = "\n".join(lines)
        super().__init__(f"{message}\nAvailable targets:\n{listing}")


async def run_attach(
    instance_name: str,
    subscriptions: list[str] | None = None,
    target_spec: str | None = None,
    target_by: str = "id",
) -> None:
    """Run the attach session.

    Connects to the named browser instance, creates an isolated CDP
    session on the specified page target, subscribes to events, and
    streams them to stdout as JSON lines until EOF or SIGTERM.

    Raises InstanceNotFoundError if the instance name is not registered.
    Raises NoPageError if the instance has no page targets.
    Raises AmbiguousTargetError if multiple targets match.
    Raises TargetNotFoundError if no target matches.
    Raises ConnectionError if the browser is unreachable.
    """
    ...


def resolve_target(
    page_targets: list[dict],
    target_spec: str | None,
    target_by: str,
) -> str:
    """Resolve a target specifier to a target ID.

    target_by: "id" (prefix match), "index" (1-based), or "url" (substring match).
    Returns the targetId string.

    Raises AmbiguousTargetError or TargetNotFoundError.
    """
    ...
```

## 4. Validation Contract

### Level 1 -- Plain English Scenarios

Happy path:
- Attach to a single-tab instance with event subscriptions. Events from those subscriptions stream to stdout when the browser navigates.
- Events caused by a one-shot command (separate process) appear on the attach stream.

Target identification:
- Attach to a multi-tab instance by target index.
- Attach to a multi-tab instance by URL substring.
- Attach to a single-tab instance with no target specifier (auto-selects).

Event isolation:
- Two attach sessions on the same page target with different subscriptions each see only their own subscribed events.

Subscription management:
- Subscribe to an additional event via stdin during the session.
- Unsubscribe from an event via stdin -- events stop appearing.

Error cases:
- Attach to a nonexistent instance name -- InstanceNotFoundError.
- Attach to an instance with multiple tabs and no target specifier -- AmbiguousTargetError listing the tabs.
- Attach to an instance whose browser has died -- ConnectionError.

Clean shutdown:
- Sending EOF (Ctrl+D) to stdin causes clean detachment. The browser continues running.
- Sending SIGTERM causes clean detachment.

### Level 2 -- Test Logic (GIVEN / WHEN / THEN)

Scenario: Attach and receive events
GIVEN: browser instance "test-01" running with one tab on example.com
WHEN: run_attach("test-01", subscriptions=["Page.loadEventFired"]) starts, then a separate process navigates the page via one-shot
THEN: stdout contains a readiness signal followed by a Page.loadEventFired event

Scenario: Cross-session event delivery
GIVEN: browser instance "test-01" running
WHEN: attach with +Network.requestWillBeSent is running, and a SEPARATE CDPClient (simulating one-shot) navigates the same page
THEN: attach stdout contains Network.requestWillBeSent events for the navigation's requests

Scenario: Event isolation
GIVEN: browser instance "test-01" running
WHEN: two attach processes start on the same target -- session A subscribes to Network.requestWillBeSent, session B does not -- and a navigation occurs
THEN: session A receives Network.requestWillBeSent events, session B receives zero Network events

Scenario: Target by index
GIVEN: browser instance "test-01" with 2 page targets
WHEN: run_attach("test-01", target_spec="2", target_by="index")
THEN: attaches to the second page target successfully

Scenario: Auto-select single target
GIVEN: browser instance "test-01" with 1 page target
WHEN: run_attach("test-01") with no target specifier
THEN: attaches to the only page target successfully

Scenario: Ambiguous target
GIVEN: browser instance "test-01" with 2 page targets, no target specifier
WHEN: run_attach("test-01")
THEN: AmbiguousTargetError with both targets listed

Scenario: Instance not found
GIVEN: no instance named "nonexistent"
WHEN: run_attach("nonexistent")
THEN: InstanceNotFoundError raised

Scenario: Subscribe via stdin
GIVEN: attached to "test-01" with no initial subscriptions
WHEN: write "+Page.loadEventFired" to stdin, then navigate the page
THEN: Page.loadEventFired appears on stdout

Scenario: Unsubscribe via stdin
GIVEN: attached to "test-01" with +Network.requestWillBeSent
WHEN: write "-Network.requestWillBeSent" to stdin, then navigate the page
THEN: no Network.requestWillBeSent events appear for the new navigation

Scenario: Clean shutdown on EOF
GIVEN: attached to "test-01"
WHEN: stdin is closed (EOF)
THEN: process exits with code 0, browser still running and accessible via one-shot

### Level 3 -- Formal Test Definitions

```
test_attach_receives_events:
    setup:
        launch browser on test port, register as "test-01"
        navigate to example.com
    action:
        start run_attach("test-01", subscriptions=["Page.loadEventFired"]) as subprocess
        wait for readiness signal on stdout
        navigate to httpbin.org/html via a separate CDPClient connection
        wait 2 seconds
        send EOF to subprocess stdin
        collect stdout
    assertions:
        first line is JSON with status="ready"
        at least one line contains "Page.loadEventFired"
    teardown:
        kill browser

test_cross_session_events:
    setup:
        launch browser, register as "test-01"
    action:
        start run_attach("test-01", subscriptions=["Network.requestWillBeSent"]) as subprocess
        wait for readiness signal
        via a SEPARATE CDPClient (browser-level WS + Target.attachToTarget):
            navigate to example.com
        wait 2 seconds
        send EOF
        collect stdout
    assertions:
        stdout contains at least one Network.requestWillBeSent event
        the event's request URL contains "example.com"
    teardown:
        kill browser

test_event_isolation:
    setup:
        launch browser, register as "test-01"
    action:
        start attach_A with subscriptions=["Network.requestWillBeSent"]
        start attach_B with subscriptions=["Page.loadEventFired"]
        wait for both readiness signals
        navigate via separate CDPClient
        wait 2 seconds
        send EOF to both
        collect stdout from both
    assertions:
        attach_A stdout contains Network.requestWillBeSent events
        attach_A stdout does NOT contain Page.loadEventFired events (unless also subscribed)
        attach_B stdout contains Page.loadEventFired events
        attach_B stdout does NOT contain Network.requestWillBeSent events
    teardown:
        kill browser

test_auto_select_single_target:
    setup:
        launch browser (1 tab), register as "test-01"
    action:
        start run_attach("test-01") with no target specifier
        read first line
    assertions:
        first line is JSON with status="ready" (no AmbiguousTargetError)
    teardown:
        send EOF, kill browser

test_ambiguous_target:
    setup:
        launch browser with 2 tabs, register as "test-01"
    action:
        try:
            await run_attach("test-01")  # no target specifier
        except AmbiguousTargetError as e:
            caught = e
    assertions:
        caught is AmbiguousTargetError
        len(caught.targets) == 2
    teardown:
        kill browser

test_instance_not_found:
    action:
        try:
            await run_attach("nonexistent")
        except InstanceNotFoundError:
            caught = True
    assertions:
        caught is True

test_subscribe_via_stdin:
    setup:
        launch browser, register as "test-01"
    action:
        start run_attach("test-01", subscriptions=[]) with no initial subs
        wait for readiness
        write "+Page.loadEventFired\n" to stdin
        navigate via separate CDPClient
        wait 2 seconds
        send EOF
        collect stdout
    assertions:
        stdout contains Page.loadEventFired event (subscribed via stdin)
    teardown:
        kill browser

test_clean_shutdown:
    setup:
        launch browser, register as "test-01"
    action:
        start run_attach("test-01", subscriptions=["Page.loadEventFired"]) as subprocess
        wait for readiness
        close subprocess stdin (EOF)
        wait for process to exit
    assertions:
        process exit code == 0
        browser still accessible (check_cdp_port returns listening=True)
    teardown:
        kill browser
```

## 5. Feedback Channels

### Visual

Inspect the JSON lines on stdout. Verify events have the expected structure: `{"method": "...", "params": {...}}`. After cross-session navigation, verify the events captured match what the navigation should have produced (e.g., a navigation to example.com produces Network.requestWillBeSent with URL containing "example.com").

### Auditory

Log connection events: browser-level WebSocket connected, Target.attachToTarget succeeded with session ID, domain enables, event subscriptions registered. On error, log the specific failure: instance lookup failed, target resolution failed, WebSocket connection refused. On shutdown, log clean detachment.

### Tactile

Run the full dual-channel workflow:
1. `chrome-agent launch` to start a browser
2. `chrome-agent attach <instance> +Page.loadEventFired +Network.requestWillBeSent > /tmp/events.jsonl &` in background
3. `chrome-agent <instance> Page.navigate '{"url": "https://example.com"}'` via one-shot
4. Read `/tmp/events.jsonl` -- verify it contains the navigation events
5. Kill the attach process
6. Verify the browser is still running via `chrome-agent status`

## 6. Dependencies

| Dependency | What this feature needs from it | Rationale |
|------------|--------------------------------|-----------|
| BRW-04 | `lookup(instance_name)` to resolve instance name to port | Attach needs the browser's CDP port to connect |
| CDP-01 | `CDPClient` for WebSocket connection, `get_ws_url()` for browser-level endpoint, `send()` for Target.attachToTarget and domain enables | The persistent connection and session management are built on CDPClient |

## 7. Scoping Decisions

| Decision | What prompted it | Rationale | Revisit when |
|----------|-----------------|-----------|--------------|
| No command-response on the attach stream | Session mode's mixing of events and command responses caused the flooding problem on Meetup | Attach is for event observation only. Commands go through one-shot. This clean separation is the whole point of the two-channel design. | If a use case emerges that genuinely requires commands and events on the same stream. |
| No built-in event filtering | User explicitly decided not to be opinionated about filtering | chrome-agent passes through subscribed events. Users subscribe selectively and filter downstream with jq, grep, or Python. CDP's `Fetch.enable` with URL patterns is documented as an advanced technique. | If common filtering patterns emerge from real-world use. |
| Domain disable not attempted on unsubscribe | Complexity and risk | When unsubscribing from an event, we remove it from the subscribed set but don't call `Domain.disable` because other subscribed events may still need the domain enabled. Disabling a domain that another subscription depends on would silently break that subscription. | If the event volume from enabled-but-unsubscribed events becomes a performance concern (unlikely -- events are filtered in chrome-agent's event handler, not in Chrome). |
| Subsumes observe.py functionality | observe.py was a standalone script; attach makes event observation a native CLI command | observe.py's tier-based filtering (nav/dev/full) is not replicated in attach -- users compose their own subscription sets. The observe.py script can be retired. | N/A |
| CLI argument parsing is CLI-01's responsibility | `attach` subcommand has `--target`, `--url` flags and `+Event` positional args | The `--target`, `--url` flags and `+Event` positional args for the `attach` subcommand are parsed by CLI-01's routing logic, which extracts flags before passing remaining args to `run_attach`. CDP-04 defines the `run_attach` interface; CLI-01 is responsible for parsing the command line and calling `run_attach` with the extracted values. | N/A |

## 8. Learnings

| # | Topic | Type | Summary | Link |
|---|-------|------|---------|------|
| 1 | Cross-session event delivery | Exploration | Navigation by one CDP session triggers events on other sessions attached to the same page target via Target.attachToTarget -- verified experimentally | /tmp/exp1_cross_session_events.py (session experiment) |
| 2 | Event isolation via Target.attachToTarget | Exploration | Two sessions on the same page target with different subscriptions see only their own events -- verified with dual-session experiment | Learning record: 2026-04-14-chrome-agent-session-mode-for-exploratory-scraping.md |
| 3 | Concurrent attach + one-shot | Exploration | Attach subprocess captures events caused by independent one-shot CLI commands -- the dual-channel pattern works across separate processes | /tmp/exp3_attach_process.py (process experiment) |
| 4 | CDP domain enabling is all-or-nothing | Research | CDP has no per-event filtering at the protocol level. Network.enable delivers ALL network events. Per-event selectivity must be implemented in chrome-agent's event handler (already done in session.py's +/- protocol). Exception: Fetch.enable takes URL patterns. | Sub-agent research from this session |

---

## 9. Implementation Status

**Status:** Not started

## 10. Test Results

### Refinement Log

[Filled during the Implementation Loop]

### Final Test Results

| Test | Result | Notes |
|------|--------|-------|
| | | |

## 11. Review Notes

[Filled during the Implementation Loop]
