"""CDP connection management.

Handles connecting to and disconnecting from a Chrome browser via the
Chrome DevTools Protocol. Also provides port status checking using only
stdlib (no Playwright needed for status).
"""

import json
import os
import socket
import urllib.request
from dataclasses import dataclass

from playwright.async_api import Playwright, async_playwright

from .errors import BrowserConnectionError, NoPageError

# Suppress Node.js deprecation warnings from Playwright internals.
# This must be set before Playwright spawns its Node.js subprocess.
os.environ.setdefault("NODE_OPTIONS", "--no-deprecation")


@dataclass
class PortStatus:
    """Result of checking whether a CDP port is active."""

    listening: bool
    browser_version: str | None = None
    page_url: str | None = None
    page_title: str | None = None


def check_cdp_port(*, port: int = 9222) -> PortStatus:
    """Check if a browser is listening on the CDP port.

    Uses stdlib only (socket + urllib) -- no Playwright dependency.
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


async def connect(*, port: int = 9222):
    """Connect to a running browser via CDP.

    Returns (playwright, browser, page) tuple. The caller is responsible
    for calling disconnect() when done.

    Raises BrowserConnectionError if no browser is listening.
    Raises NoPageError if the browser has no open pages.
    """
    pw = await async_playwright().start()

    cdp_url = f"http://localhost:{port}"
    try:
        browser = await pw.chromium.connect_over_cdp(cdp_url)
    except Exception as exc:
        await pw.stop()
        raise BrowserConnectionError(port=port) from exc

    contexts = browser.contexts
    if not contexts or not contexts[0].pages:
        await pw.stop()
        raise NoPageError()

    page = contexts[0].pages[0]
    return pw, browser, page


async def disconnect(*, pw: Playwright) -> None:
    """Clean up a Playwright connection."""
    await pw.stop()
