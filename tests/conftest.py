"""Test fixtures for chrome-agent.

Launches a real headless Chrome browser with CDP enabled for integration
tests. Uses the subprocess-based launcher (no Playwright dependency).
"""

import asyncio
import os
import signal
from pathlib import Path

import pytest

from chrome_agent.launcher import launch_browser

FIXTURE_PATH = Path(__file__).parent / "fixture.html"
CDP_PORT = 9333  # Use a non-default port to avoid conflicts


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async fixtures."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def browser_session(event_loop):
    """Launch a headless browser with CDP for the entire test session.

    Provides a browser running on CDP_PORT. Tests that need CDP access
    use CDPClient or get_ws_url directly -- no Playwright objects.
    """
    result = event_loop.run_until_complete(
        launch_browser(
            port_override=CDP_PORT,
            headless=True,
            pin_to_desktop=False,
        )
    )
    yield result
    # Teardown: kill the browser process
    try:
        os.kill(result.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass


@pytest.fixture(scope="session")
def fixture_url():
    """URL to the test fixture page."""
    return f"file://{FIXTURE_PATH.resolve()}"
