"""Tests for Instance Status (BRW-05).

Uses tmp_path for registry isolation and mocks for HTTP responses.
"""

import json
import os
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
        "proj-02": {"port": 9223, "pid": 99999999, "browser_version": "Chrome/147", "user_data_dir": ""},
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
        "proj-01": {"port": 9222, "pid": 99999999, "browser_version": "Chrome/147", "user_data_dir": ""},
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
