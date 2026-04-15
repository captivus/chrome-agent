"""CDP connection management.

Provides port status checking using stdlib only. The Playwright-based
connect/disconnect functions were removed in iteration 2 -- all CDP
connections now go through CDPClient (websockets-based).
"""

import json
import socket
import urllib.request
from dataclasses import dataclass


@dataclass
class PortStatus:
    """Result of checking whether a CDP port is active."""

    listening: bool
    browser_version: str | None = None
    page_url: str | None = None
    page_title: str | None = None


def check_cdp_port(*, port: int = 9222) -> PortStatus:
    """Check if a browser is listening on the CDP port.

    Uses stdlib only (socket + urllib).
    This is a synchronous function since it only does simple HTTP.
    """
    # Quick socket check first
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        result = sock.connect_ex(("localhost", port))
        if result != 0:
            return PortStatus(listening=False)
    finally:
        sock.close()

    # Port is open -- try to get browser version
    browser_version = None
    try:
        req = urllib.request.Request(f"http://localhost:{port}/json/version")
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read())
            browser_version = data.get("Browser")
    except Exception:
        pass

    # Try to get the first page's URL and title
    page_url = None
    page_title = None
    try:
        req = urllib.request.Request(f"http://localhost:{port}/json")
        with urllib.request.urlopen(req, timeout=2) as resp:
            pages = json.loads(resp.read())
            if pages:
                page_url = pages[0].get("url")
                page_title = pages[0].get("title")
    except Exception:
        pass

    return PortStatus(
        listening=True,
        browser_version=browser_version,
        page_url=page_url,
        page_title=page_title,
    )
