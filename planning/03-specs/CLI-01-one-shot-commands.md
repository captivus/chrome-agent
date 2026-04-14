# Feature Specification

> *This document is the complete definition of a single atomic feature -- what to build, how to validate it, what to observe during implementation, what it depends on, and (once implementation begins) its implementation history.*

## 1. Feature ID and Name

CLI-01: One-Shot Commands

## 2. User Story

As an AI agent or developer, I want a command-line entry point that routes to the right action -- whether that's launching a browser, checking status, starting a session, discovering the protocol, cleaning up stale sessions, or sending a single CDP command -- so that I can interact with chrome-agent from a shell or subprocess.

## 3. Implementation Contract

### Level 1 -- Plain English

This feature is the CLI entry point -- the `chrome-agent` command. It parses command-line arguments, determines what the user wants to do, and routes to the appropriate feature.

There are two kinds of commands: operational commands and CDP method calls.

Operational commands are words without dots: `launch`, `status`, `session`, `help`, `cleanup`. Each routes to its corresponding feature.

CDP method calls contain a dot: `Page.navigate`, `DOM.querySelector`, etc. For these, the CLI connects to the browser (first page target by default), sends the single command, prints the JSON response to stdout, and disconnects. This is the one-shot mode -- convenient for single operations but with higher overhead (~350ms) than session mode.

The CLI uses argparse or equivalent for operational commands, and falls back to raw argument handling for CDP method calls (since the method name is freeform and params are a JSON string).

### Level 2 -- Logic Flow (INPUT / LOGIC / OUTPUT)

**INPUT:**

- Command-line arguments: `chrome-agent <command> [args...]`
- For operational commands: `chrome-agent launch [--port N] [--fingerprint PATH] [--headless]`
- For operational commands: `chrome-agent status [--port N]`
- For operational commands: `chrome-agent session [--port N]`
- For operational commands: `chrome-agent help [query]`
- For operational commands: `chrome-agent cleanup`
- For CDP methods: `chrome-agent Page.navigate '{"url": "https://example.com"}'`

**LOGIC:**

```
main():
    args = parse_command_line()
    command = args[0] if args else "help"

    if command == "launch":
        parse launch flags (--port, --fingerprint, --headless)
        await launch_browser(port, fingerprint, headless)
        print result (port, version)

    elif command == "status":
        parse status flags (--port)
        status = check_cdp_port(port)
        if status.listening:
            print("Browser running on port {port}")
            print("  Version: {status.browser_version}")
            print("  URL:     {status.page_url}")
            print("  Title:   {status.page_title}")
        else:
            print("No browser running on port {port}")

    elif command == "session":
        parse session flags (--port)
        await run_session(port)

    elif command == "help":
        query = args[1] if len(args) > 1 else None
        if query is None:
            // No query -- try browser, fall back to static usage
            try:
                discover_protocol(port, query=None)
            except ConnectionError:
                print_static_usage()  // available commands, syntax, link to CDP docs
        else:
            // Query specified -- requires a browser
            discover_protocol(port, query)

    elif command == "cleanup":
        cleanup_sessions()
        print("Stale session directories cleaned up")

    elif "." in command:
        // CDP method call
        method = command
        params_str = args[1] if len(args) > 1 else None
        params = json.parse(params_str) if params_str else None

        if params is not None and not isinstance(params, dict):
            print_stderr("Error: parameters must be a JSON object")
            exit(1)

        port = get_port_from_flags_or_default()  // --port or 9222
        ws_url = get_ws_url(port=port)
        async with CDPClient(ws_url) as cdp:
            try:
                result = await cdp.send(method, params)
                print(json.dumps(result, indent=2))
            except CDPError as e:
                print_stderr(f"CDP error {e.code}: {e.message}")
                exit(1)

    else:
        print_stderr(f"Unknown command: {command}")
        print_stderr("Run 'chrome-agent help' to see available commands")
        exit(1)
```

**OUTPUT:**

- stdout: command results (JSON for CDP commands, formatted text for operational commands)
- stderr: error messages
- Exit code: 0 for success, 1 for errors

### Level 3 -- Formal Interfaces

```python
def main() -> None:
    """CLI entry point. Registered as 'chrome-agent' console script."""
    ...
```

The CLI uses asyncio.run() for async operations. The entry point is synchronous (console_scripts requirement) and wraps the async dispatch.

Console script registration in pyproject.toml:

```toml
[project.scripts]
chrome-agent = "chrome_agent.cli:main"
```

## 4. Validation Contract

### Level 1 -- Plain English Scenarios

Operational command routing:
- Each operational command (launch, status, session, help, cleanup) routes to its corresponding feature function.

CDP method call:
- A command with a dot is treated as a CDP method, connected to the browser, sent, and the response printed as JSON.

Unknown command:
- A command without a dot that isn't an operational command produces an error message and exit code 1.

Malformed JSON:
- CDP method with unparseable JSON params produces an error message and exit code 1.

No browser for CDP method:
- A CDP method call when no browser is running produces an error and exit code 1.

Help as default:
- Running `chrome-agent` with no arguments shows help.

### Level 2 -- Test Logic (GIVEN / WHEN / THEN)

Scenario: CDP method one-shot
GIVEN: a browser running on port 9333
WHEN: `chrome-agent --port 9333 Runtime.evaluate '{"expression": "1+1", "returnByValue": true}'` is run
THEN: stdout contains JSON with result.value == 2, exit code 0

Scenario: Status command
GIVEN: a browser running on port 9333
WHEN: `chrome-agent status --port 9333` is run
THEN: stdout contains "Browser running" and the browser version, exit code 0

Scenario: Status no browser
GIVEN: nothing on port 9444
WHEN: `chrome-agent status --port 9444` is run
THEN: stdout contains "No browser running", exit code 0

Scenario: Unknown command
GIVEN: any state
WHEN: `chrome-agent foobar` is run
THEN: stderr contains "Unknown command", exit code 1

Scenario: Malformed JSON
GIVEN: a browser running
WHEN: `chrome-agent Page.navigate '{bad json}'` is run
THEN: stderr contains an error about invalid JSON, exit code 1

Scenario: No arguments
GIVEN: any state
WHEN: `chrome-agent` is run with no arguments
THEN: help output appears (domain listing or usage message)

### Level 3 -- Formal Test Definitions

```
test_cdp_one_shot:
    setup:
        browser running on port 9333
    action:
        result = subprocess.run(
            ["chrome-agent", "--port", "9333", "Runtime.evaluate",
             '{"expression": "1+1", "returnByValue": true}'],
            capture_output=True, text=True)
    assertions:
        result.returncode == 0
        data = json.loads(result.stdout)
        data["result"]["value"] == 2

test_status_running:
    setup:
        browser running on port 9333
    action:
        result = subprocess.run(
            ["chrome-agent", "status", "--port", "9333"],
            capture_output=True, text=True)
    assertions:
        result.returncode == 0
        "Browser running" in result.stdout

test_status_not_running:
    action:
        result = subprocess.run(
            ["chrome-agent", "status", "--port", "9444"],
            capture_output=True, text=True)
    assertions:
        result.returncode == 0
        "No browser running" in result.stdout

test_unknown_command:
    action:
        result = subprocess.run(
            ["chrome-agent", "foobar"],
            capture_output=True, text=True)
    assertions:
        result.returncode == 1
        "Unknown command" in result.stderr

test_malformed_json:
    setup:
        browser running on port 9333
    action:
        result = subprocess.run(
            ["chrome-agent", "--port", "9333", "Page.navigate", "{bad}"],
            capture_output=True, text=True)
    assertions:
        result.returncode == 1
        "error" in result.stderr.lower() or "json" in result.stderr.lower()

test_cdp_no_browser:
    action:
        result = subprocess.run(
            ["chrome-agent", "--port", "9444", "Runtime.evaluate",
             '{"expression": "1"}'],
            capture_output=True, text=True)
    assertions:
        result.returncode == 1
        "error" in result.stderr.lower() or "no browser" in result.stderr.lower()

test_no_arguments:
    action:
        result = subprocess.run(
            ["chrome-agent"],
            capture_output=True, text=True)
    assertions:
        result.returncode == 0
        len(result.stdout) > 0  // some output (help or usage)
```

## 5. Feedback Channels

### Visual

Not applicable -- CLI output is text. The test assertions verify content.

### Auditory

Run each operational command and each error case from a terminal. Verify the output is clear, the error messages are diagnostic, and exit codes are correct.

### Tactile

Use chrome-agent from a terminal for a real workflow: `chrome-agent launch`, `chrome-agent status`, `chrome-agent help Page`, `chrome-agent Page.navigate '{"url": "https://example.com"}'`, `chrome-agent Page.captureScreenshot '{"format": "png"}'`. This exercises the full CLI surface as an agent would use it.

## 6. Dependencies

| Dependency | What this feature needs from it | Rationale |
|------------|--------------------------------|-----------|
| CDP WebSocket Client | CDPClient, get_ws_url for one-shot CDP commands | One-shot mode connects, sends, prints, disconnects |
| Browser Launch | launch_browser, cleanup_sessions for the launch and cleanup commands | CLI routes to these functions |
| Browser Status | check_cdp_port for the status command | CLI routes to this function |
| Session Mode | run_session for the session command | CLI routes to this function |
| Protocol Discovery | discover_protocol for the help command | CLI routes to this function |

## 7. Scoping Decisions

| Decision | What prompted it | Rationale | Revisit when |
|----------|-----------------|-----------|--------------|
| --port flag is global, placed before the command | Simplicity and parsing clarity | `chrome-agent --port 9333 Page.navigate ...` -- the global flag precedes the command word. This avoids argparse ambiguity between subcommand flags and positional arguments. All commands that need a port use the same one. | If the CLI needs to address multiple browsers simultaneously. |
| One-shot CDP prints raw JSON, not formatted | Consistency | The response is Chrome's JSON, passed through. Agents parse JSON easily. Pretty-printing with indent=2 for human readability. | If agents need a different output format. |
| No --target flag in this iteration | Simplicity | One-shot and session mode connect to the first page target. Target selection is done via CDP's Target domain within a session. | If agents frequently need to select specific targets from the CLI. |

## 8. Learnings

| # | Topic | Type | Summary | Link |
|---|-------|------|---------|------|
| 1 | Per-invocation overhead | Exploration | One-shot CLI invocations cost ~350ms each (Python startup + imports + WebSocket connection). Session mode amortizes this to ~0.5ms per command. | [CDP-02-learnings/02-session-persistence-approaches.md](../03-specs/CDP-02-learnings/02-session-persistence-approaches.md) |

---

## 9. Implementation Status

**Status:** Complete

## 10. Test Results

### Refinement Log

**Iteration 1:** All tests passed on the first run. No refinement needed.

- Rewrote `src/chrome_agent/cli.py` to route to new feature modules (launcher, session, protocol, cdp_client)
- Wrote 8 tests in `tests/test_cli.py` using subprocess invocation
- Old Playwright-based command tests (test_commands.py) continue to pass since they test the functions directly, not through CLI
- All 8 CLI tests passed, all 118 total tests passed (zero regressions)

### Final Test Results

| Test | Result | Notes |
|------|--------|-------|
| test_cdp_one_shot | Pass | Runtime.evaluate returns correct result via CLI |
| test_status_running | Pass | Reports "Browser running" with version |
| test_status_not_running | Pass | Reports "No browser running" |
| test_unknown_command | Pass | Error message and exit code 1 |
| test_malformed_json | Pass | JSON parse error and exit code 1 |
| test_cdp_no_browser | Pass | Connection error and exit code 1 |
| test_no_arguments | Pass | Shows usage/help text |
| test_cleanup | Pass | Reports "cleaned up" |

## 11. Review Notes

### Agent Review Notes

**Clean rewrite of cli.py.** The old CLI had ~280 lines of Playwright-specific command dispatch. The new CLI is ~170 lines that route to feature modules. The architectural shift is from "CLI does everything" to "CLI routes to features."

**Command routing logic.** The key design: if the command contains a dot, it's a CDP method call (one-shot mode). Otherwise, it's an operational command (launch, status, session, help, cleanup). This is simple, unambiguous, and matches how CDP methods are named (always `Domain.method`).

**Backward compatibility.** The old Playwright-based commands (navigate, click, fill, etc.) are no longer accessible through the CLI. They're replaced by CDP one-shot mode: `chrome-agent Page.navigate '{"url": "..."}'` instead of `chrome-agent navigate "https://..."`. The old `commands.py` module and its tests still exist but are orphaned from the CLI. They can be removed in a future cleanup.

**Help command dual-mode.** `chrome-agent help` with no args tries to connect to a browser for protocol listing. If no browser is available, it falls back to static usage text. `chrome-agent help Page` requires a browser and fails with a clear error if none is running.

**Exit code discipline.** Success = 0, errors = 1. Error messages go to stderr, results go to stdout. This is critical for agent integration -- agents check exit codes and parse stdout.

### User Review Notes

[To be filled by user]
