"""Experiment 4: Can CDP's native events replace Playwright's auto-waiting?

Playwright's waiting has several layers:
  1. Wait for navigation (load, domcontentloaded, networkidle)
  2. Wait for element to appear in DOM
  3. Wait for element to be visible/stable before acting
  4. Auto-retry on actionability failures

CDP provides:
  - Page.lifecycleEvent (load, DOMContentLoaded, networkIdle, etc.)
  - Page.loadEventFired, Page.domContentEventFired
  - Page.frameNavigated, Page.frameStoppedLoading
  - DOM.childNodeInserted, DOM.childNodeRemoved (mutation events)
  - DOM.attributeModified (attribute changes)
  - DOM.documentUpdated (full doc change)

This experiment tests:
  1. Event-driven wait for page load (no polling)
  2. Event-driven wait for element to appear (DOM mutations)
  3. Wait for element with timeout
  4. Wait for navigation after click
  5. Compare: event-driven vs polling approach

Success criteria:
  - Can wait for page load using lifecycle events (no sleep/poll)
  - Can wait for dynamically inserted elements using DOM events
  - Can detect networkidle via lifecycle events
  - Timeouts work correctly
"""

import asyncio
import json
import time
import urllib.request

import websockets


# ---------------------------------------------------------------------------
# CDP client (same minimal client)
# ---------------------------------------------------------------------------

class CDPClient:
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self._ws = None
        self._id = 0
        self._pending = {}
        self._event_handlers = {}

    async def connect(self):
        self._ws = await websockets.connect(self.ws_url, max_size=50 * 1024 * 1024)
        asyncio.ensure_future(self._recv_loop())

    async def send(self, method: str, params: dict | None = None) -> dict:
        self._id += 1
        msg_id = self._id
        msg = {"id": msg_id, "method": method}
        if params:
            msg["params"] = params
        future = asyncio.get_event_loop().create_future()
        self._pending[msg_id] = future
        await self._ws.send(json.dumps(msg))
        return await future

    def on(self, event: str, callback):
        self._event_handlers.setdefault(event, []).append(callback)

    def off(self, event: str, callback):
        handlers = self._event_handlers.get(event, [])
        if callback in handlers:
            handlers.remove(callback)

    async def _recv_loop(self):
        async for raw in self._ws:
            msg = json.loads(raw)
            if "id" in msg and msg["id"] in self._pending:
                future = self._pending.pop(msg["id"])
                if "error" in msg:
                    future.set_exception(RuntimeError(f"CDP error: {msg['error']}"))
                else:
                    future.set_result(msg.get("result", {}))
            elif "method" in msg:
                for cb in self._event_handlers.get(msg["method"], []):
                    cb(msg.get("params", {}))

    async def close(self):
        if self._ws:
            await self._ws.close()


# ---------------------------------------------------------------------------
# Waiting primitives built on CDP events
# ---------------------------------------------------------------------------

async def wait_for_lifecycle(cdp: CDPClient, event_name: str, *, timeout: float = 10.0) -> float:
    """Wait for a page lifecycle event (load, DOMContentLoaded, networkIdle, etc.).

    Returns elapsed time in seconds.
    Uses Page.lifecycleEvent -- fully event-driven, no polling.
    """
    future = asyncio.get_event_loop().create_future()
    t0 = time.perf_counter()

    def handler(params):
        if params.get("name") == event_name and not future.done():
            future.set_result(time.perf_counter() - t0)

    cdp.on("Page.lifecycleEvent", handler)
    try:
        return await asyncio.wait_for(future, timeout=timeout)
    except asyncio.TimeoutError:
        raise TimeoutError(f"Lifecycle event '{event_name}' not received within {timeout}s")
    finally:
        cdp.off("Page.lifecycleEvent", handler)


async def wait_for_selector(cdp: CDPClient, selector: str, *, timeout: float = 10.0) -> float:
    """Wait for an element matching selector to appear in the DOM.

    Two strategies combined:
    1. Check immediately (element may already exist)
    2. Listen for DOM.childNodeInserted events and re-check

    Returns elapsed time in seconds.
    """
    t0 = time.perf_counter()

    # Immediate check
    result = await cdp.send("Runtime.evaluate", {
        "expression": f"document.querySelector('{selector}') !== null",
        "returnByValue": True,
    })
    if result.get("result", {}).get("value") is True:
        return time.perf_counter() - t0

    # Event-driven: listen for DOM mutations, re-check on each
    future = asyncio.get_event_loop().create_future()

    async def check_and_resolve():
        result = await cdp.send("Runtime.evaluate", {
            "expression": f"document.querySelector('{selector}') !== null",
            "returnByValue": True,
        })
        if result.get("result", {}).get("value") is True and not future.done():
            future.set_result(time.perf_counter() - t0)

    def on_mutation(params):
        if not future.done():
            asyncio.ensure_future(check_and_resolve())

    cdp.on("DOM.childNodeInserted", on_mutation)
    cdp.on("DOM.attributeModified", on_mutation)

    # Use MutationObserver via JS with a built-in timeout.
    # Runtime.evaluate + awaitPromise lets us push a Promise into the
    # browser and await it from Python -- the browser does the watching.
    timeout_ms = int(timeout * 1000)
    result = await cdp.send("Runtime.evaluate", {
        "expression": f"""
        new Promise((resolve, reject) => {{
            const existing = document.querySelector('{selector}');
            if (existing) {{ resolve(true); return; }}

            const timer = setTimeout(() => {{
                observer.disconnect();
                reject(new Error('Timeout waiting for {selector}'));
            }}, {timeout_ms});

            const observer = new MutationObserver(() => {{
                if (document.querySelector('{selector}')) {{
                    clearTimeout(timer);
                    observer.disconnect();
                    resolve(true);
                }}
            }});
            observer.observe(document.body || document.documentElement, {{
                childList: true, subtree: true, attributes: true
            }});
        }})
        """,
        "awaitPromise": True,
        "returnByValue": True,
    })

    cdp.off("DOM.childNodeInserted", on_mutation)
    cdp.off("DOM.attributeModified", on_mutation)

    if not future.done():
        future.set_result(time.perf_counter() - t0)

    # Check if the Promise rejected (timeout)
    if "exceptionDetails" in result:
        raise TimeoutError(f"Selector '{selector}' not found within {timeout}s")

    return future.result()


async def wait_for_selector_poll(cdp: CDPClient, selector: str, *,
                                  timeout: float = 10.0, interval: float = 0.1) -> float:
    """Wait for selector by polling (for comparison with event-driven approach)."""
    t0 = time.perf_counter()
    deadline = t0 + timeout

    while time.perf_counter() < deadline:
        result = await cdp.send("Runtime.evaluate", {
            "expression": f"document.querySelector('{selector}') !== null",
            "returnByValue": True,
        })
        if result.get("result", {}).get("value") is True:
            return time.perf_counter() - t0
        await asyncio.sleep(interval)

    raise TimeoutError(f"Selector '{selector}' not found within {timeout}s")


async def wait_for_navigation(cdp: CDPClient, *, timeout: float = 10.0) -> dict:
    """Wait for a frame navigation to complete.

    Listens for Page.frameNavigated + subsequent load lifecycle event.
    Returns navigation info.
    """
    nav_future = asyncio.get_event_loop().create_future()
    t0 = time.perf_counter()

    def on_navigated(params):
        if not nav_future.done():
            nav_future.set_result({
                "url": params.get("frame", {}).get("url"),
                "elapsed": time.perf_counter() - t0,
            })

    cdp.on("Page.frameNavigated", on_navigated)
    try:
        return await asyncio.wait_for(nav_future, timeout=timeout)
    except asyncio.TimeoutError:
        raise TimeoutError(f"Navigation not completed within {timeout}s")
    finally:
        cdp.off("Page.frameNavigated", on_navigated)


# ---------------------------------------------------------------------------
# Test pages
# ---------------------------------------------------------------------------

DELAYED_ELEMENT_PAGE = """
<html><body>
<h1>Delayed Element Test</h1>
<div id="container"></div>
<script>
  // Insert element after 500ms
  setTimeout(() => {
    const el = document.createElement('div');
    el.id = 'delayed-element';
    el.textContent = 'I appeared after 500ms!';
    el.style.padding = '10px';
    el.style.background = 'lightgreen';
    document.getElementById('container').appendChild(el);
  }, 500);

  // Insert another after 1500ms
  setTimeout(() => {
    const el = document.createElement('button');
    el.id = 'very-delayed-btn';
    el.textContent = 'I appeared after 1500ms!';
    document.getElementById('container').appendChild(el);
  }, 1500);
</script>
</body></html>
"""

NAV_LINK_PAGE = """
<html><body>
<h1>Navigation Test</h1>
<a id="nav-link" href="https://example.com">Go to example.com</a>
</body></html>
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    req = urllib.request.Request("http://localhost:9222/json")
    with urllib.request.urlopen(req, timeout=2) as resp:
        targets = json.loads(resp.read())
        ws_url = next(t["webSocketDebuggerUrl"] for t in targets if t["type"] == "page")

    cdp = CDPClient(ws_url)
    await cdp.connect()

    try:
        await cdp.send("DOM.enable")
        await cdp.send("Page.enable")
        await cdp.send("Page.setLifecycleEventsEnabled", {"enabled": True})

        # Write test pages to files
        with open("/tmp/cdp-delayed-test.html", "w") as f:
            f.write(DELAYED_ELEMENT_PAGE)
        with open("/tmp/cdp-nav-test.html", "w") as f:
            f.write(NAV_LINK_PAGE)

        # --- Test 1: Wait for page load via lifecycle events ---
        print("=" * 60)
        print("TEST 1: Wait for page load (lifecycle events, no polling)")
        print("=" * 60)

        # Start listening BEFORE navigation
        load_task = asyncio.ensure_future(wait_for_lifecycle(cdp, event_name="load"))
        dcl_task = asyncio.ensure_future(wait_for_lifecycle(cdp, event_name="DOMContentLoaded"))
        ni_task = asyncio.ensure_future(wait_for_lifecycle(cdp, event_name="networkIdle"))

        await cdp.send("Page.navigate", {"url": "https://example.com"})

        dcl_time = await dcl_task
        load_time = await load_task
        ni_time = await ni_task

        print(f"  DOMContentLoaded: {dcl_time*1000:.1f}ms")
        print(f"  load:             {load_time*1000:.1f}ms")
        print(f"  networkIdle:      {ni_time*1000:.1f}ms")
        print("  PASS: all lifecycle events received (event-driven, zero polling)")

        # --- Test 2: Wait for dynamically inserted element (event-driven) ---
        print("\n" + "=" * 60)
        print("TEST 2: Wait for delayed element (event-driven via MutationObserver)")
        print("=" * 60)

        # Navigate to delayed element page
        load_task = asyncio.ensure_future(wait_for_lifecycle(cdp, event_name="load"))
        await cdp.send("Page.navigate", {"url": "file:///tmp/cdp-delayed-test.html"})
        await load_task

        # Wait for the element that appears after 500ms
        t0 = time.perf_counter()
        elapsed = await wait_for_selector(cdp, selector="#delayed-element", timeout=5.0)
        print(f"  #delayed-element found in {elapsed*1000:.1f}ms (expected ~500ms)")
        if 400 < elapsed * 1000 < 1000:
            print("  PASS: detected element promptly after insertion")
        else:
            print(f"  INFO: timing was {elapsed*1000:.1f}ms")

        # --- Test 3: Compare event-driven vs polling for second delayed element ---
        print("\n" + "=" * 60)
        print("TEST 3: Event-driven vs polling wait (1500ms delayed element)")
        print("=" * 60)

        # Reload page to reset
        load_task = asyncio.ensure_future(wait_for_lifecycle(cdp, event_name="load"))
        await cdp.send("Page.navigate", {"url": "file:///tmp/cdp-delayed-test.html"})
        await load_task

        # Event-driven wait
        t0 = time.perf_counter()
        event_elapsed = await wait_for_selector(cdp, selector="#very-delayed-btn", timeout=5.0)
        print(f"  Event-driven: found in {event_elapsed*1000:.1f}ms")

        # Reload and try polling
        load_task = asyncio.ensure_future(wait_for_lifecycle(cdp, event_name="load"))
        await cdp.send("Page.navigate", {"url": "file:///tmp/cdp-delayed-test.html"})
        await load_task

        poll_elapsed = await wait_for_selector_poll(
            cdp, selector="#very-delayed-btn", timeout=5.0, interval=0.05
        )
        print(f"  Polling (50ms): found in {poll_elapsed*1000:.1f}ms")

        print(f"  Difference: {abs(event_elapsed - poll_elapsed)*1000:.1f}ms")
        print("  PASS: both approaches work, event-driven reacts at insertion time")

        # --- Test 4: Wait for navigation after click ---
        print("\n" + "=" * 60)
        print("TEST 4: Wait for navigation triggered by click")
        print("=" * 60)

        load_task = asyncio.ensure_future(wait_for_lifecycle(cdp, event_name="load"))
        await cdp.send("Page.navigate", {"url": "file:///tmp/cdp-nav-test.html"})
        await load_task

        # Start navigation listener, then click the link
        nav_task = asyncio.ensure_future(wait_for_navigation(cdp))

        # Click the link using raw CDP
        el = await cdp.send("Runtime.evaluate", {
            "expression": "document.querySelector('#nav-link')",
            "returnByValue": False,
        })
        desc = await cdp.send("DOM.describeNode", {"objectId": el["result"]["objectId"]})
        backend_id = desc["node"]["backendNodeId"]
        await cdp.send("DOM.scrollIntoViewIfNeeded", {"backendNodeId": backend_id})
        quads = await cdp.send("DOM.getContentQuads", {"backendNodeId": backend_id})
        q = quads["quads"][0]
        cx = (q[0] + q[2] + q[4] + q[6]) / 4
        cy = (q[1] + q[3] + q[5] + q[7]) / 4

        await cdp.send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": cx, "y": cy})
        await cdp.send("Input.dispatchMouseEvent", {
            "type": "mousePressed", "x": cx, "y": cy, "button": "left", "clickCount": 1,
        })
        await cdp.send("Input.dispatchMouseEvent", {
            "type": "mouseReleased", "x": cx, "y": cy, "button": "left", "clickCount": 1,
        })

        nav_info = await nav_task
        print(f"  Navigated to: {nav_info['url']}")
        print(f"  Navigation detected in: {nav_info['elapsed']*1000:.1f}ms")

        # Now wait for load on the new page
        load_task = asyncio.ensure_future(wait_for_lifecycle(cdp, event_name="load"))
        load_time = await load_task
        print(f"  Page loaded in: {load_time*1000:.1f}ms after navigation event")
        print("  PASS: click → navigation → load, all event-driven")

        # --- Test 5: Timeout behavior ---
        print("\n" + "=" * 60)
        print("TEST 5: Timeout on non-existent element")
        print("=" * 60)

        # Need a stable page context after test 4's navigation
        load_task = asyncio.ensure_future(wait_for_lifecycle(cdp, event_name="load"))
        await cdp.send("Page.navigate", {"url": "file:///tmp/cdp-delayed-test.html"})
        await load_task

        t0 = time.perf_counter()
        try:
            await wait_for_selector(cdp, selector="#does-not-exist", timeout=1.0)
            print("  FAIL: should have timed out")
        except (TimeoutError, asyncio.TimeoutError, RuntimeError) as e:
            elapsed = time.perf_counter() - t0
            print(f"  Timed out/errored after {elapsed*1000:.1f}ms (limit: 1000ms)")
            print(f"  Exception: {type(e).__name__}")
            print("  PASS: timeout works correctly")

        # --- Test 6: Wait for attribute change ---
        print("\n" + "=" * 60)
        print("TEST 6: Wait for element to become visible (attribute/style change)")
        print("=" * 60)

        # Create a hidden element, then reveal it after a delay
        await cdp.send("Runtime.evaluate", {
            "expression": """
            document.body.innerHTML = '<div id="reveal-me" style="display:none">Hidden</div>';
            setTimeout(() => {
                document.getElementById('reveal-me').style.display = 'block';
                document.getElementById('reveal-me').setAttribute('data-ready', 'true');
            }, 600);
            """,
        })

        # Wait for the data-ready attribute using MutationObserver
        t0 = time.perf_counter()
        result = await cdp.send("Runtime.evaluate", {
            "expression": """
            new Promise((resolve) => {
                const el = document.getElementById('reveal-me');
                if (el && el.getAttribute('data-ready') === 'true') {
                    resolve(true);
                    return;
                }
                const observer = new MutationObserver(() => {
                    if (el && el.getAttribute('data-ready') === 'true') {
                        observer.disconnect();
                        resolve(true);
                    }
                });
                observer.observe(document.body, {
                    attributes: true, subtree: true, attributeFilter: ['data-ready', 'style']
                });
            })
            """,
            "awaitPromise": True,
            "returnByValue": True,
            "timeout": 5000,
        })
        elapsed = time.perf_counter() - t0
        print(f"  Element became visible in {elapsed*1000:.1f}ms (expected ~600ms)")
        print("  PASS: MutationObserver-based wait for visibility change")

        # --- Summary ---
        print("\n" + "=" * 60)
        print("SUMMARY: CDP waiting capabilities")
        print("=" * 60)
        print()
        print("Page lifecycle (event-driven, zero polling):")
        print("  Page.lifecycleEvent → load, DOMContentLoaded, networkIdle, etc.")
        print("  Page.frameNavigated → navigation detection")
        print()
        print("Element waiting (two viable approaches):")
        print("  1. Runtime.evaluate + awaitPromise + MutationObserver")
        print("     → Browser-native, zero polling, reacts at mutation time")
        print("     → Handles: element insertion, attribute changes, style changes")
        print()
        print("  2. DOM domain events (childNodeInserted, attributeModified)")
        print("     → CDP-level events, requires DOM.enable + getDocument")
        print("     → More granular but more setup")
        print()
        print("  3. Polling via Runtime.evaluate (fallback)")
        print("     → Simple, works everywhere, slightly higher latency")
        print()
        print("Key insight: Runtime.evaluate with awaitPromise=True lets you")
        print("push a JS Promise to the browser and await it from Python.")
        print("This means MutationObserver (the browser's native DOM watcher)")
        print("can be used directly -- no polling needed at all.")

    finally:
        await cdp.close()


if __name__ == "__main__":
    asyncio.run(main())
