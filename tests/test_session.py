"""Tests for CDP-02: Session Mode.

Tests the run_session() function using injectable asyncio streams.
Runs against a real browser on port 9333 (session fixture).

The output collection uses a simple approach: a custom asyncio.Transport
that feeds data directly into a StreamReader, bypassing the need for OS
pipes or complex StreamWriter setups.
"""

import asyncio
import json

import pytest
import pytest_asyncio

from chrome_agent.session import run_session

CDP_PORT = 9333


class _CollectorTransport(asyncio.Transport):
    """Transport that feeds written data into a StreamReader."""

    def __init__(self, reader: asyncio.StreamReader):
        super().__init__()
        self._reader = reader

    def write(self, data: bytes) -> None:
        self._reader.feed_data(data)

    def is_closing(self) -> bool:
        return False

    def close(self) -> None:
        self._reader.feed_eof()

    def get_extra_info(self, name, default=None):
        return default


def _make_output_pair():
    """Create a (reader, writer) pair for collecting session output."""
    reader = asyncio.StreamReader(limit=2**20)
    transport = _CollectorTransport(reader=reader)
    # Protocol needs to exist but isn't used for writing
    protocol = asyncio.StreamReaderProtocol(asyncio.StreamReader())
    writer = asyncio.StreamWriter(
        transport=transport,
        protocol=protocol,
        reader=None,
        loop=asyncio.get_event_loop(),
    )
    return reader, writer


class SessionHarness:
    """Test harness that creates injectable streams for run_session."""

    def __init__(self):
        self.input_reader: asyncio.StreamReader | None = None
        self.output_reader: asyncio.StreamReader | None = None
        self._output_writer: asyncio.StreamWriter | None = None
        self._task: asyncio.Task | None = None

    async def start(self, port: int = CDP_PORT):
        """Start a session with injectable streams."""
        self.input_reader = asyncio.StreamReader()
        self.output_reader, self._output_writer = _make_output_pair()

        self._task = asyncio.create_task(
            run_session(
                port=port,
                input_stream=self.input_reader,
                output_stream=self._output_writer,
            )
        )
        # Yield control so the task can start
        await asyncio.sleep(0)

    def send_line(self, line: str):
        """Send a line to the session's stdin."""
        self.input_reader.feed_data((line + "\n").encode())

    def send_eof(self):
        """Close the session's stdin."""
        self.input_reader.feed_eof()

    async def read_line(self, timeout: float = 5.0) -> dict:
        """Read and parse a JSON line from the session's stdout."""
        raw = await asyncio.wait_for(
            self.output_reader.readline(),
            timeout=timeout,
        )
        if not raw:
            raise EOFError("Session output closed")
        return json.loads(raw.decode())

    async def read_lines(self, timeout: float = 3.0) -> list[dict]:
        """Read all available lines within a timeout."""
        lines = []
        deadline = asyncio.get_event_loop().time() + timeout
        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                break
            try:
                raw = await asyncio.wait_for(
                    self.output_reader.readline(),
                    timeout=remaining,
                )
                if not raw:
                    break
                lines.append(json.loads(raw.decode()))
            except asyncio.TimeoutError:
                break
        return lines

    async def wait(self, timeout: float = 10.0) -> int:
        """Wait for the session to exit and return the exit code."""
        return await asyncio.wait_for(self._task, timeout=timeout)

    async def cleanup(self):
        """Clean shutdown."""
        self.send_eof()
        try:
            await self.wait(timeout=5.0)
        except (asyncio.TimeoutError, Exception):
            if self._task and not self._task.done():
                self._task.cancel()
                try:
                    await self._task
                except (asyncio.CancelledError, Exception):
                    pass


@pytest_asyncio.fixture
async def session(browser_session):
    """Create and start a session harness."""
    harness = SessionHarness()
    await harness.start(port=CDP_PORT)
    ready = await harness.read_line()
    assert ready["ready"] is True
    yield harness
    await harness.cleanup()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_command_round_trip(session):
    """Send a command, get correct response."""
    session.send_line('Runtime.evaluate {"expression": "1+1", "returnByValue": true}')
    response = await session.read_line()
    assert "id" in response
    assert response["result"]["result"]["value"] == 2


@pytest.mark.asyncio
async def test_readiness_signal(browser_session):
    """First output line is the readiness signal."""
    harness = SessionHarness()
    await harness.start(port=CDP_PORT)
    first_line = await harness.read_line()
    assert first_line["ready"] is True
    assert "ws_url" in first_line
    await harness.cleanup()


@pytest.mark.asyncio
async def test_multi_command_sequence(session):
    """Five sequential commands produce five correct responses."""
    results = []
    for i in range(5):
        session.send_line(f'Runtime.evaluate {{"expression": "{i}", "returnByValue": true}}')
        response = await session.read_line()
        results.append(response)
    assert len(results) == 5
    assert results[0]["result"]["result"]["value"] == 0
    assert results[4]["result"]["result"]["value"] == 4


# ---------------------------------------------------------------------------
# Event subscription
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_subscription(session, fixture_url):
    """Subscribing to an event and triggering it produces the event on stdout."""
    # First verify the session works with a simple command
    session.send_line('Runtime.evaluate {"expression": "1", "returnByValue": true}')
    warmup = await session.read_line()
    assert warmup["result"]["result"]["value"] == 1

    # Subscribe to events
    session.send_line("+Page.loadEventFired")
    # Give time for subscribe to process (Page.enable round-trip)
    await asyncio.sleep(1.0)

    # Navigate using a local URL to avoid network dependency
    session.send_line(f'Page.navigate {{"url": "{fixture_url}"}}')
    # Collect output lines -- expect navigate response and event
    lines = []
    try:
        for _ in range(20):
            line = await session.read_line(timeout=5.0)
            lines.append(line)
            if line.get("method") == "Page.loadEventFired":
                break
    except (asyncio.TimeoutError, EOFError):
        pass
    has_event = any(line.get("method") == "Page.loadEventFired" for line in lines)
    has_response = any("id" in line for line in lines)
    assert has_response, f"No navigate response in: {lines}"
    assert has_event, f"No loadEventFired event in: {lines}"


@pytest.mark.asyncio
async def test_event_unsubscription(session):
    """Unsubscribing stops events from appearing."""
    session.send_line("+Page.loadEventFired")
    await asyncio.sleep(0.5)
    session.send_line('Page.navigate {"url": "https://example.com"}')
    await session.read_lines(timeout=3.0)  # drain

    session.send_line("-Page.loadEventFired")
    await asyncio.sleep(0.5)

    session.send_line('Page.navigate {"url": "https://example.org"}')
    lines = await session.read_lines(timeout=3.0)

    event_lines = [l for l in lines if l.get("method") == "Page.loadEventFired"]
    assert len(event_lines) == 0, f"Unexpected events after unsubscribe: {event_lines}"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_malformed_input(session):
    """Invalid method format produces error, session continues."""
    session.send_line("not a valid command")
    error_line = await session.read_line()
    assert "error" in error_line
    assert "Invalid" in error_line["error"]["message"]

    session.send_line('Runtime.evaluate {"expression": "1", "returnByValue": true}')
    ok_line = await session.read_line()
    assert ok_line["result"]["result"]["value"] == 1


@pytest.mark.asyncio
async def test_invalid_json_params(session):
    """Invalid JSON parameters produce error, session continues."""
    session.send_line("Page.navigate {invalid json}")
    error_line = await session.read_line()
    assert "error" in error_line
    assert "Invalid JSON" in error_line["error"]["message"]

    session.send_line('Runtime.evaluate {"expression": "2", "returnByValue": true}')
    ok_line = await session.read_line()
    assert ok_line["result"]["result"]["value"] == 2


@pytest.mark.asyncio
async def test_cdp_error(session):
    """CDP error from Chrome produces error response."""
    session.send_line('DOM.querySelector {"nodeId": 99999, "selector": "div"}')
    response = await session.read_line()
    assert "error" in response
    assert response["error"]["code"] is not None


# ---------------------------------------------------------------------------
# Shutdown
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clean_shutdown(browser_session):
    """Closing stdin produces clean exit with code 0."""
    harness = SessionHarness()
    await harness.start(port=CDP_PORT)
    await harness.read_line()  # readiness
    harness.send_eof()
    exit_code = await harness.wait()
    assert exit_code == 0
