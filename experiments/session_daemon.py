"""Session daemon: maintains a persistent CDP WebSocket connection.

CLI clients connect via UNIX socket, send a JSON command, get back the
CDP response, and disconnect. The daemon keeps the WebSocket open across
client connections, eliminating per-invocation connection overhead.

Also supports event subscriptions: a client sends
  {"subscribe": "Network.requestWillBeSent"}
and receives pushed events until it disconnects.

Usage:
  python session_daemon.py [--port 9222] [--socket /tmp/chrome-agent.sock]
"""

import argparse
import asyncio
import json
import os
import signal
import sys
import urllib.request

import websockets


SOCKET_PATH = "/tmp/chrome-agent.sock"


def get_page_ws_url(*, port: int = 9222) -> str:
    """Discover the first page target's WebSocket URL from Chrome."""
    req = urllib.request.Request(f"http://localhost:{port}/json")
    with urllib.request.urlopen(req, timeout=5) as resp:
        targets = json.loads(resp.read())
        for target in targets:
            if target.get("type") == "page":
                return target["webSocketDebuggerUrl"]
    raise RuntimeError(f"No page targets found on port {port}")


class SessionDaemon:
    """Keeps a CDP WebSocket open and multiplexes client requests over it."""

    def __init__(self, *, ws_url: str, socket_path: str):
        self._ws_url = ws_url
        self._socket_path = socket_path
        self._ws = None
        self._cdp_id = 0
        self._pending: dict[int, asyncio.Future] = {}
        self._event_subscribers: dict[str, list[asyncio.Queue]] = {}
        self._server = None

    async def start(self):
        """Connect to Chrome and start the UNIX socket server."""
        self._ws = await websockets.connect(
            self._ws_url,
            max_size=50 * 1024 * 1024,
        )
        asyncio.create_task(self._cdp_recv_loop())

        # Clean up stale socket file
        if os.path.exists(self._socket_path):
            os.unlink(self._socket_path)

        self._server = await asyncio.start_unix_server(
            self._handle_client,
            path=self._socket_path,
        )
        print(f"Daemon listening on {self._socket_path}", flush=True)
        print(f"CDP connected to {self._ws_url}", flush=True)

    async def _cdp_send(self, *, method: str, params: dict | None = None) -> dict:
        """Send a CDP command and wait for the response."""
        self._cdp_id += 1
        msg_id = self._cdp_id
        msg = {"id": msg_id, "method": method}
        if params:
            msg["params"] = params

        future = asyncio.get_event_loop().create_future()
        self._pending[msg_id] = future

        await self._ws.send(json.dumps(msg))
        return await future

    async def _cdp_recv_loop(self):
        """Read from the CDP WebSocket, dispatch responses and events."""
        try:
            async for raw in self._ws:
                msg = json.loads(raw)

                # CDP response to a command we sent
                if "id" in msg and msg["id"] in self._pending:
                    future = self._pending.pop(msg["id"])
                    if "error" in msg:
                        future.set_result({"error": msg["error"]})
                    else:
                        future.set_result(msg.get("result", {}))

                # CDP event
                elif "method" in msg:
                    event_method = msg["method"]
                    if event_method in self._event_subscribers:
                        event_data = {
                            "event": event_method,
                            "params": msg.get("params", {}),
                        }
                        for queue in self._event_subscribers[event_method]:
                            try:
                                queue.put_nowait(event_data)
                            except asyncio.QueueFull:
                                pass  # Drop events if client is slow
        except websockets.exceptions.ConnectionClosed:
            print("CDP WebSocket closed", file=sys.stderr, flush=True)

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ):
        """Handle a single client connection on the UNIX socket."""
        subscribed_queues: list[tuple[str, asyncio.Queue]] = []
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break

                try:
                    request = json.loads(line.decode())
                except json.JSONDecodeError as exc:
                    response = {"error": f"Invalid JSON: {exc}"}
                    writer.write(json.dumps(response).encode() + b"\n")
                    await writer.drain()
                    continue

                # Event subscription request
                if "subscribe" in request:
                    event_name = request["subscribe"]
                    queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
                    self._event_subscribers.setdefault(event_name, []).append(queue)
                    subscribed_queues.append((event_name, queue))

                    # Enable the CDP domain if needed (best-effort)
                    domain = event_name.split(".")[0]
                    try:
                        await self._cdp_send(method=f"{domain}.enable")
                    except Exception:
                        pass

                    writer.write(
                        json.dumps({"subscribed": event_name}).encode() + b"\n"
                    )
                    await writer.drain()

                    # Push events until the client disconnects
                    try:
                        while True:
                            event = await queue.get()
                            writer.write(json.dumps(event).encode() + b"\n")
                            await writer.drain()
                    except (ConnectionError, BrokenPipeError):
                        pass
                    break

                # Shutdown request
                elif request.get("method") == "__shutdown__":
                    writer.write(json.dumps({"ok": True}).encode() + b"\n")
                    await writer.drain()
                    writer.close()
                    await writer.wait_closed()
                    asyncio.get_event_loop().call_soon(self._shutdown)
                    return

                # Regular CDP command
                else:
                    method = request.get("method", "")
                    params = request.get("params")
                    try:
                        result = await self._cdp_send(
                            method=method, params=params
                        )
                        writer.write(json.dumps(result).encode() + b"\n")
                    except Exception as exc:
                        writer.write(
                            json.dumps({"error": str(exc)}).encode() + b"\n"
                        )
                    await writer.drain()

        except (ConnectionError, BrokenPipeError):
            pass
        finally:
            # Unsubscribe from events
            for event_name, queue in subscribed_queues:
                subscribers = self._event_subscribers.get(event_name, [])
                if queue in subscribers:
                    subscribers.remove(queue)

            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    def _shutdown(self):
        """Initiate graceful shutdown."""
        print("Shutting down...", flush=True)
        for task in asyncio.all_tasks():
            task.cancel()

    async def run_forever(self):
        """Run until cancelled."""
        await self.start()
        try:
            await asyncio.Future()  # Block forever
        except asyncio.CancelledError:
            pass
        finally:
            if self._ws:
                await self._ws.close()
            if self._server:
                self._server.close()
            if os.path.exists(self._socket_path):
                os.unlink(self._socket_path)


def main():
    parser = argparse.ArgumentParser(description="Chrome CDP session daemon")
    parser.add_argument(
        "--port", type=int, default=9222, help="Chrome CDP port (default: 9222)"
    )
    parser.add_argument(
        "--socket",
        default=SOCKET_PATH,
        help=f"UNIX socket path (default: {SOCKET_PATH})",
    )
    args = parser.parse_args()

    ws_url = get_page_ws_url(port=args.port)
    daemon = SessionDaemon(ws_url=ws_url, socket_path=args.socket)

    loop = asyncio.new_event_loop()

    def handle_signal():
        for task in asyncio.all_tasks(loop):
            task.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)

    try:
        loop.run_until_complete(daemon.run_forever())
    except asyncio.CancelledError:
        pass
    finally:
        loop.close()


if __name__ == "__main__":
    main()
