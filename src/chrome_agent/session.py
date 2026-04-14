"""Persistent CDP session bridging stdin/stdout to WebSocket.

Reads CDP commands from stdin, forwards them to Chrome via CDPClient,
and writes responses and events to stdout as single JSON lines.
Designed for integration with Claude Code's Monitor tool.

All stdout output is unbuffered and one-line-per-message.
"""

import asyncio
import json
import re
import signal
import sys

from .cdp_client import CDPClient, get_ws_url
from .errors import CDPError

# Matches valid CDP method format: Domain.method
_METHOD_RE = re.compile(r"^[A-Z][a-zA-Z0-9]*\.[a-zA-Z]+$")


def _emit(obj: dict, writer: asyncio.StreamWriter | None = None) -> None:
    """Write a JSON line to stdout (or the provided writer) and flush."""
    line = json.dumps(obj, separators=(",", ":")) + "\n"
    if writer is not None:
        writer.write(line.encode())
    else:
        sys.stdout.write(line)
        sys.stdout.flush()


async def _flush_writer(writer: asyncio.StreamWriter | None) -> None:
    """Flush the writer if it's an asyncio StreamWriter."""
    if writer is not None:
        await writer.drain()


async def run_session(
    port: int = 9222,
    target: str | None = None,
    input_stream: asyncio.StreamReader | None = None,
    output_stream: asyncio.StreamWriter | None = None,
) -> int:
    """Run a persistent CDP session bridging stdin/stdout to WebSocket.

    Reads commands from input_stream (defaults to stdin),
    writes responses and events to output_stream (defaults to stdout).

    Returns exit code: 0 for clean shutdown, 1 for error.
    """
    # Phase 1: Connect
    try:
        ws_url = get_ws_url(port=port, target_type="page")
    except (ConnectionError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    cdp = CDPClient(ws_url=ws_url)
    try:
        await cdp.connect()
    except Exception as exc:
        print(f"Failed to connect: {exc}", file=sys.stderr)
        return 1

    # Phase 2: Signal readiness
    _emit({"ready": True, "ws_url": ws_url}, writer=output_stream)
    await _flush_writer(writer=output_stream)

    # Phase 3: Event forwarding
    subscribed_events: set[str] = set()
    enabled_domains: set[str] = set()
    event_callbacks: dict[str, object] = {}  # event_name -> callback for off()
    session_msg_id = 0

    def make_event_forwarder(event_name: str):
        """Create a callback that forwards CDP events to stdout."""
        def forward(params: dict) -> None:
            if event_name in subscribed_events:
                _emit({"method": event_name, "params": params}, writer=output_stream)
                # Note: can't await drain here (sync callback), but line-buffered output
                # is sufficient for Monitor tool integration
        return forward

    # Phase 4: Signal handling
    shutdown_requested = False

    def request_shutdown():
        nonlocal shutdown_requested
        shutdown_requested = True

    loop = asyncio.get_event_loop()
    try:
        loop.add_signal_handler(signal.SIGTERM, request_shutdown)
    except (NotImplementedError, OSError):
        pass  # Windows or non-main thread

    # Phase 5: Disconnection detection
    disconnected = False
    original_recv_loop_done = False

    # We detect disconnection by checking cdp._connected after send failures
    # The CDPClient's recv_loop already handles setting _connected = False

    # Phase 6: Set up stdin reader
    if input_stream is None:
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    else:
        reader = input_stream

    exit_code = 0

    try:
        while True:
            if shutdown_requested:
                break

            # Read a line with a short timeout so we can check shutdown flag
            try:
                line_bytes = await asyncio.wait_for(reader.readline(), timeout=0.5)
            except asyncio.TimeoutError:
                # Check if CDP connection is still alive
                if not cdp._connected:
                    print("WebSocket disconnected", file=sys.stderr)
                    exit_code = 1
                    break
                continue

            if not line_bytes:
                # EOF -- clean shutdown
                break

            line = line_bytes.decode().strip()
            if not line:
                continue

            if line.startswith("+"):
                # Subscribe to event
                event_name = line[1:].strip()
                if event_name not in subscribed_events:
                    # Enable the domain if not already enabled
                    domain = event_name.split(".")[0]
                    if domain not in enabled_domains:
                        try:
                            await cdp.send(method=f"{domain}.enable")
                            enabled_domains.add(domain)
                        except CDPError:
                            pass  # some domains don't have an enable command
                        except ConnectionError:
                            print("WebSocket disconnected", file=sys.stderr)
                            exit_code = 1
                            break

                    callback = make_event_forwarder(event_name=event_name)
                    event_callbacks[event_name] = callback
                    cdp.on(event=event_name, callback=callback)
                    subscribed_events.add(event_name)

            elif line.startswith("-"):
                # Unsubscribe from event
                event_name = line[1:].strip()
                if event_name in subscribed_events:
                    subscribed_events.discard(event_name)
                    callback = event_callbacks.pop(event_name, None)
                    if callback is not None:
                        cdp.off(event=event_name, callback=callback)

            else:
                # Parse as CDP command
                parts = line.split(" ", 1)
                method = parts[0]
                params = None

                if len(parts) > 1:
                    try:
                        params = json.loads(parts[1])
                    except json.JSONDecodeError as exc:
                        _emit(
                            {"error": {"code": -1, "message": f"Invalid JSON: {exc}"}},
                            writer=output_stream,
                        )
                        await _flush_writer(writer=output_stream)
                        continue

                if not _METHOD_RE.match(method):
                    _emit(
                        {"error": {"code": -1, "message": f"Invalid method: {method}"}},
                        writer=output_stream,
                    )
                    await _flush_writer(writer=output_stream)
                    continue

                if params is not None and not isinstance(params, dict):
                    _emit(
                        {"error": {"code": -1, "message": "Parameters must be a JSON object"}},
                        writer=output_stream,
                    )
                    await _flush_writer(writer=output_stream)
                    continue

                session_msg_id += 1
                current_id = session_msg_id

                try:
                    result = await cdp.send(method=method, params=params)
                    _emit(
                        {"id": current_id, "result": result},
                        writer=output_stream,
                    )
                    await _flush_writer(writer=output_stream)
                except CDPError as exc:
                    _emit(
                        {"id": current_id, "error": {"code": exc.code, "message": exc.message}},
                        writer=output_stream,
                    )
                    await _flush_writer(writer=output_stream)
                except ConnectionError:
                    print("WebSocket disconnected", file=sys.stderr)
                    exit_code = 1
                    break

    finally:
        # Phase 7: Clean shutdown
        try:
            loop.remove_signal_handler(signal.SIGTERM)
        except (NotImplementedError, OSError):
            pass
        await cdp.close()

    return exit_code
