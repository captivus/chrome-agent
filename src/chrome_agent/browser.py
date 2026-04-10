"""Browser launcher with optional anti-detection fingerprinting.

Launches a Playwright Chromium browser with CDP enabled. Optionally
applies a fingerprint profile to make the browser appear as a real
desktop browser.
"""

import asyncio
import json
import logging
import os
import subprocess
from dataclasses import dataclass

from playwright.async_api import Browser, Page, Playwright, async_playwright

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
    """Handle to a launched browser session."""

    playwright: Playwright
    browser: Browser
    page: Page


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
    wm_class: str = "chrome-agent",
    pin_to_desktop: bool = True,
) -> BrowserSession:
    """Launch a Chromium browser with CDP enabled.

    Args:
        port: CDP remote debugging port.
        fingerprint: Optional fingerprint for anti-detection. If None,
            launches a clean browser with no spoofing.
        headless: Run in headless mode.
        wm_class: X11 window class name (for desktop pinning).
        pin_to_desktop: Move browser window to the launching terminal's
            virtual desktop. Default True. Linux/X11 only, requires
            xdotool -- silently skipped on other platforms.
    """
    playwright = await async_playwright().start()

    launch_args = [
        "--disable-blink-features=AutomationControlled",
        f"--remote-debugging-port={port}",
        f"--class={wm_class}",
    ]

    browser = await playwright.chromium.launch(
        headless=headless,
        args=launch_args,
    )

    # Build context options
    context_kwargs = {}
    if fingerprint:
        context_kwargs.update(
            user_agent=fingerprint.user_agent,
            viewport=fingerprint.viewport,
            locale=fingerprint.locale,
            timezone_id=fingerprint.timezone,
        )

    context = await browser.new_context(**context_kwargs)

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

    page = await context.new_page()

    session = BrowserSession(
        playwright=playwright,
        browser=browser,
        page=page,
    )

    if pin_to_desktop:
        await _move_to_launching_desktop(wm_class=wm_class)

    return session


async def _move_to_launching_desktop(*, wm_class: str) -> None:
    """Move the browser window to the terminal's virtual desktop.

    Linux/X11 only. Requires xdotool. Silently does nothing if
    xdotool is unavailable or on non-X11 systems.
    """
    try:
        # Determine which desktop our terminal is on
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

        # Wait for the browser window to appear
        await asyncio.sleep(0.5)

        # Find our browser windows by the custom WM_CLASS
        result = subprocess.run(
            ["xdotool", "search", "--class", wm_class],
            capture_output=True, text=True,
        )
        for wid in result.stdout.strip().split("\n"):
            if wid.strip():
                subprocess.run(
                    ["xdotool", "set_desktop_for_window", wid.strip(), desktop],
                )

        logger.info("Moved browser window(s) to desktop %s", desktop)
    except FileNotFoundError:
        logger.debug("xdotool not available -- skipping desktop move")
    except Exception as e:
        logger.debug("Could not move browser to desktop: %s", e)
