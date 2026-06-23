"""Tests for BRW-03: Fingerprint Profiles.

Tests load_fingerprint() and the launch-flag spoofs (user agent, viewport,
language, timezone) against a real browser, plus anti-detection regressions
ensuring no detectable JS navigator overrides are left behind. Uses a dedicated
browser on port 9556 launched with fingerprint flags.
"""

import asyncio
import json
import os
import shutil
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
def fingerprinted_browser(profile_path, tmp_path_factory):
    """Launch a browser with fingerprint applied via Chrome launch flags.

    Uses an isolated registry so the run never touches the real registry.
    """
    reg_path = str(tmp_path_factory.mktemp("fp_registry") / "registry.json")
    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(
        launch_browser(
            port_override=FP_PORT,
            fingerprint=profile_path,
            headless=True,
            pin_to_desktop=False,
            registry_path=reg_path,
        )
    )

    yield result

    # Teardown: kill the browser (fingerprint spoofs are launch flags, so there
    # is no guard process), remove its session directory, close the loop.
    try:
        os.kill(result.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    shutil.rmtree(result.user_data_dir, ignore_errors=True)
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


# Anti-detection regression: the fingerprint must NOT leave the detectable
# JS-override signatures an earlier implementation did. See
# planning/03-specs/BRW-03-learnings/01-detection-audit.md -- those overrides flipped
# bot.sannysoft.com's WebDriver test from pass to fail and raised CreepJS's
# headless score. platform/vendor are no longer spoofed (a profile's platform
# should match the host OS), so they are not asserted here.


@pytest.mark.asyncio
async def test_fingerprint_webdriver_not_tampered(fingerprinted_browser):
    """navigator.webdriver is the native false, NOT an own-property override."""
    wd = await _eval_js(port=FP_PORT, expression="navigator.webdriver")
    assert wd is False, f"webdriver: {wd}"
    own = await _eval_js(
        port=FP_PORT,
        expression="Object.prototype.hasOwnProperty.call(navigator, 'webdriver')",
    )
    assert own is False, "webdriver must stay on the prototype (native), not be an own property"


@pytest.mark.asyncio
async def test_fingerprint_navigator_getters_native(fingerprinted_browser):
    """platform/vendor getters remain native -- not spoofed arrow functions."""
    for prop in ("platform", "vendor"):
        is_native = await _eval_js(
            port=FP_PORT,
            expression=(
                "(() => { const d = Object.getOwnPropertyDescriptor(Navigator.prototype, '%s');"
                " return d && d.get ? d.get.toString().includes('[native code]') : false; })()" % prop
            ),
        )
        assert is_native is True, f"{prop} getter must be native, not a spoofed arrow function"


@pytest.mark.asyncio
async def test_fingerprint_chrome_object_intact(fingerprinted_browser):
    """window.chrome is the genuine object, not a replaced stub."""
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
