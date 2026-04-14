"""Tests for BRW-01: Browser Launch.

Tests the launch_browser(), find_chrome_binary(), and cleanup_sessions()
functions. Launches real Chrome processes for integration tests.
"""

import asyncio
import json
import os
import shutil
import signal
import tempfile

import pytest

from chrome_agent.connection import check_cdp_port
from chrome_agent.launcher import (
    BrowserNotFoundError,
    LaunchResult,
    _SESSION_ROOT,
    cleanup_sessions,
    find_chrome_binary,
    launch_browser,
)

# Use a dedicated port to avoid conflicts with the conftest browser on 9333
LAUNCH_PORT = 9555


async def _kill_browser_on_port(port: int) -> None:
    """Kill a browser launched on a given port by checking targets."""
    status = check_cdp_port(port=port)
    if not status.listening:
        return
    # Find and kill the process using the port
    import subprocess
    result = subprocess.run(
        ["lsof", "-ti", f":{port}"],
        capture_output=True, text=True,
    )
    for pid_str in result.stdout.strip().split("\n"):
        if pid_str.strip():
            try:
                os.kill(int(pid_str.strip()), signal.SIGTERM)
            except (ProcessLookupError, ValueError):
                pass
    await asyncio.sleep(0.5)


@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Ensure any launched browser is cleaned up after each test."""
    yield
    # Kill any browser on the test port
    import subprocess
    result = subprocess.run(
        ["lsof", "-ti", f":{LAUNCH_PORT}"],
        capture_output=True, text=True,
    )
    for pid_str in result.stdout.strip().split("\n"):
        if pid_str.strip():
            try:
                os.kill(int(pid_str.strip()), signal.SIGTERM)
            except (ProcessLookupError, ValueError):
                pass


# ---------------------------------------------------------------------------
# Binary discovery
# ---------------------------------------------------------------------------


def test_find_chrome_binary():
    """Finds a Chrome binary on this system."""
    binary = find_chrome_binary()
    assert binary is not None, "No Chrome binary found on this system"
    assert os.path.isfile(binary)
    assert os.access(binary, os.X_OK)


# ---------------------------------------------------------------------------
# Happy path -- successful launch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_successful_launch():
    """Launches a browser that is accessible via CDP."""
    result = await launch_browser(
        port=LAUNCH_PORT,
        headless=True,
        pin_to_desktop=False,
    )
    try:
        assert isinstance(result, LaunchResult)
        assert result.port == LAUNCH_PORT
        assert result.pid > 0
        assert result.user_data_dir.startswith(_SESSION_ROOT)

        status = check_cdp_port(port=LAUNCH_PORT)
        assert status.listening is True
        assert status.browser_version is not None
    finally:
        os.kill(result.pid, signal.SIGTERM)
        await asyncio.sleep(0.5)


# ---------------------------------------------------------------------------
# Headless mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_headless_launch():
    """Headless browser is accessible via CDP."""
    result = await launch_browser(
        port=LAUNCH_PORT,
        headless=True,
        pin_to_desktop=False,
    )
    try:
        status = check_cdp_port(port=LAUNCH_PORT)
        assert status.listening is True
        assert "HeadlessChrome" in (status.browser_version or "") or "Chrome" in (status.browser_version or "")
    finally:
        os.kill(result.pid, signal.SIGTERM)
        await asyncio.sleep(0.5)


# ---------------------------------------------------------------------------
# Binary not found
# ---------------------------------------------------------------------------


def test_browser_not_found(monkeypatch):
    """Raises BrowserNotFoundError when no Chrome binary exists."""
    monkeypatch.setattr(
        "chrome_agent.launcher.find_chrome_binary",
        lambda: None,
    )

    async def do_launch():
        await launch_browser(port=LAUNCH_PORT)

    with pytest.raises(BrowserNotFoundError) as exc_info:
        asyncio.get_event_loop().run_until_complete(do_launch())
    assert len(exc_info.value.searched_paths) > 0


# ---------------------------------------------------------------------------
# Port already occupied
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_launch_port_occupied():
    """Refuses to launch when port is already in use."""
    # Launch a browser on the test port
    first = await launch_browser(
        port=LAUNCH_PORT,
        headless=True,
        pin_to_desktop=False,
    )
    try:
        # Count Chrome processes before second launch attempt
        import subprocess as sp
        before = sp.run(
            ["pgrep", "--count", "--full", "remote-debugging-port"],
            capture_output=True, text=True,
        )
        count_before = int(before.stdout.strip()) if before.returncode == 0 else 0

        # Attempt to launch on the same port
        with pytest.raises(RuntimeError, match="already in use"):
            await launch_browser(
                port=LAUNCH_PORT,
                headless=True,
                pin_to_desktop=False,
            )

        # Verify no new Chrome process was spawned
        after = sp.run(
            ["pgrep", "--count", "--full", "remote-debugging-port"],
            capture_output=True, text=True,
        )
        count_after = int(after.stdout.strip()) if after.returncode == 0 else 0
        assert count_after == count_before, (
            f"New Chrome process spawned despite occupied port: {count_before} -> {count_after}"
        )

        # Verify original browser is undisturbed
        status = check_cdp_port(port=LAUNCH_PORT)
        assert status.listening is True
    finally:
        os.kill(first.pid, signal.SIGTERM)
        await asyncio.sleep(0.5)


# ---------------------------------------------------------------------------
# Session cleanup
# ---------------------------------------------------------------------------


def test_cleanup_removes_stale_dirs():
    """Removes session directories with no running Chrome process."""
    stale_dir = os.path.join(_SESSION_ROOT, "session-stale-test")
    os.makedirs(stale_dir, exist_ok=True)
    # Create a fake SingletonLock pointing to a dead PID
    lock_path = os.path.join(stale_dir, "SingletonLock")
    try:
        os.symlink("hostname-999999", lock_path)
    except FileExistsError:
        os.remove(lock_path)
        os.symlink("hostname-999999", lock_path)

    cleanup_sessions()
    assert not os.path.exists(stale_dir), "Stale directory should be removed"


@pytest.mark.asyncio
async def test_cleanup_preserves_active_dirs():
    """Preserves session directories with a running Chrome process."""
    result = await launch_browser(
        port=LAUNCH_PORT,
        headless=True,
        pin_to_desktop=False,
    )
    try:
        assert os.path.isdir(result.user_data_dir)
        cleanup_sessions()
        assert os.path.isdir(result.user_data_dir), (
            "Active session directory should be preserved"
        )
    finally:
        os.kill(result.pid, signal.SIGTERM)
        await asyncio.sleep(0.5)
