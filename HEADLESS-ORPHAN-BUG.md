# Bug: Headless orphan process hijacks CDP port, silently steals commands from headed sessions

## Summary

When a headless Chromium process from a previous session remains running on the default CDP port (9222), `chrome-agent launch` fails to bind to the port but does not report the failure clearly. Subsequent commands (`navigate`, `screenshot`, `eval`, etc.) silently connect to the headless orphan instead of the visible browser window, making the tool appear non-functional to the user.

## Observed behavior

1. A previous session launched a headless browser on port 9222 (e.g., from another agent or an earlier `chrome-agent launch --headless` call).
2. The process was never cleaned up. It survived across sessions because `chrome-agent launch` runs the browser in a keep-alive loop (`while True: await asyncio.sleep(60)`), and killing the parent process (Ctrl+C, session end) may not propagate to the Chromium child process.
3. In a new session, `chrome-agent launch` (headed mode) is called. It either:
   - Fails to bind to port 9222 because the orphan holds it, or
   - Launches on a different port, but the user doesn't know which port
4. A Chromium window appears on the user's desktop (from the new launch), but it's not the instance on port 9222.
5. All subsequent commands (`chrome-agent navigate`, `chrome-agent screenshot`, etc.) connect to port 9222 by default, hitting the invisible headless orphan.
6. The agent gets valid responses (screenshots render, navigation succeeds, JS executes), but the user sees nothing in the visible browser window.
7. From the user's perspective, chrome-agent is broken -- a window opened but never shows any content.

## Root cause

Three things combine to produce the bug:

### 1. `launch` does not check if the port is already occupied

`_run_launch()` in `cli.py` calls `launch_browser(port=port)` without first checking `check_cdp_port(port=port)`. If the port is occupied, the behavior depends on Playwright/Chromium -- it may fail, bind to a random port, or produce an error that gets swallowed.

### 2. Commands default to port 9222 without validating what's there

`_run_command()` connects to whatever is listening on port 9222 via `connect(port=port)`. It has no way to distinguish a headed browser from a headless orphan. It doesn't warn if the browser was launched headless.

### 3. No process cleanup on session end

When `chrome-agent launch` runs in a terminal and the terminal is closed, the keep-alive loop (`while True: await asyncio.sleep(60)`) may be interrupted, but the Chromium child process can survive as an orphan. Playwright's `launch_persistent_context()` spawns Chromium as a subprocess, and if the parent dies without calling `session.browser.close()`, Chromium keeps running.

## How to reproduce

```bash
# Terminal 1: launch a headless browser
chrome-agent launch --headless &
# Kill the parent without cleanup
kill $!

# Verify the orphan is still there
chrome-agent status
# Output: Browser running on port 9222

# Terminal 2: launch a headed browser
chrome-agent launch  # Opens a window, but may not bind to 9222

# Navigate -- goes to the headless orphan, not the visible window
chrome-agent navigate "https://example.com"
# The visible window shows nothing
```

## Diagnosis commands

```bash
# Check what's on port 9222
chrome-agent status

# Find the actual process
ps aux | grep remote-debugging-port

# Look for --headless flag in the process args
ps aux | grep "remote-debugging-port=9222" | grep headless
# If this returns a result, you have a headless orphan

# Kill it
kill <PID>

# Verify port is clear
chrome-agent status
# Output: No browser running on port 9222

# Now launch cleanly
chrome-agent launch
```

## Suggested fixes

### Fix 1: Pre-flight check in `launch` (minimum viable fix)

Before launching, check if the port is occupied. Refuse to launch and tell the user what's there.

```python
async def _run_launch(*, port: int, args: list[str]) -> None:
    status = check_cdp_port(port=port)
    if status.listening:
        print(f"ERROR: Port {port} is already in use.")
        print(f"  Version: {status.browser_version}")
        print(f"  URL:     {status.page_url}")
        # Check if it's headless
        # (would need to inspect /proc/<pid>/cmdline or similar)
        print(f"\nTo clear it: kill the process on port {port}, then retry.")
        print(f"  Find it:  lsof -ti:{port}")
        print(f"  Kill it:  kill $(lsof -ti:{port})")
        sys.exit(1)
    # ... proceed with launch
```

### Fix 2: Offer to kill the existing process

Instead of just refusing, offer to take over:

```python
    if status.listening:
        print(f"Port {port} is already in use by: {status.browser_version}")
        print(f"  URL: {status.page_url}")
        response = input("Kill existing browser and launch a new one? [y/N]: ")
        if response.lower() == 'y':
            # Kill the process on the port
            subprocess.run(["kill", subprocess.check_output(
                ["lsof", "-ti", f":{port}"]
            ).decode().strip()])
            await asyncio.sleep(1)
        else:
            sys.exit(1)
```

Note: this approach requires interactive input, which is not available when an AI agent is driving chrome-agent. A non-interactive variant (a `--force` flag) would be needed for agent use.

### Fix 3: `--force` flag for non-interactive use

```bash
chrome-agent launch --force  # Kill whatever's on the port and take over
```

This is the agent-friendly approach. The agent can always pass `--force` to ensure a clean launch.

### Fix 4: `status` command should report headed vs headless

When `chrome-agent status` reports a running browser, it should indicate whether the browser is headed or headless. This can be determined by:
- Checking `/proc/<pid>/cmdline` for `--headless` flag
- Or querying the CDP endpoint for headless indicators

```
$ chrome-agent status
Browser running on port 9222 (headless)
  Version: Chrome/146.0.7680.177
  URL:     https://example.com
  Title:   Example Domain
  WARNING: This is a headless browser -- commands will work but no window is visible.
```

### Fix 5: Process cleanup on exit

Ensure the Chromium child process is always killed when the parent exits, even on unclean termination:

```python
import atexit
import signal

async def _run_launch(*, port: int, args: list[str]) -> None:
    session = await launch_browser(port=port, ...)

    # Register cleanup for all exit paths
    def cleanup():
        # Force-kill the browser process group
        ...

    atexit.register(cleanup)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    # ...
```

## Impact

This bug affects any user or AI agent that uses chrome-agent across multiple sessions. The probability increases over time as orphaned processes accumulate. The user experience is particularly bad because:

1. The tool appears to work (commands return valid data)
2. But the user sees nothing (all work goes to a headless process)
3. There is no warning or error message
4. The only diagnostic is to manually inspect processes with `ps aux`

For AI agents specifically, this means the agent is confidently reporting screenshots and navigation results that the user cannot observe or verify, undermining the trust and transparency that chrome-agent is designed to provide.
