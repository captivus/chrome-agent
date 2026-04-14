import asyncio, json, base64, urllib.request
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


async def screenshot(cdp, path):
    result = await cdp.send("Page.captureScreenshot", {"format": "png"})
    with open(path, "wb") as f:
        f.write(base64.b64decode(result["data"]))
    print(f"Screenshot saved to {path}")


async def evaluate(cdp, expression):
    result = await cdp.send(
        "Runtime.evaluate",
        {"expression": expression, "returnByValue": True},
    )
    return result.get("result", {}).get("value")


async def main():
    # Get page WS URL
    raw = urllib.request.urlopen("http://localhost:9222/json").read()
    targets = json.loads(raw)
    page_target = next(t for t in targets if t["type"] == "page")
    ws_url = page_target["webSocketDebuggerUrl"]
    print(f"Connecting to {ws_url}")

    cdp = CDPClient(ws_url)
    await cdp.connect()
    await asyncio.sleep(0.3)

    # 1. Navigate
    print("\n1. Navigating to test page...")
    await cdp.send("Page.enable")
    await cdp.send("Page.navigate", {"url": "file:///tmp/cdp-test-page.html"})
    await asyncio.sleep(1)
    print("   Done.")

    # 2. Screenshot before
    print("\n2. Taking before screenshot...")
    await screenshot(cdp, "/tmp/token_test_b_before.png")

    # 3. Fill #name-input with "Token Test Beta"
    print("\n3. Filling #name-input...")
    await cdp.send("Runtime.evaluate", {
        "expression": """
            (() => {
                const el = document.querySelector('#name-input');
                el.focus();
                el.value = 'Token Test Beta';
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
            })()
        """
    })
    val = await evaluate(cdp, "document.querySelector('#name-input').value")
    print(f"   name-input value: {val}")
    assert val == "Token Test Beta", f"Expected 'Token Test Beta', got '{val}'"

    # 4. Fill #email-input with "beta@token.test"
    print("\n4. Filling #email-input...")
    await cdp.send("Runtime.evaluate", {
        "expression": """
            (() => {
                const el = document.querySelector('#email-input');
                el.focus();
                el.value = 'beta@token.test';
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
            })()
        """
    })
    val = await evaluate(cdp, "document.querySelector('#email-input').value")
    print(f"   email-input value: {val}")
    assert val == "beta@token.test", f"Expected 'beta@token.test', got '{val}'"

    # 5. Click checkbox #check1
    print("\n5. Clicking checkbox #check1...")
    await cdp.send("Runtime.evaluate", {
        "expression": "document.querySelector('#check1').click()"
    })
    checked = await evaluate(cdp, "document.querySelector('#check1').checked")
    print(f"   check1 checked: {checked}")
    assert checked is True, f"Expected checked=True, got {checked}"

    # 6. Click submit button
    print("\n6. Clicking #submit-btn...")
    await cdp.send("Runtime.evaluate", {
        "expression": "document.querySelector('#submit-btn').click()"
    })
    await asyncio.sleep(0.2)

    # 7. Verify #result
    print("\n7. Verifying #result after submit...")
    result_text = await evaluate(cdp, "document.querySelector('#result').textContent")
    print(f"   result: {result_text}")
    assert result_text == "Submitted: Token Test Beta / beta@token.test", \
        f"Unexpected result: '{result_text}'"

    # 8. Scroll #far-btn into view and click it
    print("\n8. Scrolling to and clicking #far-btn...")
    await cdp.send("Runtime.evaluate", {
        "expression": "document.querySelector('#far-btn').scrollIntoView({behavior: 'instant', block: 'center'})"
    })
    await asyncio.sleep(0.3)
    await cdp.send("Runtime.evaluate", {
        "expression": "document.querySelector('#far-btn').click()"
    })
    await asyncio.sleep(0.2)

    # 9. Verify #result says "Far button clicked!"
    print("\n9. Verifying #result after far-btn click...")
    result_text = await evaluate(cdp, "document.querySelector('#result').textContent")
    print(f"   result: {result_text}")
    assert result_text == "Far button clicked!", f"Unexpected result: '{result_text}'"

    # 10. Final screenshot
    print("\n10. Taking after screenshot...")
    await screenshot(cdp, "/tmp/token_test_b_after.png")

    print("\nAll steps completed successfully!")
    await cdp.close()


asyncio.run(main())
