# Feature Specification

> *This document is the complete definition of a single atomic feature -- what to build, how to validate it, what to observe during implementation, what it depends on, and (once implementation begins) its implementation history.*

## 1. Feature ID and Name

BRW-02: Browser Status

## 2. User Story

As an AI agent, I want to check whether a browser is running on a CDP port and see its version and current page, so that I can decide whether to launch a new browser or attach to the existing one.

## 3. Implementation Contract

### Level 1 -- Plain English

This feature checks whether a Chrome browser is listening on a given CDP port and reports basic information about it. It does a socket check to see if the port is open, then queries Chrome's HTTP endpoints for the browser version, and the URL and title of the first page.

This is a synchronous, stdlib-only operation -- no WebSocket connection, no async, no external dependencies. It is used by agents before starting a session (is there a browser to connect to?) and by the `status` operational command.

If no browser is listening, it reports that. If a browser is listening but the HTTP endpoints fail, it reports the port is active but details are unavailable.

### Level 2 -- Logic Flow (INPUT / LOGIC / OUTPUT)

**INPUT:**

- `port`: integer, default 9222 -- the CDP port to check

**LOGIC:**

```
check_cdp_port(port):
    // Quick socket check
    sock = tcp_connect(localhost, port, timeout=1s)
    if connection refused:
        return PortStatus(listening=false)

    // Port is open -- try to get browser version
    browser_version = None
    try:
        response = http_get(http://localhost:{port}/json/version, timeout=2s)
        data = json_parse(response)
        browser_version = data["Browser"]
    except any error:
        pass  // port is open but can't get version

    // Try to get first page's URL and title
    page_url = None
    page_title = None
    try:
        response = http_get(http://localhost:{port}/json, timeout=2s)
        pages = json_parse(response)
        if pages is not empty:
            page_url = pages[0]["url"]
            page_title = pages[0]["title"]
    except any error:
        pass  // port is open but can't get page info

    return PortStatus(
        listening=true,
        browser_version=browser_version,
        page_url=page_url,
        page_title=page_title,
    )
```

**OUTPUT:**

- `PortStatus` dataclass with:
  - `listening`: bool -- is something listening on the port
  - `browser_version`: str or None -- e.g., "Chrome/145.0.7632.6"
  - `page_url`: str or None -- URL of the first page
  - `page_title`: str or None -- title of the first page

### Level 3 -- Formal Interfaces

```python
@dataclass
class PortStatus:
    """Result of checking whether a CDP port is active."""
    listening: bool
    browser_version: str | None = None
    page_url: str | None = None
    page_title: str | None = None


def check_cdp_port(port: int = 9222) -> PortStatus:
    """Check if a browser is listening on the CDP port.

    Synchronous. Uses stdlib only (socket + urllib).
    """
    ...
```

## 4. Validation Contract

### Level 1 -- Plain English Scenarios

Happy path:
- Given a browser running on a known port, check_cdp_port returns listening=True with the browser version, page URL, and title.

No browser:
- Given no browser running on a port, check_cdp_port returns listening=False with all other fields None.

Partial information:
- Given a port that is open but not a Chrome CDP port (e.g., a random HTTP server), check_cdp_port returns listening=True but browser_version, page_url, and page_title may be None.

### Level 2 -- Test Logic (GIVEN / WHEN / THEN)

Scenario: Browser running
GIVEN: a Chrome browser running on port 9333 with a page loaded
WHEN: check_cdp_port(port=9333) is called
THEN: result.listening is True, result.browser_version is not None and contains "Chrome", result.page_url is not None

Scenario: No browser
GIVEN: nothing listening on port 9444
WHEN: check_cdp_port(port=9444) is called
THEN: result.listening is False, result.browser_version is None, result.page_url is None, result.page_title is None

Scenario: Port open but not Chrome
GIVEN: a non-Chrome HTTP server listening on port 9444 (e.g., a simple Python HTTP server)
WHEN: check_cdp_port(port=9444) is called
THEN: result.listening is True, result.browser_version is None (the /json/version endpoint doesn't exist or returns unexpected data)

### Level 3 -- Formal Test Definitions

```
test_browser_running:
    setup:
        browser running on port 9333 with a page loaded
    action:
        status = check_cdp_port(port=9333)
    assertions:
        status.listening is True
        status.browser_version is not None
        "Chrome" in status.browser_version or "Chromium" in status.browser_version
        status.page_url is not None
        status.page_title is not None

test_no_browser:
    action:
        status = check_cdp_port(port=9444)
    assertions:
        status.listening is False
        status.browser_version is None
        status.page_url is None
        status.page_title is None
```

## 5. Feedback Channels

### Visual

Not applicable -- this feature returns a data structure, not a visual artifact. The test assertions verify correctness.

### Auditory

If the socket check or HTTP requests fail unexpectedly (not connection refused, but timeouts or malformed responses), the failure should be visible in test output. The feature deliberately swallows errors (returns None fields) so auditory feedback is about verifying it degrades gracefully rather than crashing.

### Tactile

Call `check_cdp_port()` against a running browser and against no browser. Verify the returned PortStatus matches expectations. CLI output formatting is CLI-01's responsibility.

## 6. Dependencies

| Dependency | What this feature needs from it | Rationale |
|------------|--------------------------------|-----------|
| None | N/A | BRW-02 uses stdlib only and has no dependencies on other chrome-agent features. It depends on Chrome's HTTP endpoints existing, but that is an external system. |

## 7. Scoping Decisions

| Decision | What prompted it | Rationale | Revisit when |
|----------|-----------------|-----------|--------------|
| Reports first page only | Multiple pages could be open | Reporting all pages adds complexity to output formatting without clear value for the primary use case (is a browser running?). The agent can use CDP-01 to list all targets if needed. | If agents need a richer target listing from the status command. |

## 8. Learnings

| # | Topic | Type | Summary | Link |
|---|-------|------|---------|------|
| None | | | This feature already exists in the current codebase and works well. No exploratory work was needed. | src/chrome_agent/connection.py (check_cdp_port function) |

---

## 9. Implementation Status

**Status:** Complete

## 10. Test Results

### Refinement Log

**Iteration 1:** All tests passed on the first run. No refinement needed.

- Feature code already existed in `src/chrome_agent/connection.py` (`check_cdp_port()` and `PortStatus`). No modifications needed -- the existing implementation matches the spec's Level 3 interfaces exactly (with the minor improvement of keyword-only `port` parameter).
- Wrote 4 tests in `tests/test_browser_status.py` covering: browser running (version, URL, title), no browser (listening=False, all None), non-Chrome port (listening=True, browser_version=None), and PortStatus dataclass defaults.
- All 4 tests passed, all 71 tests total passed (zero regressions).

### Final Test Results

| Test | Result | Notes |
|------|--------|-------|
| test_browser_running | Pass | Detects Chrome/Chromium with version, URL, title |
| test_no_browser | Pass | Returns listening=False, all fields None |
| test_port_open_not_chrome | Pass | Returns listening=True, browser_version=None |
| test_port_status_defaults | Pass | PortStatus defaults work correctly |

## 11. Review Notes

### Agent Review Notes

**Pre-existing implementation:** This is the only feature in the iteration where the code already existed before the Implementation Loop began. The `check_cdp_port()` function and `PortStatus` dataclass in `src/chrome_agent/connection.py` were written in an earlier development phase and match the spec's interfaces exactly. The implementation is clean: synchronous, stdlib-only (socket + urllib), graceful degradation when HTTP endpoints fail.

**What was new:** The test file `tests/test_browser_status.py` is new and covers the full Validation Contract. The existing tests in `test_commands.py` (TestConnection class) overlapped with the "browser running" and "no browser" scenarios, but the non-Chrome port test was new and required spinning up a temporary HTTP server via the `non_chrome_port` fixture. This test validates the graceful degradation path -- the function correctly reports `listening=True` but `browser_version=None` when the port is open but `/json/version` doesn't exist.

**No changes to feature code:** The existing implementation was correct. The keyword-only `port` parameter (using `*`) is stricter than the spec's positional signature but consistent with the project's named-parameter convention and doesn't affect consumers.

**Relevance to other features:** BRW-01 (Browser Launch) in Phase 2 will need Browser Status to confirm launched browsers are accessible. The integration test in Phase 1's completion criteria verifies that CDP WebSocket Client can connect to a browser that Browser Status confirms is running -- this will be checked when the phase gate is evaluated.

### User Review Notes

[To be filled by user]
