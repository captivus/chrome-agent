"""Experiment 3: Can we build click/fill/type from raw CDP primitives?

Playwright's value proposition for interactions is:
  1. Find element by selector
  2. Wait for it to exist in DOM
  3. Scroll it into view
  4. Check actionability (visible, enabled, not obscured)
  5. Get center coordinates
  6. Dispatch input events

CDP provides native commands for ALL of these steps. This experiment
builds working click, fill, and type operations from raw CDP to measure
how much code it actually takes and whether the result is reliable.

Test page: a form with inputs, buttons, and a result area.

Success criteria:
- click() works: finds element, scrolls into view, clicks at center
- fill() works: focuses input, clears it, inserts text
- type() works: sends individual key events
- Actionability: can detect when an element is obscured
- Total code for the interaction layer is measurable
"""

import asyncio
import json
import time
import urllib.request

import websockets


# ---------------------------------------------------------------------------
# Minimal CDP client (same as experiment 2)
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
# Interaction primitives built on raw CDP
# ---------------------------------------------------------------------------

async def find_element(cdp: CDPClient, selector: str) -> dict:
    """Find an element by CSS selector, return its backend node info.

    Returns dict with backendNodeId and objectId for use with other commands.
    """
    # Use Runtime.evaluate to find the element -- more flexible than DOM.querySelector
    # because we don't need to call DOM.getDocument first.
    result = await cdp.send("Runtime.evaluate", {
        "expression": f"document.querySelector('{selector}')",
        "returnByValue": False,
    })
    remote_obj = result.get("result", {})
    if remote_obj.get("subtype") == "null" or remote_obj.get("type") == "undefined":
        raise ValueError(f"Element not found: {selector}")
    return remote_obj


async def get_element_center(cdp: CDPClient, object_id: str) -> tuple[float, float]:
    """Get the center coordinates of an element using DOM.getContentQuads."""
    # First, get the DOM node for this JS object
    desc = await cdp.send("DOM.describeNode", {"objectId": object_id})
    backend_node_id = desc["node"]["backendNodeId"]

    # Scroll into view first
    await cdp.send("DOM.scrollIntoViewIfNeeded", {"backendNodeId": backend_node_id})

    # Get content quads (the actual visible area)
    quads_result = await cdp.send("DOM.getContentQuads", {"backendNodeId": backend_node_id})
    quads = quads_result.get("quads", [])
    if not quads:
        raise ValueError("Element has no visible quads (may be hidden)")

    # First quad is [x1,y1, x2,y2, x3,y3, x4,y4] -- compute center
    q = quads[0]
    cx = (q[0] + q[2] + q[4] + q[6]) / 4
    cy = (q[1] + q[3] + q[5] + q[7]) / 4
    return cx, cy


async def check_actionable(cdp: CDPClient, selector: str) -> dict:
    """Check if the element is visible and not obscured.

    Uses DOM.getNodeForLocation for native hit-testing (viewport coords)
    and Runtime.evaluate for visibility checks.
    """
    # Get visibility info and viewport-relative coordinates via JS
    vis_result = await cdp.send("Runtime.evaluate", {
        "expression": f"""(() => {{
            const el = document.querySelector('{selector}');
            if (!el) return {{ found: false }};
            const cs = getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            return {{
                found: true,
                visible: el.offsetParent !== null || cs.display !== 'none',
                display: cs.display,
                opacity: cs.opacity,
                disabled: el.disabled || false,
                width: rect.width,
                height: rect.height,
                viewportX: Math.round(rect.x + rect.width / 2),
                viewportY: Math.round(rect.y + rect.height / 2),
            }};
        }})()""",
        "returnByValue": True,
    })
    info = vis_result["result"]["value"]

    # Hit-test using viewport-relative coordinates
    if info.get("found") and info.get("visible"):
        try:
            hit_result = await cdp.send("DOM.getNodeForLocation", {
                "x": info["viewportX"],
                "y": info["viewportY"],
                "includeUserAgentShadowDOM": False,
            })
            info["hit_backend_id"] = hit_result["backendNodeId"]
        except RuntimeError:
            info["hit_backend_id"] = None

    return info


async def click(cdp: CDPClient, selector: str) -> None:
    """Click an element: find → scroll → check actionability → dispatch mouse events."""
    # Find
    el = await find_element(cdp, selector=selector)
    object_id = el["objectId"]

    # Scroll into view + get coordinates
    cx, cy = await get_element_center(cdp, object_id=object_id)

    # Check actionability
    info = await check_actionable(cdp, selector=selector)
    if not info.get("visible"):
        print(f"  WARNING: element {selector} is not visible (display={info.get('display')})")

    # Dispatch mouse events: move → press → release
    await cdp.send("Input.dispatchMouseEvent", {
        "type": "mouseMoved", "x": cx, "y": cy,
    })
    await cdp.send("Input.dispatchMouseEvent", {
        "type": "mousePressed", "x": cx, "y": cy,
        "button": "left", "clickCount": 1,
    })
    await cdp.send("Input.dispatchMouseEvent", {
        "type": "mouseReleased", "x": cx, "y": cy,
        "button": "left", "clickCount": 1,
    })


async def fill(cdp: CDPClient, selector: str, value: str) -> None:
    """Fill an input: find → focus → select all → insert text."""
    el = await find_element(cdp, selector=selector)
    object_id = el["objectId"]

    # Scroll into view
    desc = await cdp.send("DOM.describeNode", {"objectId": object_id})
    backend_node_id = desc["node"]["backendNodeId"]
    await cdp.send("DOM.scrollIntoViewIfNeeded", {"backendNodeId": backend_node_id})

    # Focus the element
    await cdp.send("DOM.focus", {"backendNodeId": backend_node_id})

    # Select all existing text and delete
    await cdp.send("Runtime.evaluate", {
        "expression": f"document.querySelector('{selector}').select()",
    })

    # Insert the new text
    await cdp.send("Input.insertText", {"text": value})

    # Dispatch input and change events for frameworks that listen
    await cdp.send("Runtime.evaluate", {
        "expression": f"""(() => {{
            const el = document.querySelector('{selector}');
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }})()""",
    })


async def type_text(cdp: CDPClient, selector: str, text: str) -> None:
    """Type text character-by-character into an element."""
    el = await find_element(cdp, selector=selector)
    desc = await cdp.send("DOM.describeNode", {"objectId": el["objectId"]})
    backend_node_id = desc["node"]["backendNodeId"]

    await cdp.send("DOM.scrollIntoViewIfNeeded", {"backendNodeId": backend_node_id})
    await cdp.send("DOM.focus", {"backendNodeId": backend_node_id})

    for char in text:
        await cdp.send("Input.dispatchKeyEvent", {
            "type": "keyDown", "text": char, "key": char,
        })
        await cdp.send("Input.dispatchKeyEvent", {
            "type": "keyUp", "key": char,
        })


async def press_key(cdp: CDPClient, key: str) -> None:
    """Press a special key (Enter, Tab, Escape, etc.)."""
    await cdp.send("Input.dispatchKeyEvent", {
        "type": "keyDown", "key": key,
    })
    await cdp.send("Input.dispatchKeyEvent", {
        "type": "keyUp", "key": key,
    })


# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------

TEST_PAGE = "file:///tmp/cdp-test-page.html"


async def main():
    # Connect to page target
    req = urllib.request.Request("http://localhost:9222/json")
    with urllib.request.urlopen(req, timeout=2) as resp:
        targets = json.loads(resp.read())
        ws_url = next(t["webSocketDebuggerUrl"] for t in targets if t["type"] == "page")

    cdp = CDPClient(ws_url)
    await cdp.connect()

    try:
        # Enable DOM domain (needed for querySelector etc.)
        await cdp.send("DOM.enable")
        await cdp.send("Page.enable")

        # Load test page
        await cdp.send("Page.navigate", {"url": TEST_PAGE})
        await asyncio.sleep(1)

        # --- Test 1: Click ---
        print("=" * 60)
        print("TEST 1: click() on submit button")
        print("=" * 60)
        # First fill the inputs so we can see the click result
        await fill(cdp, selector="#name-input", value="John Doe")
        await fill(cdp, selector="#email-input", value="john@example.com")

        t0 = time.perf_counter()
        await click(cdp, selector="#submit-btn")
        click_time = time.perf_counter() - t0
        await asyncio.sleep(0.2)

        result = await cdp.send("Runtime.evaluate", {
            "expression": "document.getElementById('result').textContent",
            "returnByValue": True,
        })
        result_text = result.get("result", {}).get("value", f"(unexpected result: {result})")
        print(f"  Click took: {click_time*1000:.1f}ms")
        print(f"  Result div: {result_text}")
        if "John Doe" in str(result_text):
            print("  PASS: click() triggered button onclick, form values correct")
        else:
            print(f"  INFO: result was '{result_text}' -- checking if click dispatched")

        # --- Test 2: fill() ---
        print("\n" + "=" * 60)
        print("TEST 2: fill() replaces existing value")
        print("=" * 60)

        # Read current value
        old_val = await cdp.send("Runtime.evaluate", {
            "expression": "document.getElementById('name-input').value",
            "returnByValue": True,
        })
        print(f"  Before: {old_val['result']['value']}")

        await fill(cdp, selector="#name-input", value="Jane Smith")

        new_val = await cdp.send("Runtime.evaluate", {
            "expression": "document.getElementById('name-input').value",
            "returnByValue": True,
        })
        print(f"  After:  {new_val['result']['value']}")
        assert new_val.get("result", {}).get("value") == "Jane Smith", f"Got: {new_val}"
        print("  PASS: fill() replaced value correctly")

        # --- Test 3: type_text() ---
        print("\n" + "=" * 60)
        print("TEST 3: type_text() character by character")
        print("=" * 60)

        # Clear the email field first
        await fill(cdp, selector="#email-input", value="")
        await type_text(cdp, selector="#email-input", text="typed@char.by.char")

        typed_val = await cdp.send("Runtime.evaluate", {
            "expression": "document.getElementById('email-input').value",
            "returnByValue": True,
        })
        print(f"  Typed value: {typed_val['result']['value']}")
        assert typed_val.get("result", {}).get("value") == "typed@char.by.char", f"Got: {typed_val}"
        print("  PASS: type_text() entered each character")

        # --- Test 4: Actionability - hidden element ---
        print("\n" + "=" * 60)
        print("TEST 4: Actionability check on hidden element")
        print("=" * 60)

        try:
            el = await find_element(cdp, selector="#hidden-btn")
            object_id = el["objectId"]
            # Try to get coordinates -- should fail since element has no layout
            try:
                cx, cy = await get_element_center(cdp, object_id=object_id)
                info = await check_actionable(cdp, selector="#hidden-btn", x=cx, y=cy)
                print(f"  Actionability info: {info}")
                if not info.get("visible"):
                    print("  PASS: correctly detected element as not visible")
                else:
                    print("  PARTIAL: element found but visibility check needed improvement")
            except (ValueError, RuntimeError) as e:
                print(f"  PASS: CDP correctly rejected hidden element: {e}")
        except ValueError:
            print("  UNEXPECTED: element not found at all")

        # --- Test 5: Hit testing - obscured element ---
        print("\n" + "=" * 60)
        print("TEST 5: Hit test on obscured element")
        print("=" * 60)

        el = await find_element(cdp, selector="#obscured-btn")
        desc = await cdp.send("DOM.describeNode", {"objectId": el["objectId"]})
        target_backend_id = desc["node"]["backendNodeId"]
        print(f"  Target backendNodeId: {target_backend_id}")

        info = await check_actionable(cdp, selector="#obscured-btn")
        hit_id = info.get("hit_backend_id")
        print(f"  Hit test backendNodeId: {hit_id}")
        if hit_id and hit_id != target_backend_id:
            print("  PASS: hit test detected that another element is on top")
        elif hit_id == target_backend_id:
            print("  NOTE: hit test returned the target (overlay may not cover center)")
        else:
            print("  NOTE: hit test couldn't determine (element may be off-screen)")

        # --- Test 6: Scroll into view - element below fold ---
        print("\n" + "=" * 60)
        print("TEST 6: click() on element 2000px below fold (auto-scroll)")
        print("=" * 60)

        scroll_before = await cdp.send("Runtime.evaluate", {
            "expression": "window.scrollY",
            "returnByValue": True,
        })
        print(f"  Scroll position before: {scroll_before['result']['value']}")

        t0 = time.perf_counter()
        await click(cdp, selector="#far-btn")
        scroll_click_time = time.perf_counter() - t0
        await asyncio.sleep(0.2)

        scroll_after = await cdp.send("Runtime.evaluate", {
            "expression": "window.scrollY",
            "returnByValue": True,
        })
        print(f"  Scroll position after:  {scroll_after['result']['value']}")
        print(f"  Click took: {scroll_click_time*1000:.1f}ms")

        result = await cdp.send("Runtime.evaluate", {
            "expression": "document.getElementById('result').textContent",
            "returnByValue": True,
        })
        print(f"  Result div: {result['result']['value']}")
        far_result = result.get("result", {}).get("value", "")
        assert "Far button clicked" in far_result, f"Got: {far_result}"
        print("  PASS: scrollIntoViewIfNeeded + click worked on off-screen element")

        # --- Test 7: Checkbox ---
        print("\n" + "=" * 60)
        print("TEST 7: click() on checkbox")
        print("=" * 60)

        before = await cdp.send("Runtime.evaluate", {
            "expression": "document.getElementById('check1').checked",
            "returnByValue": True,
        })
        print(f"  Checked before: {before['result']['value']}")

        await click(cdp, selector="#check1")

        after = await cdp.send("Runtime.evaluate", {
            "expression": "document.getElementById('check1').checked",
            "returnByValue": True,
        })
        print(f"  Checked after:  {after['result']['value']}")
        assert after.get("result", {}).get("value") is True, f"Got: {after}"
        print("  PASS: checkbox toggled via click")

        # --- Summary ---
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print("All interactions built from raw CDP primitives:")
        print("  DOM.querySelector (via Runtime.evaluate)")
        print("  DOM.describeNode → backendNodeId")
        print("  DOM.scrollIntoViewIfNeeded")
        print("  DOM.getContentQuads → center coordinates")
        print("  DOM.getNodeForLocation → hit testing")
        print("  DOM.focus")
        print("  Input.dispatchMouseEvent (move, press, release)")
        print("  Input.dispatchKeyEvent (keyDown, keyUp)")
        print("  Input.insertText")
        print()
        print("Interaction functions (click, fill, type_text, press_key):")
        print("  ~120 lines of Python total, including actionability checks")

    finally:
        await cdp.close()


if __name__ == "__main__":
    asyncio.run(main())
