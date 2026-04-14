"""Browser fingerprint profiles for anti-detection.

Loads fingerprint profiles from JSON files and applies them to a
running browser via CDP. Overrides navigator properties, viewport,
user agent, timezone, and locale to make the browser appear as a
real desktop browser.
"""

import asyncio
import json
import os
import subprocess
import sys
import textwrap
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
        # Retry page target lookup -- Chrome may not have created the initial
        # page target yet immediately after launch
        ws_url = None
        for _ in range(30):
            try:
                ws_url = get_ws_url(port=port, target_type="page")
                break
            except RuntimeError:
                await asyncio.sleep(0.2)
        if ws_url is None:
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


def spawn_fingerprint_guard(port: int, profile: BrowserFingerprint) -> subprocess.Popen:
    """Spawn a background daemon that holds the fingerprint init script alive.

    Page.addScriptToEvaluateOnNewDocument is session-scoped in CDP -- the
    script only runs on new documents while the registering CDP connection
    is alive. This daemon holds that connection open for the lifetime of
    the browser.

    The daemon is a separate process so it survives the caller exiting.
    It connects to the browser, registers the init script, and blocks
    until the browser dies (WebSocket disconnection).

    Returns the Popen handle for the daemon process.
    """
    # Serialize the init script as JSON to avoid quoting issues
    init_script_json = json.dumps(_build_init_script(profile=profile))

    # Build the guard script as a standalone Python program.
    # No indentation in the heredoc to avoid textwrap issues.
    guard_script = (
        "import asyncio, json\n"
        "from chrome_agent.cdp_client import CDPClient, get_ws_url\n"
        "async def guard():\n"
        f"    port = {port}\n"
        f"    init_script = json.loads({init_script_json!r})\n"
        "    ws_url = None\n"
        "    for _ in range(30):\n"
        "        try:\n"
        '            ws_url = get_ws_url(port=port, target_type="page")\n'
        "            break\n"
        "        except Exception:\n"
        "            await asyncio.sleep(0.2)\n"
        "    if ws_url is None:\n"
        '        ws_url = get_ws_url(port=port, target_type="page")\n'
        "    cdp = CDPClient(ws_url=ws_url)\n"
        "    await cdp.connect()\n"
        '    await cdp.send(method="Page.enable")\n'
        '    await cdp.send(method="Page.addScriptToEvaluateOnNewDocument", params={"source": init_script})\n'
        '    await cdp.send(method="Page.navigate", params={"url": "data:text/html,<html></html>"})\n'
        "    while cdp._connected:\n"
        "        await asyncio.sleep(1)\n"
        "asyncio.run(guard())\n"
    )

    process = subprocess.Popen(
        [sys.executable, "-u", "-c", guard_script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return process
