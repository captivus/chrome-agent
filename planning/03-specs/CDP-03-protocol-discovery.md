# Feature Specification

> *This document is the complete definition of a single atomic feature -- what to build, how to validate it, what to observe during implementation, what it depends on, and (once implementation begins) its implementation history.*

## 1. Feature ID and Name

CDP-03: Protocol Discovery

## 2. User Story

As an AI agent, I want to query the browser to learn what CDP commands, events, and types are available -- with their parameter names, types, and descriptions -- so that I can compose CDP operations correctly without consulting external documentation.

## 3. Implementation Contract

### Level 1 -- Plain English

This feature queries a running browser's `/json/protocol` HTTP endpoint, which returns the complete CDP protocol schema as JSON. It parses this schema and presents it in a readable format at three levels of detail: all domains, a specific domain's commands and events, or a specific command's full parameter signature.

This is a synchronous, stdlib-only operation -- HTTP GET, JSON parsing, text formatting. No WebSocket connection needed. It fails with a clear error if no browser is running.

The output is designed for both human and agent consumption -- structured enough for an agent to parse, readable enough for a human scanning for the right command.

#### Iteration 2 Updates

In iteration 2, the port is no longer specified directly by the user. Instead, the user provides an instance name (e.g., `chrome-agent help myapp Page`), and Protocol Discovery resolves the instance name to a port via the Instance Registry (BRW-04). Resolution follows a precedence chain: instance name (explicit lookup) > auto-select single live instance > explicit `port` argument > static usage fallback. When no instance is specified and exactly one instance is alive, that instance is used automatically. When no instance is specified and zero or multiple instances are alive (a non-empty registry with all dead instances counts as zero alive), the feature checks whether an explicit `port` was provided -- if so, that port is used as a fallback (e.g., `discover_protocol(port=9333)` connects to port 9333 even if auto-selection finds nothing). When `port` is None (the default) and auto-selection fails, the feature falls back to static usage text -- the same behavior as when no browser is running.

### Level 2 -- Logic Flow (INPUT / LOGIC / OUTPUT)

**INPUT:**

- `port`: integer or None, default None -- the CDP port to query
- `query`: string or None -- None for all domains, "Domain" for a domain's contents, "Domain.method" for a specific command/event

#### Iteration 2 Updates

**INPUT (updated):**

- `instance_name`: string or None -- the name of a registered browser instance to query
- `port`: integer or None, default None -- the CDP port to query (retained for backward compatibility; ignored when `instance_name` is provided). When None and auto-selection fails, falls back to static usage text. When explicitly provided and auto-selection fails, uses the provided port.
- `query`: string or None -- unchanged from iteration 1

**LOGIC (instance resolution, prepended to existing logic):**

```
// _resolve_port is a private helper in protocol.py

_resolve_port(instance_name, port):
    if instance_name is not None:
        info = registry.lookup(instance_name)  // raises InstanceNotFoundError
        return info.port

    // No instance specified -- try auto-selection
    instances = registry.enumerate_instances()
    live = [i for i in instances if i.alive]
    if len(live) == 1:
        return live[0].port

    // Zero or multiple instances alive -- check for explicit port fallback
    if port is not None:
        return port

    // port is None and auto-selection failed -- fall back to static usage text
    return None
```

When `_resolve_port` returns None, the caller prints static usage text and exits rather than attempting the HTTP fetch. When it returns a port, the existing `discover(port, query)` logic proceeds unchanged.

**Location note:** `_resolve_port` is a private helper function in `protocol.py`.

**LOGIC (original, unchanged):**

```
discover(port, query):
    // Fetch protocol schema
    try:
        response = http_get(http://localhost:{port}/json/protocol, timeout=5s)
        schema = json_parse(response)
    except connection_refused:
        raise ConnectionError("No browser running on port {port}")

    domains = schema["domains"]

    if query is None:
        // List all domains
        for domain in domains:
            print("{domain.domain}: {domain.description}")

    elif "." not in query:
        // List commands and events in a specific domain
        domain = find_domain(domains, name=query)
        if domain is None:
            raise ValueError("Unknown domain: {query}")

        print("Domain: {domain.domain}")
        if domain.description:
            print(domain.description)

        if domain.commands:
            print("\nCommands:")
            for cmd in domain.commands:
                flags = []
                if cmd.experimental: flags.append("experimental")
                if cmd.deprecated: flags.append("deprecated")
                flag_str = f" ({', '.join(flags)})" if flags else ""
                print("  {domain.domain}.{cmd.name}{flag_str}")
                if cmd.description:
                    print("    {cmd.description}")

        if domain.events:
            print("\nEvents:")
            for evt in domain.events:
                flags = []
                if evt.experimental: flags.append("experimental")
                if evt.deprecated: flags.append("deprecated")
                flag_str = f" ({', '.join(flags)})" if flags else ""
                print("  {domain.domain}.{evt.name}{flag_str}")
                if evt.description:
                    print("    {evt.description}")

    else:
        // Show details for a specific command or event
        domain_name, method_name = query.split(".", 1)
        domain = find_domain(domains, name=domain_name)
        if domain is None:
            raise ValueError("Unknown domain: {domain_name}")

        // Search commands first, then events
        item = find_in(domain.commands, name=method_name)
              or find_in(domain.events, name=method_name)
        if item is None:
            raise ValueError("Unknown method: {query}")

        print("{domain_name}.{method_name}")
        if item.description:
            print(item.description)
        if item.experimental:
            print("(experimental)")

        if item.parameters:
            print("\nParameters:")
            for param in item.parameters:
                required = "" if param.optional else " (required)"
                type_str = param.type or param.$ref or "object"
                print("  {param.name}: {type_str}{required}")
                if param.description:
                    print("    {param.description}")

        if item.returns:
            print("\nReturns:")
            for ret in item.returns:
                type_str = ret.type or ret.$ref or "object"
                print("  {ret.name}: {type_str}")
                if ret.description:
                    print("    {ret.description}")
```

**OUTPUT:**

- Formatted text printed to stdout
- On error: raises ConnectionError (no browser), ValueError (unknown domain or method)

### Level 3 -- Formal Interfaces

```python
def discover_protocol(
    port: int | None = None,
    query: str | None = None,
) -> None:
    """Query the browser's protocol schema and print formatted output.

    query=None: list all domains
    query="Page": list commands and events in the Page domain
    query="Page.navigate": show full details for Page.navigate

    Synchronous. Uses stdlib urllib.

    Raises ConnectionError if no browser is running on the port.
    Raises ValueError if the domain or method is not found.
    """
    ...


def fetch_protocol_schema(port: int = 9222) -> dict:
    """Fetch the raw protocol schema JSON from the browser.

    Returns the parsed JSON dict from /json/protocol.
    Synchronous. Uses stdlib urllib.

    Raises ConnectionError if no browser is running on the port.
    """
    ...
```

#### Iteration 2 Updates

```python
def discover_protocol(
    port: int | None = None,
    query: str | None = None,
    instance_name: str | None = None,
) -> None:
    """Query the browser's protocol schema and print formatted output.

    Port resolution follows a precedence chain:
        1. instance_name -- explicit lookup via the Instance Registry (BRW-04).
           When instance_name is provided, it takes precedence over port.
        2. Auto-select -- when no instance_name is provided and exactly one
           live instance exists, that instance is used automatically.
        3. Explicit port -- when auto-selection fails (zero or multiple alive)
           and the caller provided a non-None port, that port is used as a
           fallback (e.g., discover_protocol(port=9333) connects to 9333).
        4. Static usage text -- when port is None (the default) and none of
           the above resolve a port, prints usage text and returns.

    query=None: list all domains
    query="Page": list commands and events in the Page domain
    query="Page.navigate": show full details for Page.navigate

    Synchronous. Uses stdlib urllib.

    Raises ConnectionError if no browser is running on the resolved port.
    Raises InstanceNotFoundError if instance_name is not in the registry.
    Raises ValueError if the domain or method is not found.
    """
    ...
```

The `port` parameter is retained for backward compatibility and direct programmatic use. When `instance_name` is provided, it takes precedence and `port` is ignored. The `fetch_protocol_schema()` signature is unchanged -- it always takes a port, and instance resolution happens in the caller.

## 4. Validation Contract

### Level 1 -- Plain English Scenarios

Happy path -- list domains:
- Given a running browser, querying with no filter returns a list of domain names with descriptions. The list includes well-known domains like Page, DOM, Runtime, Network.

Happy path -- domain detail:
- Given a running browser, querying for "Page" returns the commands and events in the Page domain, including Page.navigate, Page.captureScreenshot, Page.loadEventFired.

Happy path -- method detail:
- Given a running browser, querying for "Page.navigate" returns its parameters (url required, referrer optional, etc.) and return values (frameId, loaderId, etc.).

Error -- no browser:
- Given no browser running, querying raises ConnectionError.

Error -- unknown domain:
- Given a running browser, querying for "FakeDomain" raises ValueError.

Error -- unknown method:
- Given a running browser, querying for "Page.fakeMethod" raises ValueError.

### Level 2 -- Test Logic (GIVEN / WHEN / THEN)

Scenario: List all domains
GIVEN: a browser running on port 9333
WHEN: discover_protocol(port=9333) is called
THEN: stdout contains "Page", "DOM", "Runtime", "Network" among the listed domains

Scenario: Domain detail
GIVEN: a browser running on port 9333
WHEN: discover_protocol(port=9333, query="Page") is called
THEN: stdout contains "Page.navigate" and "Page.captureScreenshot" under Commands, and "Page.loadEventFired" under Events

Scenario: Method detail
GIVEN: a browser running on port 9333
WHEN: discover_protocol(port=9333, query="Page.navigate") is called
THEN: stdout contains "url" as a required parameter of type string, and "frameId" in the returns section

Scenario: No browser
GIVEN: nothing running on port 9444
WHEN: discover_protocol(port=9444) is called
THEN: ConnectionError is raised

Scenario: Unknown domain
GIVEN: a browser running on port 9333
WHEN: discover_protocol(port=9333, query="FakeDomain") is called
THEN: ValueError is raised with "Unknown domain" in the message

Scenario: Unknown method
GIVEN: a browser running on port 9333
WHEN: discover_protocol(port=9333, query="Page.fakeMethod") is called
THEN: ValueError is raised with "Unknown method" in the message

### Level 3 -- Formal Test Definitions

```
test_list_domains:
    setup:
        browser running on port 9333
    action:
        capture stdout from discover_protocol(port=9333)
    assertions:
        "Page" in stdout
        "DOM" in stdout
        "Runtime" in stdout
        "Network" in stdout

test_domain_detail:
    setup:
        browser running on port 9333
    action:
        capture stdout from discover_protocol(port=9333, query="Page")
    assertions:
        "Page.navigate" in stdout
        "Page.captureScreenshot" in stdout
        "Commands:" in stdout
        "Events:" in stdout

test_method_detail:
    setup:
        browser running on port 9333
    action:
        capture stdout from discover_protocol(port=9333, query="Page.navigate")
    assertions:
        "url" in stdout
        "string" in stdout
        "(required)" in stdout or "url" appears without "(optional)"
        "frameId" in stdout

test_no_browser:
    action:
        try:
            discover_protocol(port=9444)
            raised = False
        except ConnectionError:
            raised = True
    assertions:
        raised is True

test_unknown_domain:
    setup:
        browser running on port 9333
    action:
        try:
            discover_protocol(port=9333, query="FakeDomain")
            raised = False
        except ValueError as e:
            raised = True
            error = e
    assertions:
        raised is True
        "Unknown domain" in str(error)

test_fetch_raw_schema:
    setup:
        browser running on port 9333
    action:
        schema = fetch_protocol_schema(port=9333)
    assertions:
        "domains" in schema
        len(schema["domains"]) > 0
        any(d["domain"] == "Page" for d in schema["domains"])

test_fetch_no_browser:
    action:
        try:
            fetch_protocol_schema(port=9444)
            raised = False
        except ConnectionError:
            raised = True
    assertions:
        raised is True

test_unknown_method:
    setup:
        browser running on port 9333
    action:
        try:
            discover_protocol(port=9333, query="Page.fakeMethod")
            raised = False
        except ValueError as e:
            raised = True
            error = e
    assertions:
        raised is True
        "Unknown method" in str(error)
```

#### Iteration 2 Updates

**Plain English Scenarios:**

Instance name routing:
- Given a registered instance "myapp" running on port 9333, querying with `instance_name="myapp"` and `query="Page"` returns the Page domain detail -- identical to querying with `port=9333`.

Auto-selection of single instance:
- Given exactly one live registered instance, querying with no instance name and no port automatically uses that instance and returns results normally.

Fallback -- no instance specified, multiple live:
- Given two or more live registered instances, querying with no instance name prints static usage text.

Fallback -- no instance specified, none live:
- Given no live registered instances, querying with no instance name prints static usage text.

Unknown instance:
- Given no instance named "ghost" in the registry, querying with `instance_name="ghost"` raises InstanceNotFoundError.

**Test Logic (GIVEN / WHEN / THEN):**

Scenario: Instance name routing
GIVEN: a registered instance "myapp" with port 9333, browser running on port 9333
WHEN: discover_protocol(instance_name="myapp", query="Page") is called
THEN: stdout contains "Page.navigate" and "Page.captureScreenshot" (same as port-based query)

Scenario: Auto-select single instance
GIVEN: exactly one live registered instance "solo" with port 9333, browser running on port 9333
WHEN: discover_protocol() is called with no instance_name and no port override
THEN: stdout contains domain names (Page, DOM, etc.) -- the single instance was used automatically

Scenario: Multiple live instances, no instance specified
GIVEN: two live registered instances "app1" and "app2"
WHEN: discover_protocol() is called with no instance_name
THEN: static usage text is printed, no protocol fetch is attempted

Scenario: No live instances, no instance specified
GIVEN: no live registered instances
WHEN: discover_protocol() is called with no instance_name
THEN: static usage text is printed, no protocol fetch is attempted

Scenario: Unknown instance name
GIVEN: no instance named "ghost" in the registry
WHEN: discover_protocol(instance_name="ghost") is called
THEN: InstanceNotFoundError is raised

**Formal Test Definitions:**

```
test_instance_name_routing:
    setup:
        registry contains instance "myapp" with port 9333
        browser running on port 9333
    action:
        capture stdout from discover_protocol(instance_name="myapp", query="Page")
    assertions:
        "Page.navigate" in stdout
        "Page.captureScreenshot" in stdout

test_auto_select_single_instance:
    setup:
        registry contains exactly one live instance "solo" with port 9333
        browser running on port 9333
    action:
        capture stdout from discover_protocol()
    assertions:
        "Page" in stdout
        "DOM" in stdout

test_multiple_instances_no_selection:
    setup:
        registry contains live instances "app1" (port 9333) and "app2" (port 9444)
    action:
        capture stdout from discover_protocol()
    assertions:
        stdout contains static usage text
        no HTTP request was made to /json/protocol

test_no_instances_no_selection:
    setup:
        registry contains no live instances
    action:
        capture stdout from discover_protocol()
    assertions:
        stdout contains static usage text
        no HTTP request was made to /json/protocol

test_unknown_instance:
    setup:
        registry contains no instance named "ghost"
    action:
        try:
            discover_protocol(instance_name="ghost")
            raised = False
        except InstanceNotFoundError:
            raised = True
    assertions:
        raised is True

test_explicit_port_fallback:
    setup:
        registry contains no live instances (empty or all dead)
    action:
        // Explicit port provided -- should connect to that port even though
        // auto-selection finds nothing
        capture stdout from discover_protocol(port=9333, query="Page")
    assertions:
        // The call attempts to connect to port 9333 (may raise ConnectionError
        // if no browser is running there, but it does NOT fall back to static
        // usage text -- the explicit port is used)
        either "Page.navigate" in stdout (if browser is running on 9333)
        or ConnectionError is raised (if no browser on 9333)
        // Crucially: static usage text is NOT printed

test_instance_name_takes_precedence_over_port:
    setup:
        registry contains instance "myapp" with port 9333
        browser running on port 9333
    action:
        // Both instance_name and port are provided -- instance_name wins
        capture stdout from discover_protocol(instance_name="myapp", port=9500, query="Page")
    assertions:
        "Page.navigate" in stdout
        // The call connected to port 9333 (from the registry), not port 9500
```

## 5. Feedback Channels

### Visual

Run the discovery against a real browser and read the output. Is it scannable? Can you quickly find the command you're looking for? Is the parameter information clear enough to compose a command from it?

### Auditory

Errors should clearly indicate what went wrong -- "No browser running on port 9222" or "Unknown domain: FakeDomain" -- not a stack trace.

### Tactile

Use the discovery output to compose a CDP command you haven't used before. If the output is good enough, you should be able to go from `chrome-agent help Page.captureScreenshot` to a working command without consulting any external documentation.

## 6. Dependencies

| Dependency | What this feature needs from it | Rationale |
|------------|--------------------------------|-----------|
| None | N/A | Uses stdlib HTTP to query the browser directly. Does not depend on CDP-01 or any other chrome-agent feature. |

#### Iteration 2 Updates

| Dependency | What this feature needs from it | Rationale |
|------------|--------------------------------|-----------|
| BRW-04 (Instance Registry) | `lookup(instance_name)` to resolve an instance name to port; `enumerate_instances()` to list live instances for auto-selection when no instance is specified. | The CLI syntax changes from `--port` to instance names. The registry is the single source of truth for mapping instance names to connection details. |

## 7. Scoping Decisions

| Decision | What prompted it | Rationale | Revisit when |
|----------|-----------------|-----------|--------------|
| Print to stdout, no structured return | Simplicity | This feature is primarily a CLI tool for agents and developers. Returning structured data would be useful for programmatic use, but the primary consumer reads text. The raw schema is available via fetch_protocol_schema() for programmatic access. | If agents need to parse the discovery output programmatically (they can use fetch_protocol_schema instead). |
| No type expansion | Complexity | When a parameter references a type (e.g., `$ref: "Page.FrameId"`), the output shows the reference name but doesn't expand the type definition inline. This keeps output concise. | If agents struggle to understand referenced types without seeing their definitions. |

## 8. Learnings

| # | Topic | Type | Summary | Link |
|---|-------|------|---------|------|
| 1 | Protocol schema sources | Research | Chrome serves its complete protocol schema as JSON at /json/protocol. Always accurate for the connected browser version. | [GEN-01-learnings/01-protocol-schema-sources.md](../03-specs/GEN-01-learnings/01-protocol-schema-sources.md) |

---

## 9. Implementation Status

**Status:** Complete

## 10. Test Results

### Refinement Log

**Iteration 1:** All tests passed on the first run. No refinement needed.

- Wrote `discover_protocol()` and `fetch_protocol_schema()` in new module `src/chrome_agent/protocol.py`
- Three presentation levels: all domains, domain detail (commands + events), method detail (parameters + returns)
- Helper functions for domain lookup and flag formatting
- Wrote 8 tests in `tests/test_protocol_discovery.py` covering the full Validation Contract
- Visual verification: output is scannable at all levels, parameter info sufficient to compose commands
- Tactile verification: used Page.navigate and Page.captureScreenshot output to confirm composability
- All 8 tests passed, all 79 tests total passed (zero regressions)

### Final Test Results

| Test | Result | Notes |
|------|--------|-------|
| test_list_domains | Pass | Output includes Page, DOM, Runtime, Network |
| test_domain_detail | Pass | Page domain shows navigate, captureScreenshot, Commands:, Events: |
| test_method_detail | Pass | Page.navigate shows url (required, string), frameId in returns |
| test_no_browser | Pass | ConnectionError on unused port |
| test_unknown_domain | Pass | ValueError with "Unknown domain" |
| test_unknown_method | Pass | ValueError with "Unknown method" |
| test_fetch_raw_schema | Pass | Returns valid schema with domains array including Page |
| test_fetch_no_browser | Pass | ConnectionError on unused port |

## 11. Review Notes

### Agent Review Notes

**Clean implementation:** The protocol discovery feature is straightforward -- HTTP GET, JSON parse, text formatting. The `/json/protocol` endpoint returns a well-structured schema that maps directly to the three levels of detail the spec requires. No surprises during implementation.

**Output quality observation:** Multi-line descriptions from Chrome's schema (e.g., the DOM domain description spans multiple lines) flow naturally into the output. The formatting handles this correctly without explicit line-wrapping logic because Python's `print()` outputs the string as-is, and Chrome's descriptions include their own newlines.

**Scoping decision validated:** The spec's "no type expansion" decision was correct. Parameters that reference types (e.g., `transitionType: TransitionType`, `clip: Viewport`) show the type name but don't expand it. The output is still usable -- an agent knows the parameter name and type, and can use `fetch_protocol_schema()` programmatically if it needs the full type definition.

**Integration note for CLI-01:** The `discover_protocol()` function prints to stdout, which is exactly what CLI-01 needs. The `help` command in CLI-01 will route to `discover_protocol()` with the appropriate query parameter. The error handling (ConnectionError, ValueError) is already in the form CLI-01 can catch and present.

**Integration note for GEN-01:** The `fetch_protocol_schema()` function returns the raw JSON dict that GEN-01's code generator needs as input. This function was specified in CDP-03 but designed with GEN-01's consumption in mind -- it provides the same structured data that the learning document confirmed is sufficient for code generation.

### User Review Notes

[To be filled by user]
