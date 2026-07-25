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
import warnings

from .cdp_client import CDPClient, get_ws_url
from .errors import CDPError, NoPageError
from .registry import (
    InstanceInfo,
    InstanceNotFoundError,
    instance_is_alive,
    lookup,
    registration_status,
)

logger = logging.getLogger(__name__)

# How often the attach observer re-checks that its instance still exists and
# its browser is still alive, and how many consecutive adverse checks it
# requires before exiting. The strike window absorbs a transient CDP-port blip
# (host suspend/resume) or a torn registry read without killing a healthy
# observer; a genuine retire or a truly-dead browser persists across it.
# Module-level so tests can shrink them for a fast, faithful subprocess run.
_LIVENESS_POLL_SECONDS = 15.0
_LIVENESS_STRIKES = 2


def _liveness_verdict(info: InstanceInfo, registry_path: str | None) -> str | None:
    """Whether an attach observer should shut down, and why.

    Returns a human-readable reason string when the observer has outlived its
    purpose, or None when it should keep running. Two exit conditions:

    - The instance was retired from the registry (``registration_status`` is
      "retired" -- a genuine deregister, distinguished from a corrupt/empty
      read which reads as "unknown" and does NOT trigger exit). This is the
      orphan case that a dropped-socket check alone never catches: the browser
      can stay alive and listening while its registry entry is removed.
    - The browser is gone or is no longer ours (``instance_is_alive`` False):
      the port is dead, or has been reclaimed by a different instance. This
      catches a wedged half-open socket that the passive connection monitor
      never sees drop.

    Pure given its two registry calls, so every branch is unit-testable
    without a live browser.
    """
    if registration_status(info.name, registry_path=registry_path) == "retired":
        return "instance retired from registry"
    if not instance_is_alive(info):
        return "browser no longer running"
    return None


def _suppress_shutdown_noise() -> None:
    """Suppress asyncio and websockets noise during clean shutdown.

    When attach exits (EOF, SIGTERM, browser disconnect), the asyncio
    event loop and websockets library can produce warnings about
    unfinished tasks and connection closures. These are expected during
    shutdown and should not leak to stderr where they'd corrupt the
    JSONL event stream for consumers using `> file.jsonl`.
    """
    # Suppress asyncio "Task was destroyed but it is pending" warnings
    warnings.filterwarnings("ignore", message=".*was destroyed but.*", category=ResourceWarning)
    # Suppress websockets connection close noise
    logging.getLogger("websockets").setLevel(logging.CRITICAL)
    # Suppress asyncio debug noise
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)


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

    _suppress_shutdown_noise()

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
        page_targets = sorted(
            (t for t in targets_result.get("targetInfos", [])
             if t.get("type") == "page"),
            key=lambda t: t.get("targetId", ""),
        )

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

        # Phase 7: Install signal handlers, then signal readiness.
        # Handlers must be registered BEFORE the ready line: a supervisor
        # that reads "ready" and immediately sends SIGTERM must get the
        # graceful shutdown path, not the default disposition.
        #
        # Register via the event loop so the signal actually wakes it.
        # A plain signal.signal handler sets the event but nothing wakes
        # asyncio.wait, leaving the process unkillable by SIGTERM while
        # stdin is held open and the websocket is live (issue #1).
        # SIGINT gets the same treatment: its default (KeyboardInterrupt)
        # terminates but skips the clean detach and can spray a traceback
        # into a redirected event stream.
        shutdown_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, shutdown_event.set)
            except (NotImplementedError, OSError):
                # Windows or non-main thread -- fall back to the sync handler;
                # shutdown_task below still makes the event a wake source.
                signal.signal(sig, lambda signum, frame: shutdown_event.set())

        print(json.dumps({
            "status": "ready",
            "sessionId": session_id[:16],
            "target": target_id[:16],
        }), flush=True)

        # Phase 8: Run stdin loop and connection monitor concurrently

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

        async def liveness_loop():
            """Exit when the instance is retired or its browser is gone.

            The passive connection monitor only fires on a cleanly-dropped
            websocket, so an observer can outlive its purpose indefinitely --
            the browser deregistered out from under it, or a half-open socket
            that never signals a drop. This active poll bounds that lifetime.
            The blocking registry/port/proc work runs in the default executor
            so it never stalls the event loop that is streaming events.
            """
            loop = asyncio.get_running_loop()
            strikes = 0
            while not shutdown_event.is_set():
                await asyncio.sleep(_LIVENESS_POLL_SECONDS)
                reason = await loop.run_in_executor(
                    None, _liveness_verdict, info, registry_path
                )
                if reason is None:
                    strikes = 0
                    continue
                strikes += 1
                if strikes >= _LIVENESS_STRIKES:
                    print(json.dumps({"status": "shutdown", "reason": reason}), flush=True)
                    return

        async def monitor_connection():
            """Wait for the WebSocket connection to drop."""
            # Wait for the recv task to complete (more reliable than polling
            # _connected). Shielded: when this task is cancelled at shutdown,
            # the cancellation must not propagate into the client's recv task,
            # which cdp.close() still needs to await cleanly.
            if cdp._recv_task is not None:
                try:
                    await asyncio.shield(cdp._recv_task)
                except Exception:
                    pass
            print(json.dumps({"error": "Browser disconnected"}), flush=True)

        stdin_task = asyncio.create_task(stdin_loop())
        monitor_task = asyncio.create_task(monitor_connection())
        shutdown_task = asyncio.create_task(shutdown_event.wait())
        liveness_task = asyncio.create_task(liveness_loop())

        done, pending = await asyncio.wait(
            [stdin_task, monitor_task, shutdown_task, liveness_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass  # Swallow all shutdown exceptions

        # Phase 9: Clean shutdown. Bounded: cdp.send has no timeout of its
        # own, and an unbounded await here on a half-open connection would
        # make the process unkillable by SIGTERM again (issue #1).
        try:
            await asyncio.wait_for(
                cdp.send(
                    method="Target.detachFromTarget",
                    params={"sessionId": session_id},
                ),
                timeout=2.0,
            )
        except Exception:
            pass  # Connection may already be dead or unresponsive

    finally:
        try:
            await cdp.close()
        except Exception:
            pass  # Swallow websocket close noise
