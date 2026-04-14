"""
Raw CDP WebSocket script: fill a form, click submit, verify result,
then click a far-away button and verify that too.

Uses only CDP commands discovered from the PDL protocol definitions:
  - DOM.getDocument, DOM.querySelector, DOM.focus, DOM.getBoxModel,
    DOM.scrollIntoViewIfNeeded, DOM.resolveNode
  - Input.insertText, Input.dispatchMouseEvent
  - Runtime.evaluate
"""

import asyncio
import json
import urllib.request

import websockets


# ---------------------------------------------------------------------------
# Minimal CDP client (provided)
# ---------------------------------------------------------------------------

class CDPClient:
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self._ws = None
        self._id = 0
        self._pending: dict = {}
        self._event_handlers: dict = {}

    async def connect(self):
        self._ws = await websockets.connect(self.ws_url, max_size=50 * 1024 * 1024)
        asyncio.ensure_future(self._recv_loop())

    async def send(self, method: str, params: dict | None = None):
        self._id += 1
        msg = {"id": self._id, "method": method}
        if params:
            msg["params"] = params
        future = asyncio.get_event_loop().create_future()
        self._pending[self._id] = future
        await self._ws.send(json.dumps(msg))
        return await future

    def on(self, event: str, callback):
        self._event_handlers.setdefault(event, []).append(callback)

    async def _recv_loop(self):
        async for raw in self._ws:
            msg = json.loads(raw)
            if "id" in msg and msg["id"] in self._pending:
                f = self._pending.pop(msg["id"])
                if "error" in msg:
                    f.set_exception(RuntimeError(f"CDP error: {msg['error']}"))
                else:
                    f.set_result(msg.get("result", {}))
            elif "method" in msg:
                for cb in self._event_handlers.get(msg["method"], []):
                    cb(msg.get("params", {}))

    async def close(self):
        if self._ws:
            await self._ws.close()


# ---------------------------------------------------------------------------
# Helper: get the WebSocket debugger URL for the first page target
# ---------------------------------------------------------------------------

def get_page_ws_url() -> str:
    raw = urllib.request.urlopen("http://localhost:9222/json").read()
    targets = json.loads(raw)
    for t in targets:
        if t.get("type") == "page":
            return t["webSocketDebuggerUrl"]
    raise RuntimeError("No page target found at localhost:9222")


# ---------------------------------------------------------------------------
# Helper: click an element identified by CSS selector
# ---------------------------------------------------------------------------

async def click_element(cdp: CDPClient, root_node_id: int, selector: str):
    """Scroll element into view, compute its center, and click it."""
    # 1. Find the node
    result = await cdp.send(
        "DOM.querySelector",
        {"nodeId": root_node_id, "selector": selector},
    )
    node_id = result["nodeId"]
    if node_id == 0:
        raise RuntimeError(f"Could not find element: {selector}")

    # 2. Scroll into view so it's in the viewport
    await cdp.send(
        "DOM.scrollIntoViewIfNeeded",
        {"nodeId": node_id},
    )

    # 3. Get bounding box via getBoxModel
    box_result = await cdp.send(
        "DOM.getBoxModel",
        {"nodeId": node_id},
    )
    content_quad = box_result["model"]["content"]
    # content is a flat array: [x1, y1, x2, y2, x3, y3, x4, y4]
    xs = [content_quad[i] for i in range(0, 8, 2)]
    ys = [content_quad[i] for i in range(1, 8, 2)]
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)

    print(f"  Clicking {selector} at ({cx:.1f}, {cy:.1f})")

    # 4. Dispatch mouse events: move, press, release
    await cdp.send(
        "Input.dispatchMouseEvent",
        {"type": "mouseMoved", "x": cx, "y": cy},
    )
    await cdp.send(
        "Input.dispatchMouseEvent",
        {"type": "mousePressed", "x": cx, "y": cy, "button": "left", "clickCount": 1},
    )
    await cdp.send(
        "Input.dispatchMouseEvent",
        {"type": "mouseReleased", "x": cx, "y": cy, "button": "left", "clickCount": 1},
    )


# ---------------------------------------------------------------------------
# Helper: focus an input and type text into it
# ---------------------------------------------------------------------------

async def fill_input(cdp: CDPClient, root_node_id: int, selector: str, text: str):
    """Focus an input element via DOM.focus, select-all existing text, then
    use Input.insertText to type new text."""
    # Find the node
    result = await cdp.send(
        "DOM.querySelector",
        {"nodeId": root_node_id, "selector": selector},
    )
    node_id = result["nodeId"]
    if node_id == 0:
        raise RuntimeError(f"Could not find element: {selector}")

    # Focus it
    await cdp.send("DOM.focus", {"nodeId": node_id})

    # Select all existing text so insertText replaces it
    await cdp.send(
        "Runtime.evaluate",
        {"expression": f"document.querySelector('{selector}').select()"},
    )

    # Insert the new text
    await cdp.send("Input.insertText", {"text": text})

    print(f"  Filled {selector} with '{text}'")


# ---------------------------------------------------------------------------
# Helper: read text content of an element
# ---------------------------------------------------------------------------

async def read_text(cdp: CDPClient, selector: str) -> str:
    result = await cdp.send(
        "Runtime.evaluate",
        {
            "expression": f"document.querySelector('{selector}').textContent",
            "returnByValue": True,
        },
    )
    return result["result"]["value"]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    ws_url = get_page_ws_url()
    print(f"Connecting to: {ws_url}")

    cdp = CDPClient(ws_url=ws_url)
    await cdp.connect()

    # Enable Page domain so we can wait for loadEventFired
    await cdp.send("Page.enable")

    # Set up a future to wait for the page load event
    load_event = asyncio.get_event_loop().create_future()
    cdp.on("Page.loadEventFired", lambda params: load_event.set_result(True))

    # Navigate to the test page
    print("Navigating to test page...")
    await cdp.send("Page.navigate", {"url": "file:///tmp/cdp-test-page.html"})
    await load_event
    print("Page loaded.")

    # Enable DOM domain (required for DOM.querySelector etc.)
    await cdp.send("DOM.enable")

    # Get document root -- depth=-1 to ensure the full DOM tree is known to CDP
    doc = await cdp.send("DOM.getDocument", {"depth": -1})
    root_id = doc["root"]["nodeId"]
    print(f"Document root nodeId: {root_id}")

    # --- Step 1: Fill the name input ---
    print("\nStep 1: Fill name input")
    await fill_input(cdp=cdp, root_node_id=root_id, selector="#name-input", text="Agent Alpha")

    # --- Step 2: Fill the email input ---
    print("\nStep 2: Fill email input")
    await fill_input(cdp=cdp, root_node_id=root_id, selector="#email-input", text="alpha@test.com")

    # --- Step 3: Click submit ---
    print("\nStep 3: Click submit button")
    await click_element(cdp=cdp, root_node_id=root_id, selector="#submit-btn")

    # Small delay to let the click handler run
    await asyncio.sleep(0.1)

    # --- Step 4: Read and verify the result ---
    print("\nStep 4: Read result div")
    result_text = await read_text(cdp=cdp, selector="#result")
    print(f"  Result text: '{result_text}'")

    expected = "Submitted: Agent Alpha / alpha@test.com"
    if result_text == expected:
        print(f"  PASS: Result matches expected value")
    else:
        print(f"  FAIL: Expected '{expected}', got '{result_text}'")

    # --- Step 5: Click the far-away button (2000px below fold) ---
    print("\nStep 5: Click far-away button")
    await click_element(cdp=cdp, root_node_id=root_id, selector="#far-btn")

    await asyncio.sleep(0.1)

    result_text = await read_text(cdp=cdp, selector="#result")
    print(f"  Result text: '{result_text}'")

    if result_text == "Far button clicked!":
        print(f"  PASS: Far button click verified")
    else:
        print(f"  FAIL: Expected 'Far button clicked!', got '{result_text}'")

    await cdp.close()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
