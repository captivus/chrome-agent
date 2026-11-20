"""Tests for managed virtual displays: where an agent's browser goes.

The live tests launch real headed Chrome on real Xvfb servers and check the X
servers themselves (with xdotool) for the window. They never touch the user's
display: the "desktop" is a second Xvfb started here under another name
(``Xdesk``, a symlink), which chrome-agent cannot tell from a real desktop --
exactly the property the desktop path relies on. Display state is kept in a
temporary directory, so a run never reuses or removes a real managed display.
"""

import asyncio
import os
import shutil
import signal
import subprocess
import sys
import time

import pytest

import chrome_agent.virtual_display as vd
from chrome_agent.desktop import browser_placements, display_running
from chrome_agent.launcher import launch_browser
from chrome_agent.registry import lookup, stop

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("linux") or shutil.which("Xvfb") is None
    or shutil.which("xdotool") is None,
    reason="needs Linux with Xvfb and xdotool",
)


@pytest.fixture
def display_dir(tmp_path, monkeypatch):
    """Isolate managed-display state (the keeper inherits the env var)."""
    state = tmp_path / "displays"
    monkeypatch.setenv("CHROME_AGENT_DISPLAY_DIR", str(state))
    monkeypatch.setattr(vd, "STATE_DIR", str(state))
    yield state
    for name in os.listdir(state) if state.exists() else []:
        if name.endswith(".json"):
            vd.stop_display(f":{name[:-5]}")


@pytest.fixture
def stand_in_desktop(tmp_path, monkeypatch):
    """A second X server standing in for the user's desktop, as DISPLAY."""
    binary = tmp_path / "Xdesk"
    binary.symlink_to(shutil.which("Xvfb"))
    number = next(n for n in range(170, 199) if vd._number_free(n))
    process = subprocess.Popen(
        [str(binary), f":{number}", "-screen", "0", "1280x800x24", "-nolisten", "tcp"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + 10
    while not display_running(f":{number}") and time.monotonic() < deadline:
        time.sleep(0.05)
    monkeypatch.setenv("DISPLAY", f":{number}")
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    yield f":{number}"
    process.terminate()
    process.wait(timeout=10)


def _visible_windows(display: str, pid: int) -> int:
    result = subprocess.run(
        ["xdotool", "search", "--onlyvisible", "--pid", str(pid)],
        capture_output=True, text=True, env={**os.environ, "DISPLAY": display},
    )
    return len(result.stdout.split())


def _wait_for_window(display: str, pid: int, timeout: float = 15) -> int:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        count = _visible_windows(display, pid)
        if count:
            return count
        time.sleep(0.2)
    return 0


def _expire_claim(display: str) -> None:
    """Age the launch claim past its grace period, as time would."""
    path = vd._claim_path(display)
    past = time.time() - vd.CLAIM_GRACE - 1
    os.utime(path, (past, past))


def _launch(tmp_path, name: str, **kwargs):
    return asyncio.run(launch_browser(
        registry_path=str(tmp_path / "registry.json"), instance_name=name,
        working_dir=str(tmp_path), **kwargs,
    ))


def test_virtual_launch_is_off_the_desktop_reused_and_removed(tmp_path, display_dir, stand_in_desktop):
    """Two virtual launches share one managed Xvfb; their windows are on it and
    not on the desktop; it survives the first stop and goes with the last."""
    registry = str(tmp_path / "registry.json")
    first = _launch(tmp_path, "vd-test-01", display="virtual")
    second = _launch(tmp_path, "vd-test-02", display="virtual")
    try:
        display = first.display
        assert display != stand_in_desktop
        assert second.display == display, "the second launch must reuse the managed display"
        assert list(vd.managed_displays()) == [display]

        for info in (first, second):
            assert _wait_for_window(display, info.pid) >= 1
            assert _visible_windows(stand_in_desktop, info.pid) == 0

        placements = browser_placements([first.port, second.port])
        for info in (first, second):
            assert placements[info.port] == {
                "kind": "virtual", "display": display, "server": "Xvfb", "managed": True,
            }

        _expire_claim(display)
        stop(instance_name="vd-test-01", registry_path=registry)
        time.sleep(vd.CHECK_INTERVAL * 3)
        assert display_running(display), "a display still in use must stay up"

        stop(instance_name="vd-test-02", registry_path=registry)
        deadline = time.monotonic() + vd.CHECK_INTERVAL * 6
        while display_running(display) and time.monotonic() < deadline:
            time.sleep(0.2)
        assert not display_running(display), "the display must go with its last browser"
        assert vd.managed_displays() == {}
        assert not os.path.exists(vd._record_path(display))
    finally:
        for name in ("vd-test-01", "vd-test-02"):
            try:
                stop(instance_name=name, registry_path=registry)
            except Exception:
                pass


def test_desktop_launch_uses_the_inherited_display(tmp_path, display_dir, stand_in_desktop):
    """display="desktop" puts the window on DISPLAY and starts no Xvfb."""
    registry = str(tmp_path / "registry.json")
    info = _launch(tmp_path, "vd-desk-01", display="desktop", pin_to_desktop=False)
    try:
        assert info.display == stand_in_desktop
        assert _wait_for_window(stand_in_desktop, info.pid) >= 1
        assert browser_placements([info.port])[info.port] == {
            "kind": "desktop", "display": stand_in_desktop,
        }
        assert vd.managed_displays() == {}
    finally:
        stop(instance_name="vd-desk-01", registry_path=registry)


def test_missing_xvfb_is_a_clear_error(monkeypatch, display_dir):
    real_which = shutil.which
    monkeypatch.setattr(vd.shutil, "which", lambda name: None if name == "Xvfb" else real_which(name))
    with pytest.raises(vd.VirtualDisplayError) as exc_info:
        vd.acquire_display()
    message = str(exc_info.value)
    assert "Xvfb is not installed" in message
    assert "apt install xvfb" in message
    assert "--display desktop" in message


def test_keeper_rearmed_by_cleanup_removes_an_unused_display(display_dir):
    """A managed display whose keeper was killed is re-armed by cleanup, and
    the new keeper removes it once nothing uses it."""
    display = vd.acquire_display()
    for pid in vd._keeper_pids(display):
        os.kill(pid, signal.SIGTERM)
    time.sleep(0.5)
    assert not vd._keeper_pids(display)
    _expire_claim(display)

    assert vd.rearm_keepers() == [display]
    deadline = time.monotonic() + vd.CHECK_INTERVAL * 6
    while display_running(display) and time.monotonic() < deadline:
        time.sleep(0.2)
    assert not display_running(display)


def test_default_display_follows_the_caller(monkeypatch):
    """Agent sessions default to a virtual display; the user's terminal to
    the desktop; CHROME_AGENT_DISPLAY overrides; an agent already on a
    virtual DISPLAY keeps it."""
    from chrome_agent import cli

    monkeypatch.delenv("CHROME_AGENT_DISPLAY", raising=False)
    monkeypatch.setenv("DISPLAY", ":1")
    monkeypatch.setattr("chrome_agent.desktop.virtual_display_server", lambda d: None)

    monkeypatch.setattr("chrome_agent.owner.is_agent_session", lambda: True)
    assert cli._default_display() == "virtual"
    monkeypatch.setenv("CHROME_AGENT_DISPLAY", "desktop")
    assert cli._default_display() == "desktop"
    monkeypatch.delenv("CHROME_AGENT_DISPLAY")
    monkeypatch.setattr("chrome_agent.desktop.virtual_display_server", lambda d: ["Xvfb", d])
    assert cli._default_display() == "desktop"  # i.e. the inherited, virtual, DISPLAY

    monkeypatch.setattr("chrome_agent.desktop.virtual_display_server", lambda d: None)
    monkeypatch.setattr("chrome_agent.owner.is_agent_session", lambda: False)
    assert cli._default_display() == "desktop"
    monkeypatch.setenv("CHROME_AGENT_DISPLAY", "virtual")
    assert cli._default_display() == "virtual"


def test_move_between_virtual_display_and_desktop(tmp_path, monkeypatch, display_dir, stand_in_desktop):
    """move takes a running browser onto the desktop and back, keeping its
    name, port, cookies and owner, and leaves no snapshot behind."""
    import base64

    import chrome_agent.registry as registry
    from chrome_agent import snapshot
    from chrome_agent.cdp_client import CDPClient, get_ws_url

    monkeypatch.setattr(registry, "REGISTRY_PATH", str(tmp_path / "registry.json"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("CHROME_AGENT_SNAPSHOT_KEY", base64.b64encode(os.urandom(32)).decode())
    owner = {"kind": "process", "pid": os.getpid(), "start": None, "pidns": None}

    info = asyncio.run(launch_browser(
        display="virtual", owner=owner, instance_name="vd-move-01", working_dir=str(tmp_path),
    ))
    try:
        async def set_cookie():
            async with CDPClient(ws_url=get_ws_url(port=info.port, target_type="browser")) as cdp:
                await cdp.send(method="Storage.setCookies", params={"cookies": [
                    {"name": "sid", "value": "kept", "domain": "example.test", "path": "/"},
                ]})

        async def cookies():
            async with CDPClient(ws_url=get_ws_url(port=info.port, target_type="browser")) as cdp:
                return {c["name"]: c["value"] for c in (await cdp.send(method="Storage.getCookies"))["cookies"]}

        asyncio.run(set_cookie())

        report = snapshot.move_instance("vd-move-01", "desktop")
        assert (report["name"], report["port"]) == ("vd-move-01", info.port)
        assert _wait_for_window(stand_in_desktop, report["pid"]) >= 1
        assert browser_placements([info.port])[info.port]["kind"] == "desktop"
        assert asyncio.run(cookies())["sid"] == "kept"
        assert lookup(instance_name="vd-move-01").owner == owner
        assert snapshot.list_versions() == []

        report = snapshot.move_instance("vd-move-01", "virtual")
        assert report["display"] and report["display"] != stand_in_desktop
        assert _wait_for_window(report["display"], report["pid"]) >= 1
        assert _visible_windows(stand_in_desktop, report["pid"]) == 0
        assert lookup(instance_name="vd-move-01").owner == owner

        with pytest.raises(snapshot.SnapshotError, match="already on"):
            snapshot.move_instance("vd-move-01", "virtual")
    finally:
        stop(instance_name="vd-move-01")


# -- restore: the same placement and ownership rule as launch ----------------

@pytest.fixture
def snapshots(tmp_path, monkeypatch, display_dir, stand_in_desktop):
    """A private registry, snapshot store and key; DISPLAY is the stand-in."""
    import base64

    import chrome_agent.registry as registry

    monkeypatch.setattr(registry, "REGISTRY_PATH", str(tmp_path / "registry.json"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("CHROME_AGENT_SNAPSHOT_KEY", base64.b64encode(os.urandom(32)).decode())
    monkeypatch.delenv("CHROME_AGENT_DISPLAY", raising=False)
    names = []
    yield names
    for name in names:
        try:
            stop(instance_name=name)
        except Exception:
            pass


def _as_caller(monkeypatch, owner):
    """Make the CLI see an agent session owned by ``owner`` (a record), or,
    with None, a person at their own terminal."""
    monkeypatch.setattr("chrome_agent.owner.is_agent_session", lambda: owner is not None)
    monkeypatch.setattr("chrome_agent.owner.find_owner", lambda: owner)


def _saved(tmp_path, names, name, **launch):
    """Launch ``name``, save it with --stop, and return nothing: the snapshot
    is filed under its name in the private store."""
    from chrome_agent import snapshot

    workdir = tmp_path / name
    workdir.mkdir(exist_ok=True)
    asyncio.run(launch_browser(instance_name=name, working_dir=str(workdir), **launch))
    names.append(name)
    snapshot.save_instance(snapshot.plan_save(name), stop=True)


def _restore(*args):
    from chrome_agent import cli

    cli._run_restore(args=list(args))


def _pid_of(port: int) -> int:
    import chrome_agent.registry as registry

    for entry in registry._load_registry(registry.REGISTRY_PATH).values():
        if entry["port"] == port:
            return entry["pid"]
    raise AssertionError(f"nothing registered on port {port}")


def test_agent_restore_of_a_desktop_snapshot_goes_virtual_and_ends_with_the_agent(
    tmp_path, monkeypatch, snapshots, stand_in_desktop,
):
    """A snapshot saved on the desktop, restored by an agent, comes back on
    the managed virtual display -- not the desktop -- owned by the agent's
    session, and is stopped when that session ends."""
    from chrome_agent import owner as owner_mod

    _saved(tmp_path, snapshots, "rs-desk-01", display="desktop")
    agent = subprocess.Popen(["sleep", "600"])
    try:
        _as_caller(monkeypatch, owner_mod._record(agent.pid, "claude-code"))
        _restore("rs-desk-01")

        info = lookup(instance_name="rs-desk-01")
        placement = browser_placements([info.port])[info.port]
        assert placement["kind"] == "virtual" and placement.get("managed")
        pid = _pid_of(info.port)
        assert _wait_for_window(placement["display"], pid) >= 1
        assert _visible_windows(stand_in_desktop, pid) == 0
        assert info.owner["pid"] == agent.pid
    finally:
        agent.terminate()
        agent.wait()
    from chrome_agent.registry import _port_is_listening
    from chrome_agent.supervisor import OWNER_CHECK_INTERVAL

    deadline = time.monotonic() + OWNER_CHECK_INTERVAL * 4
    while _port_is_listening(info.port) and time.monotonic() < deadline:
        time.sleep(0.25)
    assert not _port_is_listening(info.port), "an agent's restored browser ends with the agent"


def test_agent_restore_display_desktop_keep(tmp_path, monkeypatch, snapshots, stand_in_desktop):
    """--display desktop puts an agent's restore on the screen; --keep leaves
    it without an owner."""
    from chrome_agent import owner as owner_mod

    _saved(tmp_path, snapshots, "rs-keep-01", display="desktop")
    _as_caller(monkeypatch, owner_mod._record(os.getpid(), "claude-code"))
    _restore("rs-keep-01", "--display", "desktop", "--keep")

    info = lookup(instance_name="rs-keep-01")
    assert browser_placements([info.port])[info.port]["kind"] == "desktop"
    assert _wait_for_window(stand_in_desktop, _pid_of(info.port)) >= 1
    assert info.owner is None


def test_person_restores_where_saved_and_agent_restores_virtual(
    tmp_path, monkeypatch, snapshots, stand_in_desktop,
):
    """A person gets a desktop snapshot back on the desktop and a snapshot of
    a particular Xvfb back on that Xvfb, with no owner. An agent restoring the
    same Xvfb snapshot gets the managed display; the recorded number plays no
    part."""
    from chrome_agent import owner as owner_mod

    _saved(tmp_path, snapshots, "rs-person-01", display="desktop")

    # A virtual display chrome-agent does not manage, as someone started by hand.
    number = next(n for n in range(150, 170) if vd._number_free(n))
    hand = subprocess.Popen(["Xvfb", f":{number}", "-screen", "0", "1280x800x24", "-nolisten", "tcp"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 10
        while not display_running(f":{number}") and time.monotonic() < deadline:
            time.sleep(0.05)
        monkeypatch.setenv("DISPLAY", f":{number}")
        _saved(tmp_path, snapshots, "rs-hand-01", display="desktop")  # i.e. the inherited :number
        monkeypatch.setenv("DISPLAY", stand_in_desktop)

        _as_caller(monkeypatch, None)
        _restore("rs-person-01")
        _restore("rs-hand-01", "--any-port")  # both were saved on the first free port
        person = lookup(instance_name="rs-person-01")
        hand_info = lookup(instance_name="rs-hand-01")
        placements = browser_placements([person.port, hand_info.port])
        assert placements[person.port] == {"kind": "desktop", "display": stand_in_desktop}
        assert placements[hand_info.port]["display"] == f":{number}"
        assert person.owner is None and hand_info.owner is None

        stop(instance_name="rs-hand-01")
        _as_caller(monkeypatch, owner_mod._record(os.getpid(), "claude-code"))
        _restore("rs-hand-01", "--any-port")
        again = lookup(instance_name="rs-hand-01")
        placement = browser_placements([again.port])[again.port]
        assert placement.get("managed") and placement["display"] != f":{number}"
        assert again.owner["pid"] == os.getpid()
    finally:
        for name in ("rs-hand-01",):
            try:
                stop(instance_name=name)
            except Exception:
                pass
        hand.terminate()
        hand.wait(timeout=10)


def test_agent_restore_all_and_here(tmp_path, monkeypatch, snapshots, stand_in_desktop):
    """restore --all and bare restore (--here) follow the same rule; a
    headless snapshot stays headless but is owned all the same."""
    from chrome_agent import cli
    from chrome_agent import owner as owner_mod

    for name, launch in (("rs-all-01", {"display": "desktop"}), ("rs-all-02", {"headless": True})):
        workdir = tmp_path / "batch"
        workdir.mkdir(exist_ok=True)
        asyncio.run(launch_browser(instance_name=name, working_dir=str(workdir), **launch))
        snapshots.append(name)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    cli._run_save(args=["--all", "--stop"])

    record = owner_mod._record(os.getpid(), "claude-code")
    _as_caller(monkeypatch, record)
    _restore("--all")
    first, second = lookup(instance_name="rs-all-01"), lookup(instance_name="rs-all-02")
    placements = browser_placements([first.port, second.port])
    assert placements[first.port].get("managed")
    assert placements[second.port] == {"kind": "headless"}
    assert first.owner == record and second.owner == record
    assert _visible_windows(stand_in_desktop, _pid_of(first.port)) == 0

    stop(instance_name="rs-all-01")
    stop(instance_name="rs-all-02")
    monkeypatch.chdir(tmp_path / "batch")
    _restore()  # bare: everything launched from here
    first = lookup(instance_name="rs-all-01")
    assert browser_placements([first.port])[first.port].get("managed")
    assert first.owner == record


def test_restore_display_default_follows_the_caller(monkeypatch):
    from chrome_agent import cli

    monkeypatch.delenv("CHROME_AGENT_DISPLAY", raising=False)
    monkeypatch.setenv("DISPLAY", ":1")
    monkeypatch.setattr("chrome_agent.desktop.virtual_display_server", lambda d: None)
    monkeypatch.setattr("chrome_agent.owner.is_agent_session", lambda: True)
    assert cli._restore_display() == "virtual"
    monkeypatch.setattr("chrome_agent.owner.is_agent_session", lambda: False)
    assert cli._restore_display() is None  # where it was saved
    monkeypatch.setenv("CHROME_AGENT_DISPLAY", "virtual")
    assert cli._restore_display() == "virtual"
