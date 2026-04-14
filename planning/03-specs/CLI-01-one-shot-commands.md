# Feature Specification

> *This document is the complete definition of a single atomic feature -- what to build, how to validate it, what to observe during implementation, what it depends on, and (once implementation begins) its implementation history.*

## 1. Feature ID and Name

CLI-01: One-Shot Commands

## 2. User Story

As an AI agent or developer, I want a command-line entry point that routes to the right action -- whether that's launching a browser, checking status, attaching to a session, discovering the protocol, cleaning up stale sessions, or sending a single CDP command -- so that I can interact with chrome-agent from a shell or subprocess.

## 3. Implementation Contract

### Level 1 -- Plain English

This feature is the CLI entry point -- the `chrome-agent` command. It parses command-line arguments, determines what the user wants to do, and routes to the appropriate feature.

There are two kinds of commands: operational commands and CDP method calls.

Operational commands are words without dots: `launch`, `status`, `attach`, `help`, `cleanup`. Each routes to its corresponding feature.

CDP method calls contain a dot: `Page.navigate`, `DOM.querySelector`, etc. For these, the CLI connects to the browser (first page target by default), sends the single command, prints the JSON response to stdout, and disconnects. This is the one-shot mode -- convenient for single operations but with higher overhead (~50-80ms, dominated by Python startup) than attach mode.

The CLI uses argparse or equivalent for operational commands, and falls back to raw argument handling for CDP method calls (since the method name is freeform and params are a JSON string).

#### Iteration 2 Updates

**Instance name routing replaces `--port` for one-shot commands.** Instead of specifying `--port` globally, one-shot CDP commands now address a browser instance by name. The instance name is resolved to a port via the Instance Registry (BRW-04). Example: `chrome-agent aroundchicago.tech-01 Page.navigate '{"url": "https://example.com"}'`.

The `--port` flag is removed from the global position. It remains available only on the `launch` command as an override for the registry-assigned port.

**Target specifier support.** One-shot commands accept `--target <id-prefix-or-index>` and `--url <substring>` to specify which page target in a multi-tab browser. When there is only one tab, no specifier is needed.

**Isolated sessions.** One-shot CDP commands connect to the browser-level WebSocket, create a temporary CDP session via `Target.attachToTarget`, send the command through that session, and detach. This provides event isolation from other participants.

**`session` replaced by `attach`.** The `session` operational command is replaced by `attach`, which routes to Attach Mode (CDP-04).

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

> **Note:** The original LOGIC block below is from iteration 1 and is **superseded by the Iteration 2 Updates LOGIC** that follows it. The iteration 1 pseudocode references `--port` and `session` which are replaced by instance-name routing and `attach` in iteration 2. It is retained here for historical reference only -- the Iteration 2 Updates LOGIC is the authoritative version.

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

#### Iteration 2 Updates

**Updated INPUT:**

- For operational commands: `chrome-agent launch [--port PORT] [--fingerprint PATH] [--headless]`
- For operational commands: `chrome-agent attach <instance> [+Event ...] [--target SPEC] [--url SUBSTRING]`
- For operational commands: `chrome-agent status [<instance>]`
- For operational commands: `chrome-agent help [<instance-or-domain> [Domain | Domain.method]]`
  - Disambiguation rule: if the first arg after `help` exists in the registry, treat it as an instance name (and the next arg, if any, as a domain query). Otherwise, treat it as a domain query.
- For operational commands: `chrome-agent cleanup`
- For CDP methods: `chrome-agent <instance> Domain.method '{"params"}'`

**Updated LOGIC:**

The routing logic changes to support instance name resolution. The key change: the first argument is checked against known operational commands first. If it contains a dot, it is treated as a CDP one-shot with the default instance. Otherwise, it is treated as an instance name and the second argument as the CDP method.

```
OPERATIONAL_COMMANDS = {"launch", "attach", "status", "help", "cleanup"}

main():
    args = parse_command_line()

    // Phase 0: Extract global flags
    args, target_spec = extract_flag(args, "--target")  // returns (remaining_args, value_or_None)
    args, url_spec = extract_flag(args, "--url")

    // --target and --url are mutually exclusive
    if target_spec is not None and url_spec is not None:
        print_stderr("Error: Cannot specify both --target and --url")
        exit(1)

    target_by = "id" if target_spec else ("url" if url_spec else None)
    target_value = target_spec or url_spec

    command = args[0] if args else "help"

    if command in OPERATIONAL_COMMANDS:
        route_operational_command(command, args[1:])

        // Status routing within route_operational_command:
        // if command == "status":
        //     if args:
        //         // Instance name provided -- filter to that instance
        //         get_instance_status(instance_name=args[0])
        //     else:
        //         // No args -- show all instances
        //         get_instance_status()

        // Help disambiguation within route_operational_command:
        // if command == "help":
        //     arg = args[0] if args else None
        //     if arg is None:
        //         // No query -- try browser, fall back to static usage
        //         try: discover_protocol(query=None)
        //         except ConnectionError: print_static_usage()
        //     elif registry.exists(arg):
        //         // arg is an instance name -- use it for protocol discovery
        //         instance_name = arg
        //         domain_query = args[1] if len(args) > 1 else None
        //         discover_protocol(instance_name, query=domain_query)
        //     else:
        //         // arg is not in registry -- treat as domain query
        //         discover_protocol(query=arg)

    elif "." in command:
        // Bare CDP method -- use default instance
        method = command
        params_str = args[1] if len(args) > 1 else None
        run_one_shot(instance_name=None, method, params_str, target_spec, url_spec)

    else:
        // Treat as instance name; next arg must be CDP method
        instance_name = command
        if len(args) < 2 or "." not in args[1]:
            print_stderr(f"Unknown command: {command}")
            print_stderr("Run 'chrome-agent help' to see available commands")
            exit(1)
        method = args[1]
        params_str = args[2] if len(args) > 2 else None
        run_one_shot(instance_name, method, params_str, target_spec, url_spec)


resolve_default_instance():
    // When no instance name is provided, resolve to the single running instance.
    instances = registry.enumerate_instances()
    alive = [i for i in instances if i.alive]
    if len(alive) == 0:
        print_stderr("No instances registered. Launch one with: chrome-agent launch")
        exit(1)
    elif len(alive) == 1:
        return alive[0].name
    else:
        names = ", ".join(i.name for i in alive)
        print_stderr(f"Multiple instances running. Specify one: {names}")
        exit(1)


run_one_shot(instance_name, method, params_str, target_spec, url_spec):
    params = json.parse(params_str) if params_str else None
    if params is not None and not isinstance(params, dict):
        print_stderr("Error: parameters must be a JSON object")
        exit(1)

    if instance_name is None:
        instance_name = resolve_default_instance()

    info = registry.lookup(instance_name)  // InstanceInfo with port, ws_url
    browser_ws_url = info.browser_ws_url   // browser-level WebSocket

    async with CDPClient(browser_ws_url) as cdp:
        // Get page targets
        targets = await cdp.send("Target.getTargets")
        page_targets = [t for t in targets["targetInfos"] if t["type"] == "page"]

        // Resolve target
        if target_spec or url_spec:
            target_id = resolve_target(page_targets, target_spec, url_spec)
        else:
            target_id = page_targets[0]["targetId"]

        // Create isolated session
        result = await cdp.send("Target.attachToTarget",
                                {"targetId": target_id, "flatten": True})
        session_id = result["sessionId"]

        try:
            response = await cdp.send(method, params, session_id=session_id)
            print(json.dumps(response, indent=2))
        except CDPError as e:
            print_stderr(f"CDP error {e.code}: {e.message}")
            exit(1)
        finally:
            await cdp.send("Target.detachFromTarget",
                           {"sessionId": session_id})
```

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

#### Iteration 2 Updates

```python
def main() -> None:
    """CLI entry point. Routes operational commands and instance-based CDP one-shots."""
    ...

def resolve_default_instance() -> str:
    """When no instance name is provided, resolve to the single running instance.
    Errors if zero or multiple instances are alive."""
    ...

def run_one_shot(
    instance_name: str | None,
    method: str,
    params_str: str | None,
    target_spec: str | None,
    url_spec: str | None,
) -> None:
    """Execute a single CDP command via an isolated session and print the result.
    If instance_name is None, calls resolve_default_instance()."""
    ...
```

External interfaces consumed:

```python
# From BRW-04 (Instance Registry)
def lookup(instance_name: str) -> InstanceInfo:
    """Look up a registered instance by name. Raises InstanceNotFoundError."""

def enumerate_instances() -> list[InstanceInfo]:
    """List all registered instances with their alive/dead status."""

def exists(instance_name: str) -> bool:
    """Check whether an instance name exists in the registry."""

# From CDP-04 (Attach Mode) -- shared target resolution logic
def resolve_target(page_targets, target_spec, target_by) -> str:
    """Resolve target specifier to target ID. Raises AmbiguousTargetError or TargetNotFoundError."""
```

## 4. Validation Contract

### Level 1 -- Plain English Scenarios

Operational command routing:
- Each operational command (launch, status, attach, help, cleanup) routes to its corresponding feature function.

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

#### Iteration 2 Updates

Instance-name routing:
- A CDP command addressed to a registered instance resolves the instance name to a port via the registry and executes the command.

Instance not found:
- A CDP command addressed to an unregistered instance name produces an error message and exit code 1.

Target specifier:
- `--target <id-prefix>` selects the matching page target in a multi-tab browser.
- `--url <substring>` selects the page whose URL contains the substring.
- When neither is provided and only one tab exists, it is selected automatically.
- When neither is provided and multiple tabs exist, an error is produced listing available targets.

Attach routing:
- `chrome-agent attach <instance>` routes to Attach Mode (CDP-04).

Isolated session:
- A one-shot command creates a temporary CDP session via `Target.attachToTarget` and detaches after the command completes, ensuring event isolation.

Default instance resolution:
- A bare CDP method with no instance name resolves to the single alive instance if exactly one exists.
- If no instances are alive, an error directs the user to launch one.
- If multiple instances are alive, an error lists the available names.

Flag extraction:
- `--target` and `--url` flags are extracted from argv before routing, so they work regardless of position in the argument list.
- `--target` and `--url` are mutually exclusive. If both are provided, the CLI errors with "Cannot specify both --target and --url".

Help disambiguation:
- `chrome-agent help <arg>` checks whether `<arg>` exists in the instance registry. If it does, `<arg>` is treated as an instance name (and a subsequent arg, if any, as a domain query). If it does not, `<arg>` is treated as a domain query.

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

#### Iteration 2 Updates

Scenario: Instance-name CDP one-shot
GIVEN: a browser registered as "mysite-01" in the Instance Registry
WHEN: `chrome-agent mysite-01 Runtime.evaluate '{"expression": "1+1", "returnByValue": true}'` is run
THEN: stdout contains JSON with result.value == 2, exit code 0

Scenario: Instance not found
GIVEN: no instance named "ghost-99" in the registry
WHEN: `chrome-agent ghost-99 Runtime.evaluate '{"expression": "1"}'` is run
THEN: stderr contains an error about instance not found, exit code 1

Scenario: Target specifier by ID prefix
GIVEN: a browser registered as "mysite-01" with two page targets (IDs "ABC123..." and "DEF456...")
WHEN: `chrome-agent mysite-01 --target ABC Page.getFrameTree` is run
THEN: the command executes against the target whose ID starts with "ABC", exit code 0

Scenario: Target specifier by URL substring
GIVEN: a browser registered as "mysite-01" with tabs open to "https://example.com/a" and "https://example.com/b"
WHEN: `chrome-agent mysite-01 --url "/b" Page.getFrameTree` is run
THEN: the command executes against the tab whose URL contains "/b", exit code 0

Scenario: Ambiguous target (no specifier, multiple tabs)
GIVEN: a browser registered as "mysite-01" with two page targets
WHEN: `chrome-agent mysite-01 Page.getFrameTree` is run (no --target or --url)
THEN: stderr contains an error listing available targets, exit code 1

Scenario: Mutual exclusivity of --target and --url
GIVEN: a browser registered as "mysite-01"
WHEN: `chrome-agent mysite-01 --target ABC --url "/b" Page.getFrameTree` is run
THEN: stderr contains "Cannot specify both --target and --url", exit code 1

Scenario: Attach command routing
GIVEN: a browser registered as "mysite-01"
WHEN: `chrome-agent attach mysite-01` is run
THEN: the command routes to Attach Mode (CDP-04)

Scenario: Bare CDP method with single running instance
GIVEN: exactly one alive instance is registered in the registry
WHEN: `chrome-agent Runtime.evaluate '{"expression": "1+1", "returnByValue": true}'` is run
THEN: the single alive instance is resolved and the command executes, exit code 0

Scenario: Bare CDP method with no running instances
GIVEN: no alive instances are registered in the registry
WHEN: `chrome-agent Runtime.evaluate '{"expression": "1"}'` is run
THEN: stderr contains "No instances registered. Launch one with: chrome-agent launch", exit code 1

Scenario: Bare CDP method with multiple running instances
GIVEN: multiple alive instances ("site-01", "site-02") are registered in the registry
WHEN: `chrome-agent Runtime.evaluate '{"expression": "1"}'` is run
THEN: stderr contains "Multiple instances running. Specify one:" and lists the available names, exit code 1

Scenario: Help with domain query (not an instance name)
GIVEN: no instance named "Page" exists in the registry, a browser is running
WHEN: `chrome-agent help Page` is run
THEN: "Page" is treated as a domain query and protocol help for the Page domain is displayed

Scenario: Help with instance name
GIVEN: an instance named "mysite-01" exists in the registry
WHEN: `chrome-agent help mysite-01` is run
THEN: "mysite-01" is treated as an instance name and protocol help is displayed for that instance

Scenario: Help with instance name and domain query
GIVEN: an instance named "mysite-01" exists in the registry
WHEN: `chrome-agent help mysite-01 Page` is run
THEN: protocol help for the Page domain is displayed, discovered from the "mysite-01" instance

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

#### Iteration 2 Updates

```
test_instance_name_one_shot:
    setup:
        browser registered as "mysite-01" in Instance Registry
    action:
        result = subprocess.run(
            ["chrome-agent", "mysite-01", "Runtime.evaluate",
             '{"expression": "1+1", "returnByValue": true}'],
            capture_output=True, text=True)
    assertions:
        result.returncode == 0
        data = json.loads(result.stdout)
        data["result"]["value"] == 2

test_instance_not_found:
    action:
        result = subprocess.run(
            ["chrome-agent", "ghost-99", "Runtime.evaluate",
             '{"expression": "1"}'],
            capture_output=True, text=True)
    assertions:
        result.returncode == 1
        "not found" in result.stderr.lower() or "unknown" in result.stderr.lower()

test_target_specifier_by_id:
    setup:
        browser registered as "mysite-01" with two page targets
    action:
        result = subprocess.run(
            ["chrome-agent", "mysite-01", "--target", "ABC",
             "Page.getFrameTree"],
            capture_output=True, text=True)
    assertions:
        result.returncode == 0
        // Response corresponds to the target with ID starting "ABC"

test_target_specifier_by_url:
    setup:
        browser registered as "mysite-01" with tabs at /a and /b
    action:
        result = subprocess.run(
            ["chrome-agent", "mysite-01", "--url", "/b",
             "Page.getFrameTree"],
            capture_output=True, text=True)
    assertions:
        result.returncode == 0
        // Response corresponds to the /b tab

test_ambiguous_target:
    setup:
        browser registered as "mysite-01" with two page targets
    action:
        result = subprocess.run(
            ["chrome-agent", "mysite-01", "Page.getFrameTree"],
            capture_output=True, text=True)
    assertions:
        result.returncode == 1
        // stderr lists available targets

test_target_and_url_mutual_exclusivity:
    action:
        result = subprocess.run(
            ["chrome-agent", "mysite-01", "--target", "ABC",
             "--url", "/b", "Page.getFrameTree"],
            capture_output=True, text=True)
    assertions:
        result.returncode == 1
        "Cannot specify both --target and --url" in result.stderr

test_attach_routing:
    setup:
        browser registered as "mysite-01"
    action:
        // Verify that attach routes to CDP-04 Attach Mode
        result = subprocess.run(
            ["chrome-agent", "attach", "mysite-01", "--help"],
            capture_output=True, text=True)
    assertions:
        result.returncode == 0
        // Output reflects attach mode options

test_bare_cdp_method_single_instance:
    setup:
        exactly one alive instance registered in the registry
    action:
        result = subprocess.run(
            ["chrome-agent", "Runtime.evaluate",
             '{"expression": "1+1", "returnByValue": true}'],
            capture_output=True, text=True)
    assertions:
        result.returncode == 0
        data = json.loads(result.stdout)
        data["result"]["value"] == 2

test_bare_cdp_method_no_instances:
    setup:
        no alive instances in the registry
    action:
        result = subprocess.run(
            ["chrome-agent", "Runtime.evaluate",
             '{"expression": "1"}'],
            capture_output=True, text=True)
    assertions:
        result.returncode == 1
        "No instances registered" in result.stderr

test_bare_cdp_method_multiple_instances:
    setup:
        two alive instances ("site-01", "site-02") in the registry
    action:
        result = subprocess.run(
            ["chrome-agent", "Runtime.evaluate",
             '{"expression": "1"}'],
            capture_output=True, text=True)
    assertions:
        result.returncode == 1
        "Multiple instances running" in result.stderr
        "site-01" in result.stderr
        "site-02" in result.stderr

test_help_domain_query:
    setup:
        no instance named "Page" in the registry; a browser running
    action:
        result = subprocess.run(
            ["chrome-agent", "help", "Page"],
            capture_output=True, text=True)
    assertions:
        result.returncode == 0
        // Output contains Page domain protocol info

test_help_instance_name:
    setup:
        instance "mysite-01" registered in the registry
    action:
        result = subprocess.run(
            ["chrome-agent", "help", "mysite-01"],
            capture_output=True, text=True)
    assertions:
        result.returncode == 0
        // Output contains protocol info from mysite-01

test_help_instance_name_with_domain_query:
    setup:
        instance "mysite-01" registered in the registry
    action:
        result = subprocess.run(
            ["chrome-agent", "help", "mysite-01", "Page"],
            capture_output=True, text=True)
    assertions:
        result.returncode == 0
        // Output contains Page domain protocol info from mysite-01
```

## 5. Feedback Channels

### Visual

Not applicable -- CLI output is text. The test assertions verify content.

### Auditory

Run each operational command and each error case from a terminal. Verify the output is clear, the error messages are diagnostic, and exit codes are correct.

### Tactile

Use chrome-agent from a terminal for a real workflow: `chrome-agent launch`, `chrome-agent status`, `chrome-agent help Page`, `chrome-agent Page.navigate '{"url": "https://example.com"}'`, `chrome-agent Page.captureScreenshot '{"format": "png"}'`. This exercises the full CLI surface as an agent would use it.

#### Iteration 2 Updates

Updated tactile workflow: `chrome-agent launch --port 9333`, `chrome-agent status mysite-01`, `chrome-agent mysite-01 Page.navigate '{"url": "https://example.com"}'`, `chrome-agent mysite-01 --url "example" Page.captureScreenshot '{"format": "png"}'`, `chrome-agent attach mysite-01`. This exercises instance-name routing, target specifiers, and attach mode.

## 6. Dependencies

| Dependency | What this feature needs from it | Rationale |
|------------|--------------------------------|-----------|
| CDP WebSocket Client | CDPClient, get_ws_url for one-shot CDP commands | One-shot mode connects, sends, prints, disconnects |
| Browser Launch | launch_browser, cleanup_sessions for the launch and cleanup commands | CLI routes to these functions |
| Browser Status | check_cdp_port for the status command | CLI routes to this function |
| Session Mode | run_session for the session command | CLI routes to this function |
| Protocol Discovery | discover_protocol for the help command | CLI routes to this function |

#### Iteration 2 Updates

| Dependency | What this feature needs from it | Rationale |
|------------|--------------------------------|-----------|
| Instance Registry (BRW-04) | `lookup(instance_name)` to resolve instance names to ports and WebSocket URLs | One-shot commands address browsers by instance name, not port |
| Attach Mode (CDP-04) | `attach` command routes to CDP-04; shared `resolve_target` logic for target specifier resolution | The `attach` operational command delegates to CDP-04; target resolution is shared between one-shot and attach |

## 7. Scoping Decisions

| Decision | What prompted it | Rationale | Revisit when |
|----------|-----------------|-----------|--------------|
| --port flag is global, placed before the command | Simplicity and parsing clarity | `chrome-agent --port 9333 Page.navigate ...` -- the global flag precedes the command word. This avoids argparse ambiguity between subcommand flags and positional arguments. All commands that need a port use the same one. | If the CLI needs to address multiple browsers simultaneously. |
| One-shot CDP prints raw JSON, not formatted | Consistency | The response is Chrome's JSON, passed through. Agents parse JSON easily. Pretty-printing with indent=2 for human readability. | If agents need a different output format. |
| No --target flag in this iteration | Simplicity | One-shot and session mode connect to the first page target. Target selection is done via CDP's Target domain within a session. | If agents frequently need to select specific targets from the CLI. |

#### Iteration 2 Updates

| Decision | What prompted it | Rationale | Revisit when |
|----------|-----------------|-----------|--------------|
| `--port` removed from global position, retained on `launch` only | Instance Registry makes port management implicit | Agents address browsers by name, not port. The registry resolves names to ports. `--port` on `launch` is an override for cases where a specific port is needed. | If there is a use case for bypassing the registry entirely. |
| `session` replaced by `attach` | Alignment with CDP-04 (Attach Mode) naming | `attach` better describes the operation -- connecting to an existing browser. `session` was ambiguous (it could mean creating a browser session or a CDP session). | N/A -- this is a permanent rename. |
| `--target` and `--url` flags added to one-shot commands | Multi-tab browser support | Agents working with multiple tabs need to specify which target to send commands to. The flags use the same resolution logic as Attach Mode (CDP-04). | If more complex target selection is needed (e.g., by title, by type). |
| Isolated sessions via `Target.attachToTarget` for one-shot | Event isolation in multi-participant scenarios | Without isolated sessions, one-shot commands share the page-level WebSocket and can receive events intended for other participants. Creating a temporary session via `Target.attachToTarget` provides clean isolation. | If the overhead of attach/detach proves problematic (unlikely -- it is sub-millisecond). |

## 8. Learnings

| # | Topic | Type | Summary | Link |
|---|-------|------|---------|------|
| 1 | Per-invocation overhead | Exploration | One-shot CLI invocations cost ~50-80ms each (Python startup dominates). Attach mode amortizes this to ~0.5ms per command. | [CDP-02-learnings/02-session-persistence-approaches.md](../03-specs/CDP-02-learnings/02-session-persistence-approaches.md) |

---

## 9. Implementation Status

**Iteration 1 Status:** Complete

**Iteration 2 Status:** Not started

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
