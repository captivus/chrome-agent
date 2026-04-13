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

### Level 2 -- Logic Flow (INPUT / LOGIC / OUTPUT)

**INPUT:**

- `port`: integer, default 9222 -- the CDP port to query
- `query`: string or None -- None for all domains, "Domain" for a domain's contents, "Domain.method" for a specific command/event

**LOGIC:**

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
    port: int = 9222,
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
