"""Tests for BRW-01: Browser Launch.

Tests the launch_browser(), find_chrome_binary(), and cleanup_sessions()
functions. Launches real Chrome processes for integration tests.

Iteration 2: launch_browser now returns InstanceInfo (from registry),
takes port_override instead of port, and registers instances.
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
    _SESSION_ROOT,
    cleanup_sessions,
    find_chrome_binary,
    launch_browser,
)
from chrome_agent.registry import InstanceInfo, lookup

# Use a dedicated port to avoid conflicts with the conftest browser on 9333
LAUNCH_PORT = 9555


async def _kill_browser_on_port(port: int) -> None:
    """Kill a browser launched on a given port by checking targets."""
    status = check_cdp_port(port=port)
    if not status.listening:
        return
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
# Happy path -- successful launch with registry integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_successful_launch(tmp_path):
    """Launches a browser, returns InstanceInfo, and registers in the registry."""
    reg_path = str(tmp_path / "registry.json")

    result = await launch_browser(
        port_override=LAUNCH_PORT,
        headless=True,
        pin_to_desktop=False,
        working_dir="/home/user/testproject",
        registry_path=reg_path,
    )
    try:
        assert isinstance(result, InstanceInfo)
        assert result.port == LAUNCH_PORT
        assert result.pid > 0
        assert result.name == "testproject-01"
        assert result.user_data_dir.startswith(_SESSION_ROOT)

        # Verify browser is running
        status = check_cdp_port(port=LAUNCH_PORT)
        assert status.listening is True

        # Verify instance is in registry
        looked_up = lookup("testproject-01", registry_path=reg_path)
        assert looked_up.port == LAUNCH_PORT
        assert looked_up.pid == result.pid
    finally:
        os.kill(result.pid, signal.SIGTERM)
        await asyncio.sleep(0.5)


# ---------------------------------------------------------------------------
# Headless mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_headless_launch(tmp_path):
    """Headless browser is accessible via CDP."""
    reg_path = str(tmp_path / "registry.json")

    result = await launch_browser(
        port_override=LAUNCH_PORT,
        headless=True,
        pin_to_desktop=False,
        registry_path=reg_path,
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
        await launch_browser(port_override=LAUNCH_PORT)

    with pytest.raises(BrowserNotFoundError) as exc_info:
        asyncio.get_event_loop().run_until_complete(do_launch())
    assert len(exc_info.value.searched_paths) > 0


# ---------------------------------------------------------------------------
# Auto-port allocation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_port_allocation(tmp_path):
    """Launch with no port_override auto-allocates a port."""
    reg_path = str(tmp_path / "registry.json")

    result = await launch_browser(
        headless=True,
        pin_to_desktop=False,
        working_dir="/home/user/autoport",
        registry_path=reg_path,
    )
    try:
        assert result.port >= 9222
        status = check_cdp_port(port=result.port)
        assert status.listening is True
    finally:
        os.kill(result.pid, signal.SIGTERM)
        await asyncio.sleep(0.5)


# ---------------------------------------------------------------------------
# Instance naming
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_instance_naming(tmp_path):
    """Instance name derived from working_dir basename."""
    reg_path = str(tmp_path / "registry.json")

    result = await launch_browser(
        port_override=LAUNCH_PORT,
        headless=True,
        pin_to_desktop=False,
        working_dir="/home/user/aroundchicago.tech",
        registry_path=reg_path,
    )
    try:
        assert result.name == "aroundchicago.tech-01"
    finally:
        os.kill(result.pid, signal.SIGTERM)
        await asyncio.sleep(0.5)


# ---------------------------------------------------------------------------
# Session cleanup
# ---------------------------------------------------------------------------


def test_cleanup_removes_stale_dirs(tmp_path):
    """Removes session directories with no running Chrome process."""
    stale_dir = os.path.join(_SESSION_ROOT, "session-stale-test")
    os.makedirs(stale_dir, exist_ok=True)
    lock_path = os.path.join(stale_dir, "SingletonLock")
    try:
        os.symlink("hostname-999999", lock_path)
    except FileExistsError:
        os.remove(lock_path)
        os.symlink("hostname-999999", lock_path)

    reg_path = str(tmp_path / "registry.json")
    cleanup_sessions(registry_path=reg_path)
    assert not os.path.exists(stale_dir), "Stale directory should be removed"


@pytest.mark.asyncio
async def test_cleanup_preserves_active_dirs(tmp_path):
    """Preserves session directories with a running Chrome process."""
    reg_path = str(tmp_path / "registry.json")

    result = await launch_browser(
        port_override=LAUNCH_PORT,
        headless=True,
        pin_to_desktop=False,
        registry_path=reg_path,
    )
    try:
        assert os.path.isdir(result.user_data_dir)
        cleanup_sessions(registry_path=reg_path)
        assert os.path.isdir(result.user_data_dir), (
            "Active session directory should be preserved"
        )
    finally:
        os.kill(result.pid, signal.SIGTERM)
        await asyncio.sleep(0.5)
