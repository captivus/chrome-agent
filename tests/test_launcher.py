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
    default_persistent_profile_dir,
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
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{LAUNCH_PORT}"],
            capture_output=True, text=True,
        )
    except FileNotFoundError:
        return
    for pid_str in result.stdout.strip().split("\n"):
        if pid_str.strip():
            try:
                os.kill(int(pid_str.strip()), signal.SIGTERM)
            except (ProcessLookupError, ValueError, OSError):
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
        asyncio.run(do_launch())
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


# ---------------------------------------------------------------------------
# Persistent profile
# ---------------------------------------------------------------------------


def test_default_persistent_profile_dir_windows(monkeypatch):
    """Windows profile lives under LOCALAPPDATA, not daily Chrome."""
    monkeypatch.setattr("chrome_agent.launcher.sys.platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\bart\AppData\Local")
    path = default_persistent_profile_dir()
    assert path == os.path.join(
        r"C:\Users\bart\AppData\Local", "chrome-agent", "profile",
    )


def test_default_persistent_profile_dir_linux(monkeypatch):
    monkeypatch.setattr("chrome_agent.launcher.sys.platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", "/home/bart/.local/share")
    path = default_persistent_profile_dir()
    assert path == os.path.join(
        "/home/bart/.local/share", "chrome-agent", "profile",
    )


@pytest.mark.asyncio
async def test_refuses_daily_chrome_profile(tmp_path):
    """Will not launch against Chrome's everyday User Data directory."""
    daily = tmp_path / "Google" / "Chrome" / "User Data"
    daily.mkdir(parents=True)
    with pytest.raises(ValueError, match="daily profile"):
        await launch_browser(
            user_data_dir=str(daily),
            headless=True,
            pin_to_desktop=False,
            registry_path=str(tmp_path / "registry.json"),
        )


@pytest.mark.asyncio
async def test_persistent_and_user_data_dir_are_mutex(tmp_path):
    with pytest.raises(ValueError, match="not both"):
        await launch_browser(
            persistent=True,
            user_data_dir=str(tmp_path / "profile"),
            headless=True,
            pin_to_desktop=False,
            registry_path=str(tmp_path / "registry.json"),
        )


@pytest.mark.asyncio
async def test_launch_user_data_dir_keeps_existing_prefs(tmp_path):
    """Reuses the supplied profile and does not clobber existing Preferences."""
    profile = tmp_path / "agent-profile"
    prefs_path = profile / "Default" / "Preferences"
    prefs_path.parent.mkdir(parents=True)
    prefs_path.write_text('{"keep": true}', encoding="utf-8")
    reg_path = str(tmp_path / "registry.json")

    result = await launch_browser(
        port_override=LAUNCH_PORT,
        headless=True,
        pin_to_desktop=False,
        working_dir="/home/user/persisttest",
        registry_path=reg_path,
        user_data_dir=str(profile),
    )
    try:
        assert result.persistent is True
        assert os.path.normcase(os.path.abspath(result.user_data_dir)) == (
            os.path.normcase(os.path.abspath(str(profile)))
        )
        assert json.loads(prefs_path.read_text(encoding="utf-8")) == {"keep": True}

        reused = await launch_browser(
            headless=True,
            pin_to_desktop=False,
            registry_path=reg_path,
            user_data_dir=str(profile),
        )
        assert reused.name == result.name
        assert reused.pid == result.pid
    finally:
        os.kill(result.pid, signal.SIGTERM)
        await asyncio.sleep(0.5)
