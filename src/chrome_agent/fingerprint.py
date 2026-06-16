"""Browser fingerprint profiles for anti-detection.

Loads fingerprint profiles from JSON and exposes the values that
``launch_browser`` applies via Chrome command-line flags and environment:
user agent, viewport, language, and timezone.

This module intentionally does NOT inject JavaScript to override navigator
properties (``webdriver`` / ``platform`` / ``vendor`` / ``window.chrome``).
An empirical detection audit (``research/2026-06-16-detection-audit.md``)
showed those overrides are each independently detectable and make the browser
*more* detectable, not less: they flip bot.sannysoft.com's WebDriver test from
pass to fail (the override makes ``navigator.webdriver`` an own property -- a
tamper signature), expose arrow-function getters where natives are expected,
replace ``window.chrome`` with a wrong-shaped stub, and raise CreepJS's
headless heuristic from 0% to 33%.

A plain CDP-attached Chrome already reports ``navigator.webdriver`` as the
native ``false`` and keeps the genuine ``window.chrome`` shape, so the right
move is to leave the JS environment untouched and only spoof what can be set
cleanly at launch. ``platform`` and ``vendor`` are retained in the profile
schema for compatibility and documentation but are not spoofed -- a profile's
platform should match the host OS (WebGL/font signals leak the real OS anyway).
"""

import json
from dataclasses import dataclass


@dataclass
class BrowserFingerprint:
    """Browser fingerprint profile for anti-detection."""
    user_agent: str
    viewport: dict[str, int]  # {"width": int, "height": int}
    locale: str
    timezone: str
    platform: str
    vendor: str


def load_fingerprint(path: str) -> BrowserFingerprint:
    """Load a fingerprint profile from a JSON file.

    Expected JSON schema:
        {
            "userAgent": "...",
            "platform": "...",
            "vendor": "...",
            "language": "en-US",
            "timezone": "America/Chicago",
            "viewport": {"width": 1920, "height": 1080}
        }

    Raises FileNotFoundError if path doesn't exist.
    Raises KeyError if required fields are missing.
    """
    with open(path, "r") as f:
        data = json.load(f)

    return BrowserFingerprint(
        user_agent=data["userAgent"],
        viewport=data["viewport"],
        locale=data["language"],
        timezone=data["timezone"],
        platform=data["platform"],
        vendor=data["vendor"],
    )
