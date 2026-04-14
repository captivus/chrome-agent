"""Browser fingerprint profiles for anti-detection.

Loads fingerprint profiles from JSON files and applies them to a
running browser via CDP. Overrides navigator properties, viewport,
user agent, timezone, and locale to make the browser appear as a
real desktop browser.
"""

import json
from dataclasses import dataclass

from .cdp_client import CDPClient, get_ws_url


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


def _build_init_script(profile: BrowserFingerprint) -> str:
    """Build the JavaScript init script that overrides navigator properties.

    Uses Navigator.prototype for platform and vendor because instance-level
    properties on navigator are non-configurable in modern Chrome. The
    prototype override is configurable and takes effect on all reads.
    """
    return f"""\
Object.defineProperty(navigator, 'webdriver', {{
    get: () => false
}});

Object.defineProperty(Navigator.prototype, 'platform', {{
    get: () => '{profile.platform}'
}});

Object.defineProperty(Navigator.prototype, 'vendor', {{
    get: () => '{profile.vendor}'
}});

window.chrome = {{
    runtime: {{}},
    app: {{}}
}};
"""


async def apply_fingerprint(
    port: int = 9222,
    profile: BrowserFingerprint | None = None,
    client: CDPClient | None = None,
) -> CDPClient:
    """Apply a fingerprint profile to a running browser via CDP.

    Injects an init script that overrides navigator properties on every
    new document load. The init script is session-scoped -- it persists
    only while the CDP connection that registered it is alive.

    If a CDPClient is provided, uses it directly. Otherwise, creates a
    new connection. In either case, the returned CDPClient must be kept
    alive for the fingerprint to persist across navigations. The caller
    is responsible for closing it.

    Browser-level overrides (user agent HTTP header, viewport, timezone,
    locale) should be set via Chrome command-line flags at launch time
    (handled by launch_browser in launcher.py). This function handles
    only the JavaScript-level overrides that require CDP.

    Returns the CDPClient used (either the provided one or a new one).
    Raises CDPError if CDP commands fail.
    """
    if client is None:
        ws_url = get_ws_url(port=port, target_type="page")
        client = CDPClient(ws_url=ws_url)
        await client.connect()

    # Enable the Page domain
    await client.send(method="Page.enable")

    # Inject init script that overrides navigator properties
    init_script = _build_init_script(profile=profile)
    await client.send(
        method="Page.addScriptToEvaluateOnNewDocument",
        params={"source": init_script},
    )

    # Navigate to a data: URL to trigger the init script immediately
    # (about:blank does not trigger addScriptToEvaluateOnNewDocument)
    await client.send(
        method="Page.navigate",
        params={"url": "data:text/html,<html></html>"},
    )

    return client
