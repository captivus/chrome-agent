"""Tests for Instance Status (BRW-05).

Uses tmp_path for registry isolation and mocks for HTTP responses.
"""

import json
import os
import socket
from unittest.mock import MagicMock, patch

import pytest

from chrome_agent.instance_status import (
    InstanceStatus,
    PageTarget,
    format_status_json,
    format_status_text,
    get_instance_status,
    query_targets,
)
from chrome_agent.registry import InstanceNotFoundError


def _free_port() -> int:
    """A port with nothing listening on it (bound then released).

    Dead instances must use a free port: liveness is now pid-OR-port, so a
    hardcoded low port (9222) would read as alive if a real browser happens
    to be listening on it.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("localhost", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _write_registry(reg_path, entries):
    """Helper to write a registry file directly."""
    os.makedirs(os.path.dirname(reg_path), exist_ok=True)
    with open(reg_path, "w") as f:
        json.dump(entries, f)


def test_query_targets_success():
    """query_targets returns PageTarget list from /json response."""
    mock_targets = [
        {"id": "ABCD1234EFGH5678", "type": "page", "url": "https://example.com", "title": "Example"},
        {"id": "IJKL9012MNOP3456", "type": "page", "url": "https://test.com", "title": "Test"},
        {"id": "WORKER001", "type": "service_worker", "url": "sw.js", "title": ""},
    ]

    with patch("chrome_agent.instance_status.urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_targets).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        targets = query_targets(port=9222)

    assert len(targets) == 2  # only page targets
    assert targets[0].short_id == "ABCD1234"
    assert targets[0].index == 1
    assert targets[0].url == "https://example.com"
    assert targets[1].index == 2


def test_query_targets_failure():
    """query_targets returns empty list on HTTP failure."""
    with patch("chrome_agent.instance_status.urllib.request.urlopen", side_effect=Exception("connection refused")):
        targets = query_targets(port=9999)

    assert targets == []


def test_get_instance_status_all(tmp_path):
    """get_instance_status with no filter returns all instances."""
    reg_path = str(tmp_path / "registry.json")
    _write_registry(reg_path, {
        "proj-01": {"port": 9222, "pid": os.getpid(), "browser_version": "Chrome/147", "user_data_dir": ""},
        "proj-02": {"port": _free_port(), "pid": 99999999, "browser_version": "Chrome/147", "user_data_dir": ""},
    })

    with patch("chrome_agent.instance_status.query_targets", return_value=[]):
        statuses = get_instance_status(registry_path=reg_path)

    assert len(statuses) == 2
    status_map = {s.name: s for s in statuses}
    assert status_map["proj-01"].alive is True
    assert status_map["proj-02"].alive is False


def test_get_instance_status_filter_by_name(tmp_path):
    """get_instance_status with instance_name filters to one."""
    reg_path = str(tmp_path / "registry.json")
    _write_registry(reg_path, {
        "proj-01": {"port": 9222, "pid": os.getpid(), "browser_version": "Chrome/147", "user_data_dir": ""},
        "proj-02": {"port": 9223, "pid": os.getpid(), "browser_version": "Chrome/147", "user_data_dir": ""},
    })

    with patch("chrome_agent.instance_status.query_targets", return_value=[]):
        statuses = get_instance_status(instance_name="proj-01", registry_path=reg_path)

    assert len(statuses) == 1
    assert statuses[0].name == "proj-01"


def test_get_instance_status_not_found(tmp_path):
    """get_instance_status raises InstanceNotFoundError for unknown name."""
    reg_path = str(tmp_path / "registry.json")
    _write_registry(reg_path, {
        "proj-01": {"port": 9222, "pid": os.getpid(), "browser_version": "Chrome/147", "user_data_dir": ""},
    })

    with pytest.raises(InstanceNotFoundError) as exc_info:
        get_instance_status(instance_name="nonexistent", registry_path=reg_path)

    assert "proj-01" in exc_info.value.available


def test_get_instance_status_empty_registry(tmp_path):
    """get_instance_status with empty registry returns empty list."""
    reg_path = str(tmp_path / "registry.json")

    statuses = get_instance_status(registry_path=reg_path)
    assert statuses == []


def test_dead_instance_no_targets(tmp_path):
    """Dead instances get empty target lists (no /json query)."""
    reg_path = str(tmp_path / "registry.json")
    _write_registry(reg_path, {
        "proj-01": {"port": _free_port(), "pid": 99999999, "browser_version": "Chrome/147", "user_data_dir": ""},
    })

    # query_targets should NOT be called for dead instances
    with patch("chrome_agent.instance_status.query_targets") as mock_qt:
        statuses = get_instance_status(registry_path=reg_path)

    mock_qt.assert_not_called()
    assert statuses[0].alive is False
    assert statuses[0].targets == []


def test_format_text():
    """Text format matches expected output structure."""
    statuses = [
        InstanceStatus(
            name="aroundchicago.tech-01",
            port=9222,
            alive=True,
            targets=[
                PageTarget(target_id="956FD3C2ABCDEF12", short_id="956FD3C2", index=1,
                           url="https://www.meetup.com/find/", title="Find Events | Meetup"),
            ],
        ),
        InstanceStatus(
            name="kindle2markdown-01",
            port=9223,
            alive=False,
            targets=[],
        ),
    ]

    text = format_status_text(statuses)
    lines = text.split("\n")

    assert "aroundchicago.tech-01" in lines[0]
    assert "port 9222" in lines[0]
    assert "DEAD" not in lines[0]
    assert "956FD3C2" in lines[1]
    assert "meetup.com" in lines[1]
    assert "kindle2markdown-01" in lines[3] or "kindle2markdown-01" in lines[2]
    assert "DEAD" in text


def test_format_json():
    """JSON format produces valid JSON with expected structure."""
    statuses = [
        InstanceStatus(
            name="proj-01",
            port=9222,
            alive=True,
            targets=[
                PageTarget(target_id="ABCD1234EFGH5678", short_id="ABCD1234", index=1,
                           url="https://example.com", title="Example"),
            ],
        ),
    ]

    result = format_status_json(statuses)
    data = json.loads(result)

    assert len(data) == 1
    assert data[0]["name"] == "proj-01"
    assert data[0]["port"] == 9222
    assert data[0]["alive"] is True
    assert len(data[0]["targets"]) == 1
    assert data[0]["targets"][0]["id"] == "ABCD1234"
    assert data[0]["targets"][0]["full_id"] == "ABCD1234EFGH5678"
    assert data[0]["targets"][0]["index"] == 1


def test_target_id_truncation():
    """Target IDs are truncated to 8 characters and uppercased."""
    mock_targets = [
        {"id": "abcdef1234567890", "type": "page", "url": "https://example.com", "title": "Test"},
    ]

    with patch("chrome_agent.instance_status.urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_targets).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        targets = query_targets(port=9222)

    assert targets[0].short_id == "ABCDEF12"
    assert targets[0].target_id == "abcdef1234567890"


def test_off_screen_instances_are_tagged():
    """A browser on a virtual display or headless is tagged; one on the user's
    desktop is not -- the tag exists to flag windows the user cannot see."""
    statuses = [
        InstanceStatus(name="desk-01", port=9222, alive=True,
                       placement={"kind": "desktop", "display": ":1"}),
        InstanceStatus(name="xvfb-01", port=9223, alive=True,
                       placement={"kind": "virtual", "display": ":95", "server": "Xvfb"}),
        InstanceStatus(name="head-01", port=9224, alive=True, placement={"kind": "headless"}),
        InstanceStatus(name="gone-01", port=9225, alive=False),
    ]
    text = format_status_text(statuses)
    assert "desk-01  port 9222\n" in text + "\n"
    assert "xvfb-01  port 9223  [Xvfb :95]" in text
    assert "head-01  port 9224  [headless]" in text
    assert "gone-01  port 9225  DEAD" in text

    data = {entry["name"]: entry for entry in json.loads(format_status_json(statuses))}
    assert data["xvfb-01"]["display"] == {"kind": "virtual", "display": ":95", "server": "Xvfb"}
    assert data["gone-01"]["display"] is None


def test_browser_placements_detects_headless(browser_session):
    """The conftest browser is headless; the /proc scan must classify it so."""
    from chrome_agent.desktop import browser_placements

    assert browser_placements([browser_session.port]) == {
        browser_session.port: {"kind": "headless"}
    }


def test_browser_placements_ignores_unknown_ports():
    from chrome_agent.desktop import browser_placements

    assert browser_placements([_free_port()]) == {}


# -- tab order -----------------------------------------------------------------

def _target(tid: str, index: int) -> PageTarget:
    return PageTarget(target_id=tid, short_id=tid[:8], index=index, url=f"https://{tid}/", title=tid)


def test_order_targets_sorts_by_window_then_position(monkeypatch):
    """Tabs follow the extension's on-screen order and are renumbered by it."""
    from chrome_agent import instance_status, taborder

    targets = [_target("AAAA", 1), _target("BBBB", 2), _target("CCCC", 3), _target("DDDD", 4)]
    positions = {"CCCC": (7, 0), "AAAA": (7, 1), "DDDD": (9, 0)}  # BBBB unseen

    class FakeClient:
        def __init__(self, ws_url): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *exc): return False

    async def fake_positions(cdp):
        return positions

    monkeypatch.setattr("chrome_agent.cdp_client.CDPClient", FakeClient)
    monkeypatch.setattr("chrome_agent.cdp_client.get_ws_url", lambda port, target_type: "ws://x")
    monkeypatch.setattr(taborder, "tab_positions", fake_positions)

    assert instance_status.order_targets({9222: targets}) == {9222}

    assert [t.target_id for t in targets] == ["CCCC", "AAAA", "DDDD", "BBBB"]
    assert [t.index for t in targets] == [1, 2, 3, 4]
    assert [(t.window, t.position) for t in targets] == [(1, 1), (1, 2), (2, 1), (None, None)]


def test_order_targets_keeps_listing_when_order_unreadable(monkeypatch):
    from chrome_agent import instance_status

    def refuse(port, target_type):
        raise ConnectionError("nothing there")

    monkeypatch.setattr("chrome_agent.cdp_client.get_ws_url", refuse)
    targets = [_target("AAAA", 1), _target("BBBB", 2)]
    assert instance_status.order_targets({9222: targets}) == set()
    assert [(t.target_id, t.index) for t in targets] == [("AAAA", 1), ("BBBB", 2)]
    text = format_status_text([InstanceStatus(name="x-01", port=9222, alive=True, targets=targets)])
    assert "tab order unavailable" in text


def test_format_status_text_separates_windows():
    a, b, c = _target("AAAA", 1), _target("BBBB", 2), _target("CCCC", 3)
    a.window, a.position = 1, 1
    b.window, b.position = 1, 2
    c.window, c.position = 2, 1
    text = format_status_text([InstanceStatus(name="x-01", port=9222, alive=True, targets=[a, b, c], tab_order=True)])
    assert text.splitlines()[1:] == [
        '  [1] AAAA  https://AAAA/  "AAAA"',
        '  [2] BBBB  https://BBBB/  "BBBB"',
        "  --- window",
        '  [3] CCCC  https://CCCC/  "CCCC"',
    ]
    entry = json.loads(format_status_json([InstanceStatus(name="x-01", port=9222, alive=True, targets=[c])]))[0]
    assert (entry["targets"][0]["window"], entry["targets"][0]["position"]) == (2, 1)


def test_single_tab_is_window_1_position_1_without_a_lookup(tmp_path, monkeypatch):
    from chrome_agent import instance_status

    reg_path = str(tmp_path / "registry.json")
    _write_registry(reg_path, {"solo-01": {"port": 9222, "pid": os.getpid()}})
    monkeypatch.setattr("chrome_agent.registry._instance_is_alive", lambda *a, **k: True)
    monkeypatch.setattr("chrome_agent.desktop.browser_placements", lambda ports: {})
    monkeypatch.setattr(instance_status, "query_targets", lambda *, port: [_target("AAAA", 1)])

    def no_lookup(targets_by_port):
        assert not any(len(t) > 1 for t in targets_by_port.values())
        return set()

    monkeypatch.setattr(instance_status, "order_targets", no_lookup)
    status = get_instance_status(registry_path=reg_path, order_tabs=True)[0]
    assert status.tab_order
    assert (status.targets[0].window, status.targets[0].position) == (1, 1)
