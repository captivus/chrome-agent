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


def _fake_chrome(directory, name="google-chrome"):
    """Write an executable stand-in for a Chrome binary and return its path."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text("#!/bin/sh\nexit 0\n")
    path.chmod(0o755)
    return str(path)


def test_discovery_prefers_explicit_argument(tmp_path, monkeypatch):
    """The chrome_path argument wins over every other source."""
    binary = _fake_chrome(tmp_path)
    monkeypatch.delenv("CHROME_AGENT_PATH", raising=False)
    monkeypatch.setenv("PATH", "")
    monkeypatch.setattr("chrome_agent.launcher._platform_candidates", lambda: [])

    assert find_chrome_binary(chrome_path=binary) == binary


def test_discovery_honors_chrome_path_env(tmp_path, monkeypatch):
    """CHROME_AGENT_PATH points at a browser the standard locations do not have."""
    binary = _fake_chrome(tmp_path)
    monkeypatch.setenv("CHROME_AGENT_PATH", binary)
    monkeypatch.setenv("PATH", "")
    monkeypatch.setattr("chrome_agent.launcher._platform_candidates", lambda: [])

    assert find_chrome_binary() == binary


def test_discovery_argument_beats_env(tmp_path, monkeypatch):
    """--chrome-path overrides CHROME_AGENT_PATH."""
    flag_binary = _fake_chrome(tmp_path / "flag", name="google-chrome")
    env_binary = _fake_chrome(tmp_path / "env", name="google-chrome")
    monkeypatch.setenv("CHROME_AGENT_PATH", env_binary)

    assert find_chrome_binary(chrome_path=flag_binary) == flag_binary


def test_discovery_standard_locations_win_over_path(tmp_path, monkeypatch):
    """A browser at a standard location beats a different one on PATH.

    Pins the resolution order itself: PATH is the last resort, so adding it
    cannot change which browser an already-working host launches.
    """
    candidate = _fake_chrome(tmp_path / "standard")
    _fake_chrome(tmp_path / "path")
    monkeypatch.delenv("CHROME_AGENT_PATH", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path / "path"))
    monkeypatch.setattr(
        "chrome_agent.launcher._platform_candidates", lambda: [candidate]
    )

    assert find_chrome_binary() == candidate


def test_discovery_searches_path_when_no_standard_install(tmp_path, monkeypatch):
    """Chrome reachable only via PATH is found (Playwright/Nix/rootless hosts).

    Regression: discovery probed a fixed list of absolute paths, so an
    unprivileged environment whose browser lives outside /usr/bin -- a
    Playwright-managed chromium, a Nix store path -- could not launch at all.
    """
    binary = _fake_chrome(tmp_path, name="chromium")
    monkeypatch.delenv("CHROME_AGENT_PATH", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setattr("chrome_agent.launcher._platform_candidates", lambda: [])

    assert find_chrome_binary() == binary


def test_discovery_finds_a_plain_chrome_on_path(tmp_path, monkeypatch):
    """A binary named `chrome` is found -- the name no candidate list carries."""
    binary = _fake_chrome(tmp_path, name="chrome")
    monkeypatch.delenv("CHROME_AGENT_PATH", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setattr("chrome_agent.launcher._platform_candidates", lambda: [])

    assert find_chrome_binary() == binary


def test_discovery_falls_back_to_platform_candidates(tmp_path, monkeypatch):
    """With no override and nothing on PATH, the standard locations still win."""
    binary = _fake_chrome(tmp_path)
    monkeypatch.delenv("CHROME_AGENT_PATH", raising=False)
    monkeypatch.setenv("PATH", "")
    monkeypatch.setattr("chrome_agent.launcher._platform_candidates", lambda: [binary])

    assert find_chrome_binary() == binary


def test_discovery_flag_override_does_not_fall_back(tmp_path, monkeypatch):
    """A wrong --chrome-path fails instead of launching a different browser."""
    _fake_chrome(tmp_path)
    monkeypatch.setenv("PATH", str(tmp_path))

    assert find_chrome_binary(chrome_path=str(tmp_path / "nonexistent")) is None


def test_discovery_env_override_does_not_fall_back(tmp_path, monkeypatch):
    """A wrong CHROME_AGENT_PATH fails, like a wrong --chrome-path.

    The variable is this project's own, so a value in it is an instruction to
    chrome-agent: honoring it or failing is right, quietly launching something
    else is not.
    """
    _fake_chrome(tmp_path)
    monkeypatch.setenv("CHROME_AGENT_PATH", str(tmp_path / "moved-away"))
    monkeypatch.setattr(
        "chrome_agent.launcher._platform_candidates", lambda: [_fake_chrome(tmp_path / "standard")]
    )

    assert find_chrome_binary() is None


def test_discovery_ignores_the_unnamespaced_chrome_path(tmp_path, monkeypatch):
    """A foreign CHROME_PATH is not read at all.

    Lighthouse's chrome-launcher owns that name. Reading it would let another
    tool's variable -- stale or merely pointing at a different browser -- decide
    what chrome-agent launches on a host that already resolves one.
    """
    candidate = _fake_chrome(tmp_path / "standard")
    monkeypatch.delenv("CHROME_AGENT_PATH", raising=False)
    monkeypatch.setenv("CHROME_PATH", _fake_chrome(tmp_path / "lighthouse"))
    monkeypatch.setattr(
        "chrome_agent.launcher._platform_candidates", lambda: [candidate]
    )

    assert find_chrome_binary() == candidate


def test_discovery_expands_a_tilde_in_an_override(tmp_path, monkeypatch):
    """`~` in an override is expanded -- env files and unit files do not."""
    binary = _fake_chrome(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))

    assert find_chrome_binary(chrome_path="~/google-chrome") == binary


def test_discovery_error_names_the_escape_hatches():
    """The not-found error tells the user how to point chrome-agent at a browser."""
    message = str(BrowserNotFoundError(searched_paths=["/usr/bin/google-chrome"]))

    assert "CHROME_AGENT_PATH" in message
    assert "--chrome-path" in message
    assert "on PATH" in message


def test_discovery_error_for_a_bad_override_says_what_is_wrong(tmp_path):
    """The override branch names the unusable path instead of re-advising the flag.

    Suggesting PATH or CHROME_AGENT_PATH there is inert -- an override
    suppresses both searches -- and the user just set the thing suggested.
    """
    missing = str(tmp_path / "nonexistent")

    message = str(BrowserNotFoundError(
        searched_paths=[missing], override=f"--chrome-path {missing}"
    ))

    assert missing in message
    assert "does not name an executable" in message
    assert "install Chrome/Chromium on PATH" not in message


def test_discovery_error_for_a_bad_env_override_names_the_variable(tmp_path):
    """The env override branch names CHROME_AGENT_PATH, not the flag."""
    missing = str(tmp_path / "nonexistent")

    message = str(BrowserNotFoundError(
        searched_paths=[missing], override=f"CHROME_AGENT_PATH={missing}"
    ))

    assert f"CHROME_AGENT_PATH={missing}" in message
    assert "--chrome-path" not in message


def test_discovery_launch_rejects_a_bad_chrome_path(tmp_path):
    """launch_browser reports the override it was given when it does not resolve."""
    missing = str(tmp_path / "nonexistent")

    with pytest.raises(BrowserNotFoundError) as exc_info:
        asyncio.run(launch_browser(chrome_path=missing, port_override=LAUNCH_PORT))
    assert exc_info.value.searched_paths == [missing]


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
        lambda **kwargs: None,
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
