"""Tests for PID identity and ghost-entry handling.

Covers the namespace-PID ghost scenario: a browser launched from inside a
PID-namespaced sandbox (e.g. an agent CLI's bwrap with --unshare-pid and a
shared /tmp) records a namespace-local PID in the registry. On the host that
PID aliases to an unrelated process -- observed in practice as root kernel
threads -- which the old bare-existence check treated as a live browser
forever: status showed the instance alive, cleanup never reaped it, and
stop's SIGTERM fallback fired at the foreign PID.

All tests use tmp_path registry isolation and monkeypatched os.kill where a
foreign-PID response must be deterministic -- no dependence on host PID layout.
"""

import json
import os
import socket
import subprocess
import sys

import pytest

from chrome_agent import registry as reg
from chrome_agent.registry import (
    InstanceNotFoundError,
    allocate_port,
    cleanup,
    enumerate_instances,
    lookup,
    register,
    stop,
)
from chrome_agent.utils import process_is_ours, process_start_time

GHOST_PID = 999999901  # never a real PID in these tests; os.kill is faked for it


def _dead_pid() -> int:
    """A PID guaranteed not to be running (spawned, then reaped)."""
    p = subprocess.Popen(["true"])
    p.wait()
    return p.pid


def _free_port() -> int:
    """A port with nothing listening on it (bound then released)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("localhost", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def foreign_pid(monkeypatch):
    """Make GHOST_PID behave like another user's process: unsignalable.

    Mimics what a namespace-local PID aliasing to a root kernel thread does on
    the host. Records every non-zero signal fired at it -- the fix's contract
    is that this list stays empty.
    """
    real_kill = os.kill
    fired: list[tuple[int, int]] = []

    def fake_kill(pid, sig):
        if pid == GHOST_PID:
            if sig != 0:
                fired.append((pid, sig))
            raise PermissionError(1, "Operation not permitted")
        return real_kill(pid, sig)

    monkeypatch.setattr(os, "kill", fake_kill)
    return fired


# --- process identity primitives ---


def test_unsignalable_pid_is_not_ours(foreign_pid):
    """PermissionError means another user's process -- never our browser."""
    assert process_is_ours(pid=GHOST_PID) is False


def test_dead_pid_is_not_ours():
    assert process_is_ours(pid=_dead_pid()) is False


def test_own_pid_is_ours_and_start_token_matches():
    token = process_start_time(pid=os.getpid())
    assert token is not None
    assert process_is_ours(pid=os.getpid()) is True
    assert process_is_ours(pid=os.getpid(), expected_start=token) is True


def test_start_token_mismatch_means_recycled_pid():
    """A live PID with a different start time is a later occupant, not ours."""
    assert process_is_ours(pid=os.getpid(), expected_start="not-the-real-token") is False


def test_start_time_of_dead_pid_is_none():
    assert process_start_time(pid=_dead_pid()) is None


# --- ghost entries in the registry ---


def _write_entry(reg_path, name, *, pid, port, user_data_dir, pid_start=None):
    registry = {}
    if os.path.exists(reg_path):
        with open(reg_path) as f:
            registry = json.load(f)
    registry[name] = {
        "port": port,
        "pid": pid,
        "browser_version": "Chrome/150",
        "user_data_dir": user_data_dir,
        "pid_start": pid_start,
    }
    with open(reg_path, "w") as f:
        json.dump(registry, f)


def test_ghost_entry_reads_dead(tmp_path, foreign_pid):
    """Foreign PID + dead port = dead, not immortal."""
    reg_path = str(tmp_path / "registry.json")
    _write_entry(
        reg_path, "ghost-01",
        pid=GHOST_PID, port=_free_port(), user_data_dir=str(tmp_path / "s"),
    )
    assert lookup("ghost-01", registry_path=reg_path).alive is False
    assert enumerate_instances(registry_path=reg_path)[0].alive is False


def test_cleanup_reaps_ghost_entry_and_session_dir(tmp_path, foreign_pid):
    reg_path = str(tmp_path / "registry.json")
    session_dir = tmp_path / "ghost-session"
    session_dir.mkdir()
    _write_entry(
        reg_path, "ghost-01",
        pid=GHOST_PID, port=_free_port(), user_data_dir=str(session_dir),
    )

    assert cleanup(registry_path=reg_path) == ["ghost-01"]
    assert not session_dir.exists()
    with pytest.raises(InstanceNotFoundError):
        lookup("ghost-01", registry_path=reg_path)


def test_stop_ghost_cleans_up_without_signalling_foreign_pid(tmp_path, foreign_pid):
    """stop() must never fire a signal at a PID that is not our browser.

    Pre-fix behavior: Browser.close failed (dead port), then the SIGTERM
    fallback fired os.kill(pid, 15) at the foreign PID and stop() died with
    PermissionError, leaving the entry in place.
    """
    reg_path = str(tmp_path / "registry.json")
    session_dir = tmp_path / "ghost-session"
    session_dir.mkdir()
    _write_entry(
        reg_path, "ghost-01",
        pid=GHOST_PID, port=_free_port(), user_data_dir=str(session_dir),
    )

    result = stop(instance_name="ghost-01", registry_path=reg_path)

    assert "cleaned up" in result
    assert foreign_pid == []  # no signal ever fired at the foreign PID
    assert not session_dir.exists()
    with pytest.raises(InstanceNotFoundError):
        lookup("ghost-01", registry_path=reg_path)


def test_recycled_pid_entry_reads_dead(tmp_path):
    """A live PID with a mismatched start token is a recycled PID, not the browser."""
    reg_path = str(tmp_path / "registry.json")
    _write_entry(
        reg_path, "recycled-01",
        pid=os.getpid(), port=_free_port(),
        user_data_dir=str(tmp_path / "s"), pid_start="0",
    )
    assert lookup("recycled-01", registry_path=reg_path).alive is False


def test_launch_records_pid_start_token(tmp_path):
    """register() persists the start token so later checks can detect recycling."""
    reg_path = str(tmp_path / "registry.json")
    token = process_start_time(pid=os.getpid())
    info = register(
        working_dir="/home/user/proj",
        pid=os.getpid(),
        browser_version="Chrome/150",
        user_data_dir=str(tmp_path / "s"),
        registry_path=reg_path,
        pid_start=token,
    )
    assert info.pid_start == token
    assert lookup(info.name, registry_path=reg_path).pid_start == token
    assert lookup(info.name, registry_path=reg_path).alive is True


# --- port attribution ---


@pytest.fixture
def port_with_decoy_owner(tmp_path):
    """A listening port whose 'serving' process advertises another profile dir.

    Models the observed production collision: a ghost entry's recorded port
    claimed since by a different instance's browser. The decoy process carries
    --remote-debugging-port / --user-data-dir in its argv (visible via /proc),
    and a plain socket keeps the port listening.
    """
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("localhost", 0))
    listener.listen()
    port = listener.getsockname()[1]
    other_dir = str(tmp_path / "other-profile")
    decoy = subprocess.Popen([
        sys.executable, "-c", "import time; time.sleep(60)",
        f"--remote-debugging-port={port}",
        f"--user-data-dir={other_dir}",
    ])
    # Wait until /proc shows the decoy's argv
    deadline_pid = decoy.pid
    for _ in range(50):
        if other_dir in reg._cdp_port_claimants(port=port):
            break
    yield port, other_dir
    decoy.kill()
    decoy.wait()
    listener.close()


@pytest.mark.skipif(not os.path.isdir("/proc"), reason="requires /proc for attribution")
def test_port_claimed_by_other_browser_means_dead(tmp_path, foreign_pid, port_with_decoy_owner):
    """A listener attributed to a different profile dir does not vouch for a ghost."""
    port, other_dir = port_with_decoy_owner
    reg_path = str(tmp_path / "registry.json")
    _write_entry(
        reg_path, "ghost-01",
        pid=GHOST_PID, port=port, user_data_dir=str(tmp_path / "mine"),
    )
    assert lookup("ghost-01", registry_path=reg_path).alive is False


@pytest.mark.skipif(not os.path.isdir("/proc"), reason="requires /proc for attribution")
def test_stop_never_closes_another_browsers_port(tmp_path, foreign_pid, port_with_decoy_owner):
    """stop() on a collision ghost cleans the entry without touching the port.

    Firing Browser.close at the listener would kill the OTHER instance's
    browser. The fix routes this through ghost cleanup instead.
    """
    port, other_dir = port_with_decoy_owner
    reg_path = str(tmp_path / "registry.json")
    session_dir = tmp_path / "mine"
    session_dir.mkdir()
    _write_entry(
        reg_path, "ghost-01",
        pid=GHOST_PID, port=port, user_data_dir=str(session_dir),
    )

    result = stop(instance_name="ghost-01", registry_path=reg_path)

    assert "cleaned up" in result
    assert foreign_pid == []
    with pytest.raises(InstanceNotFoundError):
        lookup("ghost-01", registry_path=reg_path)


@pytest.mark.skipif(not os.path.isdir("/proc"), reason="requires /proc for attribution")
def test_port_serving_our_profile_dir_means_alive(tmp_path, foreign_pid):
    """The wrapper-fork case via attribution: dead recorded PID, but the port's
    serving process advertises OUR profile dir -> alive."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("localhost", 0))
    listener.listen()
    port = listener.getsockname()[1]
    my_dir = str(tmp_path / "mine")
    server = subprocess.Popen([
        sys.executable, "-c", "import time; time.sleep(60)",
        f"--remote-debugging-port={port}",
        f"--user-data-dir={my_dir}",
    ])
    try:
        for _ in range(50):
            if my_dir in reg._cdp_port_claimants(port=port):
                break
        reg_path = str(tmp_path / "registry.json")
        _write_entry(
            reg_path, "forked-01",
            pid=_dead_pid(), port=port, user_data_dir=my_dir,
        )
        assert lookup("forked-01", registry_path=reg_path).alive is True
    finally:
        server.kill()
        server.wait()
        listener.close()


# --- port allocation ---


def test_ghost_entry_does_not_reserve_its_port(monkeypatch, foreign_pid):
    """Pre-fix, a ghost's foreign 'live' PID reserved its port forever."""
    free = _free_port()
    monkeypatch.setattr(reg, "BASE_PORT", free)
    monkeypatch.setattr(reg, "MAX_PORT", free + 5)
    registry = {
        "ghost-01": {
            "port": free,
            "pid": GHOST_PID,
            "browser_version": "Chrome/150",
            "user_data_dir": "/nonexistent",
            "pid_start": None,
        },
    }
    assert allocate_port(registry) == free


# --- session-dir sweep (cleanup_sessions) ---


@pytest.fixture
def session_root(tmp_path, monkeypatch):
    """Redirect the launcher's session root to an isolated directory."""
    from chrome_agent import launcher
    root = tmp_path / "chrome-agent-root"
    root.mkdir()
    monkeypatch.setattr(launcher, "_SESSION_ROOT", str(root))
    return root


def _make_session_dir(root, name, lock_target_pid=None):
    d = root / name
    d.mkdir()
    if lock_target_pid is not None:
        os.symlink(f"testhost-{lock_target_pid}", d / "SingletonLock")
    return d


def test_sweep_keeps_registered_dir_even_with_dead_lock_pid(tmp_path, session_root):
    """A live instance's dir must survive the sweep regardless of its lock PID.

    A sandbox-launched browser's SingletonLock records a namespace-local PID;
    if that aliases to a dead host PID, the pre-fix sweep deleted the profile
    out from under the running browser.
    """
    from chrome_agent.launcher import cleanup_sessions

    reg_path = str(tmp_path / "registry.json")
    live_dir = _make_session_dir(session_root, "session-live", lock_target_pid=_dead_pid())
    _write_entry(
        reg_path, "live-01",
        pid=os.getpid(), port=_free_port(), user_data_dir=str(live_dir),
    )

    cleanup_sessions(registry_path=reg_path)

    assert live_dir.exists()


def test_sweep_removes_untracked_dir_with_foreign_lock_pid(tmp_path, session_root, foreign_pid):
    """An untracked dir whose lock PID is not ours is a ghost leftover.

    Pre-fix, the unsignalable foreign PID read as 'running' and the dir was
    kept forever.
    """
    from chrome_agent.launcher import cleanup_sessions

    reg_path = str(tmp_path / "registry.json")
    ghost_dir = _make_session_dir(session_root, "session-ghost", lock_target_pid=GHOST_PID)

    cleanup_sessions(registry_path=reg_path)

    assert not ghost_dir.exists()


def test_sweep_keeps_untracked_dir_with_our_live_lock_pid(tmp_path, session_root):
    from chrome_agent.launcher import cleanup_sessions

    reg_path = str(tmp_path / "registry.json")
    ours_dir = _make_session_dir(session_root, "session-ours", lock_target_pid=os.getpid())

    cleanup_sessions(registry_path=reg_path)

    assert ours_dir.exists()


def test_sweep_honors_default_registry_from_isolated_invocation(tmp_path, session_root, monkeypatch):
    """An isolated-registry sweep must not delete default-registry instances' dirs.

    _SESSION_ROOT is shared by all registries. Pre-fix, a cleanup_sessions()
    call with an isolated registry path (tests, tools) treated dirs tracked by
    the DEFAULT registry as untracked and deleted them -- including lock-less
    recreated dirs belonging to live registered browsers.
    """
    from chrome_agent import launcher
    from chrome_agent.launcher import cleanup_sessions

    # A "default" registry tracking a live instance whose dir has no lock
    default_reg = str(tmp_path / "default-registry.json")
    monkeypatch.setattr(launcher, "REGISTRY_PATH", default_reg)
    tracked_dir = _make_session_dir(session_root, "session-tracked")  # no lock
    _write_entry(
        default_reg, "live-01",
        pid=os.getpid(), port=_free_port(), user_data_dir=str(tracked_dir),
    )

    # A dir tracked by NO registry, also lock-less: a genuine orphan
    orphan_dir = _make_session_dir(session_root, "session-orphan")  # no lock

    isolated_reg = str(tmp_path / "isolated-registry.json")
    cleanup_sessions(registry_path=isolated_reg)

    assert tracked_dir.exists()      # protected by the default registry
    assert not orphan_dir.exists()   # genuine orphans still reaped


@pytest.mark.skipif(not os.path.isdir("/proc"), reason="requires /proc for attribution")
def test_attribution_works_against_a_real_chrome(browser_session):
    """Port attribution must recognize a REAL Chrome's port -> profile dir claim.

    Regression: real Chrome rewrites its argv into a single space-joined
    string in /proc/<pid>/cmdline (one trailing NUL), which a NUL-split
    element match never sees. Decoy processes with well-formed argv passed
    while every actual browser failed attribution.
    """
    assert browser_session.user_data_dir in reg._cdp_port_claimants(port=browser_session.port)


@pytest.mark.skipif(not os.path.isdir("/proc"), reason="requires /proc for attribution")
def test_our_dir_among_multiple_claimants_means_alive(tmp_path, foreign_pid):
    """Two processes claiming the same port must not mask our own claim.

    Observed in production: two browsers launched with the same
    --remote-debugging-port; attribution must ask 'is OUR dir among the
    claimants', not 'who is THE owner'.
    """
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("localhost", 0))
    listener.listen()
    port = listener.getsockname()[1]
    my_dir = str(tmp_path / "mine")
    other_dir = str(tmp_path / "other")
    procs = [
        subprocess.Popen([
            sys.executable, "-c", "import time; time.sleep(60)",
            f"--remote-debugging-port={port}", f"--user-data-dir={d}",
        ])
        for d in (other_dir, my_dir)
    ]
    try:
        for _ in range(50):
            if {my_dir, other_dir} <= reg._cdp_port_claimants(port=port):
                break
        reg_path = str(tmp_path / "registry.json")
        _write_entry(
            reg_path, "contested-01",
            pid=_dead_pid(), port=port, user_data_dir=my_dir,
        )
        assert lookup("contested-01", registry_path=reg_path).alive is True
    finally:
        for p in procs:
            p.kill()
            p.wait()
        listener.close()


@pytest.mark.skipif(not os.path.isdir("/proc"), reason="requires /proc for attribution")
def test_stop_bind_race_loser_terminates_by_pid_not_by_port(tmp_path, port_with_decoy_owner):
    """A live browser that lost the bind race must be stopped by ITS PID.

    Observed in production: instance B launched with instance A's port; A's
    browser holds the listener, B's runs CDP-less. Pre-fix, stop(B) fired
    Browser.close at the port -- killing A's browser. Post-fix it terminates
    B's own (verified) process and never touches the port.
    """
    port, other_dir = port_with_decoy_owner
    # A live own-user process standing in for the CDP-less browser
    zombie = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        reg_path = str(tmp_path / "registry.json")
        session_dir = tmp_path / "mine"
        session_dir.mkdir()
        _write_entry(
            reg_path, "raceloser-01",
            pid=zombie.pid, port=port, user_data_dir=str(session_dir),
        )

        result = stop(instance_name="raceloser-01", registry_path=reg_path)

        assert "terminated by PID" in result
        zombie.wait(timeout=5)  # SIGTERM landed on the right process
        with pytest.raises(InstanceNotFoundError):
            lookup("raceloser-01", registry_path=reg_path)
    finally:
        if zombie.poll() is None:
            zombie.kill()
            zombie.wait()
