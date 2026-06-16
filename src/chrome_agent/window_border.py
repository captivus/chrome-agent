"""Window-border marker for chrome-agent.

Makes an agent-launched Chrome window visually distinct from the user's other
Chrome windows: a colored border + corner badge around every tab, plus a title
prefix so the window is identifiable in the taskbar / Alt-Tab / overview while
still showing the page's own title.

Like the persistent parts of CDP, the marker only stays applied while a CDP
connection holds it: ``Page.addScriptToEvaluateOnNewDocument`` re-runs the
overlay script on every new document, but only for as long as the registering
connection is alive. So the marker runs as a detached guard process (spawned by
``launch_browser``) that auto-attaches to every current and future page target
and holds the connection open until the browser dies.

Detection note: the overlay is page-observable (a host element in the DOM and a
modified ``document.title``), so ``launch_browser`` suppresses it when a
fingerprint profile is active. To minimize the footprint for the normal case,
the border/badge render inside a *closed* shadow DOM under a *randomized* host
id, and the injected code is a side-effect-free IIFE that leaks no globals.
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


async def run_guard(*, port: int, name: str) -> None:
    """Hold a CDP connection open, marking every page target until the browser dies."""
    color = derive_color(name)
    host_id = "_ca" + secrets.token_hex(8)
    source = build_overlay_script(name=name, color=color, host_id=host_id)

    browser_ws = get_ws_url(port=port, target_type="browser")
    cdp = CDPClient(ws_url=browser_ws)
    await cdp.connect()

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


def spawn_window_border_guard(*, port: int, name: str) -> subprocess.Popen:
    """Spawn the detached window-border guard process for a launched browser."""
    return subprocess.Popen(
        [sys.executable, "-m", "chrome_agent.window_border", str(port), name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> None:
    """Entry point for the detached guard process: `python -m chrome_agent.window_border PORT NAME`."""
    if len(sys.argv) < 3:
        print("usage: python -m chrome_agent.window_border PORT NAME", file=sys.stderr)
        sys.exit(2)
    port = int(sys.argv[1])
    name = sys.argv[2]
    try:
        asyncio.run(run_guard(port=port, name=name))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
