"""Tests for CDP-04 Attach Mode.

Tests use the session-scoped browser fixture from conftest.py (port 9333)
and a temporary registry for isolation.
"""

import asyncio
import json
import os
import subprocess
import sys

import pytest

from chrome_agent import attach as attach_mod
from chrome_agent.attach import (
    AmbiguousTargetError,
    NoPageError,
    TargetNotFoundError,
    _liveness_verdict,
    resolve_target,
    run_attach,
)
from chrome_agent.cdp_client import CDPClient, get_ws_url
from chrome_agent.registry import (
    InstanceInfo,
    InstanceNotFoundError,
    deregister,
    register,
)


# ---------------------------------------------------------------------------
# Target resolution (unit tests, no browser needed)
# ---------------------------------------------------------------------------


def test_resolve_target_single():
    """Single target auto-selected when no specifier given."""
    targets = [{"targetId": "ABCD1234", "url": "https://example.com", "title": "Ex"}]
    result = resolve_target(page_targets=targets, target_spec=None, target_by=None)
    assert result == "ABCD1234"


def test_resolve_target_ambiguous():
    """Multiple targets with no specifier raises AmbiguousTargetError."""
    targets = [
        {"targetId": "ABCD1234", "url": "https://a.com", "title": "A"},
        {"targetId": "EFGH5678", "url": "https://b.com", "title": "B"},
    ]
    with pytest.raises(AmbiguousTargetError) as exc_info:
        resolve_target(page_targets=targets, target_spec=None, target_by=None)
    assert len(exc_info.value.targets) == 2


def test_resolve_target_by_index():
    """Target resolved by 1-based index."""
    targets = [
        {"targetId": "ABCD1234", "url": "https://a.com", "title": "A"},
        {"targetId": "EFGH5678", "url": "https://b.com", "title": "B"},
    ]
    result = resolve_target(page_targets=targets, target_spec="2", target_by="index")
    assert result == "EFGH5678"


def test_resolve_target_by_id_prefix():
    """Target resolved by ID prefix."""
    targets = [
        {"targetId": "ABCD1234FULL", "url": "https://a.com", "title": "A"},
        {"targetId": "EFGH5678FULL", "url": "https://b.com", "title": "B"},
    ]
    result = resolve_target(page_targets=targets, target_spec="EFGH", target_by="id")
    assert result == "EFGH5678FULL"


def test_resolve_target_by_url():
    """Target resolved by URL substring."""
    targets = [
        {"targetId": "ABCD1234", "url": "https://example.com", "title": "Example"},
        {"targetId": "EFGH5678", "url": "https://test.com", "title": "Test"},
    ]
    result = resolve_target(page_targets=targets, target_spec="test.com", target_by="url")
    assert result == "EFGH5678"


def test_resolve_target_not_found():
    """No matching target raises TargetNotFoundError."""
    targets = [{"targetId": "ABCD1234", "url": "https://example.com", "title": "Ex"}]
    with pytest.raises(TargetNotFoundError):
        resolve_target(page_targets=targets, target_spec="ZZZZ", target_by="id")


# ---------------------------------------------------------------------------
# Instance not found
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_attach_instance_not_found(tmp_path):
    """Attach to nonexistent instance raises InstanceNotFoundError."""
    reg_path = str(tmp_path / "registry.json")
    with pytest.raises(InstanceNotFoundError):
        await run_attach(
            instance_name="nonexistent",
            registry_path=reg_path,
        )


# ---------------------------------------------------------------------------
# Integration: attach receives events from cross-session navigation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_attach_receives_events(browser_session):
    """Attach session receives events caused by a separate CDP connection.

    Runs against the isolated session-scoped fixture browser (its own port and
    registry), NOT the default debug port -- an earlier version hardcoded 9222
    and drove whatever Chrome happened to be running there. Operates on a tab
    it creates and closes, so a failure cannot leak state into the shared
    fixture browser or the next test.
    """
    browser_ws = get_ws_url(port=browser_session.port, target_type="browser")
    cdp_navigator = CDPClient(ws_url=browser_ws)
    await cdp_navigator.connect()
    cdp_observer = CDPClient(ws_url=browser_ws)
    await cdp_observer.connect()

    # A dedicated tab for this test -- never a pre-existing shared one.
    created = await cdp_navigator.send(
        method="Target.createTarget", params={"url": "about:blank"}
    )
    target_id = created["targetId"]

    try:
        # Navigator session (drives the page)
        nav_session = await cdp_navigator.send(
            method="Target.attachToTarget",
            params={"targetId": target_id, "flatten": True},
        )
        nav_sid = nav_session["sessionId"]

        # Observer session (simulating what attach does), subscribed to Page events
        obs_session = await cdp_observer.send(
            method="Target.attachToTarget",
            params={"targetId": target_id, "flatten": True},
        )
        obs_sid = obs_session["sessionId"]
        await cdp_observer.send(method="Page.enable", session_id=obs_sid)
        events_received = []
        cdp_observer.on(
            event="Page.loadEventFired",
            callback=lambda params: events_received.append(params),
            session_id=obs_sid,
        )

        # Navigate via the navigator session (a different session)
        await cdp_navigator.send(
            method="Page.navigate",
            params={"url": "https://example.com"},
            session_id=nav_sid,
        )
        await asyncio.sleep(3)

        assert len(events_received) > 0, "Observer should receive events from navigator's action"
    finally:
        try:
            await cdp_navigator.send(
                method="Target.closeTarget", params={"targetId": target_id}
            )
        except Exception:
            pass
        await cdp_navigator.close()
        await cdp_observer.close()


# ---------------------------------------------------------------------------
# Event isolation between sessions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_isolation(browser_session):
    """Two sessions on the same target have isolated event subscriptions.

    Runs against the isolated fixture browser on its own tab (created and
    closed here), not the default debug port.
    """
    browser_ws = get_ws_url(port=browser_session.port, target_type="browser")

    cdp_a = CDPClient(ws_url=browser_ws)
    await cdp_a.connect()
    cdp_b = CDPClient(ws_url=browser_ws)
    await cdp_b.connect()

    created = await cdp_a.send(
        method="Target.createTarget", params={"url": "about:blank"}
    )
    target_id = created["targetId"]

    try:
        # Session A: subscribes to Network
        sa = await cdp_a.send(method="Target.attachToTarget", params={"targetId": target_id, "flatten": True})
        sid_a = sa["sessionId"]
        await cdp_a.send(method="Network.enable", session_id=sid_a)
        a_network = []
        cdp_a.on(event="Network.requestWillBeSent", callback=lambda p: a_network.append(p), session_id=sid_a)

        # Session B: does NOT subscribe to Network
        sb = await cdp_b.send(method="Target.attachToTarget", params={"targetId": target_id, "flatten": True})
        sid_b = sb["sessionId"]
        b_network = []
        cdp_b.on(event="Network.requestWillBeSent", callback=lambda p: b_network.append(p), session_id=sid_b)

        # Navigate via session B
        await cdp_b.send(method="Page.navigate", params={"url": "https://example.com"}, session_id=sid_b)
        await asyncio.sleep(3)

        # Session A should have Network events, Session B should not
        assert len(a_network) > 0, "Session A (Network enabled) should receive network events"
        assert len(b_network) == 0, "Session B (Network NOT enabled) should NOT receive network events"
    finally:
        try:
            await cdp_a.send(method="Target.closeTarget", params={"targetId": target_id})
        except Exception:
            pass
        await cdp_a.close()
        await cdp_b.close()


# ---------------------------------------------------------------------------
# SIGTERM shutdown (issue #1): attach must exit on plain SIGTERM while idle
# ---------------------------------------------------------------------------


def test_attach_sigterm_exits_while_idle(tmp_path):
    """A SIGTERM must terminate an idle attach session promptly.

    Reproduces issue #1: with stdin held open (the state of any
    backgrounded attach) and a live websocket, the process must still
    exit on plain SIGTERM -- no SIGKILL required.

    Runs the real run_attach code path in a subprocess so the signal
    delivery, asyncio.run lifecycle, and stdin pipe are all real.
    """
    import select
    import signal as signal_mod
    import time

    from chrome_agent.launcher import launch_browser

    reg_path = str(tmp_path / "registry.json")

    # Auto-allocate the port: a hardcoded one can collide with an existing
    # Chrome, leaving this launch CDP-less and attaching to a foreign browser.
    result = asyncio.run(
        launch_browser(
            headless=True,
            pin_to_desktop=False,
            registry_path=reg_path,
            working_dir=str(tmp_path),
        )
    )

    stub = (
        "import asyncio, sys\n"
        "from chrome_agent.attach import run_attach\n"
        f"asyncio.run(run_attach(instance_name={result.name!r}, "
        f"subscriptions=['Page.loadEventFired'], registry_path={reg_path!r}))\n"
    )

    proc = subprocess.Popen(
        args=[sys.executable, "-c", stub],
        stdin=subprocess.PIPE,   # held open: the issue's `sleep infinity |` state
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        # Wait for the ready line before signaling
        readable, _, _ = select.select([proc.stdout], [], [], 15)
        assert readable, "attach subprocess never produced its ready line"
        first_line = proc.stdout.readline()
        if not first_line:
            proc.wait(timeout=5)
            pytest.fail(
                "attach subprocess died before its ready line "
                f"(returncode {proc.returncode}): "
                f"{proc.stderr.read().decode(errors='replace')[:1000]}"
            )
        ready = json.loads(first_line)
        assert ready.get("status") == "ready"

        proc.send_signal(signal_mod.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pytest.fail("attach ignored SIGTERM: still alive 5s after signal (issue #1)")
        assert proc.returncode == 0, (
            f"attach exited non-gracefully on SIGTERM (returncode {proc.returncode}): "
            f"{proc.stderr.read().decode(errors='replace')[:500]}"
        )
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        try:
            os.kill(result.pid, signal_mod.SIGTERM)
            deadline = time.time() + 5
            while time.time() < deadline:
                try:
                    os.kill(result.pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.2)
        except ProcessLookupError:
            pass
        import shutil
        shutil.rmtree(result.user_data_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Bounded attach lifetime (#1 secondary): exit when the instance is retired
# or its browser is gone. Unit-test the pure verdict, then integration-test
# the retire path end-to-end.
# ---------------------------------------------------------------------------


def _info(name="obs-01"):
    return InstanceInfo(
        name=name,
        port=59998,
        pid=os.getpid(),
        browser_version="Chrome/147",
        user_data_dir="/tmp/obs-profile",
        pid_start=None,
    )


def test_liveness_verdict_healthy_keeps_running(monkeypatch):
    """Registered + alive -> no exit reason."""
    monkeypatch.setattr(attach_mod, "registration_status", lambda name, registry_path=None: "present")
    monkeypatch.setattr(attach_mod, "instance_is_alive", lambda info: True)
    assert _liveness_verdict(_info(), None) is None


def test_liveness_verdict_exits_on_retire(monkeypatch):
    """A genuine deregister ('retired') triggers exit even if the browser lives.

    This is the 26-day-orphan case: the browser is still alive (instance_is_alive
    True) but the registry entry is gone. A dropped-socket check never catches
    this; the registry verdict must.
    """
    monkeypatch.setattr(attach_mod, "registration_status", lambda name, registry_path=None: "retired")
    monkeypatch.setattr(attach_mod, "instance_is_alive", lambda info: True)
    assert _liveness_verdict(_info(), None) == "instance retired from registry"


def test_liveness_verdict_exits_on_dead_browser(monkeypatch):
    """Still registered but the browser is gone/not-ours -> exit."""
    monkeypatch.setattr(attach_mod, "registration_status", lambda name, registry_path=None: "present")
    monkeypatch.setattr(attach_mod, "instance_is_alive", lambda info: False)
    assert _liveness_verdict(_info(), None) == "browser no longer running"


def test_liveness_verdict_unknown_registry_does_not_exit(monkeypatch):
    """An ambiguous ('unknown') registry read must NOT trigger exit while alive.

    Guards the corrupt-{} false positive: a torn/empty registry read must not
    kill a healthy observer whose browser is plainly still alive and ours.
    """
    monkeypatch.setattr(attach_mod, "registration_status", lambda name, registry_path=None: "unknown")
    monkeypatch.setattr(attach_mod, "instance_is_alive", lambda info: True)
    assert _liveness_verdict(_info(), None) is None


def test_attach_exits_when_instance_retired(tmp_path):
    """End-to-end: attach exits when its instance is deregistered, browser alive.

    Reproduces the issue's secondary orphan scenario faithfully. A decoy
    instance is left registered so the registry stays NON-EMPTY after the
    target is removed -- so registration_status reads 'retired' (genuine), not
    'unknown'. The target browser is left RUNNING, which is what makes this a
    clean isolation of the new liveness path: the passive connection monitor
    cannot be what fires, because the websocket never drops.
    """
    import select
    import signal as signal_mod
    import time

    from chrome_agent.launcher import launch_browser

    reg_path = str(tmp_path / "registry.json")

    result = asyncio.run(
        launch_browser(
            headless=True,
            pin_to_desktop=False,
            registry_path=reg_path,
            working_dir=str(tmp_path),
        )
    )
    # Decoy entry so the registry stays non-empty after the target is retired
    # (else registration_status would read 'unknown', not 'retired').
    register(
        working_dir="/home/user/decoy",
        pid=os.getpid(),
        browser_version="Chrome/147",
        user_data_dir=str(tmp_path / "decoy"),
        registry_path=reg_path,
    )

    # Shrink the poll cadence in the subprocess so the test is fast and faithful
    # (real code path, just a tighter timer) -- no production config surface.
    stub = (
        "import asyncio\n"
        "import chrome_agent.attach as attach\n"
        "attach._LIVENESS_POLL_SECONDS = 0.3\n"
        "attach._LIVENESS_STRIKES = 2\n"
        f"asyncio.run(attach.run_attach(instance_name={result.name!r}, "
        f"subscriptions=['Page.loadEventFired'], registry_path={reg_path!r}))\n"
    )

    proc = subprocess.Popen(
        args=[sys.executable, "-c", stub],
        stdin=subprocess.PIPE,   # held open -- the backgrounded-attach state
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        readable, _, _ = select.select([proc.stdout], [], [], 15)
        assert readable, "attach subprocess never produced its ready line"
        first_line = proc.stdout.readline()
        if not first_line:
            proc.wait(timeout=5)
            pytest.fail(
                "attach subprocess died before its ready line "
                f"(returncode {proc.returncode}): "
                f"{proc.stderr.read().decode(errors='replace')[:1000]}"
            )
        assert json.loads(first_line).get("status") == "ready"

        # Confirm the browser is genuinely still up: the websocket has NOT
        # dropped, so only the liveness path can end this session.
        assert result.pid and os.path.exists(f"/proc/{result.pid}")

        # Retire the target instance while its browser keeps running.
        assert deregister(instance_name=result.name, registry_path=reg_path) is True

        try:
            proc.wait(timeout=10)  # ~0.3s * 2 strikes + margin
        except subprocess.TimeoutExpired:
            pytest.fail("attach did not exit after its instance was retired")
        assert proc.returncode == 0, (
            f"attach exited non-gracefully after retire (returncode {proc.returncode}): "
            f"{proc.stderr.read().decode(errors='replace')[:500]}"
        )

        # The shutdown line names the retire reason, distinguishing this exit
        # from a browser-disconnect.
        rest = proc.stdout.read().decode(errors="replace")
        reasons = [
            json.loads(ln).get("reason")
            for ln in rest.splitlines()
            if ln.strip().startswith("{") and "reason" in ln
        ]
        assert "instance retired from registry" in reasons, (
            f"expected a retire shutdown line; got stdout tail: {rest[:500]!r}"
        )
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        # Browser was intentionally left alive -- tear it down now.
        try:
            os.kill(result.pid, signal_mod.SIGTERM)
            deadline = time.time() + 5
            while time.time() < deadline:
                try:
                    os.kill(result.pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.2)
        except ProcessLookupError:
            pass
        import shutil
        shutil.rmtree(result.user_data_dir, ignore_errors=True)
