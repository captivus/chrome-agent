"""Tests for BRW-03: Fingerprint Profiles.

Tests apply_fingerprint() and load_fingerprint() against a real browser.
Uses a dedicated browser on port 9556 launched with fingerprint flags.
"""

import asyncio
import json
import os
import signal
import tempfile

import pytest

from chrome_agent.cdp_client import CDPClient, get_ws_url
from chrome_agent.fingerprint import (
    BrowserFingerprint,
    load_fingerprint,
)
from chrome_agent.launcher import launch_browser

FP_PORT = 9556

TEST_PROFILE = {
    "userAgent": "TestAgent/1.0",
    "platform": "TestPlatform",
    "vendor": "TestVendor",
    "language": "en-US",
    "timezone": "UTC",
    "viewport": {"width": 1024, "height": 768},
}


@pytest.fixture(scope="module")
def profile_path():
    """Create a temporary fingerprint profile JSON file."""
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(TEST_PROFILE, f)
    yield path
    os.unlink(path)


@pytest.fixture(scope="module")
def fingerprinted_browser(profile_path):
    """Launch a browser with fingerprint applied via Chrome flags + init script."""
    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(
        launch_browser(
            port_override=FP_PORT,
            fingerprint=profile_path,
            headless=True,
            pin_to_desktop=False,
        )
    )

    yield result

    # Note: fingerprint_guard is now internal to launch_browser, not on InstanceInfo
    try:
        os.kill(result.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    loop.close()


async def _eval_js(port: int, expression: str):
    """Evaluate JS in the browser and return the value."""
    ws_url = get_ws_url(port=port, target_type="page")
    async with CDPClient(ws_url=ws_url) as cdp:
        result = await cdp.send(
            method="Runtime.evaluate",
            params={"expression": expression, "returnByValue": True},
        )
        return result["result"]["value"]


# ---------------------------------------------------------------------------
# Happy path -- fingerprint signals
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fingerprint_user_agent(fingerprinted_browser):
    """User agent is overridden."""
    ua = await _eval_js(port=FP_PORT, expression="navigator.userAgent")
    assert ua == "TestAgent/1.0", f"userAgent: {ua}"


@pytest.mark.asyncio
async def test_fingerprint_platform(fingerprinted_browser):
    """Platform is overridden."""
    plat = await _eval_js(port=FP_PORT, expression="navigator.platform")
    assert plat == "TestPlatform", f"platform: {plat}"


@pytest.mark.asyncio
async def test_fingerprint_vendor(fingerprinted_browser):
    """Vendor is overridden."""
    vend = await _eval_js(port=FP_PORT, expression="navigator.vendor")
    assert vend == "TestVendor", f"vendor: {vend}"


@pytest.mark.asyncio
async def test_fingerprint_webdriver(fingerprinted_browser):
    """Webdriver flag is false."""
    wd = await _eval_js(port=FP_PORT, expression="navigator.webdriver")
    assert wd is False, f"webdriver: {wd}"


@pytest.mark.asyncio
async def test_fingerprint_chrome_object(fingerprinted_browser):
    """window.chrome object exists."""
    wc = await _eval_js(port=FP_PORT, expression="typeof window.chrome")
    assert wc == "object", f"window.chrome: {wc}"


@pytest.mark.asyncio
async def test_fingerprint_viewport(fingerprinted_browser):
    """Viewport width matches profile. Height may be less due to Chrome UI."""
    vw = await _eval_js(port=FP_PORT, expression="window.innerWidth")
    vh = await _eval_js(port=FP_PORT, expression="window.innerHeight")
    assert vw == 1024, f"innerWidth: {vw}"
    # Headless Chrome subtracts toolbar area from window height
    assert vh > 600, f"innerHeight too small: {vh}"


@pytest.mark.asyncio
async def test_fingerprint_timezone(fingerprinted_browser):
    """Timezone matches profile."""
    tz = await _eval_js(
        port=FP_PORT,
        expression="Intl.DateTimeFormat().resolvedOptions().timeZone",
    )
    assert tz == "UTC", f"timezone: {tz}"


@pytest.mark.asyncio
async def test_fingerprint_language(fingerprinted_browser):
    """Language matches profile."""
    lang = await _eval_js(port=FP_PORT, expression="navigator.language")
    assert lang == "en-US", f"language: {lang}"


# ---------------------------------------------------------------------------
# Persistence across navigation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fingerprint_persists(fingerprinted_browser):
    """Fingerprint persists after navigating to a new page."""
    ws_url = get_ws_url(port=FP_PORT, target_type="page")
    async with CDPClient(ws_url=ws_url) as cdp:
        await cdp.send(method="Page.navigate", params={"url": "https://example.com"})
        await asyncio.sleep(2)

    ua = await _eval_js(port=FP_PORT, expression="navigator.userAgent")
    assert ua == "TestAgent/1.0", f"userAgent after navigation: {ua}"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_missing_field():
    """Missing required field raises KeyError."""
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump({"platform": "X", "vendor": "Y", "language": "en",
                    "timezone": "UTC", "viewport": {"width": 1, "height": 1}}, f)
    try:
        with pytest.raises(KeyError):
            load_fingerprint(path=path)
    finally:
        os.unlink(path)


def test_nonexistent_file():
    """Nonexistent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_fingerprint(path="/tmp/does-not-exist-fp.json")
