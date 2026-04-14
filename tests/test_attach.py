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

from chrome_agent.attach import (
    AmbiguousTargetError,
    NoPageError,
    TargetNotFoundError,
    resolve_target,
    run_attach,
)
from chrome_agent.cdp_client import CDPClient, get_ws_url
from chrome_agent.registry import InstanceNotFoundError, register


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
async def test_attach_receives_events(tmp_path):
    """Attach session receives events caused by a separate CDP connection."""
    reg_path = str(tmp_path / "registry.json")

    # Register the conftest browser (port 9333)
    register(
        working_dir="/home/user/testproject",
        pid=os.getpid(),  # use our PID so it shows as alive
        browser_version="Chrome/147",
        user_data_dir=str(tmp_path / "session"),
        port_override=9222,
        registry_path=reg_path,
    )

    # Get the browser-level WebSocket URL and find the page target
    browser_ws = get_ws_url(port=9222, target_type="browser")
    cdp_navigator = CDPClient(ws_url=browser_ws)
    await cdp_navigator.connect()

    targets_result = await cdp_navigator.send(method="Target.getTargets")
    page_targets = [t for t in targets_result["targetInfos"] if t["type"] == "page"]
    target_id = page_targets[0]["targetId"]

    # Create a navigator session
    nav_session = await cdp_navigator.send(
        method="Target.attachToTarget",
        params={"targetId": target_id, "flatten": True},
    )
    nav_sid = nav_session["sessionId"]

    # Create an observer session (simulating what attach does)
    cdp_observer = CDPClient(ws_url=browser_ws)
    await cdp_observer.connect()

    obs_session = await cdp_observer.send(
        method="Target.attachToTarget",
        params={"targetId": target_id, "flatten": True},
    )
    obs_sid = obs_session["sessionId"]

    # Subscribe to Page events on observer session
    await cdp_observer.send(method="Page.enable", session_id=obs_sid)
    events_received = []
    cdp_observer.on(
        event="Page.loadEventFired",
        callback=lambda params: events_received.append(params),
        session_id=obs_sid,
    )

    # Navigate via the navigator session (different session)
    await cdp_navigator.send(
        method="Page.navigate",
        params={"url": "https://example.com"},
        session_id=nav_sid,
    )
    await asyncio.sleep(3)

    # Observer should have received the Page.loadEventFired event
    assert len(events_received) > 0, "Observer should receive events from navigator's action"

    # Cleanup
    await cdp_navigator.send(method="Target.detachFromTarget", params={"sessionId": nav_sid})
    await cdp_observer.send(method="Target.detachFromTarget", params={"sessionId": obs_sid})
    await cdp_navigator.close()
    await cdp_observer.close()


# ---------------------------------------------------------------------------
# Event isolation between sessions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_isolation(tmp_path):
    """Two sessions on the same target have isolated event subscriptions."""
    browser_ws = get_ws_url(port=9222, target_type="browser")

    targets_result_raw = CDPClient(ws_url=browser_ws)
    await targets_result_raw.connect()
    targets_result = await targets_result_raw.send(method="Target.getTargets")
    page_targets = [t for t in targets_result["targetInfos"] if t["type"] == "page"]
    target_id = page_targets[0]["targetId"]
    await targets_result_raw.close()

    # Session A: subscribes to Network
    cdp_a = CDPClient(ws_url=browser_ws)
    await cdp_a.connect()
    sa = await cdp_a.send(method="Target.attachToTarget", params={"targetId": target_id, "flatten": True})
    sid_a = sa["sessionId"]
    await cdp_a.send(method="Network.enable", session_id=sid_a)
    a_network = []
    cdp_a.on(event="Network.requestWillBeSent", callback=lambda p: a_network.append(p), session_id=sid_a)

    # Session B: does NOT subscribe to Network
    cdp_b = CDPClient(ws_url=browser_ws)
    await cdp_b.connect()
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

    # Cleanup
    await cdp_a.send(method="Target.detachFromTarget", params={"sessionId": sid_a})
    await cdp_b.send(method="Target.detachFromTarget", params={"sessionId": sid_b})
    await cdp_a.close()
    await cdp_b.close()
