"""Session REPL: persistent WebSocket CDP connection reading commands from stdin.

Protocol:
  - Each input line is: Domain.method {"param": "value"}
    (method name, space, optional JSON params)
  - Each response is a JSON line on stdout.
  - Lines starting with + subscribe to an event (e.g. +Page.loadEventFired).
  - Event notifications are printed prefixed with ! so they're distinguishable.
  - EOF on stdin triggers graceful disconnect.
"""

import asyncio
import json
import sys
import urllib.request

import websockets


class CDPSession:
    """Minimal CDP client that multiplexes commands and event subscriptions."""

    def __init__(self, ws_url: str):
        self._ws_url = ws_url
        self._ws = None
        self._msg_id = 0
        self._pending: dict[int, asyncio.Future] = {}
        self._subscriptions: set[str] = set()
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._recv_task = None

    async def connect(self):
        self._ws = await websockets.connect(
            self._ws_url,
            max_size=50 * 1024 * 1024,
        )
        self._recv_task = asyncio.create_task(self._recv_loop())

    async def send(self, method: str, params: dict | None = None) -> dict:
        self._msg_id += 1
        msg_id = self._msg_id
        msg = {"id": msg_id, "method": method}
        if params:
            msg["params"] = params

        future = asyncio.get_event_loop().create_future()
        self._pending[msg_id] = future
        await self._ws.send(json.dumps(msg))
        return await future

    def subscribe(self, event: str):
        self._subscriptions.add(event)

    async def _recv_loop(self):
        try:
            async for raw in self._ws:
                msg = json.loads(raw)
                if "id" in msg and msg["id"] in self._pending:
                    self._pending.pop(msg["id"]).set_result(msg)
                elif "method" in msg and msg["method"] in self._subscriptions:
                    await self._event_queue.put(msg)
        except websockets.exceptions.ConnectionClosed:
            pass

    async def close(self):
        if self._ws:
            await self._ws.close()
        if self._recv_task:
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass


def get_page_ws_url(port: int = 9222) -> str:
    """Get WebSocket URL for the first page target."""
    req = urllib.request.Request(f"http://localhost:{port}/json")
    with urllib.request.urlopen(req, timeout=5) as resp:
        targets = json.loads(resp.read())
        for t in targets:
            if t.get("type") == "page":
                return t["webSocketDebuggerUrl"]
        raise RuntimeError("No page targets found")


def _emit(obj: dict):
    """Write a JSON line to stdout and flush."""
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


async def _drain_events(session: CDPSession):
    """Drain any queued events and emit them."""
    while not session._event_queue.empty():
        evt = session._event_queue.get_nowait()
        _emit({"event": evt["method"], "params": evt.get("params", {})})


async def main():
    ws_url = get_page_ws_url()
    session = CDPSession(ws_url=ws_url)
    await session.connect()

    # Enable common domains
    for domain in ("Page", "DOM", "Runtime"):
        await session.send(f"{domain}.enable")

    # Signal readiness
    _emit({"status": "ready"})

    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    try:
        while True:
            line_bytes = await reader.readline()
            if not line_bytes:
                break  # EOF
            line = line_bytes.decode().strip()
            if not line:
                continue

            # Drain any pending events before processing command
            await _drain_events(session=session)

            if line.startswith("+"):
                # Subscribe to event
                event_name = line[1:].strip()
                session.subscribe(event=event_name)
                _emit({"subscribed": event_name})
                continue

            # Parse: "Domain.method {json params}" or just "Domain.method"
            parts = line.split(" ", 1)
            method = parts[0]
            params = None
            if len(parts) > 1:
                try:
                    params = json.loads(parts[1])
                except json.JSONDecodeError as exc:
                    _emit({"error": f"Bad JSON params: {exc}"})
                    continue

            try:
                result = await asyncio.wait_for(
                    session.send(method=method, params=params),
                    timeout=30.0,
                )
                _emit(result)
            except asyncio.TimeoutError:
                _emit({"error": f"Timeout waiting for response to {method}"})
            except Exception as exc:
                _emit({"error": str(exc)})

            # Drain events that arrived during command execution
            await _drain_events(session=session)

    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
