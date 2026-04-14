"""Token cost experiment F: proper CDP domain commands (no Runtime.evaluate shortcuts)."""

import asyncio
import json
import base64
import urllib.request
import pathlib

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


def get_ws_url():
    data = urllib.request.urlopen("http://localhost:9222/json").read()
    tabs = json.loads(data)
    return tabs[0]["webSocketDebuggerUrl"]


async def get_node_id(cdp, root_node_id, selector):
    """Use DOM.querySelector to find an element."""
    result = await cdp.send("DOM.querySelector", {
        "nodeId": root_node_id,
        "selector": selector,
    })
    node_id = result["nodeId"]
    if node_id == 0:
        raise RuntimeError(f"Element not found: {selector}")
    return node_id


async def get_element_center(cdp, node_id):
    """Use DOM.getBoxModel to compute the center of an element."""
    result = await cdp.send("DOM.getBoxModel", {"nodeId": node_id})
    content = result["model"]["content"]
    # content is [x1,y1, x2,y2, x3,y3, x4,y4]
    xs = [content[i] for i in range(0, 8, 2)]
    ys = [content[i] for i in range(1, 8, 2)]
    cx = sum(xs) / 4
    cy = sum(ys) / 4
    return cx, cy


async def click_element(cdp, node_id):
    """Scroll into view, get center coordinates, dispatch mouse events."""
    await cdp.send("DOM.scrollIntoViewIfNeeded", {"nodeId": node_id})
    cx, cy = await get_element_center(cdp=cdp, node_id=node_id)
    x, y = int(cx), int(cy)
    await cdp.send("Input.dispatchMouseEvent", {
        "type": "mousePressed",
        "x": x,
        "y": y,
        "button": "left",
        "clickCount": 1,
    })
    await cdp.send("Input.dispatchMouseEvent", {
        "type": "mouseReleased",
        "x": x,
        "y": y,
        "button": "left",
        "clickCount": 1,
    })


async def fill_input(cdp, node_id, text):
    """Focus the element via DOM.focus, select all existing text, then use Input.insertText."""
    await cdp.send("DOM.focus", {"nodeId": node_id})
    # Select all existing text so insertText replaces it
    await cdp.send("Input.dispatchKeyEvent", {
        "type": "keyDown",
        "modifiers": 2,  # Ctrl
        "key": "a",
        "code": "KeyA",
        "windowsVirtualKeyCode": 65,
    })
    await cdp.send("Input.dispatchKeyEvent", {
        "type": "keyUp",
        "modifiers": 2,
        "key": "a",
        "code": "KeyA",
        "windowsVirtualKeyCode": 65,
    })
    await cdp.send("Input.insertText", {"text": text})


async def take_screenshot(cdp, path):
    """Use Page.captureScreenshot and save to disk."""
    result = await cdp.send("Page.captureScreenshot", {"format": "png"})
    img_data = base64.b64decode(result["data"])
    pathlib.Path(path).write_bytes(img_data)
    print(f"  Screenshot saved to {path} ({len(img_data)} bytes)")


async def read_text_content(cdp, root_node_id, selector):
    """Use Runtime.evaluate ONLY for reading back values (as permitted)."""
    result = await cdp.send("Runtime.evaluate", {
        "expression": f'document.querySelector("{selector}").textContent',
        "returnByValue": True,
    })
    return result["result"]["value"]


async def main():
    ws_url = get_ws_url()
    print(f"Connecting to {ws_url}")
    cdp = CDPClient(ws_url=ws_url)
    await cdp.connect()

    # Enable required domains
    await cdp.send("DOM.enable")
    await cdp.send("Page.enable")
    await cdp.send("Runtime.enable")

    # Step 1: Navigate to the test page
    print("Step 1: Navigating to test page...")
    await cdp.send("Page.navigate", {"url": "file:///tmp/cdp-test-page.html"})
    await asyncio.sleep(1)  # Wait for page load
    print("  Done.")

    # Get document root for DOM queries
    doc = await cdp.send("DOM.getDocument", {"depth": 0})
    root_node_id = doc["root"]["nodeId"]

    # Step 2: Take screenshot before
    print("Step 2: Taking 'before' screenshot...")
    await take_screenshot(cdp=cdp, path="/tmp/token_test_f_before.png")

    # Step 3: Fill #name-input with "Token Test Foxtrot"
    print("Step 3: Filling #name-input...")
    name_node = await get_node_id(cdp=cdp, root_node_id=root_node_id, selector="#name-input")
    await fill_input(cdp=cdp, node_id=name_node, text="Token Test Foxtrot")
    print("  Done.")

    # Step 4: Fill #email-input with "foxtrot@token.test"
    print("Step 4: Filling #email-input...")
    email_node = await get_node_id(cdp=cdp, root_node_id=root_node_id, selector="#email-input")
    await fill_input(cdp=cdp, node_id=email_node, text="foxtrot@token.test")
    print("  Done.")

    # Step 5: Click checkbox #check1
    print("Step 5: Clicking checkbox #check1...")
    check_node = await get_node_id(cdp=cdp, root_node_id=root_node_id, selector="#check1")
    await click_element(cdp=cdp, node_id=check_node)
    print("  Done.")

    # Step 6: Click submit button #submit-btn
    print("Step 6: Clicking #submit-btn...")
    submit_node = await get_node_id(cdp=cdp, root_node_id=root_node_id, selector="#submit-btn")
    await click_element(cdp=cdp, node_id=submit_node)
    await asyncio.sleep(0.3)
    print("  Done.")

    # Step 7: Verify #result text
    print("Step 7: Verifying #result after submit...")
    result_text = await read_text_content(cdp=cdp, root_node_id=root_node_id, selector="#result")
    expected = "Submitted: Token Test Foxtrot / foxtrot@token.test"
    if expected in result_text:
        print(f"  PASS: '{result_text}'")
    else:
        print(f"  FAIL: expected '{expected}', got '{result_text}'")

    # Step 8: Click #far-btn (scroll into view first)
    print("Step 8: Scrolling to and clicking #far-btn...")
    far_node = await get_node_id(cdp=cdp, root_node_id=root_node_id, selector="#far-btn")
    await click_element(cdp=cdp, node_id=far_node)  # click_element already calls scrollIntoViewIfNeeded
    await asyncio.sleep(0.3)
    print("  Done.")

    # Step 9: Verify #result text after far button click
    print("Step 9: Verifying #result after far button click...")
    result_text = await read_text_content(cdp=cdp, root_node_id=root_node_id, selector="#result")
    expected_far = "Far button clicked!"
    if expected_far in result_text:
        print(f"  PASS: '{result_text}'")
    else:
        print(f"  FAIL: expected '{expected_far}', got '{result_text}'")

    # Step 10: Take screenshot after
    print("Step 10: Taking 'after' screenshot...")
    await take_screenshot(cdp=cdp, path="/tmp/token_test_f_after.png")

    print("\nAll 10 steps completed.")
    await cdp.close()


if __name__ == "__main__":
    asyncio.run(main())
