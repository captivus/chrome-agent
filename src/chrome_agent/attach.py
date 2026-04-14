"""Attach mode for chrome-agent.

Creates a persistent connection to a named browser instance for event
observation with isolated event subscriptions. This is the observation
channel in chrome-agent's two-channel interaction pattern.

Replaces CDP-02 (Session Mode).
"""

import asyncio
import json
import logging
import signal
import sys

from .cdp_client import CDPClient, get_ws_url
from .errors import CDPError, NoPageError
from .registry import InstanceNotFoundError, lookup

logger = logging.getLogger(__name__)


class AmbiguousTargetError(Exception):
    """Multiple page targets match the specifier."""
    def __init__(self, targets: list[dict]):
        self.targets = targets
        lines = [
            f"  [{i+1}] {t['targetId'][:8]}  {t['url'][:60]}  \"{t.get('title', '')}\""
            for i, t in enumerate(targets)
        ]
        listing = "\n".join(lines)
        super().__init__(f"Multiple page targets found. Specify one:\n{listing}")


class TargetNotFoundError(Exception):
    """No page target matches the specifier."""
    def __init__(self, message: str, targets: list[dict]):
        self.targets = targets
        lines = [
            f"  [{i+1}] {t['targetId'][:8]}  {t['url'][:60]}  \"{t.get('title', '')}\""
            for i, t in enumerate(targets)
        ]
        listing = "\n".join(lines)
        super().__init__(f"{message}\nAvailable targets:\n{listing}")


def resolve_target(
    page_targets: list[dict],
    target_spec: str | None,
    target_by: str | None,
) -> str:
    """Resolve a target specifier to a target ID.

    target_by: "id" (prefix match), "index" (1-based), or "url" (substring).
    Returns the targetId string.

    Raises AmbiguousTargetError or TargetNotFoundError.
    """
    if target_spec is None:
        if len(page_targets) == 1:
            return page_targets[0]["targetId"]
        else:
            raise AmbiguousTargetError(targets=page_targets)

    if target_by == "index":
        index = int(target_spec) - 1
        if 0 <= index < len(page_targets):
            return page_targets[index]["targetId"]
        raise TargetNotFoundError(
            message=f"Index {target_spec} out of range (1-{len(page_targets)})",
            targets=page_targets,
        )

    elif target_by == "id":
        matches = [t for t in page_targets if t["targetId"].startswith(target_spec)]
        if len(matches) == 1:
            return matches[0]["targetId"]
        elif len(matches) == 0:
            raise TargetNotFoundError(
                message=f"No target matching ID prefix '{target_spec}'",
                targets=page_targets,
            )
        else:
            raise AmbiguousTargetError(targets=matches)

    elif target_by == "url":
        matches = [t for t in page_targets if target_spec in t.get("url", "")]
        if len(matches) == 1:
            return matches[0]["targetId"]
        elif len(matches) == 0:
            raise TargetNotFoundError(
                message=f"No target matching URL '{target_spec}'",
                targets=page_targets,
            )
        else:
            raise AmbiguousTargetError(targets=matches)

    raise ValueError(f"Unknown target_by: {target_by}")


async def run_attach(
    instance_name: str,
    subscriptions: list[str] | None = None,
    target_spec: str | None = None,
    target_by: str | None = None,
    registry_path: str | None = None,
) -> None:
    """Run the attach session.

    Connects to the named browser instance, creates an isolated CDP
    session on the specified page target, subscribes to events, and
    streams them to stdout as JSON lines until EOF or SIGTERM.

    Raises InstanceNotFoundError if the instance name is not registered.
    Raises AmbiguousTargetError if multiple targets match.
    Raises TargetNotFoundError if no target matches.
    Raises NoPageError if no page targets exist.
    Raises ConnectionError if the browser is unreachable.
    """
    if subscriptions is None:
        subscriptions = []

    # Phase 1: Resolve instance to port
    info = lookup(instance_name=instance_name, registry_path=registry_path)
    port = info.port

    # Phase 2: Connect to browser-level WebSocket
    browser_ws_url = get_ws_url(port=port, target_type="browser")
    cdp = CDPClient(ws_url=browser_ws_url)
    await cdp.connect()

    try:
        # Phase 3: Resolve page target
        targets_result = await cdp.send(method="Target.getTargets")
        page_targets = [
            t for t in targets_result.get("targetInfos", [])
            if t.get("type") == "page"
        ]

        if not page_targets:
            raise NoPageError(f"No page targets in instance '{instance_name}'")

        target_id = resolve_target(
            page_targets=page_targets,
            target_spec=target_spec,
            target_by=target_by,
        )

        # Phase 4: Create isolated CDP session
        try:
            result = await cdp.send(
                method="Target.attachToTarget",
                params={"targetId": target_id, "flatten": True},
            )
        except (CDPError, Exception) as exc:
            raise TargetNotFoundError(
                message=f"Failed to attach to target {target_id[:16]}: {exc}",
                targets=page_targets,
            ) from exc

        session_id = result["sessionId"]

        # Phase 5: Set up event subscription tracking
        enabled_domains: set[str] = set()
        subscribed_events: set[str] = set()
        event_handlers: dict[str, object] = {}

        def _make_handler(event_name: str):
            """Create a handler that emits JSON to stdout."""
            def handler(params):
                line = json.dumps({"method": event_name, "params": params})
                print(line, flush=True)
            return handler

        async def _subscribe(event_name: str) -> None:
            """Subscribe to a single event, auto-enabling the domain."""
            domain = event_name.split(".")[0]
            if domain not in enabled_domains:
                try:
                    await cdp.send(
                        method=f"{domain}.enable",
                        session_id=session_id,
                    )
                except CDPError:
                    pass  # Some domains may not support enable
                enabled_domains.add(domain)
            subscribed_events.add(event_name)
            handler = _make_handler(event_name)
            event_handlers[event_name] = handler
            cdp.on(event=event_name, callback=handler, session_id=session_id)

        def _unsubscribe(event_name: str) -> None:
            """Unsubscribe from a single event."""
            subscribed_events.discard(event_name)
            handler = event_handlers.pop(event_name, None)
            if handler is not None:
                # CDPClient.off() takes (event, callback) -- no session_id
                cdp.off(event=event_name, callback=handler)

        # Phase 6: Subscribe to initial events
        for event_name in subscriptions:
            await _subscribe(event_name)

        # Phase 7: Signal readiness
        print(json.dumps({
            "status": "ready",
            "sessionId": session_id[:16],
            "target": target_id[:16],
        }), flush=True)

        # Phase 8: Run stdin loop and connection monitor concurrently
        shutdown_event = asyncio.Event()

        def _signal_handler(signum, frame):
            shutdown_event.set()

        signal.signal(signal.SIGTERM, _signal_handler)

        async def stdin_loop():
            loop = asyncio.get_event_loop()
            reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(reader)
            await loop.connect_read_pipe(lambda: protocol, sys.stdin)

            try:
                while not shutdown_event.is_set():
                    line_bytes = await reader.readline()
                    if not line_bytes:
                        break  # EOF
                    line = line_bytes.decode().strip()
                    if not line:
                        continue
                    if line.startswith("+"):
                        await _subscribe(line[1:])
                    elif line.startswith("-"):
                        _unsubscribe(line[1:])
                    else:
                        print(json.dumps({"warning": f"Unknown command: {line}"}), flush=True)
            except (EOFError, asyncio.CancelledError):
                pass

        async def monitor_connection():
            """Wait for the WebSocket connection to drop."""
            # Wait for the recv task to complete (more reliable than polling _connected)
            if cdp._recv_task is not None:
                try:
                    await cdp._recv_task
                except Exception:
                    pass
            print(json.dumps({"error": "Browser disconnected"}), flush=True)

        stdin_task = asyncio.create_task(stdin_loop())
        monitor_task = asyncio.create_task(monitor_connection())

        done, pending = await asyncio.wait(
            [stdin_task, monitor_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Phase 9: Clean shutdown
        try:
            await cdp.send(
                method="Target.detachFromTarget",
                params={"sessionId": session_id},
            )
        except (ConnectionError, Exception):
            pass

    finally:
        await cdp.close()
