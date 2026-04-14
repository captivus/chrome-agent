# Feature Specification

> *This document is the complete definition of a single atomic feature -- what to build, how to validate it, what to observe during implementation, what it depends on, and (once implementation begins) its implementation history.*

## 1. Feature ID and Name

BRW-01: Browser Launch

## 2. User Story

As an AI agent, I want to launch a Chrome browser with CDP enabled so that I can connect to it and control it through the protocol, without needing to manually find and start Chrome with the right flags.

## 3. Implementation Contract

### Level 1 -- Plain English

This feature finds the Chrome or Chromium binary on the system, launches it as a subprocess with remote debugging enabled on a specified port, and waits for the CDP port to become available before returning. The browser continues running after chrome-agent exits -- it is a fire-and-forget launch.

The binary discovery searches platform-specific standard paths. On Linux, it looks for google-chrome, chromium-browser, and chromium in standard locations. On macOS, it looks in the Applications directory. On Windows, it looks in Program Files. If no binary is found, it fails with a helpful error listing the paths it searched.

The browser is launched with a temporary user data directory (so it doesn't conflict with the user's normal Chrome profile), with the automation-detection flag disabled, and with remote debugging on the requested port.

After starting the subprocess, the feature polls the CDP port (using BRW-02's check_cdp_port) until the browser is ready to accept connections, then returns the browser version.

If a fingerprint profile is provided, it is applied after launch via BRW-03.

On Linux with X11, the browser window can optionally be moved to the virtual desktop where the launching terminal is, so the browser appears on the same workspace as the agent. This requires xdotool and is silently skipped if unavailable.

### Level 2 -- Logic Flow (INPUT / LOGIC / OUTPUT)

**INPUT:**

- `port`: integer, default 9222 -- CDP remote debugging port
- `fingerprint`: string or None -- path to a fingerprint profile JSON file
- `headless`: bool, default False -- run in headless mode
- `wm_class`: string, default "chrome-agent" -- X11 window class name (for desktop pinning)
- `pin_to_desktop`: bool, default True -- move browser to launching terminal's desktop (Linux/X11 only)

**LOGIC:**

```
launch_browser(port, fingerprint, headless, wm_class, pin_to_desktop):
    // Phase 1: Find Chrome binary
    binary = find_chrome_binary()
    if binary is None:
        raise BrowserNotFoundError(searched_paths)

    // Phase 2: Prepare launch arguments
    root_dir = "/tmp/chrome-agent"
    ensure_directory_exists(root_dir)
    session_dir = create_subdirectory(root_dir, prefix="session-")
    args = [
        binary,
        "--remote-debugging-port={port}",
        "--disable-blink-features=AutomationControlled",
        "--user-data-dir={session_dir}",
        "--class={wm_class}",
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

    // Phase 5: Apply fingerprint if provided
    if fingerprint is not None:
        profile = load_fingerprint(path=fingerprint)
        apply_fingerprint(port=port, profile=profile)

    // Phase 6: Pin to desktop (Linux/X11, best-effort)
    if pin_to_desktop:
        move_to_launching_desktop(wm_class=wm_class)

    return LaunchResult(
        pid=process.pid,
        port=port,
        browser_version=status.browser_version,
        user_data_dir=session_dir,
    )


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

move_to_launching_desktop(wm_class):
    // Requires xdotool. Silently skipped if unavailable.
    try:
        desktop = get_current_desktop()  // xdotool get_desktop or get_desktop_for_window $WINDOWID
        sleep(0.5 seconds)  // wait for browser window to appear
        window_ids = xdotool_search_by_class(wm_class)
        for wid in window_ids:
            xdotool_set_desktop_for_window(wid, desktop)
    except xdotool_not_found:
        pass  // silently skip
```

**OUTPUT:**

- On success: returns LaunchResult with pid, port, browser_version, and user_data_dir. Browser process is running.
- On failure: raises BrowserNotFoundError (no Chrome binary) or TimeoutError (browser didn't start).
- The browser process is NOT managed by chrome-agent. It continues running independently.
- Session data lives under `/tmp/chrome-agent/session-<id>/`. The system cleans `/tmp` on reboot. Between reboots, `cleanup_sessions()` removes stale directories.

### Level 3 -- Formal Interfaces

```python
@dataclass
class LaunchResult:
    """Result of launching a browser."""
    pid: int
    port: int
    browser_version: str
    user_data_dir: str


class BrowserNotFoundError(Exception):
    """Chrome/Chromium binary not found on the system."""
    def __init__(self, searched_paths: list[str]):
        self.searched_paths = searched_paths
        paths_str = "\n  ".join(searched_paths)
        super().__init__(
            f"Chrome/Chromium not found. Searched:\n  {paths_str}"
        )


async def launch_browser(
    port: int = 9222,
    fingerprint: str | None = None,
    headless: bool = False,
    wm_class: str = "chrome-agent",
    pin_to_desktop: bool = True,
) -> LaunchResult:
    """Launch Chrome with CDP enabled.

    Finds the Chrome binary, starts it with --remote-debugging-port,
    waits for the port to be ready, and optionally applies a fingerprint
    profile.

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

### Level 2 -- Test Logic (GIVEN / WHEN / THEN)

Scenario: Successful launch
GIVEN: Chrome is installed on the system, port 9333 is free
WHEN: launch_browser(port=9333) is called
THEN: check_cdp_port(port=9333).listening is True, browser_version contains "Chrome" or "Chromium"

Scenario: Browser not found
GIVEN: no Chrome binary exists at any searched path (test with a mocked find_chrome_binary returning None)
WHEN: launch_browser() is called
THEN: BrowserNotFoundError is raised with a non-empty searched_paths list

Scenario: Headless launch
GIVEN: Chrome is installed, port 9333 is free
WHEN: launch_browser(port=9333, headless=True) is called
THEN: check_cdp_port(port=9333).listening is True (browser is running headlessly)

Scenario: Launch with fingerprint
GIVEN: Chrome is installed, port 9333 is free, a valid fingerprint profile exists
WHEN: launch_browser(port=9333, fingerprint="path/to/profile.json") is called
THEN: connecting via CDP and evaluating navigator.userAgent returns the fingerprint's user agent value

### Level 3 -- Formal Test Definitions

```
test_successful_launch:
    setup:
        port 9333 is free (no browser running)
    action:
        await launch_browser(port=9333)
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
        await launch_browser(port=9333, headless=True)
    assertions:
        check_cdp_port(port=9333).listening is True
    teardown:
        kill browser process on port 9333

test_launch_with_fingerprint:
    setup:
        port 9333 is free
        fingerprint profile at /tmp/test-fingerprint.json with userAgent "TestAgent/1.0"
    action:
        result = await launch_browser(port=9333, fingerprint="/tmp/test-fingerprint.json")
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
```

## 5. Feedback Channels

### Visual

After launching, take a screenshot via CDP to verify the browser started and is rendering. For headless mode, verify the screenshot is non-empty (browser is producing frames even without a window).

### Auditory

Monitor subprocess stderr output from Chrome during launch. Chrome logs startup information and errors to stderr. If the browser fails to start (bad flags, port conflict, missing GPU libraries), the diagnostic information is in Chrome's stderr.

### Tactile

Run `chrome-agent launch` from the terminal, then run `chrome-agent status` to verify the browser is running. Open a session and send a command. This is the end-to-end workflow from the MPS.

## 6. Dependencies

| Dependency | What this feature needs from it | Rationale |
|------------|--------------------------------|-----------|
| BRW-02 | check_cdp_port() to poll for port readiness after launch | Need to know when the browser is ready to accept connections |

## 7. Scoping Decisions

| Decision | What prompted it | Rationale | Revisit when |
|----------|-----------------|-----------|--------------|
| No port conflict detection before launch | Edge case consideration | Checking the port before launch adds a race condition (port could become occupied between check and launch). Let Chrome fail on its own if the port is in use -- the timeout will catch it. | If agents frequently hit port conflicts and the timeout-based detection is too slow. |
| Fresh session directory per launch | Simplicity | A fresh profile avoids state leakage between sessions. All session directories live under `/tmp/chrome-agent/` so the system cleans them on reboot. Between reboots, `cleanup_sessions()` removes stale directories. | If persistent browser profiles become a common need. |
| 30 second startup timeout | Reasonable default | Most Chrome launches complete in under 5 seconds. 30 seconds accommodates slow systems without hanging indefinitely. | If real-world usage shows this is too short (e.g., first launch downloading components) or too long. |
| Function is async despite mostly sync body | apply_fingerprint requires CDP (async), polling should use asyncio.sleep to not block the event loop | The async boundary is at launch_browser so callers don't need to manage the sync/async split themselves. | N/A |
| SingletonLock parsing is best-effort | Chrome writes SingletonLock as a symlink with format "hostname-PID" but this is undocumented Chrome internals | If the lock file format can't be parsed, treat the directory as active (don't delete it). Verify the actual format empirically during implementation. | If Chrome changes the lock file format. |

## 8. Learnings

| # | Topic | Type | Summary | Link |
|---|-------|------|---------|------|
| None | | | The existing browser.py in the current codebase implements this feature using Playwright's launch_persistent_context. The reimplementation replaces Playwright's launcher with direct subprocess management. | src/chrome_agent/browser.py |

---

## 9. Implementation Status

**Status:** Complete

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
