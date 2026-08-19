"""Page operations built on the one-shot CDP channel.

These are convenience verbs -- `eval`, `screenshot`, `wait` -- over the same
primitives the raw `chrome-agent <instance> Domain.method` form exposes. They
exist because three things an agent does constantly are painful to express as
a single raw command:

  * `Runtime.evaluate` requires JavaScript nested inside a JSON string nested
    inside a shell argument, so any non-trivial expression dies of quoting.
  * `Page.captureScreenshot` returns base64 that has to be decoded by hand.
  * Waiting for an event otherwise means a fixed `sleep`, which is exactly
    what this tool's guidance tells agents not to do.

Nothing here gates the protocol: every verb is a thin wrapper, and the raw
form still reaches any method, including ones these wrappers never mention.
"""

import asyncio
import base64
import json
import os
from contextlib import asynccontextmanager

from .cdp_client import CDPClient, get_ws_url
from .errors import CDPError, NoPageError
from . import registry
from .registry import InstanceNotFoundError


class NoLiveInstanceError(Exception):
    """No live instance to auto-select."""


class AmbiguousInstanceError(Exception):
    """More than one live instance and no name given."""

    def __init__(self, names: list[str]):
        self.names = names
        super().__init__(
            "multiple instances running. Specify one: " + ", ".join(names)
        )


class EvaluationError(Exception):
    """The page threw while evaluating the expression."""


class NavigationError(Exception):
    """Chrome refused the navigation (bad scheme, DNS failure, blocked)."""


def resolve_port(
    instance_name: str | None = None,
    registry_path: str | None = None,
) -> int:
    """Resolve an instance name (or the single live instance) to a CDP port.

    Raises InstanceNotFoundError, NoLiveInstanceError, or
    AmbiguousInstanceError.
    """
    # Resolved through the module, not a from-import, so a caller (or test)
    # that swaps the registry's functions is honored here too.
    if instance_name is not None:
        return registry.lookup(
            instance_name=instance_name, registry_path=registry_path
        ).port

    live = [
        i for i in registry.enumerate_instances(registry_path=registry_path) if i.alive
    ]
    if not live:
        raise NoLiveInstanceError(
            "no instances registered. Launch one with: chrome-agent launch"
        )
    if len(live) > 1:
        raise AmbiguousInstanceError(names=[i.name for i in live])
    return live[0].port


def target_selector(
    target_spec: str | None,
    url_spec: str | None,
) -> tuple[str | None, str | None]:
    """Map the --target/--url flags onto resolve_target's (spec, target_by)."""
    if target_spec is not None:
        return target_spec, ("index" if target_spec.isdigit() else "id")
    if url_spec is not None:
        return url_spec, "url"
    return None, None


@asynccontextmanager
async def attached_page_session(
    port: int,
    target_spec: str | None = None,
    url_spec: str | None = None,
):
    """Yield (client, session_id) for an isolated session on one page target.

    Connects to the browser-level endpoint, resolves the page target, and
    attaches a flattened session -- the same sequence one-shot commands use,
    so every caller gets identical target-selection and isolation semantics.
    The session is always detached on exit.
    """
    from .attach import resolve_target

    browser_ws_url = get_ws_url(port=port, target_type="browser")
    async with CDPClient(ws_url=browser_ws_url) as cdp:
        targets_result = await cdp.send(method="Target.getTargets")
        page_targets = sorted(
            (t for t in targets_result.get("targetInfos", [])
             if t.get("type") == "page"),
            key=lambda t: t.get("targetId", ""),
        )
        if not page_targets:
            raise NoPageError("No page targets in browser")

        spec, target_by = target_selector(target_spec=target_spec, url_spec=url_spec)
        target_id = resolve_target(
            page_targets=page_targets,
            target_spec=spec,
            target_by=target_by,
        )

        result = await cdp.send(
            method="Target.attachToTarget",
            params={"targetId": target_id, "flatten": True},
        )
        session_id = result["sessionId"]

        try:
            yield cdp, session_id
        finally:
            try:
                await cdp.send(
                    method="Target.detachFromTarget",
                    params={"sessionId": session_id},
                )
            except Exception:
                pass  # Session may already be gone with its target


async def run_eval(
    expression: str,
    port: int,
    target_spec: str | None = None,
    url_spec: str | None = None,
    raw_json: bool = False,
) -> str:
    """Evaluate JavaScript in the page and return it rendered for stdout.

    Promises are awaited. By default the returned value is unwrapped -- a
    string prints as itself, anything else as indented JSON -- because the
    caller almost never wants the CDP envelope. raw_json returns the full
    Runtime.evaluate response instead.

    Raises EvaluationError if the page threw.
    """
    async with attached_page_session(
        port=port, target_spec=target_spec, url_spec=url_spec
    ) as (cdp, session_id):
        response = await cdp.send(
            method="Runtime.evaluate",
            params={
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True,
            },
            session_id=session_id,
        )

    details = response.get("exceptionDetails")
    if details:
        raise EvaluationError(_format_exception(details=details))

    if raw_json:
        return json.dumps(response, indent=2)

    remote = response.get("result", {})
    if "value" not in remote:
        # undefined, or an object CDP declined to serialize by value.
        return remote.get("description") or remote.get("type", "undefined")

    value = remote["value"]
    return value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False)


def _format_exception(details: dict) -> str:
    """Render Runtime.exceptionDetails as a single readable line."""
    exception = details.get("exception") or {}
    text = (
        exception.get("description")
        or exception.get("value")
        or details.get("text")
        or "evaluation failed"
    )
    line = details.get("lineNumber")
    if line is not None:
        return f"{text} (line {line + 1})"
    return str(text)


async def run_screenshot(
    port: int,
    output_path: str,
    image_format: str = "png",
    quality: int | None = None,
    full_page: bool = False,
    selector: str | None = None,
    target_spec: str | None = None,
    url_spec: str | None = None,
) -> tuple[str, int]:
    """Capture the page to a file. Returns (absolute path, bytes written).

    full_page captures the whole scrollable content rather than the viewport.
    selector captures just the first element matching a CSS selector, scrolled
    into view first. The two are mutually exclusive at the CLI layer.

    Raises EvaluationError if selector matches nothing.
    """
    params: dict = {"format": image_format}
    if quality is not None and image_format == "jpeg":
        params["quality"] = quality

    async with attached_page_session(
        port=port, target_spec=target_spec, url_spec=url_spec
    ) as (cdp, session_id):
        if selector is not None:
            clip = await _selector_clip(
                cdp=cdp, session_id=session_id, selector=selector
            )
            params["clip"] = clip
            params["captureBeyondViewport"] = True
        elif full_page:
            metrics = await cdp.send(
                method="Page.getLayoutMetrics", session_id=session_id
            )
            content = metrics.get("cssContentSize") or metrics.get("contentSize", {})
            params["clip"] = {
                "x": 0,
                "y": 0,
                "width": content.get("width", 0),
                "height": content.get("height", 0),
                "scale": 1,
            }
            params["captureBeyondViewport"] = True

        response = await cdp.send(
            method="Page.captureScreenshot",
            params=params,
            session_id=session_id,
        )

    data = base64.b64decode(response["data"])
    path = os.path.abspath(output_path)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(data)
    return path, len(data)


async def _selector_clip(cdp: CDPClient, session_id: str, selector: str) -> dict:
    """Return a capture clip for the first element matching selector."""
    expression = (
        "(() => {"
        f"  const el = document.querySelector({json.dumps(selector)});"
        "  if (!el) return null;"
        "  el.scrollIntoView({block: 'center', inline: 'center'});"
        "  const r = el.getBoundingClientRect();"
        "  return {x: r.x + window.scrollX, y: r.y + window.scrollY,"
        "          width: r.width, height: r.height};"
        "})()"
    )
    response = await cdp.send(
        method="Runtime.evaluate",
        params={"expression": expression, "returnByValue": True},
        session_id=session_id,
    )
    if response.get("exceptionDetails"):
        raise EvaluationError(_format_exception(details=response["exceptionDetails"]))

    box = response.get("result", {}).get("value")
    if not box:
        raise EvaluationError(f"no element matches selector: {selector}")
    if not box["width"] or not box["height"]:
        raise EvaluationError(f"element has zero size: {selector}")

    return {
        "x": box["x"],
        "y": box["y"],
        "width": box["width"],
        "height": box["height"],
        "scale": 1,
    }


async def run_wait(
    events: list[str],
    port: int,
    timeout: float = 30.0,
    contains: list[str] | None = None,
    target_spec: str | None = None,
    url_spec: str | None = None,
) -> dict | None:
    """Block until one of the named CDP events fires. Returns it, or None.

    Only events that fire *after* the subscription is live can match: this
    opens its own session, so anything that already happened is gone. To catch
    an event that may fire before the wait begins, background `attach` to a
    file first and match against that (scripts/cdp-wait.py).

    contains narrows a match to events whose JSON holds every given substring.
    """
    matched: asyncio.Queue = asyncio.Queue(maxsize=1)
    needles = contains or []

    def _handler(event_name: str):
        def callback(params):
            if matched.full():
                return
            event = {"method": event_name, "params": params}
            if needles:
                blob = json.dumps(event)
                if not all(needle in blob for needle in needles):
                    return
            try:
                matched.put_nowait(event)
            except asyncio.QueueFull:
                pass
        return callback

    async with attached_page_session(
        port=port, target_spec=target_spec, url_spec=url_spec
    ) as (cdp, session_id):
        enabled: set[str] = set()
        for event_name in events:
            domain = event_name.split(".")[0]
            if domain not in enabled:
                try:
                    await cdp.send(method=f"{domain}.enable", session_id=session_id)
                except CDPError:
                    pass  # Not every domain has an enable
                enabled.add(domain)
            cdp.on(
                event=event_name,
                callback=_handler(event_name=event_name),
                session_id=session_id,
            )

        try:
            return await asyncio.wait_for(matched.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None


async def run_navigate(
    url: str,
    port: int,
    wait_for: str = "load",
    timeout: float = 30.0,
    target_spec: str | None = None,
    url_spec: str | None = None,
) -> dict:
    """Navigate a page and report what actually happened.

    Raw `Page.navigate` returns as soon as the navigation is *committed*, and
    its result carries no HTTP status -- so a 404 and a 200 are indistinguishable
    without a second round trip, and any following command races the load. This
    waits for the document to finish (wait_for: "load", "domcontentloaded", or
    "none") and reports the main document's status code.

    Returns {"url", "status", "frameId", "loaderId", "loaded", "elapsedMs"};
    "loaded" is null when wait_for is "none".
    Raises NavigationError if Chrome refused the navigation outright.
    """
    loop = asyncio.get_running_loop()
    started = loop.time()

    async with attached_page_session(
        port=port, target_spec=target_spec, url_spec=url_spec
    ) as (cdp, session_id):
        await cdp.send(method="Page.enable", session_id=session_id)
        await cdp.send(method="Network.enable", session_id=session_id)

        statuses: dict[str, dict] = {}
        finished = asyncio.Event()

        def on_response(params):
            if params.get("type") == "Document":
                loader_id = params.get("loaderId")
                if loader_id:
                    statuses[loader_id] = params.get("response", {})

        def on_finished(params):
            finished.set()

        cdp.on(event="Network.responseReceived", callback=on_response, session_id=session_id)
        if wait_for == "domcontentloaded":
            cdp.on(
                event="Page.domContentEventFired",
                callback=on_finished,
                session_id=session_id,
            )
        elif wait_for == "load":
            cdp.on(
                event="Page.loadEventFired", callback=on_finished, session_id=session_id
            )

        result = await cdp.send(
            method="Page.navigate", params={"url": url}, session_id=session_id
        )
        if result.get("errorText"):
            raise NavigationError(f"{result['errorText']} ({url})")

        # None, not True: with wait_for="none" nothing was waited on, and
        # claiming the document loaded would be a fact this never checked.
        loaded = None
        if wait_for != "none":
            loaded = True
            try:
                await asyncio.wait_for(finished.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                loaded = False

        loader_id = result.get("loaderId")
        response = statuses.get(loader_id, {})

        return {
            "url": response.get("url", url),
            "status": response.get("status"),
            "frameId": result.get("frameId"),
            "loaderId": loader_id,
            "loaded": loaded,
            "elapsedMs": round((loop.time() - started) * 1000),
        }


__all__ = [
    "AmbiguousInstanceError",
    "EvaluationError",
    "InstanceNotFoundError",
    "NavigationError",
    "NoLiveInstanceError",
    "attached_page_session",
    "resolve_port",
    "run_eval",
    "run_navigate",
    "run_screenshot",
    "run_wait",
    "target_selector",
]
