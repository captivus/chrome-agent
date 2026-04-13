"""Tests for CDP-01: CDP WebSocket Client.

Tests run against a real browser on port 9333. The browser is launched
by the session-scoped browser_session fixture in conftest.py.
"""

import asyncio
import base64

import pytest

from chrome_agent.cdp_client import CDPClient, get_targets, get_ws_url
from chrome_agent.errors import CDPError

CDP_PORT = 9333


@pytest.fixture
def page_ws_url(browser_session):
    """Get the WebSocket URL for the first page target."""
    return get_ws_url(port=CDP_PORT, target_type="page")


@pytest.fixture
def browser_ws_url(browser_session):
    """Get the browser-level WebSocket URL."""
    return get_ws_url(port=CDP_PORT, target_type="browser")


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_command_round_trip(page_ws_url):
    """Successful command round-trip: send Runtime.evaluate, get result."""
    async with CDPClient(ws_url=page_ws_url) as cdp:
        result = await cdp.send(
            method="Runtime.evaluate",
            params={"expression": "1 + 1", "returnByValue": True},
        )
    assert result["result"]["type"] == "number"
    assert result["result"]["value"] == 2


@pytest.mark.asyncio
async def test_event_subscription(page_ws_url):
    """Event subscription and delivery: Page.loadEventFired fires on navigate."""
    events = []
    async with CDPClient(ws_url=page_ws_url) as cdp:
        await cdp.send(method="Page.enable")
        cdp.on(event="Page.loadEventFired", callback=lambda p: events.append(p))
        await cdp.send(method="Page.navigate", params={"url": "https://example.com"})
        # Wait for the event to arrive
        for _ in range(40):
            if events:
                break
            await asyncio.sleep(0.1)
    assert len(events) >= 1
    assert "timestamp" in events[0]


@pytest.mark.asyncio
async def test_message_id_correlation(page_ws_url):
    """Multiple concurrent commands maintain correct ID correlation."""
    async with CDPClient(ws_url=page_ws_url) as cdp:
        f1 = cdp.send(method="Runtime.evaluate", params={"expression": "'a'", "returnByValue": True})
        f2 = cdp.send(method="Runtime.evaluate", params={"expression": "'b'", "returnByValue": True})
        f3 = cdp.send(method="Runtime.evaluate", params={"expression": "'c'", "returnByValue": True})
        r1, r2, r3 = await asyncio.gather(f1, f2, f3)
    assert r1["result"]["value"] == "a"
    assert r2["result"]["value"] == "b"
    assert r3["result"]["value"] == "c"


# ---------------------------------------------------------------------------
# Session multiplexing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_session_multiplexing(browser_ws_url):
    """Session multiplexing: attach to a target and send commands via sessionId."""
    async with CDPClient(ws_url=browser_ws_url) as cdp:
        targets = await cdp.send(method="Target.getTargets")
        page_target = next(
            t for t in targets["targetInfos"] if t["type"] == "page"
        )
        attach = await cdp.send(
            method="Target.attachToTarget",
            params={"targetId": page_target["targetId"], "flatten": True},
        )
        session_id = attach["sessionId"]
        result = await cdp.send(
            method="Runtime.evaluate",
            params={"expression": "document.title", "returnByValue": True},
            session_id=session_id,
        )
    assert "result" in result
    assert result["result"]["type"] == "string"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cdp_error_propagation(page_ws_url):
    """CDP errors propagate as CDPError with code and message."""
    async with CDPClient(ws_url=page_ws_url) as cdp:
        with pytest.raises(CDPError) as exc_info:
            await cdp.send(
                method="DOM.querySelector",
                params={"nodeId": 99999, "selector": "div"},
            )
    assert exc_info.value.code is not None
    assert exc_info.value.message is not None


@pytest.mark.asyncio
async def test_send_when_not_connected():
    """Sending on an unconnected client raises ConnectionError."""
    cdp = CDPClient(ws_url="ws://localhost:9333/devtools/page/fake")
    with pytest.raises(ConnectionError):
        await cdp.send(method="Runtime.evaluate", params={"expression": "1"})


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_large_response(page_ws_url):
    """Large responses (screenshots) are handled without truncation."""
    async with CDPClient(ws_url=page_ws_url) as cdp:
        result = await cdp.send(method="Page.captureScreenshot", params={"format": "png"})
    assert "data" in result
    decoded = base64.b64decode(result["data"])
    assert len(decoded) > 0


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_context_manager_cleanup(page_ws_url):
    """Context manager closes the connection on normal exit."""
    cdp = CDPClient(ws_url=page_ws_url)
    async with cdp:
        await cdp.send(method="Runtime.evaluate", params={"expression": "1"})
    # After exit, sending should fail
    with pytest.raises(ConnectionError):
        await cdp.send(method="Runtime.evaluate", params={"expression": "1"})


@pytest.mark.asyncio
async def test_context_manager_exception_cleanup(page_ws_url):
    """Context manager closes the connection even when an exception is raised."""
    cdp = CDPClient(ws_url=page_ws_url)
    with pytest.raises(ValueError, match="test exception"):
        async with cdp:
            await cdp.send(method="Runtime.evaluate", params={"expression": "1"})
            raise ValueError("test exception")
    # After exit with exception, sending should fail
    with pytest.raises(ConnectionError):
        await cdp.send(method="Runtime.evaluate", params={"expression": "1"})


# ---------------------------------------------------------------------------
# Target discovery helpers
# ---------------------------------------------------------------------------


def test_get_targets(browser_session):
    """get_targets returns a list of target dicts."""
    targets = get_targets(port=CDP_PORT)
    assert isinstance(targets, list)
    assert len(targets) > 0
    assert "type" in targets[0]
    assert "webSocketDebuggerUrl" in targets[0]


def test_get_ws_url_page(browser_session):
    """get_ws_url returns a WebSocket URL for a page target."""
    url = get_ws_url(port=CDP_PORT, target_type="page")
    assert url.startswith("ws://")
    assert "/devtools/page/" in url


def test_get_ws_url_browser(browser_session):
    """get_ws_url returns a WebSocket URL for the browser target."""
    url = get_ws_url(port=CDP_PORT, target_type="browser")
    assert url.startswith("ws://")
    assert "/devtools/browser/" in url


def test_get_targets_no_browser():
    """get_targets raises ConnectionError when no browser is listening."""
    with pytest.raises(ConnectionError):
        get_targets(port=19999)


def test_get_ws_url_no_browser():
    """get_ws_url raises ConnectionError when no browser is listening."""
    with pytest.raises(ConnectionError):
        get_ws_url(port=19999, target_type="page")
