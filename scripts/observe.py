#!/usr/bin/env python3
"""Browser observation monitor for Claude Code's Monitor tool.

Connects to a running Chrome browser via CDP and streams filtered
events to stdout. Each stdout line becomes a real-time notification
in Claude Code's Monitor tool.

Usage:
    uv run python scripts/observe.py [--port 9222] [--tier nav|dev|full]

Tiers control verbosity:
    nav  -- navigation only (2-3 events per page, safe for any site)
    dev  -- navigation + errors + meaningful network (default)
    full -- dev + interaction bridge (sees clicks, scrolls, text selection)
"""

import argparse
import asyncio
import json
import time

from chrome_agent.cdp_client import CDPClient, get_ws_url


# ---------------------------------------------------------------------------
# Rate limiter -- prevents Monitor auto-stop on noisy pages
# ---------------------------------------------------------------------------

class RateLimiter:
    """Token-bucket limiter that suppresses bursts and emits summaries."""

    def __init__(
        self,
        max_events: int = 15,
        window: float = 2.0,
        summary_interval: float = 5.0,
    ):
        self._max = max_events
        self._window = window
        self._summary_interval = summary_interval
        self._timestamps: list[float] = []
        self._suppressed = 0
        self._last_summary = 0.0

    def allow(self) -> bool:
        now = time.monotonic()
        cutoff = now - self._window
        self._timestamps = [t for t in self._timestamps if t > cutoff]
        if len(self._timestamps) < self._max:
            self._timestamps.append(now)
            return True
        self._suppressed += 1
        return False

    def get_summary(self) -> str | None:
        now = time.monotonic()
        if self._suppressed == 0:
            return None
        if now - self._last_summary < self._summary_interval:
            return None
        count = self._suppressed
        self._suppressed = 0
        self._last_summary = now
        return f"[SUPPRESSED] {count} events dropped (rate limited)"


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def emit(line: str) -> None:
    print(line, flush=True)


def short_url(url: str, max_len: int = 80) -> str:
    if len(url) <= max_len:
        return url
    return url[:max_len - 3] + "..."


# ---------------------------------------------------------------------------
# Event handlers by tier
# ---------------------------------------------------------------------------

def make_nav_handlers(limiter: RateLimiter) -> dict:
    """Tier: nav -- page lifecycle only."""

    def on_frame_navigated(params: dict) -> None:
        frame = params.get("frame", {})
        if frame.get("parentId"):
            return
        if not limiter.allow():
            return
        url = frame.get("url", "?")
        title = frame.get("title", "")
        if title:
            emit(f"[PAGE] {title} | {short_url(url)}")
        else:
            emit(f"[PAGE] {short_url(url)}")

    def on_load(params: dict) -> None:
        if not limiter.allow():
            return
        emit("[LOADED]")

    return {
        "Page.frameNavigated": on_frame_navigated,
        "Page.loadEventFired": on_load,
    }


def make_dev_handlers(limiter: RateLimiter) -> dict:
    """Tier: dev -- nav + errors + filtered network."""

    handlers = make_nav_handlers(limiter=limiter)

    def on_console(params: dict) -> None:
        level = params.get("type", "log")
        if level not in ("error", "warning"):
            return
        if not limiter.allow():
            return
        args = params.get("args", [])
        text = " ".join(
            a.get("value", a.get("description", "?")) for a in args
        )[:200]
        tag = "ERR" if level == "error" else "WARN"
        emit(f"[{tag}] {text}")

    def on_exception(params: dict) -> None:
        if not limiter.allow():
            return
        details = params.get("exceptionDetails", {})
        exception = details.get("exception", {})
        desc = exception.get("description", "")
        if desc:
            msg = desc.split("\n")[0]
        else:
            msg = details.get("text", "unknown")
        url = details.get("url", "")
        line_no = details.get("lineNumber", "?")
        loc = f" at {short_url(url)}:{line_no}" if url else ""
        emit(f"[EXCEPTION] {msg}{loc}")

    def on_request(params: dict) -> None:
        req_type = params.get("type", "")
        if req_type not in ("Document", "XHR", "Fetch"):
            return
        if not limiter.allow():
            return
        request = params.get("request", {})
        method = request.get("method", "GET")
        url = request.get("url", "")
        tag = "XHR" if req_type in ("XHR", "Fetch") else "NET"
        emit(f"[{tag}] {method} {short_url(url)}")

    def on_network_fail(params: dict) -> None:
        req_type = params.get("type", "")
        if req_type not in ("Document", "XHR", "Fetch", ""):
            return
        if params.get("blockedReason"):
            return
        if not limiter.allow():
            return
        error = params.get("errorText", "?")
        emit(f"[NET FAIL] {error}")

    handlers.update({
        "Runtime.consoleAPICalled": on_console,
        "Runtime.exceptionThrown": on_exception,
        "Network.requestWillBeSent": on_request,
        "Network.loadingFailed": on_network_fail,
    })
    return handlers


# ---------------------------------------------------------------------------
# Interaction bridge (full tier only)
# ---------------------------------------------------------------------------

INTERACTION_LISTENERS = """
(function() {
    if (window.__chromeAgentObserver) return;
    window.__chromeAgentObserver = true;

    document.addEventListener('click', (e) => {
        if (typeof reportInteraction !== 'function') return;
        const el = e.target;
        const text = (el.innerText || el.alt || el.title || '').substring(0, 50);
        reportInteraction(JSON.stringify({
            type: 'click',
            x: e.clientX, y: e.clientY,
            target: el.tagName + (el.id ? '#' + el.id : ''),
            text: text
        }));
    }, true);

    let scrollTimer = null;
    document.addEventListener('scroll', () => {
        if (typeof reportInteraction !== 'function') return;
        clearTimeout(scrollTimer);
        scrollTimer = setTimeout(() => {
            reportInteraction(JSON.stringify({
                type: 'scroll',
                y: Math.round(window.scrollY)
            }));
        }, 300);
    }, {passive: true});

    document.addEventListener('selectionchange', () => {
        if (typeof reportInteraction !== 'function') return;
        const text = window.getSelection().toString().trim();
        if (text && text.length > 2) {
            reportInteraction(JSON.stringify({
                type: 'selection',
                text: text.substring(0, 200)
            }));
        }
    });
})();
"""


def make_interaction_handler(limiter: RateLimiter) -> dict:
    """Binding bridge handler for click, scroll, selection."""

    def on_binding(params: dict) -> None:
        if params.get("name") != "reportInteraction":
            return
        try:
            payload = json.loads(params.get("payload", "{}"))
        except json.JSONDecodeError:
            return

        itype = payload.get("type", "")

        if itype == "click":
            if not limiter.allow():
                return
            target = payload.get("target", "?")
            text = payload.get("text", "")
            label = f' "{text[:40]}"' if text else ""
            emit(f"[CLICK] {target}{label}")

        elif itype == "scroll":
            if not limiter.allow():
                return
            y = payload.get("y", 0)
            emit(f"[SCROLL] y={y}")

        elif itype == "selection":
            if not limiter.allow():
                return
            text = payload.get("text", "")
            if len(text) > 80:
                text = text[:80] + "..."
            emit(f'[SELECT] "{text}"')

    return {"Runtime.bindingCalled": on_binding}


async def inject_interaction_bridge(cdp: CDPClient) -> None:
    await cdp.send(method="Runtime.addBinding", params={"name": "reportInteraction"})
    await cdp.send(method="Runtime.evaluate", params={"expression": INTERACTION_LISTENERS})
    await cdp.send(method="Page.addScriptToEvaluateOnNewDocument", params={"source": INTERACTION_LISTENERS})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def observe(port: int, tier: str) -> None:
    ws_url = get_ws_url(port=port, target_type="page")
    cdp = CDPClient(ws_url=ws_url)
    await cdp.connect()

    limiter = RateLimiter()

    await cdp.send(method="Page.enable")
    if tier in ("dev", "full"):
        await cdp.send(method="Runtime.enable")
        await cdp.send(method="Network.enable")

    if tier == "nav":
        handlers = make_nav_handlers(limiter=limiter)
    elif tier == "dev":
        handlers = make_dev_handlers(limiter=limiter)
    else:
        handlers = make_dev_handlers(limiter=limiter)
        handlers.update(make_interaction_handler(limiter=limiter))
        await inject_interaction_bridge(cdp=cdp)

    for event_name, callback in handlers.items():
        cdp.on(event=event_name, callback=callback)

    emit(f"[OBSERVE] tier={tier} port={port}")

    while cdp._connected:
        await asyncio.sleep(1)
        summary = limiter.get_summary()
        if summary:
            emit(summary)

    emit("[OBSERVE] disconnected")


def main():
    parser = argparse.ArgumentParser(description="Browser monitor for Claude Code")
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--tier", choices=["nav", "dev", "full"], default="dev")
    args = parser.parse_args()
    asyncio.run(observe(port=args.port, tier=args.tier))


if __name__ == "__main__":
    main()
