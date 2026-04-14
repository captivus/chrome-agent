"""Browser launch and session management.

Finds Chrome/Chromium on the system, launches it with CDP enabled,
waits for the port to become ready, and manages session directories.
No Playwright dependency -- uses subprocess directly.
"""

import asyncio
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass

from .connection import check_cdp_port

logger = logging.getLogger(__name__)

_SESSION_ROOT = "/tmp/chrome-agent"


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


def find_chrome_binary() -> str | None:
    """Search platform-specific paths for Chrome/Chromium.

    Returns the path to the first found executable, or None.
    """
    candidates = _platform_candidates()
    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def _platform_candidates() -> list[str]:
    """Return platform-specific Chrome/Chromium binary paths."""
    if sys.platform == "linux":
        return [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium",
            "/snap/bin/chromium",
        ]
    elif sys.platform == "darwin":
        return [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
    elif sys.platform == "win32":
        return [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
    return []


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
    # Phase 1: Find Chrome binary
    binary = find_chrome_binary()
    if binary is None:
        raise BrowserNotFoundError(searched_paths=_platform_candidates())

    # Phase 2: Prepare launch arguments
    os.makedirs(_SESSION_ROOT, exist_ok=True)
    session_dir = tempfile.mkdtemp(prefix="session-", dir=_SESSION_ROOT)

    args = [
        binary,
        f"--remote-debugging-port={port}",
        "--disable-blink-features=AutomationControlled",
        f"--user-data-dir={session_dir}",
        f"--class={wm_class}",
    ]
    if headless:
        args.append("--headless=new")

    # Phase 3: Launch subprocess
    process = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    logger.info("Launched Chrome PID %d on port %d", process.pid, port)

    # Phase 4: Wait for CDP port to be ready
    deadline = asyncio.get_event_loop().time() + 30.0
    status = None
    while asyncio.get_event_loop().time() < deadline:
        # Check if process died
        if process.poll() is not None:
            stderr_output = process.stderr.read().decode(errors="replace") if process.stderr else ""
            raise RuntimeError(
                f"Chrome exited immediately with code {process.returncode}. "
                f"stderr: {stderr_output[:500]}"
            )
        status = check_cdp_port(port=port)
        if status.listening:
            break
        await asyncio.sleep(0.2)
    else:
        # Timeout -- kill the process and fail
        process.kill()
        raise TimeoutError("Browser did not start within 30 seconds")

    # Phase 5: Apply fingerprint if provided
    if fingerprint is not None:
        # BRW-03 (Fingerprint Profiles) will provide this functionality.
        # For now, log a warning if fingerprint is requested but not yet available.
        logger.warning("Fingerprint profiles not yet implemented (BRW-03)")

    # Phase 6: Pin to desktop (Linux/X11, best-effort)
    if pin_to_desktop and not headless:
        await _move_to_launching_desktop(wm_class=wm_class)

    return LaunchResult(
        pid=process.pid,
        port=port,
        browser_version=status.browser_version or "unknown",
        user_data_dir=session_dir,
    )


def cleanup_sessions() -> None:
    """Remove stale session directories under /tmp/chrome-agent/.

    Removes directories that don't have a running Chrome process
    (checks Chrome's SingletonLock file and whether the PID is alive).
    """
    if not os.path.isdir(_SESSION_ROOT):
        return

    for entry in os.listdir(_SESSION_ROOT):
        session_dir = os.path.join(_SESSION_ROOT, entry)
        if not os.path.isdir(session_dir):
            continue

        lock_file = os.path.join(session_dir, "SingletonLock")
        if not os.path.exists(lock_file) and not os.path.islink(lock_file):
            # No lock file -- safe to remove
            logger.info("Removing stale session directory: %s", session_dir)
            shutil.rmtree(session_dir, ignore_errors=True)
        else:
            # Lock file exists -- check if the process is alive
            pid = _read_lock_pid(lock_file=lock_file)
            if pid is not None and not _process_is_running(pid=pid):
                logger.info("Removing stale session directory (dead PID %d): %s", pid, session_dir)
                shutil.rmtree(session_dir, ignore_errors=True)


def _read_lock_pid(lock_file: str) -> int | None:
    """Read the PID from Chrome's SingletonLock file.

    Chrome creates SingletonLock as a symlink with target "hostname-PID".
    Returns the PID, or None if the format can't be parsed.
    """
    try:
        # SingletonLock is a symlink, not a regular file
        target = os.readlink(lock_file)
        # Format: "hostname-PID"
        parts = target.rsplit("-", 1)
        if len(parts) == 2:
            return int(parts[1])
    except (OSError, ValueError):
        pass
    return None


def _process_is_running(pid: int) -> bool:
    """Check if a process with the given PID is still running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


async def _move_to_launching_desktop(wm_class: str) -> None:
    """Move the browser window to the terminal's virtual desktop.

    Linux/X11 only. Requires xdotool. Silently does nothing if
    xdotool is unavailable or on non-X11 systems.
    """
    try:
        window_id = os.environ.get("WINDOWID", "")
        if window_id:
            result = subprocess.run(
                ["xdotool", "get_desktop_for_window", window_id],
                capture_output=True, text=True,
            )
            desktop = result.stdout.strip()
        else:
            result = subprocess.run(
                ["xdotool", "get_desktop"],
                capture_output=True, text=True,
            )
            desktop = result.stdout.strip()

        if not desktop:
            return

        await asyncio.sleep(0.5)

        result = subprocess.run(
            ["xdotool", "search", "--class", wm_class],
            capture_output=True, text=True,
        )
        for wid in result.stdout.strip().split("\n"):
            if wid.strip():
                subprocess.run(
                    ["xdotool", "set_desktop_for_window", wid.strip(), desktop],
                )

        logger.info("Moved browser window(s) to desktop %s", desktop)
    except FileNotFoundError:
        logger.debug("xdotool not available -- skipping desktop move")
    except Exception as exc:
        logger.debug("Could not move browser to desktop: %s", exc)
