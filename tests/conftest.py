"""Test fixtures for chrome-agent.

Launches a real browser with CDP enabled and provides connection
fixtures that go through the actual CDP code path.
"""

import asyncio
from pathlib import Path

import pytest

from chrome_agent.browser import launch_browser
from chrome_agent.connection import check_cdp_port, connect, disconnect

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
    """Launch a browser with CDP for the entire test session."""
    session = event_loop.run_until_complete(
        launch_browser(port=CDP_PORT, pin_to_desktop=True)
    )
    yield session
    event_loop.run_until_complete(session.browser.close())
    event_loop.run_until_complete(session.playwright.stop())


@pytest.fixture(scope="session")
def fixture_url():
    """URL to the test fixture page."""
    return f"file://{FIXTURE_PATH.resolve()}"


@pytest.fixture()
def cdp_connection(event_loop, browser_session, fixture_url):
    """Connect to the browser via CDP and navigate to the fixture.

    Each test gets a fresh CDP connection (matching real usage where
    every chrome-agent invocation is a separate connection).
    """
    pw, browser, page = event_loop.run_until_complete(
        connect(port=CDP_PORT)
    )
    # Navigate to fixture before each test
    event_loop.run_until_complete(page.goto(fixture_url))
    event_loop.run_until_complete(page.wait_for_load_state("load"))
    yield pw, browser, page
    event_loop.run_until_complete(disconnect(pw=pw))
