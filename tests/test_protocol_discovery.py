"""Tests for CDP-03: Protocol Discovery.

Tests the discover_protocol() and fetch_protocol_schema() functions.
Runs against a real browser on port 9333 (session fixture).
"""

import pytest

from chrome_agent.protocol import _resolve_port, discover_protocol, fetch_protocol_schema
from chrome_agent.registry import InstanceInfo

CDP_PORT = 9333


def _inst(name: str, port: int, alive: bool) -> InstanceInfo:
    return InstanceInfo(name=name, port=port, pid=1234, browser_version="test", alive=alive)


# ---------------------------------------------------------------------------
# Happy path -- list all domains
# ---------------------------------------------------------------------------


def test_list_domains(browser_session, capsys):
    """Lists all domains including well-known ones."""
    discover_protocol(port=CDP_PORT)
    output = capsys.readouterr().out
    assert "Page" in output
    assert "DOM" in output
    assert "Runtime" in output
    assert "Network" in output


# ---------------------------------------------------------------------------
# Happy path -- domain detail
# ---------------------------------------------------------------------------


def test_domain_detail(browser_session, capsys):
    """Shows commands and events for a specific domain."""
    discover_protocol(port=CDP_PORT, query="Page")
    output = capsys.readouterr().out
    assert "Page.navigate" in output
    assert "Page.captureScreenshot" in output
    assert "Commands:" in output
    assert "Events:" in output


# ---------------------------------------------------------------------------
# Happy path -- method detail
# ---------------------------------------------------------------------------


def test_method_detail(browser_session, capsys):
    """Shows parameters and returns for a specific command."""
    discover_protocol(port=CDP_PORT, query="Page.navigate")
    output = capsys.readouterr().out
    assert "url" in output
    assert "string" in output
    assert "frameId" in output


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_no_browser():
    """Raises ConnectionError when no browser is running."""
    with pytest.raises(ConnectionError):
        discover_protocol(port=9444)


def test_unknown_domain(browser_session):
    """Raises ValueError with 'Unknown domain' for nonexistent domain."""
    with pytest.raises(ValueError, match="Unknown domain"):
        discover_protocol(port=CDP_PORT, query="FakeDomain")


def test_unknown_method(browser_session):
    """Raises ValueError with 'Unknown method' for nonexistent method."""
    with pytest.raises(ValueError, match="Unknown method"):
        discover_protocol(port=CDP_PORT, query="Page.fakeMethod")


# ---------------------------------------------------------------------------
# Port auto-selection (the `help <Domain>` dispatch fix)
# ---------------------------------------------------------------------------


def test_resolve_port_any_when_multiple_live(monkeypatch):
    """With 2+ live instances and no name/port, auto-select picks a live one (not None).

    Regression: the prior "exactly one live instance" rule returned None whenever
    zero or two-plus instances were live, so `help <Domain>` with several browsers
    running fell through to the static usage banner instead of showing the domain.
    Protocol discovery is read-only and the schema is identical across instances,
    so any live instance must be able to answer.
    """
    insts = [_inst("a-01", 9501, True), _inst("b-01", 9502, True), _inst("c-01", 9503, True)]
    monkeypatch.setattr("chrome_agent.registry.enumerate_instances", lambda *a, **k: insts)
    assert _resolve_port(instance_name=None, port=None) in {9501, 9502, 9503}


def test_resolve_port_single_live(monkeypatch):
    """Exactly one live instance still resolves to its port (behavior preserved)."""
    monkeypatch.setattr(
        "chrome_agent.registry.enumerate_instances",
        lambda *a, **k: [_inst("only-01", 9555, True)],
    )
    assert _resolve_port(instance_name=None, port=None) == 9555


def test_resolve_port_skips_dead(monkeypatch):
    """Dead instances are skipped; a live one is chosen."""
    insts = [_inst("dead-01", 9501, False), _inst("live-01", 9502, True), _inst("dead-02", 9503, False)]
    monkeypatch.setattr("chrome_agent.registry.enumerate_instances", lambda *a, **k: insts)
    assert _resolve_port(instance_name=None, port=None) == 9502


def test_resolve_port_none_when_no_live(monkeypatch):
    """Zero live instances -> None, so the caller emits a clean error / usage banner."""
    monkeypatch.setattr(
        "chrome_agent.registry.enumerate_instances",
        lambda *a, **k: [_inst("dead-01", 9501, False)],
    )
    assert _resolve_port(instance_name=None, port=None) is None


def test_resolve_port_explicit_port_beats_autoselect(monkeypatch):
    """An explicit port takes precedence over auto-selection."""
    monkeypatch.setattr(
        "chrome_agent.registry.enumerate_instances",
        lambda *a, **k: [_inst("a-01", 9501, True)],
    )
    assert _resolve_port(instance_name=None, port=9999) == 9999


# ---------------------------------------------------------------------------
# Raw schema access
# ---------------------------------------------------------------------------


def test_fetch_raw_schema(browser_session):
    """fetch_protocol_schema returns a valid schema with domains."""
    schema = fetch_protocol_schema(port=CDP_PORT)
    assert "domains" in schema
    assert len(schema["domains"]) > 0
    assert any(d["domain"] == "Page" for d in schema["domains"])


def test_fetch_no_browser():
    """fetch_protocol_schema raises ConnectionError when no browser."""
    with pytest.raises(ConnectionError):
        fetch_protocol_schema(port=9444)
