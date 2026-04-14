"""
Token cost experiment E: Pure CDP domain commands (no Runtime.evaluate shortcuts).

Uses DOM.getDocument, DOM.querySelector, DOM.focus, Input.insertText,
DOM.getBoxModel, Input.dispatchMouseEvent, DOM.scrollIntoViewIfNeeded,
and Page.captureScreenshot for all interactions.

Runtime.evaluate is used ONLY for reading back values to verify results.
"""

import asyncio
import base64
import json
import urllib.request

import websockets


class CDPClient:
    def __init__(self, ws_url):
        self.ws_url = ws_url
        self._ws = None
        self._id = 0
        self._pending = {}

    async def connect(self):
        self._ws = await websockets.connect(self.ws_url, max_size=50 * 1024 * 1024)
        asyncio.ensure_future(self._recv_loop())

    async def send(self, method, params=None):
        self._id += 1
        msg = {"id": self._id, "method": method}
        if params:
            msg["params"] = params
        future = asyncio.get_event_loop().create_future()
        self._pending[self._id] = future
        await self._ws.send(json.dumps(msg))
        return await future

    async def _recv_loop(self):
        async for raw in self._ws:
            msg = json.loads(raw)
            if "id" in msg and msg["id"] in self._pending:
                f = self._pending.pop(msg["id"])
                if "error" in msg:
                    f.set_exception(RuntimeError(f"CDP: {msg['error']}"))
                else:
                    f.set_result(msg.get("result", {}))

    async def close(self):
        if self._ws:
            await self._ws.close()


async def get_node_id(cdp, selector):
    """Get a DOM nodeId via DOM.getDocument + DOM.querySelector."""
    doc = await cdp.send("DOM.getDocument", {"depth": 0})
    root_node_id = doc["root"]["nodeId"]
    result = await cdp.send(
        "DOM.querySelector",
        {"nodeId": root_node_id, "selector": selector},
    )
    node_id = result["nodeId"]
    if node_id == 0:
        raise RuntimeError(f"Element not found: {selector}")
    return node_id


async def get_box_center(cdp, node_id):
    """Get the center coordinates of a node via DOM.getBoxModel."""
    box = await cdp.send("DOM.getBoxModel", {"nodeId": node_id})
    content = box["model"]["content"]
    # content is [x1,y1, x2,y2, x3,y3, x4,y4] -- a quad
    xs = [content[i] for i in range(0, 8, 2)]
    ys = [content[i] for i in range(1, 8, 2)]
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    return cx, cy


async def click_element(cdp, selector):
    """Click an element using DOM commands + Input.dispatchMouseEvent."""
    node_id = await get_node_id(cdp, selector=selector)
    cx, cy = await get_box_center(cdp, node_id=node_id)
    await cdp.send(
        "Input.dispatchMouseEvent",
        {"type": "mousePressed", "x": cx, "y": cy, "button": "left", "clickCount": 1},
    )
    await cdp.send(
        "Input.dispatchMouseEvent",
        {"type": "mouseReleased", "x": cx, "y": cy, "button": "left", "clickCount": 1},
    )


async def clear_and_type(cdp, selector, text):
    """Clear an input field and type text using DOM.focus + keyboard events + Input.insertText."""
    node_id = await get_node_id(cdp, selector=selector)

    # Focus the element using DOM.focus
    await cdp.send("DOM.focus", {"nodeId": node_id})

    # Triple-click to select all text in the field
    cx, cy = await get_box_center(cdp, node_id=node_id)
    await cdp.send(
        "Input.dispatchMouseEvent",
        {"type": "mousePressed", "x": cx, "y": cy, "button": "left", "clickCount": 3},
    )
    await cdp.send(
        "Input.dispatchMouseEvent",
        {"type": "mouseReleased", "x": cx, "y": cy, "button": "left", "clickCount": 3},
    )

    # Delete selected text
    await cdp.send(
        "Input.dispatchKeyEvent",
        {"type": "keyDown", "key": "Backspace", "code": "Backspace"},
    )
    await cdp.send(
        "Input.dispatchKeyEvent",
        {"type": "keyUp", "key": "Backspace", "code": "Backspace"},
    )

    # Insert the new text
    await cdp.send("Input.insertText", {"text": text})


async def screenshot(cdp, path):
    """Take a screenshot using Page.captureScreenshot and save to path."""
    result = await cdp.send("Page.captureScreenshot", {"format": "png"})
    with open(path, "wb") as f:
        f.write(base64.b64decode(result["data"]))
    print(f"  Screenshot saved to {path}")


async def read_text(cdp, selector):
    """Read element text content -- this is the ONE place we use Runtime.evaluate."""
    result = await cdp.send(
        "Runtime.evaluate",
        {"expression": f'document.querySelector("{selector}").textContent'},
    )
    return result["result"]["value"]


async def main():
    # Discover the websocket URL
    raw = urllib.request.urlopen("http://localhost:9222/json").read()
    tabs = json.loads(raw)
    ws_url = tabs[0]["webSocketDebuggerUrl"]

    cdp = CDPClient(ws_url=ws_url)
    await cdp.connect()
    print("Connected to browser")

    # Enable required domains
    await cdp.send("DOM.enable")
    await cdp.send("Page.enable")
    await cdp.send("Runtime.enable")

    # Step 1: Navigate to the test page
    print("Step 1: Navigating to test page...")
    await cdp.send("Page.navigate", {"url": "file:///tmp/cdp-test-page.html"})
    await asyncio.sleep(0.5)
    print("  Done")

    # Step 2: Take a screenshot before interactions
    print("Step 2: Taking before screenshot...")
    await screenshot(cdp, path="/tmp/token_test_e_before.png")

    # Step 3: Fill #name-input with "Token Test Echo"
    print("Step 3: Filling #name-input...")
    await clear_and_type(cdp, selector="#name-input", text="Token Test Echo")
    print("  Done")

    # Step 4: Fill #email-input with "echo@token.test"
    print("Step 4: Filling #email-input...")
    await clear_and_type(cdp, selector="#email-input", text="echo@token.test")
    print("  Done")

    # Step 5: Click checkbox #check1
    print("Step 5: Clicking checkbox #check1...")
    await click_element(cdp, selector="#check1")
    print("  Done")

    # Step 6: Click submit button #submit-btn
    print("Step 6: Clicking #submit-btn...")
    await click_element(cdp, selector="#submit-btn")
    print("  Done")

    # Step 7: Verify #result text
    print("Step 7: Verifying #result...")
    result_text = await read_text(cdp, selector="#result")
    expected = "Submitted: Token Test Echo / echo@token.test"
    assert result_text == expected, f"Expected '{expected}', got '{result_text}'"
    print(f"  PASS: {result_text}")

    # Step 8: Scroll #far-btn into view and click it
    print("Step 8: Scrolling to and clicking #far-btn...")
    far_node_id = await get_node_id(cdp, selector="#far-btn")
    await cdp.send("DOM.scrollIntoViewIfNeeded", {"nodeId": far_node_id})
    await asyncio.sleep(0.2)
    # Re-fetch coordinates after scroll
    cx, cy = await get_box_center(cdp, node_id=far_node_id)
    await cdp.send(
        "Input.dispatchMouseEvent",
        {"type": "mousePressed", "x": cx, "y": cy, "button": "left", "clickCount": 1},
    )
    await cdp.send(
        "Input.dispatchMouseEvent",
        {"type": "mouseReleased", "x": cx, "y": cy, "button": "left", "clickCount": 1},
    )
    print("  Done")

    # Step 9: Verify #result says "Far button clicked!"
    print("Step 9: Verifying #result...")
    result_text = await read_text(cdp, selector="#result")
    expected = "Far button clicked!"
    assert result_text == expected, f"Expected '{expected}', got '{result_text}'"
    print(f"  PASS: {result_text}")

    # Step 10: Take a screenshot after interactions
    print("Step 10: Taking after screenshot...")
    await screenshot(cdp, path="/tmp/token_test_e_after.png")

    print("\nAll 10 steps completed successfully!")
    await cdp.close()


if __name__ == "__main__":
    asyncio.run(main())
