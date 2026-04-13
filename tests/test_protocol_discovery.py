"""Tests for CDP-03: Protocol Discovery.

Tests the discover_protocol() and fetch_protocol_schema() functions.
Runs against a real browser on port 9333 (session fixture).
"""

import pytest

from chrome_agent.protocol import discover_protocol, fetch_protocol_schema

CDP_PORT = 9333


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
