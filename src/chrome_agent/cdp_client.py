"""Async CDP client over WebSocket.

Provides direct Chrome DevTools Protocol access without Playwright.
Connects to Chrome's CDP WebSocket endpoint, sends commands with
message ID correlation, dispatches events to registered callbacks,
and supports CDP session multiplexing.
"""

import asyncio
import json
import logging
import urllib.request
from collections import defaultdict
from typing import Callable

import websockets

from .errors import CDPError

logger = logging.getLogger(__name__)

# 50 MB -- screenshots and screencast frames can be multi-megabyte base64
_MAX_MESSAGE_SIZE = 50 * 1024 * 1024


class CDPClient:
    """Async CDP client over WebSocket.

    Usage:
        async with CDPClient(ws_url="ws://localhost:9222/devtools/page/...") as cdp:
            result = await cdp.send(method="Page.navigate", params={"url": "https://example.com"})
            cdp.on(event="Page.loadEventFired", callback=my_handler)
    """

    def __init__(self, ws_url: str):
        self._ws_url = ws_url
        self._ws = None
        self._next_id = 0
        self._pending: dict[int, asyncio.Future] = {}
        self._event_handlers: dict[str, list[tuple[Callable[[dict], None], str | None]]] = defaultdict(list)
        self._recv_task: asyncio.Task | None = None
        self._connected = False

    async def connect(self) -> None:
        """Establish WebSocket connection and start receive loop."""
        self._ws = await websockets.connect(
            self._ws_url,
            max_size=_MAX_MESSAGE_SIZE,
        )
        self._connected = True
        self._recv_task = asyncio.create_task(self._recv_loop())
        logger.info("Connected to %s", self._ws_url)

    async def send(
        self,
        method: str,
        params: dict | None = None,
        session_id: str | None = None,
    ) -> dict:
        """Send a CDP command and await the response.

        Raises CDPError for protocol errors.
        Raises ConnectionError if not connected or connection lost.
        """
        if not self._connected:
            raise ConnectionError("Not connected to CDP WebSocket")

        self._next_id += 1
        msg_id = self._next_id
        message: dict = {"id": msg_id, "method": method}
        if params is not None:
            message["params"] = params
        if session_id is not None:
            message["sessionId"] = session_id

        future = asyncio.get_event_loop().create_future()
        self._pending[msg_id] = future

        try:
            await self._ws.send(json.dumps(message))
        except Exception as exc:
            self._pending.pop(msg_id, None)
            self._connected = False
            raise ConnectionError(f"Failed to send CDP command: {exc}") from exc

        return await future

    def on(
        self,
        event: str,
        callback: Callable[[dict], None],
        session_id: str | None = None,
    ) -> None:
        """Register a callback for a CDP event.

        If session_id is provided, the callback fires only for events
        from that session. If None, fires for all sessions.
        """
        self._event_handlers[event].append((callback, session_id))

    def off(self, event: str, callback: Callable[[dict], None]) -> None:
        """Remove a previously registered event callback.

        Silent no-op if the callback is not registered.
        """
        self._event_handlers[event] = [
            (cb, sid) for (cb, sid) in self._event_handlers[event]
            if cb is not callback
        ]

    async def close(self) -> None:
        """Close the WebSocket connection and clean up."""
        self._connected = False
        if self._ws:
            await self._ws.close()
        if self._recv_task:
            try:
                await self._recv_task
            except Exception:
                pass
        logger.info("Disconnected from %s", self._ws_url)

    async def __aenter__(self) -> "CDPClient":
        await self.connect()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()

    async def _recv_loop(self) -> None:
        """Background loop that receives and dispatches WebSocket messages."""
        try:
            async for raw in self._ws:
                msg = json.loads(raw)

                if "id" in msg and msg["id"] in self._pending:
                    future = self._pending.pop(msg["id"])
                    if "error" in msg:
                        err = msg["error"]
                        future.set_exception(
                            CDPError(code=err.get("code", -1), message=err.get("message", "Unknown CDP error"))
                        )
                    else:
                        future.set_result(msg.get("result", {}))

                elif "method" in msg:
                    event_name = msg["method"]
                    event_params = msg.get("params", {})
                    event_session = msg.get("sessionId")
                    for callback, filter_session in self._event_handlers.get(event_name, []):
                        if filter_session is None or filter_session == event_session:
                            callback(event_params)

        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as exc:
            logger.error("Unexpected error in receive loop: %s", exc)

        # Connection lost or closed -- fail all pending futures
        self._connected = False
        for future in self._pending.values():
            if not future.done():
                future.set_exception(ConnectionError("WebSocket connection closed"))
        self._pending.clear()


def get_targets(port: int = 9222) -> list[dict]:
    """Query Chrome's /json endpoint for available targets.

    Returns a list of target dicts, each with 'type', 'url', 'title',
    'webSocketDebuggerUrl', etc.

    Uses stdlib urllib. Synchronous.
    Raises ConnectionError if no browser is listening on the port.
    """
    try:
        req = urllib.request.Request(f"http://localhost:{port}/json")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        raise ConnectionError(
            f"No browser listening on port {port}. "
            f"Start one with: chrome-agent launch"
        ) from exc


def get_ws_url(port: int = 9222, target_type: str = "page") -> str:
    """Get the WebSocket debugger URL for the first target of the given type.

    For target_type="browser", queries /json/version for the browser-level
    WebSocket URL. For any other type (default "page"), queries /json and
    finds the first target matching that type.

    Raises ConnectionError if no browser is listening on the port.
    Raises RuntimeError if no matching target is found.
    """
    if target_type == "browser":
        try:
            req = urllib.request.Request(f"http://localhost:{port}/json/version")
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read())
                return data["webSocketDebuggerUrl"]
        except Exception as exc:
            raise ConnectionError(
                f"No browser listening on port {port}. "
                f"Start one with: chrome-agent launch"
            ) from exc

    targets = get_targets(port=port)
    for target in targets:
        if target.get("type") == target_type:
            ws_url = target.get("webSocketDebuggerUrl")
            if ws_url:
                return ws_url
    raise RuntimeError(f"No '{target_type}' target found on port {port}")
