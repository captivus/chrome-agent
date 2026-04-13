"""Tests for BRW-02: Browser Status.

Tests the check_cdp_port() function and PortStatus dataclass.
Runs against a real browser on port 9333 (session fixture) and
against ports with no browser or non-Chrome services.
"""

import http.server
import threading

import pytest

from chrome_agent.connection import PortStatus, check_cdp_port

CDP_PORT = 9333


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_browser_running(browser_session):
    """Detects a running browser with version, URL, and title."""
    status = check_cdp_port(port=CDP_PORT)
    assert status.listening is True
    assert status.browser_version is not None
    assert "Chrome" in status.browser_version or "Chromium" in status.browser_version
    assert status.page_url is not None
    assert status.page_title is not None


# ---------------------------------------------------------------------------
# No browser
# ---------------------------------------------------------------------------


def test_no_browser():
    """Reports listening=False when nothing is on the port."""
    status = check_cdp_port(port=9444)
    assert status.listening is False
    assert status.browser_version is None
    assert status.page_url is None
    assert status.page_title is None


# ---------------------------------------------------------------------------
# Partial information -- port open but not Chrome
# ---------------------------------------------------------------------------


@pytest.fixture
def non_chrome_port():
    """Start a minimal HTTP server that is not Chrome CDP."""
    handler = http.server.SimpleHTTPRequestHandler

    # Suppress request logging
    class QuietHandler(handler):
        def log_message(self, format, *args):
            pass

    server = http.server.HTTPServer(("localhost", 0), QuietHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield port
    server.shutdown()


def test_port_open_not_chrome(non_chrome_port):
    """Reports listening=True but version/page are None for non-Chrome port."""
    status = check_cdp_port(port=non_chrome_port)
    assert status.listening is True
    # /json/version doesn't exist on a random HTTP server
    assert status.browser_version is None


# ---------------------------------------------------------------------------
# PortStatus dataclass
# ---------------------------------------------------------------------------


def test_port_status_defaults():
    """PortStatus defaults optional fields to None."""
    status = PortStatus(listening=False)
    assert status.listening is False
    assert status.browser_version is None
    assert status.page_url is None
    assert status.page_title is None
