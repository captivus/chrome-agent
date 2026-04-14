# Feature Specification

> *This document is the complete definition of a single atomic feature -- what to build, how to validate it, what to observe during implementation, what it depends on, and (once implementation begins) its implementation history.*

## 1. Feature ID and Name

BRW-01: Browser Launch

## 2. User Story

As an AI agent, I want to launch a Chrome browser with CDP enabled so that I can connect to it and control it through the protocol, without needing to manually find and start Chrome with the right flags.

### Iteration 2 Updates

As an AI agent, I want the browser launch to automatically allocate a free port and register the instance by name, so that I can launch multiple browsers without manually tracking ports and identify each instance by a human-readable name derived from my working directory.

## 3. Implementation Contract

### Level 1 -- Plain English

This feature finds the Chrome or Chromium binary on the system, launches it as a subprocess with remote debugging enabled on a specified port, and waits for the CDP port to become available before returning. The browser continues running after chrome-agent exits -- it is a fire-and-forget launch.

The binary discovery searches platform-specific standard paths. On Linux, it looks for google-chrome, chromium-browser, and chromium in standard locations. On macOS, it looks in the Applications directory. On Windows, it looks in Program Files. If no binary is found, it fails with a helpful error listing the paths it searched.

The browser is launched with a temporary user data directory (so it doesn't conflict with the user's normal Chrome profile), with remote debugging on the requested port, and with flags to suppress first-run prompts and default browser checks.

After starting the subprocess, the feature polls the CDP port (using BRW-02's check_cdp_port) until the browser is ready to accept connections, then returns the browser version.

If a fingerprint profile is provided, it is applied after launch via BRW-03.

On Linux with X11, the browser window can optionally be moved to the virtual desktop where the launching terminal is, so the browser appears on the same workspace as the agent. This uses PID-based window search via xdotool and is silently skipped if unavailable.

#### Iteration 2 Updates

After the browser process starts and the CDP port is confirmed ready, launch registers the instance with the Instance Registry (BRW-04). The registry auto-allocates a port by scanning from 9222 upward unless `--port` is provided as an explicit override. The instance receives a name derived from the current working directory basename (e.g., `aroundchicago.tech-01`), with the registry managing naming, auto-increment, and storage.

When stdout is not a TTY, launch returns structured JSON output: `{"name": "aroundchicago.tech-01", "port": 9222, "pid": 58469, "browser_version": "Chrome/147"}`. When stdout is a TTY, it prints formatted text as before.

### Level 2 -- Logic Flow (INPUT / LOGIC / OUTPUT)

**INPUT:**

- `port_override`: integer or None -- explicit CDP port override. When None, the registry auto-allocates a port starting from 9222.
- `fingerprint`: string or None -- path to a fingerprint profile JSON file
- `headless`: bool, default False -- run in headless mode
- `pin_to_desktop`: bool, default True -- move browser to launching terminal's desktop (Linux/X11 only)

**LOGIC:**

```
launch_browser(port_override, fingerprint, headless, pin_to_desktop):
    // Phase 1: Find Chrome binary
    binary = find_chrome_binary()
    if binary is None:
        raise BrowserNotFoundError(searched_paths)

    // Phase 2: Prepare launch arguments
    root_dir = "/tmp/chrome-agent"
    ensure_directory_exists(root_dir)
    session_dir = create_subdirectory(root_dir, prefix="session-")

    // Port allocation flow: we need the port before launching Chrome (for
    // --remote-debugging-port), so we allocate it here via the registry.
    // After launch succeeds, we pass the already-allocated port as
    // port_override to registry.register(), which uses it directly without
    // re-scanning. This means allocate_port() is called once, before launch,
    // and register() receives the result.
    registry_data = registry.load_registry()
    port = port_override if port_override is not None else registry.allocate_port(registry=registry_data)

    args = [
        binary,
        "--remote-debugging-port={port}",
        "--user-data-dir={session_dir}",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if headless:
        args.append("--headless=new")

    // Phase 3: Launch subprocess
    process = subprocess_start(args)
    // Do not wait for process -- fire and forget

    // Phase 4: Wait for CDP port to be ready
    deadline = now() + 30 seconds
    while now() < deadline:
        status = check_cdp_port(port=port)
        if status.listening:
            break
        sleep(0.2 seconds)
    else:
        raise TimeoutError("Browser did not start within 30 seconds")

    // Phase 5: Register with Instance Registry
    // Pass the already-allocated port as port_override so register() uses it
    // directly without re-scanning for available ports.
    instance = registry.register(
        working_dir=get_current_working_directory(),
        pid=process.pid,
        browser_version=status.browser_version,
        port_override=port,
        user_data_dir=session_dir,
    )

    // Phase 6: Apply fingerprint if provided
    if fingerprint is not None:
        profile = load_fingerprint(path=fingerprint)
        apply_fingerprint(port=port, profile=profile)

    // Phase 7: Pin to desktop (Linux/X11, best-effort)
    if pin_to_desktop:
        move_to_launching_desktop(pid=process.pid)

    return instance  // InstanceInfo from BRW-04


cleanup_sessions():
    // Remove session directories under /tmp/chrome-agent/ that don't have
    // a running Chrome process holding a lock.
    root_dir = "/tmp/chrome-agent"
    if not exists(root_dir):
        return

    for session_dir in list_subdirectories(root_dir):
        lock_file = session_dir / "SingletonLock"
        if not exists(lock_file):
            // No lock -- safe to remove
            remove_directory(session_dir)
        else:
            // Lock exists -- check if the process is still running
            // Chrome's SingletonLock contains the PID
            // If the process is dead, remove the directory
            pid = read_lock_pid(lock_file)
            if not process_is_running(pid):
                remove_directory(session_dir)


find_chrome_binary():
    candidates = platform_specific_candidates()
    for path in candidates:
        if file_exists(path) and is_executable(path):
            return path
    return None

platform_specific_candidates():
    if linux:
        return [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium",
            "/snap/bin/chromium",
        ]
    elif macos:
        return [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
    elif windows:
        return [
            "C:/Program Files/Google/Chrome/Application/chrome.exe",
            "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
        ]

move_to_launching_desktop(pid):
    // Requires xdotool. Silently skipped if unavailable.
    // Uses PID-based window search instead of WM_CLASS, because
    // Chrome ignores the --class flag.
    try:
        desktop = get_current_desktop()  // xdotool get_desktop or get_desktop_for_window $WINDOWID
        sleep(0.5 seconds)  // wait for browser window to appear
        window_ids = xdotool_search_by_pid(pid)
        for wid in window_ids:
            xdotool_set_desktop_for_window(wid, desktop)
    except xdotool_not_found:
        pass  // silently skip
```

**OUTPUT:**

- On success: returns InstanceInfo (from BRW-04) with name, port, pid, browser_version, user_data_dir, and alive status. Browser process is running. Note: `InstanceInfo` (defined in BRW-04) now includes `user_data_dir` so callers can locate the session directory. The `fingerprint_guard` subprocess handle (from BRW-03) is internal to `launch_browser`'s scope -- it is managed within the launch function and not exposed on the return type, since callers do not need to interact with it.
- **TTY detection and output formatting clarification:** `launch_browser()` returns `InstanceInfo` -- it does not format output or check whether stdout is a TTY. TTY detection and output formatting (JSON vs formatted text) is the CLI layer's responsibility. The CLI command handler in `cli.py` checks `sys.stdout.isatty()` and formats the returned `InstanceInfo` accordingly. This separation keeps `launch_browser()` focused on launching and registering.
- On failure: raises BrowserNotFoundError (no Chrome binary) or TimeoutError (browser didn't start).
- The browser process is NOT managed by chrome-agent. It continues running independently.
- Session data lives under `/tmp/chrome-agent/session-<id>/`. The system cleans `/tmp` on reboot. Between reboots, `cleanup_sessions()` removes stale directories.
- When stdout is not a TTY, output is structured JSON. When stdout is a TTY, output is formatted text.

#### Iteration 2 Updates

Phase 0 (port conflict pre-check) is removed. With auto-port allocation, the port is known to be free when allocated. When `--port` override is used, Chrome's own binding failure + the 30-second timeout handles conflicts, same as the iteration 1 scoping decision.

### Level 3 -- Formal Interfaces

```python
from chrome_agent.registry import InstanceInfo


class BrowserNotFoundError(Exception):
    """Chrome/Chromium binary not found on the system."""
    def __init__(self, searched_paths: list[str]):
        self.searched_paths = searched_paths
        paths_str = "\n  ".join(searched_paths)
        super().__init__(
            f"Chrome/Chromium not found. Searched:\n  {paths_str}"
        )


async def launch_browser(
    port_override: int | None = None,
    fingerprint: str | None = None,
    headless: bool = False,
    pin_to_desktop: bool = True,
) -> InstanceInfo:
    """Launch Chrome with CDP enabled and register it in the Instance Registry.

    Finds the Chrome binary, starts it with --remote-debugging-port,
    waits for the port to be ready, registers the instance with BRW-04,
    and optionally applies a fingerprint profile.

    Port is auto-allocated by the registry unless port_override is provided.
    Instance name is derived from the current working directory.

    Session data is stored under /tmp/chrome-agent/session-<id>/.
    The browser continues running after this function returns.

    Raises BrowserNotFoundError if Chrome is not installed.
    Raises TimeoutError if the browser doesn't start within 30 seconds.
    """
    ...


def find_chrome_binary() -> str | None:
    """Search platform-specific paths for Chrome/Chromium.

    Returns the path to the first found executable, or None.
    """
    ...


def cleanup_sessions() -> None:
    """Remove stale session directories under /tmp/chrome-agent/.

    Removes directories that don't have a running Chrome process
    (checks Chrome's SingletonLock file and whether the PID is alive).
    """
    ...
```

## 4. Validation Contract

### Level 1 -- Plain English Scenarios

Happy path:
- Given Chrome is installed on the system, launch_browser starts a browser on the specified port and the port is accessible via check_cdp_port afterward.

Binary not found:
- Given Chrome is not installed (or not in any searched path), launch_browser raises BrowserNotFoundError listing the paths it searched.

Port already in use:
- Given something is already listening on the requested port, Chrome fails to bind and the launch times out. No pre-check is performed (see Scoping Decisions).

Headless mode:
- Given headless=True, the browser launches without a visible window and the CDP port is still accessible.

Fingerprint integration:
- Given a valid fingerprint profile path, the browser has the fingerprint applied after launch (verified by checking navigator properties via CDP).

#### Iteration 2 Updates

Auto-port allocation:
- Given no port_override is provided, the registry allocates an available port starting from 9222 and the browser launches on that port.

Instance registration:
- Given a successful launch, the instance is registered in `/tmp/chrome-agent/registry.json` with a name derived from the current working directory basename and an auto-incremented suffix.

Structured JSON output:
- Given stdout is not a TTY, launch outputs structured JSON containing name, port, pid, and browser_version.

Port override:
- Given port_override=9333, the browser launches on port 9333 and the registry records that port (no auto-allocation).

### Level 2 -- Test Logic (GIVEN / WHEN / THEN)

Scenario: Successful launch
GIVEN: Chrome is installed on the system, port 9333 is free
WHEN: launch_browser(port_override=9333) is called
THEN: check_cdp_port(port=9333).listening is True, browser_version contains "Chrome" or "Chromium"

Scenario: Browser not found
GIVEN: no Chrome binary exists at any searched path (test with a mocked find_chrome_binary returning None)
WHEN: launch_browser() is called
THEN: BrowserNotFoundError is raised with a non-empty searched_paths list

Scenario: Headless launch
GIVEN: Chrome is installed, port 9333 is free
WHEN: launch_browser(port_override=9333, headless=True) is called
THEN: check_cdp_port(port=9333).listening is True (browser is running headlessly)

Scenario: Launch with fingerprint
GIVEN: Chrome is installed, port 9333 is free, a valid fingerprint profile exists
WHEN: launch_browser(port_override=9333, fingerprint="path/to/profile.json") is called
THEN: connecting via CDP and evaluating navigator.userAgent returns the fingerprint's user agent value

#### Iteration 2 Updates

Scenario: Auto-port allocation
GIVEN: Chrome is installed, no port_override provided, port 9222 is free
WHEN: launch_browser() is called
THEN: the returned InstanceInfo has port=9222, and registry.json contains the instance entry

Scenario: Auto-port allocation with occupied port
GIVEN: Chrome is installed, no port_override provided, port 9222 is occupied
WHEN: launch_browser() is called
THEN: the returned InstanceInfo has a port > 9222, and the browser is listening on that port

Scenario: Instance registration with name
GIVEN: Chrome is installed, current working directory is /home/user/projects/aroundchicago.tech
WHEN: launch_browser() is called
THEN: the returned InstanceInfo.name matches "aroundchicago.tech-01", and registry.json contains this entry

Scenario: Structured JSON output (non-TTY)
GIVEN: Chrome is installed, stdout is not a TTY
WHEN: launch_browser() is called from the CLI
THEN: stdout contains valid JSON with keys "name", "port", "pid", "browser_version"

### Level 3 -- Formal Test Definitions

```
test_successful_launch:
    setup:
        port 9333 is free (no browser running)
    action:
        await launch_browser(port_override=9333)
    assertions:
        check_cdp_port(port=9333).listening is True
        check_cdp_port(port=9333).browser_version is not None
    teardown:
        kill browser process on port 9333

test_browser_not_found:
    setup:
        mock find_chrome_binary to return None
    action:
        try:
            await launch_browser()
            raised = False
        except BrowserNotFoundError as e:
            raised = True
            error = e
    assertions:
        raised is True
        len(error.searched_paths) > 0

test_headless_launch:
    setup:
        port 9333 is free
    action:
        await launch_browser(port_override=9333, headless=True)
    assertions:
        check_cdp_port(port=9333).listening is True
    teardown:
        kill browser process on port 9333

test_launch_with_fingerprint:
    setup:
        port 9333 is free
        fingerprint profile at /tmp/test-fingerprint.json with userAgent "TestAgent/1.0"
    action:
        result = await launch_browser(port_override=9333, fingerprint="/tmp/test-fingerprint.json")
    assertions:
        // Connect via CDP and check
        async with CDPClient(ws_url=get_ws_url(port=9333)) as cdp:
            ua = await cdp.send("Runtime.evaluate",
                                 {"expression": "navigator.userAgent", "returnByValue": True})
            ua["result"]["value"] == "TestAgent/1.0"
    teardown:
        kill process result.pid

test_cleanup_removes_stale_dirs:
    setup:
        create /tmp/chrome-agent/session-stale/ with no running Chrome process
        create a fake SingletonLock pointing to a dead PID
    action:
        cleanup_sessions()
    assertions:
        /tmp/chrome-agent/session-stale/ no longer exists

test_cleanup_preserves_active_dirs:
    setup:
        launch a browser (creates a session directory with an active process)
    action:
        cleanup_sessions()
    assertions:
        the session directory still exists (active process is preserved)
    teardown:
        kill the browser process

test_auto_port_allocation:
    setup:
        registry.json is empty or does not exist
        port 9222 is free
    action:
        instance = await launch_browser()
    assertions:
        instance.port == 9222
        instance.name ends with "-01"
        registry.json contains entry for instance.name
    teardown:
        kill browser process

test_auto_port_skips_occupied:
    setup:
        start a listener on port 9222 (simulate occupied port)
    action:
        instance = await launch_browser()
    assertions:
        instance.port > 9222
        check_cdp_port(port=instance.port).listening is True
    teardown:
        kill browser process
        stop listener on 9222

test_instance_registration:
    setup:
        current working directory basename is "myproject"
    action:
        instance = await launch_browser()
    assertions:
        instance.name == "myproject-01"
        registry.json contains "myproject-01" with matching port and pid
    teardown:
        kill browser process

test_structured_json_output:
    setup:
        stdout is not a TTY (e.g., piped)
    action:
        output = run_cli("chrome-agent launch")
    assertions:
        json.loads(output) succeeds
        parsed output has keys: "name", "port", "pid", "browser_version"
        parsed["pid"] corresponds to a running process
```

## 5. Feedback Channels

### Visual

After launching, take a screenshot via CDP to verify the browser started and is rendering. For headless mode, verify the screenshot is non-empty (browser is producing frames even without a window).

#### Iteration 2 Updates

After launching, inspect `/tmp/chrome-agent/registry.json` to verify the instance was registered with the expected name, port, and PID. Verify the JSON structure matches the InstanceInfo schema.

### Auditory

Monitor subprocess stderr output from Chrome during launch. Chrome logs startup information and errors to stderr. If the browser fails to start (bad flags, port conflict, missing GPU libraries), the diagnostic information is in Chrome's stderr.

### Tactile

Run `chrome-agent launch` from the terminal, then run `chrome-agent status` to verify the browser is running. Open a session and send a command. This is the end-to-end workflow from the MPS.

#### Iteration 2 Updates

Run `chrome-agent launch` from a terminal (TTY) and verify formatted text output. Run `chrome-agent launch | cat` (non-TTY) and verify structured JSON output. Run two launches from the same directory and verify the names are auto-incremented (e.g., `myproject-01`, `myproject-02`).

## 6. Dependencies

| Dependency | What this feature needs from it | Rationale |
|------------|--------------------------------|-----------|
| BRW-02 | check_cdp_port() to poll for port readiness after launch | Need to know when the browser is ready to accept connections |
| BRW-04 | registry.register() for port allocation, naming, and instance registration | Iteration 2: launch delegates port allocation and instance naming to the registry |

## 7. Scoping Decisions

| Decision | What prompted it | Rationale | Revisit when |
|----------|-----------------|-----------|--------------|
| No port conflict detection before launch | Edge case consideration | Checking the port before launch adds a race condition (port could become occupied between check and launch). Let Chrome fail on its own if the port is in use -- the timeout will catch it. | If agents frequently hit port conflicts and the timeout-based detection is too slow. |
| Fresh session directory per launch | Simplicity | A fresh profile avoids state leakage between sessions. All session directories live under `/tmp/chrome-agent/` so the system cleans them on reboot. Between reboots, `cleanup_sessions()` removes stale directories. | If persistent browser profiles become a common need. |
| 30 second startup timeout | Reasonable default | Most Chrome launches complete in under 5 seconds. 30 seconds accommodates slow systems without hanging indefinitely. | If real-world usage shows this is too short (e.g., first launch downloading components) or too long. |
| Function is async despite mostly sync body | apply_fingerprint requires CDP (async), polling should use asyncio.sleep to not block the event loop | The async boundary is at launch_browser so callers don't need to manage the sync/async split themselves. | N/A |
| SingletonLock parsing is best-effort | Chrome writes SingletonLock as a symlink with format "hostname-PID" but this is undocumented Chrome internals | If the lock file format can't be parsed, treat the directory as active (don't delete it). Verify the actual format empirically during implementation. | If Chrome changes the lock file format. |
| Removed `wm_class` parameter (iteration 2) | Chrome ignores `--class` flag | Chrome does not honor the `--class` flag, so setting WM_CLASS via launch args has no effect. Desktop pinning now uses PID-based window search via xdotool, which reliably identifies the browser window. | N/A |
| Removed `--disable-blink-features=AutomationControlled` (iteration 2) | Unnecessary on Chrome 147+ | Chrome 147+ no longer sets the `navigator.webdriver` property by default, making this flag unnecessary. Removing it reduces launch arg clutter. | If a future Chrome version reintroduces automation detection flags. |
| Added `--no-first-run` and `--no-default-browser-check` (iteration 2) | Clean launch experience | These flags suppress first-run dialogs and default browser prompts that would otherwise interfere with automated browser control. | N/A |

## 8. Learnings

| # | Topic | Type | Summary | Link |
|---|-------|------|---------|------|
| None | | | The existing browser.py in the current codebase implements this feature using Playwright's launch_persistent_context. The reimplementation replaces Playwright's launcher with direct subprocess management. | src/chrome_agent/browser.py |

---

## 9. Implementation Status

**Status:** Complete (iteration 1)

## 10. Test Results

### Refinement Log

**Iteration 1:** All tests passed on the first run. No refinement needed.

- Wrote `launch_browser()`, `find_chrome_binary()`, `cleanup_sessions()`, `LaunchResult`, and `BrowserNotFoundError` in `src/chrome_agent/launcher.py`
- Wrote 6 tests in `tests/test_launcher.py` covering: binary discovery, successful launch, headless launch, browser not found (mocked), cleanup removes stale dirs, cleanup preserves active dirs
- All 6 tests passed, all 94 total tests passed (zero regressions)

### Final Test Results

| Test | Result | Notes |
|------|--------|-------|
| test_find_chrome_binary | Pass | Finds google-chrome on Linux system |
| test_successful_launch | Pass | Browser starts, check_cdp_port confirms listening |
| test_headless_launch | Pass | Headless browser accessible via CDP |
| test_browser_not_found | Pass | BrowserNotFoundError with searched_paths |
| test_cleanup_removes_stale_dirs | Pass | Stale session dir with dead PID removed |
| test_cleanup_preserves_active_dirs | Pass | Active session dir preserved during cleanup |
| test_launch_with_fingerprint | Not implemented | Requires BRW-03 (Fingerprint Profiles) which is not yet complete |

## 11. Review Notes

### Agent Review Notes

**Direct subprocess management replaces Playwright.** The existing `browser.py` uses Playwright's `launch_persistent_context()` to launch Chrome. The new `launcher.py` uses `subprocess.Popen` directly, which eliminates the Playwright dependency for launching. Chrome is found via platform-specific path search, launched with standard CDP flags, and the port is polled using `check_cdp_port()` from BRW-02.

**Key implementation details:**

- **Session directories under /tmp/chrome-agent/.** Each launch creates a unique `session-<id>/` subdirectory. The system cleans `/tmp` on reboot. Between reboots, `cleanup_sessions()` inspects Chrome's `SingletonLock` symlink (format: `hostname-PID`) to determine if the Chrome process is still alive.
- **Fire-and-forget model.** The browser subprocess is started with `Popen` and not waited on. `stdout` is devnull, `stderr` is captured for diagnostic use if Chrome exits immediately.
- **Process death detection.** Between port polling cycles, `process.poll()` checks if Chrome died. If it did, the stderr output is included in the error message.
- **30-second timeout with 200ms polling.** Matches the scoping decision. Most launches complete in under 2 seconds.

**Fingerprint integration deferred.** The spec says "If a fingerprint profile is provided, it is applied after launch via BRW-03." Since BRW-03 is not yet implemented, the `fingerprint` parameter is accepted but only produces a warning log. The fingerprint test was omitted. This will be connected when BRW-03 is complete.

**Platform coverage.** The binary search paths cover Linux, macOS, and Windows per the spec. Only Linux is tested (the development platform). macOS and Windows paths are untestable without those platforms.

### User Review Notes

[To be filled by user]
