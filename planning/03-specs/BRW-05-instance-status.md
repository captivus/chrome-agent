# Feature Specification

> *This document is the complete definition of a single atomic feature -- what to build, how to validate it, what to observe during implementation, what it depends on, and (once implementation begins) its implementation history.*

## 1. Feature ID and Name

BRW-05: Instance Status

## 2. User Story

As an AI agent or developer, I want to list all registered browser instances with their page targets, so that I can discover what's running, identify specific page targets by ID, and decide which instance or target to attach to or send commands to.

## 3. Implementation Contract

### Level 1 -- Plain English

This feature lists all registered browser instances and enriches the registry data with live browser state. It replaces BRW-02 (Browser Status), which checked a single port -- Instance Status operates on all named instances from the registry.

For each registered instance, the feature reports the instance name, CDP port, and whether the Chrome process is alive or dead. For each alive instance, it queries Chrome's `/json` HTTP endpoint to enumerate page targets and reports each target's ID (truncated to 8 characters), a numeric index (for shorthand reference), URL, and title.

An optional instance name argument filters output to a single instance. When no argument is provided, all registered instances are listed.

Output is formatted text for human consumers (when stdout is a TTY) and structured JSON for programmatic consumers (when stdout is not a TTY). Dead instances are always reported as dead rather than silently omitted -- this surfaces stale state and prompts the user to run cleanup.

The feature is synchronous and uses stdlib only (urllib for HTTP requests, json for parsing). It does not require Playwright or a WebSocket connection.

### Level 2 -- Logic Flow (INPUT / LOGIC / OUTPUT)

**INPUT:**

- `instance_name`: optional string -- if provided, show only this instance. If omitted, show all instances.
- `is_tty`: bool -- whether stdout is a TTY (determines output format)
- Registry data: comes from BRW-04's `enumerate_instances()` (returns `list[InstanceInfo]`) and `lookup()` (for single-instance filtering)

**LOGIC:**

```
TARGET_ID_LENGTH = 8  // truncation length for target IDs

@dataclass
class PageTarget:
    target_id: str       // full target ID from Chrome
    short_id: str        // first 8 characters of target_id, uppercased
    index: int           // 1-based numeric index within the instance
    url: str
    title: str

@dataclass
class InstanceStatus:
    name: str
    port: int
    alive: bool
    targets: list[PageTarget]  // empty if dead or if query fails


query_targets(port) -> list[PageTarget]:
    // Query Chrome's /json endpoint for page targets
    try:
        response = http_get(http://localhost:{port}/json, timeout=2s)
        all_targets = json_parse(response)
    except any error:
        return []  // browser alive but /json failed -- return empty

    // Filter for page targets only (ignore service workers, iframes, etc.)
    pages = [t for t in all_targets if t.get("type") == "page"]

    results = []
    for index, target in enumerate(pages, start=1):
        target_id = target["id"]
        results.append(PageTarget(
            target_id=target_id,
            short_id=target_id[:TARGET_ID_LENGTH].upper(),
            index=index,
            url=target.get("url", ""),
            title=target.get("title", ""),
        ))
    return results


get_instance_status(instance_name=None) -> list[InstanceStatus]:
    // Phase 1: Get instances from registry
    if instance_name is not None:
        // Single instance lookup
        try:
            info = registry.lookup(instance_name)
        except InstanceNotFoundError:
            raise  // propagate -- caller handles the error message
        // lookup() returns alive=True by default without checking PID liveness.
        // Re-check here so the alive field reflects actual process state.
        info.alive = process_is_running(info.pid)
        instances = [info]
    else:
        instances = registry.enumerate_instances()

    // Phase 2: Enrich with live target data
    results = []
    for info in instances:
        if info.alive:
            targets = query_targets(info.port)
        else:
            targets = []

        results.append(InstanceStatus(
            name=info.name,
            port=info.port,
            alive=info.alive,
            targets=targets,
        ))

    return results


format_text(statuses: list[InstanceStatus]) -> str:
    // Human-readable text output
    lines = []
    for status in statuses:
        // Instance header line
        header = f"{status.name}  port {status.port}"
        if not status.alive:
            header += "  DEAD"
        lines.append(header)

        // Target lines (only for alive instances with targets)
        if status.alive and status.targets:
            for target in status.targets:
                // Pad columns for alignment
                line = f"  [{target.index}] {target.short_id}  {target.url}  \"{target.title}\""
                lines.append(line)

        // Blank line between instances (but not after the last one)
        lines.append("")

    // Remove trailing blank line
    if lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


format_json(statuses: list[InstanceStatus]) -> str:
    // Structured JSON output for programmatic consumers
    data = []
    for status in statuses:
        entry = {
            "name": status.name,
            "port": status.port,
            "alive": status.alive,
            "targets": [
                {
                    "id": t.short_id,
                    "full_id": t.target_id,
                    "index": t.index,
                    "url": t.url,
                    "title": t.title,
                }
                for t in status.targets
            ],
        }
        data.append(entry)
    return json_dumps(data, indent=2)


// CLI entry point integration
status_command(instance_name=None):
    statuses = get_instance_status(instance_name)

    if no statuses and instance_name is None:
        print("No instances registered. Launch one with: chrome-agent launch")
        return

    if stdout is a TTY:
        print(format_text(statuses))
    else:
        print(format_json(statuses))
```

**OUTPUT:**

- `get_instance_status()`: returns `list[InstanceStatus]` -- one entry per instance, each with name, port, alive flag, and a list of page targets (empty for dead instances or when `/json` query fails).
- Text format (TTY): formatted multi-line string as shown in the example output.
- JSON format (non-TTY): JSON array of instance objects, each with `name`, `port`, `alive`, and `targets` array.
- When no instances are registered: a helpful message directing the user to `chrome-agent launch`.
- When a named instance is not found: `InstanceNotFoundError` propagates from the registry with available instance names.

### Level 3 -- Formal Interfaces

```python
from dataclasses import dataclass, field

TARGET_ID_LENGTH = 8


@dataclass
class PageTarget:
    """A single page target within a browser instance."""
    target_id: str       # full target ID from Chrome's /json endpoint
    short_id: str        # first TARGET_ID_LENGTH chars, uppercased
    index: int           # 1-based numeric index within the instance
    url: str
    title: str


@dataclass
class InstanceStatus:
    """Status of a registered browser instance with its page targets."""
    name: str
    port: int
    alive: bool
    targets: list[PageTarget] = field(default_factory=list)


def query_targets(*, port: int) -> list[PageTarget]:
    """Query Chrome's /json endpoint for page targets.

    Filters for type=="page" only. Returns an empty list if the
    HTTP request fails (browser alive but unresponsive, port
    recycled to a non-Chrome process, etc.).

    Synchronous, stdlib only (urllib + json).
    """
    ...


def get_instance_status(
    *,
    instance_name: str | None = None,
) -> list[InstanceStatus]:
    """Get status for all instances or a single named instance.

    Reads the registry via enumerate_instances() or lookup().
    For alive instances, enriches with page targets from query_targets().

    Raises InstanceNotFoundError (from BRW-04) if instance_name
    is provided but not found in the registry.
    """
    ...


def format_status_text(*, statuses: list[InstanceStatus]) -> str:
    """Format instance statuses as human-readable text.

    Output format per instance:
        instance-name  port NNNN [DEAD]
          [1] ABCD1234  https://example.com  "Page Title"
          [2] EFGH5678  https://other.com    "Other Title"
    """
    ...


def format_status_json(*, statuses: list[InstanceStatus]) -> str:
    """Format instance statuses as JSON for programmatic consumers.

    Returns a JSON array of objects, each with:
        name, port, alive, targets (array of {id, full_id, index, url, title})
    """
    ...
```

## 4. Validation Contract

### Level 1 -- Plain English Scenarios

Happy path:
- Given two registered instances where both are alive with page targets, listing all instances shows both with their targets, including truncated target IDs and numeric indexes.
- Given one registered instance, filtering by its name shows just that instance with its targets.

Dead instances:
- Given a mix of alive and dead instances, the dead instance is shown with "DEAD" and no targets, while the alive instance shows its targets normally.

No instances:
- Given an empty registry, the status command outputs a helpful message suggesting `chrome-agent launch`.

Instance not found:
- Given a registered instance "proj-01", filtering by "nonexistent" raises InstanceNotFoundError listing available instances.

Target enumeration:
- Given an alive instance with multiple page tabs, each page target has a unique numeric index (starting at 1) and an 8-character uppercased target ID.
- Non-page targets (service workers, browser-level targets) are excluded from the output.

Output format:
- When stdout is a TTY, output is formatted text.
- When stdout is not a TTY, output is structured JSON.

Target query failure:
- Given an alive instance where the `/json` endpoint is unreachable (e.g., browser is starting up or shutting down), the instance is shown as alive with an empty target list rather than crashing.

### Level 2 -- Test Logic (GIVEN / WHEN / THEN)

Scenario: List all instances with targets
GIVEN: registry contains "proj-01" (alive, port 9222) and "proj-02" (alive, port 9223), each with a mock `/json` endpoint returning two page targets
WHEN: `get_instance_status()` is called
THEN:
- returns 2 InstanceStatus entries
- each has alive=True
- each has 2 PageTarget entries
- targets have index 1 and 2 respectively
- short_id is 8 characters long and uppercased

Scenario: Filter by instance name
GIVEN: registry contains "proj-01" and "proj-02"
WHEN: `get_instance_status(instance_name="proj-01")` is called
THEN: returns exactly 1 InstanceStatus with name="proj-01"

Scenario: Dead instance shown with DEAD label
GIVEN: registry contains "proj-01" (alive, port 9222) and "proj-02" (dead PID)
WHEN: `get_instance_status()` is called
THEN:
- returns 2 entries
- proj-01 has alive=True with targets
- proj-02 has alive=False with empty targets

Scenario: Empty registry
GIVEN: empty registry (no instances registered)
WHEN: `get_instance_status()` is called
THEN: returns empty list

Scenario: Instance not found
GIVEN: registry contains "proj-01"
WHEN: `get_instance_status(instance_name="nonexistent")` is called
THEN: InstanceNotFoundError raised with "nonexistent" as name and ["proj-01"] in available

Scenario: Non-page targets filtered out
GIVEN: an alive instance whose `/json` returns targets of types "page", "service_worker", and "browser"
WHEN: `query_targets(port=...)` is called
THEN: returns only the "page" target, not the service_worker or browser targets

Scenario: Target ID truncation
GIVEN: an alive instance with a page target whose id is "956FD3C2E1A4B7F8D9C0E2F3A4B5C6D7"
WHEN: `query_targets(port=...)` is called
THEN: the target's short_id is "956FD3C2" (first 8 chars, uppercased)

Scenario: Text output formatting
GIVEN: one alive instance "proj-01" on port 9222 with one page target, and one dead instance "proj-02" on port 9223
WHEN: `format_status_text(statuses=...)` is called
THEN:
- output contains "proj-01  port 9222"
- output contains a target line with "[1]", the short ID, URL, and quoted title
- output contains "proj-02  port 9223  DEAD"
- proj-02 has no target lines

Scenario: JSON output formatting
GIVEN: one alive instance with one page target
WHEN: `format_status_json(statuses=...)` is called
THEN:
- output is valid JSON
- JSON is an array with one object
- object has keys: name, port, alive, targets
- targets is an array with one object having keys: id, full_id, index, url, title

Scenario: Target query failure gracefully handled
GIVEN: an alive instance on a port where `/json` returns an HTTP error or times out
WHEN: `query_targets(port=...)` is called
THEN: returns empty list (no exception raised)

### Level 3 -- Formal Test Definitions

```
test_list_all_instances:
    external dependency strategy: mock registry.enumerate_instances() to return
        two InstanceInfo entries, mock HTTP responses to /json for each port
    setup:
        mock enumerate_instances() returning:
            InstanceInfo(name="proj-01", port=9222, pid=1000, browser_version="Chrome/147", alive=True)
            InstanceInfo(name="proj-02", port=9223, pid=1001, browser_version="Chrome/147", alive=True)
        mock http://localhost:9222/json returning:
            [{"id": "AAAA1111BBBB2222", "type": "page", "url": "https://example.com", "title": "Example"}]
        mock http://localhost:9223/json returning:
            [{"id": "CCCC3333DDDD4444", "type": "page", "url": "https://other.com", "title": "Other"}]
    action:
        result = get_instance_status()
    assertions:
        len(result) == 2
        result[0].name == "proj-01"
        result[0].alive is True
        len(result[0].targets) == 1
        result[0].targets[0].short_id == "AAAA1111"
        result[0].targets[0].index == 1
        result[0].targets[0].url == "https://example.com"
        result[0].targets[0].title == "Example"
        result[1].name == "proj-02"
        len(result[1].targets) == 1

test_filter_by_name:
    external dependency strategy: mock registry.lookup() to return a single InstanceInfo
    setup:
        mock lookup("proj-01") returning:
            InstanceInfo(name="proj-01", port=9222, pid=1000, browser_version="Chrome/147", alive=True)
        mock http://localhost:9222/json returning:
            [{"id": "AAAA1111BBBB2222", "type": "page", "url": "https://example.com", "title": "Example"}]
    action:
        result = get_instance_status(instance_name="proj-01")
    assertions:
        len(result) == 1
        result[0].name == "proj-01"

test_dead_instance:
    external dependency strategy: mock registry.enumerate_instances()
    setup:
        mock enumerate_instances() returning:
            InstanceInfo(name="proj-01", port=9222, pid=1000, browser_version="Chrome/147", alive=True)
            InstanceInfo(name="proj-02", port=9223, pid=99999999, browser_version="Chrome/147", alive=False)
        mock http://localhost:9222/json returning:
            [{"id": "AAAA1111BBBB2222", "type": "page", "url": "https://example.com", "title": "Example"}]
    action:
        result = get_instance_status()
    assertions:
        len(result) == 2
        result[0].alive is True
        len(result[0].targets) == 1
        result[1].alive is False
        len(result[1].targets) == 0

test_empty_registry:
    external dependency strategy: mock registry.enumerate_instances() returning empty list
    setup:
        mock enumerate_instances() returning []
    action:
        result = get_instance_status()
    assertions:
        result == []

test_instance_not_found:
    external dependency strategy: mock registry.lookup() raising InstanceNotFoundError
    setup:
        mock lookup("nonexistent") raising InstanceNotFoundError(
            name="nonexistent", available=["proj-01"]
        )
    action:
        result = get_instance_status(instance_name="nonexistent")
    assertions:
        InstanceNotFoundError is raised
        error.name == "nonexistent"
        "proj-01" in error.available

test_non_page_targets_filtered:
    external dependency strategy: mock HTTP response with mixed target types
    setup:
        mock http://localhost:9222/json returning:
            [
                {"id": "AAAA1111BBBB2222", "type": "page", "url": "https://example.com", "title": "Example"},
                {"id": "EEEE5555FFFF6666", "type": "service_worker", "url": "https://example.com/sw.js", "title": ""},
                {"id": "GGGG7777HHHH8888", "type": "browser", "url": "", "title": ""}
            ]
    action:
        result = query_targets(port=9222)
    assertions:
        len(result) == 1
        result[0].short_id == "AAAA1111"
        result[0].url == "https://example.com"

test_target_id_truncation:
    external dependency strategy: mock HTTP response
    setup:
        mock http://localhost:9222/json returning:
            [{"id": "956fd3c2e1a4b7f8d9c0e2f3a4b5c6d7", "type": "page", "url": "https://example.com", "title": "Test"}]
    action:
        result = query_targets(port=9222)
    assertions:
        result[0].target_id == "956fd3c2e1a4b7f8d9c0e2f3a4b5c6d7"
        result[0].short_id == "956FD3C2"
        len(result[0].short_id) == 8

test_text_output_format:
    external dependency strategy: construct InstanceStatus objects directly
    setup:
        statuses = [
            InstanceStatus(
                name="proj-01", port=9222, alive=True,
                targets=[PageTarget(
                    target_id="aaaa1111bbbb2222", short_id="AAAA1111",
                    index=1, url="https://example.com", title="Example"
                )]
            ),
            InstanceStatus(name="proj-02", port=9223, alive=False, targets=[]),
        ]
    action:
        output = format_status_text(statuses=statuses)
    assertions:
        "proj-01  port 9222" in output
        "[1] AAAA1111" in output
        "https://example.com" in output
        '"Example"' in output
        "proj-02  port 9223  DEAD" in output
        // no target lines appear after the DEAD instance line

test_json_output_format:
    external dependency strategy: construct InstanceStatus objects directly
    setup:
        statuses = [
            InstanceStatus(
                name="proj-01", port=9222, alive=True,
                targets=[PageTarget(
                    target_id="aaaa1111bbbb2222", short_id="AAAA1111",
                    index=1, url="https://example.com", title="Example"
                )]
            ),
        ]
    action:
        output = format_status_json(statuses=statuses)
        parsed = json.loads(output)
    assertions:
        len(parsed) == 1
        parsed[0]["name"] == "proj-01"
        parsed[0]["port"] == 9222
        parsed[0]["alive"] is True
        len(parsed[0]["targets"]) == 1
        parsed[0]["targets"][0]["id"] == "AAAA1111"
        parsed[0]["targets"][0]["full_id"] == "aaaa1111bbbb2222"
        parsed[0]["targets"][0]["index"] == 1
        parsed[0]["targets"][0]["url"] == "https://example.com"
        parsed[0]["targets"][0]["title"] == "Example"

test_target_query_failure:
    external dependency strategy: mock HTTP request to /json that raises an exception
    setup:
        mock http://localhost:9222/json to raise ConnectionError or timeout
    action:
        result = query_targets(port=9222)
    assertions:
        result == []
```

## 5. Feedback Channels

### Visual

Inspect the text output formatting -- are instance names and ports aligned? Do target lines indent consistently under their parent instance? Are target IDs exactly 8 characters and uppercased? Is the "DEAD" label clearly visible for dead instances? Compare the actual output against the example format from the learning record:

```
aroundchicago.tech-01  port 9222
  [1] 956FD3C2  https://www.meetup.com/find/...     "Find Events | Meetup"
  [2] A1B2C3D4  https://www.meetup.com/find/...     "Find Events | Meetup"

kindle2markdown-01     port 9223  DEAD
```

For JSON output, inspect the structure -- is it valid JSON? Are all expected fields present? Are types correct (port is number, alive is boolean, targets is array)?

### Auditory

Monitor for HTTP request failures when querying `/json` endpoints. If an instance is alive but `query_targets()` returns empty, the logs should indicate why -- connection refused, timeout, or malformed response. Errors should be logged at debug level (not warning/error) since a query failure for a dying browser is expected, not exceptional. The `InstanceNotFoundError` message should be clear and actionable -- listing available instances so the user can correct a typo.

### Tactile

Exercise the full workflow as an agent would: launch two browser instances using `chrome-agent launch`, navigate each to different URLs, then run `chrome-agent status` and verify both instances appear with their page targets. Kill one browser process, run `chrome-agent status` again, and verify the killed instance shows as DEAD while the surviving instance still shows its targets. Run `chrome-agent status <name>` with a valid instance name and verify it filters correctly. Run it with an invalid name and verify the error message lists available instances. Pipe the output through a non-TTY context (e.g., `chrome-agent status | cat`) and verify JSON output is produced and parseable.

## 6. Dependencies

| Dependency | What this feature needs from it | Rationale |
|------------|--------------------------------|-----------|
| BRW-04 | `enumerate_instances()` returning `list[InstanceInfo]` with fields: name, port, pid, browser_version, alive. Also `lookup(instance_name)` returning a single `InstanceInfo` or raising `InstanceNotFoundError`. Registry path: `/tmp/chrome-agent/registry.json`. | Instance Status reads the registry to discover what instances exist and their liveness. Without the registry, there is nothing to enumerate. |

## 7. Scoping Decisions

| Decision | What prompted it | Rationale | Revisit when |
|----------|-----------------|-----------|--------------|
| No column alignment padding between target fields | The example output shows rough spacing but precise column alignment requires knowing the maximum width of each field across all targets across all instances | Adds formatting complexity for marginal readability benefit. URLs vary wildly in length so column alignment on URLs provides little value. | If users report readability issues with the text output. |
| Target IDs truncated to 8 characters, not configurable | 8 hex characters = over 4 billion combinations, more than sufficient for disambiguation within a single browser instance | A configurable length adds a flag for negligible benefit. 8 characters matches git short hash conventions and is a familiar pattern. | If target ID collisions are observed in practice (extremely unlikely within a single browser). |
| No automatic cleanup of dead instances | Instance Status reports dead instances but does not remove them from the registry | Status is a read-only operation. Mixing observation with mutation violates single-responsibility. Cleanup is a separate command (BRW-04's `cleanup()`). | If users consistently forget to run cleanup and accumulate many dead entries, a warning message suggesting cleanup could be added. |
| No WebSocket URL in output | Chrome's `/json` endpoint returns `webSocketDebuggerUrl` for each target | The agent constructs the WebSocket URL from the target ID when needed (for attach or one-shot). Including it in status output adds clutter without aiding the discovery workflow. | If agents need the full WebSocket URL from status output rather than constructing it themselves. |
| lookup() for single-instance filtering re-checks alive on the returned InstanceInfo | BRW-04's `lookup()` now checks PID liveness and sets the `alive` field correctly (this was fixed during spec review). The re-check in BRW-05 is technically redundant but kept as defensive programming -- it costs a single `os.kill(pid, 0)` syscall and protects against a race where the process dies between the registry read and the status query. | The re-check is cheap and provides a safety margin. If it becomes confusing during implementation, it can be removed since BRW-04's `lookup()` already handles liveness. | N/A |

## 8. Learnings

| # | Topic | Type | Summary | Link |
|---|-------|------|---------|------|
| None yet | | | No exploratory work needed -- the Chrome `/json` endpoint behavior is well-understood from BRW-02's implementation in `connection.py`, and the registry interface is fully specified in BRW-04. | |

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
