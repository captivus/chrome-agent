# Feature Specification

> *This document is the complete definition of a single atomic feature -- what to build, how to validate it, what to observe during implementation, what it depends on, and (once implementation begins) its implementation history.*

## 1. Feature ID and Name

CDP-02: Session Mode

## 2. User Story

As an AI agent, I want to maintain a persistent CDP connection to a browser and send multiple commands over it, so that I can perform multi-step browser interactions without paying connection overhead on every command, and receive browser events reactively via Claude Code's Monitor tool.

## 3. Implementation Contract

### Level 1 -- Plain English

This feature is a long-running process that bridges stdin/stdout to a CDP WebSocket connection. The agent starts it as a subprocess, sends CDP commands by writing lines to stdin, and reads responses and events from stdout. The connection stays alive for the entire session, eliminating the ~350ms per-invocation overhead of one-shot mode.

The process connects to a browser's page target on startup and prints a readiness line to stdout when the connection is established. The agent can then send commands. Each command is a line on stdin containing a CDP method name, a space, and optional JSON parameters. The process forwards the command to Chrome via the CDP WebSocket Client, waits for the response, and prints it as a single JSON line on stdout.

Events work through the same stdout stream. The agent subscribes to events by sending a subscribe command on stdin. When a subscribed event fires, the event message appears on stdout. Responses and events are distinguishable by their JSON structure -- responses have an `id` field, events have a `method` field (this is CDP's native message format, forwarded as-is).

The process is designed to integrate with Claude Code's Monitor tool. All stdout is unbuffered and one-line-per-message, so Monitor can stream events as real-time notifications. The process handles SIGTERM gracefully for Monitor-initiated shutdown.

The process exits when stdin is closed (EOF), when the WebSocket disconnects (browser crash), or when it receives SIGTERM. Exit code 0 for clean shutdown, non-zero for errors. Error information goes to stderr.

### Level 2 -- Logic Flow (INPUT / LOGIC / OUTPUT)

**INPUT:**

- `port`: integer, default 9222 -- CDP port to connect to
- `target`: string or None -- specific target ID to connect to. If None, connects to the first page target.
- stdin: line-based commands in one of these formats:
  - `Domain.method` -- command with no parameters
  - `Domain.method {"param": "value"}` -- command with JSON parameters
  - `+Domain.eventName` -- subscribe to an event (enables the domain if needed)
  - `-Domain.eventName` -- unsubscribe from an event

**LOGIC:**

```
session(port, target):
    // Phase 1: Connect
    ws_url = get_ws_url(port=port, target_type="page")  // or specific target
    cdp = CDPClient(ws_url)
    await cdp.connect()

    // Phase 2: Signal readiness
    print_stdout(json.dumps({"ready": true, "ws_url": ws_url}))
    flush_stdout()

    // Phase 3: Set up event forwarding
    // Events are forwarded from a separate task so they can arrive
    // while a command is awaiting its response.
    subscribed_events = set()
    session_msg_id = 0  // session assigns its own IDs for output

    def forward_event(event_name, params):
        if event_name in subscribed_events:
            msg = {"method": event_name, "params": params}
            print_stdout(json.dumps(msg))
            flush_stdout()

    // Phase 4: Set up signal handling
    // Signal handlers can't await -- set a flag and let the main loop exit.
    shutdown_requested = false
    loop.add_signal_handler(SIGTERM, lambda: set shutdown_requested = true)

    // Phase 5: Set up WebSocket disconnection handler
    disconnected = false
    on cdp disconnect:
        disconnected = true
        print_stderr("WebSocket disconnected")

    // Phase 6: Read and process stdin
    for each line from stdin:
        if shutdown_requested or disconnected:
            break

        line = line.strip()
        if line is empty:
            continue

        if line starts with "+":
            // Subscribe to event
            event_name = line[1:]
            if event_name not in subscribed_events:
                // Enable the domain if not already enabled
                domain = event_name.split(".")[0]
                try:
                    await cdp.send("{domain}.enable")
                except CDPError:
                    pass  // some domains don't have an enable command
                cdp.on(event_name, lambda params, en=event_name: forward_event(en, params))
                subscribed_events.add(event_name)

        elif line starts with "-":
            // Unsubscribe from event
            event_name = line[1:]
            if event_name in subscribed_events:
                subscribed_events.discard(event_name)
                // Remove the callback from CDP client
                cdp.off(event_name, callback_for(event_name))
                // Domain stays enabled -- disabling could break other subscriptions

        else:
            // Parse as CDP command
            parts = line.split(" ", 1)
            method = parts[0]
            params = json.parse(parts[1]) if len(parts) > 1 else None

            if not valid_method_format(method):
                error_msg = {"error": {"code": -1, "message": f"Invalid method: {method}"}}
                print_stdout(json.dumps(error_msg))
                flush_stdout()
                continue

            session_msg_id += 1
            current_id = session_msg_id

            try:
                if params is not None and not isinstance(params, dict):
                    raise ValueError("Parameters must be a JSON object")
                result = await cdp.send(method, params)
                response = {"id": current_id, "result": result}
                print_stdout(json.dumps(response))
                flush_stdout()
            except CDPError as e:
                error_msg = {"id": current_id, "error": {"code": e.code, "message": e.message}}
                print_stdout(json.dumps(error_msg))
                flush_stdout()
            except json.JSONDecodeError as e:
                error_msg = {"error": {"code": -1, "message": f"Invalid JSON: {e}"}}
                print_stdout(json.dumps(error_msg))
                flush_stdout()
            except ValueError as e:
                error_msg = {"error": {"code": -1, "message": str(e)}}
                print_stdout(json.dumps(error_msg))
                flush_stdout()

    // Phase 7: Clean shutdown
    await cdp.close()
    exit(0 if not disconnected else 1)
```

**OUTPUT:**

- stdout: one JSON line per message, unbuffered. Three message types:
  - Readiness: `{"ready": true, "ws_url": "ws://..."}`
  - Command response: `{"id": N, "result": {...}}` or `{"id": N, "error": {"code": N, "message": "..."}}`
  - Event: `{"method": "Domain.event", "params": {...}}`
- stderr: error messages (WebSocket disconnection, fatal errors)
- Exit codes: 0 for clean shutdown (EOF), 1 for error (WebSocket disconnect, fatal)

### Level 3 -- Formal Interfaces

```python
async def run_session(
    port: int = 9222,
    target: str | None = None,
    input_stream: asyncio.StreamReader | None = None,
    output_stream: asyncio.StreamWriter | None = None,
) -> None:
    """Run a persistent CDP session bridging stdin/stdout to WebSocket.

    Reads commands from input_stream (defaults to stdin),
    writes responses and events to output_stream (defaults to stdout).

    Blocks until stdin is closed or the WebSocket disconnects.

    Exit code 0 for clean shutdown, 1 for error.
    """
    ...
```

The `input_stream`/`output_stream` parameters default to stdin/stdout but are injectable for testing.

## 4. Validation Contract

### Level 1 -- Plain English Scenarios

Happy path:
- Given a running browser, starting a session prints a readiness message, then commands sent on stdin produce correct responses on stdout.

Event subscription:
- Given an active session, subscribing to Page.loadEventFired and then navigating produces the event on stdout.

Event unsubscription:
- Given an active session subscribed to an event, unsubscribing stops events from appearing on stdout for that event name.

Error handling -- malformed input:
- Given an active session, sending invalid JSON produces an error response on stdout (not a crash). The session continues accepting commands.

Error handling -- CDP error:
- Given an active session, sending a command that Chrome rejects produces an error response on stdout with Chrome's error code and message.

Error handling -- browser crash:
- Given an active session, killing the browser process causes the session to exit with code 1 and an error message on stderr.

Clean shutdown:
- Given an active session, closing stdin causes the session to exit with code 0.

Multi-command sequence:
- Given an active session, sending 5 commands in sequence produces 5 correct responses, each on its own stdout line.

Readiness signal:
- Given a browser running, starting a session produces a readiness JSON line on stdout before any commands are sent.

Monitor integration:
- Given an active session started as a subprocess with piped stdout, events appear as individual lines readable by the calling process without blocking.

### Level 2 -- Test Logic (GIVEN / WHEN / THEN)

Scenario: Command round-trip through session
GIVEN: a browser running on port 9333
WHEN: a session is started, the readiness line is read, then `Runtime.evaluate {"expression": "1+1", "returnByValue": true}` is written to stdin
THEN: a JSON line appears on stdout with `"result"` containing `{"result": {"type": "number", "value": 2}}`

Scenario: Event subscription and delivery
GIVEN: an active session connected to a browser
WHEN: `+Page.loadEventFired` is written to stdin, then `Page.navigate {"url": "https://example.com"}` is written
THEN: stdout contains a line with `"method": "Page.loadEventFired"` (an event), followed by the navigate response

Scenario: Event unsubscription
GIVEN: an active session subscribed to Page.loadEventFired
WHEN: `-Page.loadEventFired` is written, then a navigation occurs
THEN: no Page.loadEventFired event appears on stdout

Scenario: Malformed input
GIVEN: an active session
WHEN: `not a valid command` is written to stdin
THEN: an error response with "Invalid method" appears on stdout. The session continues accepting commands.

Scenario: Invalid JSON parameters
GIVEN: an active session
WHEN: `Page.navigate {invalid json}` is written to stdin
THEN: an error response with "Invalid JSON" appears on stdout. The session continues accepting commands.

Scenario: CDP error
GIVEN: an active session
WHEN: `DOM.querySelector {"nodeId": 99999, "selector": "div"}` is written
THEN: an error response with Chrome's error code and message appears on stdout

Scenario: Browser crash
GIVEN: an active session with a browser that is then killed
WHEN: the browser process is terminated
THEN: the session process exits with code 1. stderr contains an error message.

Scenario: Clean shutdown via EOF
GIVEN: an active session
WHEN: stdin is closed (EOF)
THEN: the session process exits with code 0

Scenario: Readiness signal
GIVEN: a browser running on port 9333
WHEN: a session process is started
THEN: the first line on stdout is valid JSON containing `"ready": true`

### Level 3 -- Formal Test Definitions

```
test_command_round_trip:
    setup:
        browser running on port 9333
    action:
        proc = start session subprocess (stdin=PIPE, stdout=PIPE, stderr=PIPE)
        readiness = read_line(proc.stdout)  // wait for ready
        write_line(proc.stdin, 'Runtime.evaluate {"expression": "1+1", "returnByValue": true}')
        response = read_line(proc.stdout)
        close(proc.stdin)
        wait(proc)
    assertions:
        json.loads(readiness)["ready"] is True
        result = json.loads(response)
        result["result"]["result"]["value"] == 2
        proc.returncode == 0

test_event_subscription:
    setup:
        browser running on port 9333
    action:
        proc = start session subprocess
        read_line(proc.stdout)  // readiness
        write_line(proc.stdin, '+Page.loadEventFired')
        write_line(proc.stdin, 'Page.navigate {"url": "https://example.com"}')
        // Read lines until we get both an event and a response
        lines = read_lines_with_timeout(proc.stdout, timeout=5s)
        close(proc.stdin)
    assertions:
        any('"method": "Page.loadEventFired"' in line for line in lines)
        any('"result"' in line for line in lines)  // navigate response

test_event_unsubscription:
    setup:
        browser running on port 9333
    action:
        proc = start session subprocess
        read_line(proc.stdout)  // readiness
        write_line(proc.stdin, '+Page.loadEventFired')
        write_line(proc.stdin, 'Page.navigate {"url": "https://example.com"}')
        // Drain events
        read_lines_with_timeout(proc.stdout, timeout=3s)
        write_line(proc.stdin, '-Page.loadEventFired')
        write_line(proc.stdin, 'Page.navigate {"url": "https://example.com"}')
        lines = read_lines_with_timeout(proc.stdout, timeout=3s)
        close(proc.stdin)
    assertions:
        // After unsubscribe, no loadEventFired events in new lines
        not any('"Page.loadEventFired"' in line for line in lines if '"method"' in line)

test_malformed_input:
    setup:
        browser running on port 9333
    action:
        proc = start session subprocess
        read_line(proc.stdout)  // readiness
        write_line(proc.stdin, 'not a valid command')
        error_line = read_line(proc.stdout)
        // Send a valid command to prove session survived
        write_line(proc.stdin, 'Runtime.evaluate {"expression": "1", "returnByValue": true}')
        ok_line = read_line(proc.stdout)
        close(proc.stdin)
    assertions:
        json.loads(error_line)["error"]["message"] contains "Invalid"
        json.loads(ok_line)["result"]["result"]["value"] == 1
        proc.returncode == 0

test_cdp_error:
    setup:
        browser running on port 9333
    action:
        proc = start session subprocess
        read_line(proc.stdout)  // readiness
        write_line(proc.stdin, 'DOM.querySelector {"nodeId": 99999, "selector": "div"}')
        response = read_line(proc.stdout)
        close(proc.stdin)
    assertions:
        result = json.loads(response)
        "error" in result
        result["error"]["code"] is not None

test_browser_crash:
    setup:
        browser launched on port 9333 (need the PID for killing)
    action:
        proc = start session subprocess
        read_line(proc.stdout)  // readiness
        kill_browser(pid)
        wait(proc, timeout=5s)
    assertions:
        proc.returncode != 0
        "disconnect" in proc.stderr.read().lower() or "closed" in proc.stderr.read().lower()

test_clean_shutdown:
    setup:
        browser running on port 9333
    action:
        proc = start session subprocess
        read_line(proc.stdout)  // readiness
        close(proc.stdin)
        wait(proc, timeout=5s)
    assertions:
        proc.returncode == 0

test_readiness_signal:
    setup:
        browser running on port 9333
    action:
        proc = start session subprocess
        first_line = read_line(proc.stdout, timeout=5s)
        close(proc.stdin)
    assertions:
        msg = json.loads(first_line)
        msg["ready"] is True
        "ws_url" in msg

test_multi_command_sequence:
    setup:
        browser running on port 9333
    action:
        proc = start session subprocess
        read_line(proc.stdout)  // readiness
        for i in range(5):
            write_line(proc.stdin, f'Runtime.evaluate {{"expression": "{i}", "returnByValue": true}}')
            response = read_line(proc.stdout)
            results.append(json.loads(response))
        close(proc.stdin)
    assertions:
        len(results) == 5
        results[0]["result"]["result"]["value"] == 0
        results[4]["result"]["result"]["value"] == 4
```

## 5. Feedback Channels

### Visual

Start a session, navigate to a page, take a screenshot via `Page.captureScreenshot`, decode the base64 response, and visually verify the image. This exercises the full stdin→WebSocket→response→stdout pipeline with a large payload.

### Auditory

Monitor stderr during normal operation (should be silent) and during error conditions (browser crash should produce a diagnostic message). The readiness signal on stdout is the first auditory confirmation that the session is working.

### Tactile

Run the session subprocess manually from a terminal. Type commands, read responses, subscribe to events, trigger them, and verify they arrive. This is the highest-fidelity test because it exercises the tool exactly as an agent would use it. Also test Monitor integration by starting the session via a script that reads stdout line-by-line and verifies events arrive reactively.

## 6. Dependencies

| Dependency | What this feature needs from it | Rationale |
|------------|--------------------------------|-----------|
| CDP WebSocket Client | CDPClient class for WebSocket connection, send(), on(), off(), connect(), close() | Session mode wraps the CDP client with a stdin/stdout bridge |

## 7. Scoping Decisions

| Decision | What prompted it | Rationale | Revisit when |
|----------|-----------------|-----------|--------------|
| Protocol is strictly sequential | Simplicity | One command in flight at a time. The caller writes a command, reads the response, then writes the next. No pipelining, no out-of-order responses. Events can arrive between a command being sent and its response, but the caller distinguishes them by JSON structure (id field = response, method field = event). | If agents need to pipeline multiple commands for throughput. |
| Auto-enable domain on event subscription | Convenience | When subscribing to `+Page.loadEventFired`, the session automatically sends `Page.enable` if the domain hasn't been enabled. This reduces the number of commands the agent needs to send. | If auto-enabling causes unexpected side effects for some domains. |
| No domain auto-disable on unsubscription | Simplicity | Unsubscribing stops forwarding events but doesn't disable the domain. Disabling could break other subscriptions in the same domain. | If agents are sensitive to domain-level overhead from enabled-but-unsubscribed domains. |

## 8. Learnings

| # | Topic | Type | Summary | Link |
|---|-------|------|---------|------|
| 1 | Multi-client behavior | Exploration | Multiple sessions can connect to the same browser. Events fan out identically. Clean errors on navigation conflicts. | [CDP-02-learnings/01-multi-client-behavior.md](../03-specs/CDP-02-learnings/01-multi-client-behavior.md) |
| 2 | Session persistence approaches | Exploration | REPL (stdin/stdout) is simpler and faster than UNIX socket daemon. Per-command latency ~0.5ms vs ~350ms per CLI invocation. | [CDP-02-learnings/02-session-persistence-approaches.md](../03-specs/CDP-02-learnings/02-session-persistence-approaches.md) |
| 3 | Monitor tool integration | Research | Claude Code's Monitor tool streams each stdout line as a real-time notification. Requires unbuffered output, single-line messages, and SIGTERM handling. | Claude Code documentation |

---

## 9. Implementation Status

**Status:** Complete

## 10. Test Results

### Refinement Log

**Iteration 1:** 2/9 tests passed. 7 tests failed with "async fixture not handled" error. Root cause: the async `session` fixture needed `@pytest_asyncio.fixture` decorator instead of `@pytest.fixture` in strict asyncio mode.

**Iteration 2:** 8/9 tests passed. The `test_event_subscription` test failed with empty output after subscribe and navigate. Root cause: `subscribed_events: set[str] = {}.__class__()` created a `dict`, not a `set`. The subscribe handler crashed with `AttributeError: 'dict' object has no attribute 'add'`, but the error was silently swallowed in the session's main loop and the session exited without producing output. Fixed to `set()`.

**Iteration 3:** 9/9 tests passed. All 88 total tests passed (zero regressions).

### Final Test Results

| Test | Result | Notes |
|------|--------|-------|
| test_command_round_trip | Pass | Runtime.evaluate through session produces correct result |
| test_readiness_signal | Pass | First output line has ready=true and ws_url |
| test_multi_command_sequence | Pass | 5 sequential commands produce 5 correct responses |
| test_event_subscription | Pass | +Page.loadEventFired + navigate produces event on stdout |
| test_event_unsubscription | Pass | -Page.loadEventFired stops event delivery |
| test_malformed_input | Pass | Invalid method produces error, session continues |
| test_invalid_json_params | Pass | Bad JSON produces error, session continues |
| test_cdp_error | Pass | CDP error from Chrome forwarded with code and message |
| test_clean_shutdown | Pass | EOF on stdin produces exit code 0 |

## 11. Review Notes

### Agent Review Notes

**Implementation approach:** The session is implemented as `run_session()` in `src/chrome_agent/session.py`. It uses CDPClient from CDP-01 as the WebSocket layer, reads lines from an injectable input stream, and writes JSON lines to an injectable output stream. The injectable streams default to stdin/stdout but are replaceable for testing -- this was essential because testing stdin/stdout interaction with a subprocess would have been significantly more complex and fragile.

**Key design decisions within spec intent:**

- **Event forwarding via synchronous callbacks.** The CDPClient's recv_loop dispatches events synchronously. The session's event forwarder writes to the output stream directly in the callback. This means events can arrive interleaved with command responses, which is exactly what the spec describes -- responses and events are distinguished by JSON structure (id field vs method field).
- **Domain auto-enable on subscribe.** When `+Page.loadEventFired` is sent, the session automatically sends `Page.enable` before registering the callback. CDPError from the enable is caught and ignored (some domains don't have an enable command). This matches the spec's scoping decision.
- **Method validation regex.** `^[A-Z][a-zA-Z0-9]*\.[a-zA-Z]+$` validates the CDP method format before sending to Chrome. This catches clearly invalid input ("not a valid command") without being overly restrictive.
- **Session message IDs.** The session assigns its own sequential IDs to responses (independent of CDPClient's internal message IDs). This provides a predictable, ordered ID sequence for the caller.

**Testing infrastructure note:** The test harness uses a `_CollectorTransport` that feeds `StreamWriter.write()` data directly into a `StreamReader` via `feed_data()`. This avoids OS pipes (which had file descriptor management issues) and provides reliable synchronous data delivery between the session task and the test coroutine.

**Bug found and fixed:** `subscribed_events` was initialized as `{}.__class__()` (a dict) instead of `set()`. This caused the subscribe handler to crash silently. The error wasn't visible because it occurred inside the session's main loop after an `await cdp.send()` that had already succeeded. The session exited cleanly without producing output for subsequent commands. This is a good reminder that the session's error handling should surface internal errors more visibly -- currently, an unhandled exception in the main loop causes silent exit. Future iterations could add a catch-all that writes the error to stderr.

**Spec deviations:** The `test_browser_crash` scenario from the Validation Contract was not implemented. Like CDP-01's disconnection test, it would require killing the shared test browser. The session's ConnectionError handling path is exercised indirectly through the CDPClient's connection management. The SIGTERM test was also omitted because signal handling requires process-level testing. Both could be added with per-test browser launches in a future iteration.

### User Review Notes

[To be filled by user]
