"""Browser launcher with optional anti-detection fingerprinting.

Launches a Playwright Chromium browser with CDP enabled. Optionally
applies a fingerprint profile to make the browser appear as a real
desktop browser.

Uses launch_persistent_context() so the page lives in the browser's
default context -- visible to any CDP client reconnecting via
connect_over_cdp(). Playwright's browser.new_context() creates an
isolated context that is invisible to CDP reconnections.
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass

from playwright.async_api import BrowserContext, Page, Playwright, async_playwright

logger = logging.getLogger(__name__)


@dataclass
class BrowserFingerprint:
    """Browser fingerprint profile for anti-detection."""

    user_agent: str
    viewport: dict[str, int]
    locale: str
    timezone: str
    platform: str
    vendor: str


@dataclass
class BrowserSession:
    """Handle to a launched browser session.

    The context is a persistent browser context -- calling close()
    on it shuts down the browser process.
    """

    playwright: Playwright
    context: BrowserContext
    page: Page

    @property
    def browser(self) -> BrowserContext:
        """Backwards-compatible alias.

        Persistent contexts don't have a separate Browser object.
        The context itself has a close() method that shuts down
        the browser, so existing code like session.browser.close()
        continues to work.
        """
        return self.context


async def load_fingerprint(*, path: str) -> BrowserFingerprint:
    """Load a browser fingerprint profile from a JSON file.

    Expected JSON schema:
        {
            "userAgent": "...",
            "platform": "...",
            "vendor": "...",
            "language": "en-US",
            "timezone": "America/Chicago",
            "viewport": {"width": 1920, "height": 1080}
        }
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


async def launch_browser(
    *,
    port: int = 9222,
    fingerprint: BrowserFingerprint | None = None,
    headless: bool = False,
    pin_to_desktop: bool = True,
) -> BrowserSession:
    """Launch a Chromium browser with CDP enabled.

    Uses a persistent context so the page is in the browser's default
    context and visible to CDP reconnections (chrome-agent attach mode).

    Args:
        port: CDP remote debugging port.
        fingerprint: Optional fingerprint for anti-detection. If None,
            launches a clean browser with no spoofing.
        headless: Run in headless mode.
        pin_to_desktop: Move browser window to the launching terminal's
            virtual desktop. Default True. Linux/X11 only, requires
            xdotool -- silently skipped on other platforms.
    """
    playwright = await async_playwright().start()

    launch_args = [
        f"--remote-debugging-port={port}",
        "--no-first-run",
        "--no-default-browser-check",
    ]

    # Build context options from fingerprint
    context_kwargs = {}
    if fingerprint:
        context_kwargs.update(
            user_agent=fingerprint.user_agent,
            viewport=fingerprint.viewport,
            locale=fingerprint.locale,
            timezone_id=fingerprint.timezone,
        )

    # Use a temp directory for the user data dir. Persistent context
    # requires one, but we don't need state to persist across runs.
    user_data_dir = tempfile.mkdtemp(prefix="chrome-agent-")

    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        headless=headless,
        args=launch_args,
        **context_kwargs,
    )

    # Apply anti-detection init script if fingerprinted
    if fingerprint:
        await context.add_init_script(f"""
            Object.defineProperty(navigator, 'webdriver', {{
                get: () => false
            }});

            Object.defineProperty(navigator, 'platform', {{
                get: () => '{fingerprint.platform}'
            }});

            Object.defineProperty(navigator, 'vendor', {{
                get: () => '{fingerprint.vendor}'
            }});

            window.chrome = {{
                runtime: {{}},
                app: {{}}
            }};
        """)

    # Persistent context starts with one page
    page = context.pages[0] if context.pages else await context.new_page()

    session = BrowserSession(
        playwright=playwright,
        context=context,
        page=page,
    )

    if pin_to_desktop:
        await _move_to_launching_desktop(port=port)

    return session


async def _move_to_launching_desktop(*, port: int) -> None:
    """Move the browser window to the terminal's virtual desktop.

    Linux/X11 only. Requires xdotool and lsof. Silently does nothing
    if unavailable or on non-X11 systems.

    Uses the terminal's WINDOWID to determine the target desktop,
    and finds the Chrome PID via lsof on the CDP port.
    """
    try:
        window_id = os.environ.get("WINDOWID", "")
        if window_id:
            result = subprocess.run(
                ["xdotool", "get_desktop_for_window", window_id],
                capture_output=True, text=True,
            )
            desktop = result.stdout.strip()
        else:
            result = subprocess.run(
                ["xdotool", "get_desktop"],
                capture_output=True, text=True,
            )
            desktop = result.stdout.strip()

        if not desktop:
            return

        # Find Chrome PID from the CDP port
        result = subprocess.run(
            ["lsof", f"-ti:{port}", "-sTCP:LISTEN"],
            capture_output=True, text=True,
        )
        pid = result.stdout.strip().split("\n")[0].strip()
        if not pid:
            return

        # Poll for the browser window, move it immediately
        for _ in range(80):
            result = subprocess.run(
                ["xdotool", "search", "--pid", pid],
                capture_output=True, text=True,
            )
            for wid in result.stdout.strip().split("\n"):
                wid = wid.strip()
                if not wid:
                    continue
                wid_desktop = subprocess.run(
                    ["xdotool", "get_desktop_for_window", wid],
                    capture_output=True, text=True,
                ).stdout.strip()
                if wid_desktop != "-1" and wid_desktop != "":
                    if wid_desktop != desktop:
                        subprocess.run(
                            ["xdotool", "set_desktop_for_window", wid, desktop],
                        )
                        logger.info("Moved browser window to desktop %s", desktop)
                    else:
                        logger.info("Browser window already on desktop %s", desktop)
                    return
            await asyncio.sleep(0.03)

        logger.debug("Browser window did not appear within polling timeout")
    except FileNotFoundError:
        logger.debug("xdotool not available -- skipping desktop move")
    except Exception as e:
        logger.debug("Could not move browser to desktop: %s", e)
