"""Per-instance supervisor for chrome-agent.

A detached process spawned per headed launch that holds a browser-level CDP
connection open for the browser's lifetime. It does two jobs:

1. **Lifecycle** -- when the connection drops (the window/browser is closed,
   crashes, or is shut down), it removes the instance from the registry and
   deletes its session directory. This keeps the registry mirroring reality in
   real time: close the window and the instance disappears, no command needed.
   Because chrome-agent has no daemon, this long-lived connection is the only
   thing that can observe a close as it happens.

2. **Window border** (optional) -- while the browser is alive, mark every tab
   (current and future) with a colored border + corner badge and a title prefix
   so an agent-driven window is easy to tell apart from the user's own Chrome.
   ``Page.addScriptToEvaluateOnNewDocument`` re-runs the overlay on every new
   document, but only while the registering connection is alive -- hence the
   same long-lived process.

The border is page-observable (a host element in the DOM + a modified
``document.title``), so it is suppressed under a fingerprint profile; the
lifecycle job still runs. To minimize the footprint when drawn, the border
renders in a *closed* shadow DOM under a *randomized* host id, and the injected
code is a side-effect-free IIFE that leaks no globals.
See ``research/2026-06-16-detection-audit.md``.
"""

import asyncio
import hashlib
import json
import secrets
import subprocess
import sys

from .cdp_client import CDPClient, get_ws_url

ISOLATED_WORLD = "__chrome_agent_marker__"

# Curated palette of vivid, well-separated colors, each dark enough for white
# badge text. A fixed palette (vs. a continuous hue) avoids deceptively-similar
# colors for different instances -- two instances are either an obvious match
# or obviously different, never a near-match that reads as the same.
_PALETTE = (
    "#d11149",  # crimson
    "#c2185b",  # pink
    "#7b1fa2",  # purple
    "#512da8",  # deep purple
    "#303f9f",  # indigo
    "#1976d2",  # blue
    "#0277bd",  # light blue
    "#00838f",  # cyan
    "#00695c",  # teal
    "#2e7d32",  # green
    "#e65100",  # orange
    "#d84315",  # deep orange
    "#5d4037",  # brown
    "#455a64",  # blue grey
)


def derive_color(name: str) -> str:
    """Derive a stable, distinct palette color from an instance name.

    Deterministic (same name -> same color) so a given instance is always the
    same color, and chosen from a fixed well-separated palette so different
    instances are visually distinct from each other, not just from un-marked
    Chrome.
    """
    digest = int(hashlib.md5(name.encode()).hexdigest(), 16)
    return _PALETTE[digest % len(_PALETTE)]


def build_overlay_script(*, name: str, color: str, host_id: str) -> str:
    """Build the IIFE injected into each page to draw the marker.

    Draws a fixed, click-through colored border + corner badge inside a closed
    shadow DOM, and keeps ``document.title`` prefixed (re-applied idempotently
    on SPA/title changes). Re-draws if the page wipes it. Leaks no globals.
    """
    NAME = json.dumps(name)
    COLOR = json.dumps(color)
    HOST = json.dumps(host_id)
    return (
        "(() => {"
        f"  var NAME={NAME}, COLOR={COLOR}, HOST_ID={HOST};"
        "  var PREFIX = '\\uD83E\\uDD16 ' + NAME + ' \\u2014 ';"  # 🤖 NAME —
        "  function fixTitle(){ try { var t = document.title || ''; if (t.indexOf(PREFIX) !== 0) document.title = PREFIX + t; } catch(e){} }"
        "  function draw(){"
        "    try {"
        "      if (!document.documentElement) return false;"
        "      if (document.getElementById(HOST_ID)) return true;"
        "      var host = document.createElement('div');"
        "      host.id = HOST_ID;"
        "      host.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;z-index:2147483647;pointer-events:none;margin:0;padding:0;border:0;background:transparent';"
        "      var html = '<div style=\"position:fixed;top:0;left:0;right:0;bottom:0;border:6px solid ' + COLOR + ';box-sizing:border-box;pointer-events:none\"></div>'"
        "               + '<div style=\"position:fixed;top:0;left:0;background:' + COLOR + ';color:#fff;font:600 12px/1.45 system-ui,-apple-system,Segoe UI,sans-serif;padding:3px 9px;border-bottom-right-radius:6px;pointer-events:none;white-space:nowrap\">\\uD83E\\uDD16 ' + NAME + '</div>';"
        "      if (host.attachShadow) { host.attachShadow({mode:'closed'}).innerHTML = html; } else { host.innerHTML = html; }"
        "      document.documentElement.appendChild(host);"
        "      return true;"
        "    } catch(e){ return false; }"
        "  }"
        "  function ensureDraw(){ if (draw()) return; var mo = new MutationObserver(function(){ if (draw()) mo.disconnect(); }); mo.observe(document, {childList:true, subtree:true}); }"
        "  function watchTitle(){"
        "    fixTitle();"
        "    try {"
        "      var t = document.querySelector('title'); if (t) new MutationObserver(fixTitle).observe(t, {childList:true, characterData:true, subtree:true});"
        "      if (document.head) new MutationObserver(fixTitle).observe(document.head, {childList:true, subtree:true});"
        "      if (document.documentElement) new MutationObserver(function(){ if (!document.getElementById(HOST_ID)) draw(); }).observe(document.documentElement, {childList:true});"
        "    } catch(e){}"
        "  }"
        "  ensureDraw();"
        "  if (document.head || document.readyState !== 'loading') { watchTitle(); }"
        "  else { document.addEventListener('DOMContentLoaded', watchTitle); }"
        "})();"
    )


async def _setup_session(cdp: CDPClient, session_id: str, source: str) -> None:
    """Register the overlay on a page session: future docs + the current doc."""
    try:
        await cdp.send(method="Page.enable", session_id=session_id)
        # Future documents: re-run on every navigation, in an isolated world.
        await cdp.send(
            method="Page.addScriptToEvaluateOnNewDocument",
            params={"source": source, "worldName": ISOLATED_WORLD},
            session_id=session_id,
        )
        # The already-loaded document needs a one-time injection.
        await cdp.send(
            method="Runtime.evaluate",
            params={"expression": source},
            session_id=session_id,
        )
    except Exception:
        pass  # tab may close mid-setup; the guard keeps running for other tabs


async def _supervise_connection(
    *, port: int, draw_border: bool, source: str | None
) -> None:
    """Hold one browser-level CDP connection until it drops.

    Connects, and (when ``draw_border`` and ``source`` are set) installs the
    window border on every current and future page target, then blocks until the
    connection drops. Returns when disconnected; raises if the connect itself
    fails. Caller decides whether a drop means the browser closed (retire) or was
    a transient blip (reconnect).
    """
    browser_ws = get_ws_url(port=port, target_type="browser")
    cdp = CDPClient(ws_url=browser_ws)
    await cdp.connect()

    if draw_border and source is not None:
        loop = asyncio.get_event_loop()
        handled: set[str] = set()

        def on_attached(params: dict) -> None:
            info = params.get("targetInfo", {})
            session_id = params.get("sessionId")
            if info.get("type") != "page" or not session_id or session_id in handled:
                return
            handled.add(session_id)
            loop.create_task(_setup_session(cdp, session_id, source))

        cdp.on(event="Target.attachedToTarget", callback=on_attached)

        # autoAttach with flatten attaches to all current AND future page targets,
        # firing Target.attachedToTarget (with a sessionId) for each.
        await cdp.send(
            method="Target.setAutoAttach",
            params={"autoAttach": True, "waitForDebuggerOnStart": False, "flatten": True},
        )

    try:
        while cdp._connected:
            await asyncio.sleep(1)
    finally:
        await cdp.close()


# Seconds to wait for a dropped browser's CDP port to stop listening before
# concluding it really closed. A browser that is genuinely closing drops its
# listener within a moment; a live one whose WebSocket merely dropped (host
# suspend/resume, transient blip) keeps the port up across this window.
_RETIRE_GRACE_SECONDS = 5.0


async def _browser_gone(port: int) -> bool:
    """Whether the browser is truly gone, vs. a transient CDP drop.

    Polls the CDP port for up to ``_RETIRE_GRACE_SECONDS``. Returns True as soon
    as the port stops listening (the browser closed), or False if it stays up
    for the whole window (the drop was transient -- e.g. a host suspend/resume
    severed the WebSocket while Chrome kept running and listening).
    """
    from .registry import _port_is_listening

    deadline = asyncio.get_event_loop().time() + _RETIRE_GRACE_SECONDS
    while asyncio.get_event_loop().time() < deadline:
        if not _port_is_listening(port):
            return True
        await asyncio.sleep(0.2)
    return False


async def run_supervisor(
    *, port: int, name: str, registry_path: str | None = None, draw_border: bool = True
) -> None:
    """Supervise a launched browser until it actually closes.

    Holds a browser-level CDP connection. While alive and ``draw_border`` is set,
    marks every page target with the window border. The instance is retired from
    the registry (and its session directory removed) ONLY when the browser is
    truly gone -- detected by its CDP port no longer listening.

    A dropped CDP connection is NOT taken as proof the browser closed: a host
    suspend/resume (or any transient network blip) severs the long-lived
    WebSocket while Chrome keeps running and listening on its CDP port. Retiring
    on the dropped socket alone orphaned live instances from the registry across
    a suspend. Instead, when the connection drops we consult the port via
    ``_browser_gone`` -- the same signal ``_instance_is_alive`` trusts -- and
    reconnect-and-resume if the browser is still up, retiring only once it is gone.
    """
    from .registry import deregister

    # Compute the border host id / script ONCE so reconnects reuse the same
    # randomized host id and the overlay's idempotent guard suppresses redraws.
    source: str | None = None
    if draw_border:
        host_id = "_ca" + secrets.token_hex(8)
        source = build_overlay_script(name=name, color=derive_color(name), host_id=host_id)

    while True:
        try:
            await _supervise_connection(port=port, draw_border=draw_border, source=source)
        except Exception:
            # A failed (re)connect or a mid-stream CDP error lands here; fall
            # through to the liveness check to decide retire-vs-reconnect.
            pass

        if await _browser_gone(port):
            # Browser really closed -> retire from the registry and exit.
            deregister(instance_name=name, registry_path=registry_path)
            return

        # Transient drop -- the browser is still alive. Reconnect and resume
        # supervising (re-installs the border on the live tabs) rather than
        # orphaning a live instance.
        await asyncio.sleep(0.5)


def spawn_supervisor(
    *, port: int, name: str, registry_path: str, draw_border: bool
) -> subprocess.Popen:
    """Spawn the detached per-instance supervisor process for a launched browser."""
    return subprocess.Popen(
        [
            sys.executable, "-m", "chrome_agent.supervisor",
            str(port), name, registry_path, "1" if draw_border else "0",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> None:
    """Entry point: `python -m chrome_agent.supervisor PORT NAME REGISTRY_PATH DRAW_BORDER`."""
    if len(sys.argv) < 5:
        print("usage: python -m chrome_agent.supervisor PORT NAME REGISTRY_PATH DRAW_BORDER", file=sys.stderr)
        sys.exit(2)
    port = int(sys.argv[1])
    name = sys.argv[2]
    registry_path = sys.argv[3]
    draw_border = sys.argv[4] == "1"
    try:
        asyncio.run(run_supervisor(
            port=port, name=name, registry_path=registry_path, draw_border=draw_border,
        ))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
