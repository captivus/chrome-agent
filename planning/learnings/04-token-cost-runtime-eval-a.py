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


async def main():
    # Get the page WebSocket URL
    raw = urllib.request.urlopen("http://localhost:9222/json").read()
    targets = json.loads(raw)
    page_target = next(t for t in targets if t["type"] == "page")
    ws_url = page_target["webSocketDebuggerUrl"]
    print(f"Connecting to: {ws_url}")

    cdp = CDPClient(ws_url)
    await cdp.connect()
    await asyncio.sleep(0.3)

    # 1. Navigate to the test page
    print("1. Navigating to test page...")
    await cdp.send("Page.enable")
    await cdp.send("Page.navigate", {"url": "file:///tmp/cdp-test-page.html"})
    await asyncio.sleep(1)
    print("   Done.")

    # 2. Take before screenshot
    print("2. Taking before screenshot...")
    result = await cdp.send("Page.captureScreenshot", {"format": "png"})
    with open("/tmp/token_test_a_before.png", "wb") as f:
        f.write(base64.b64decode(result["data"]))
    print("   Saved /tmp/token_test_a_before.png")

    # Helper: evaluate JS and return result
    async def evaluate(expression):
        r = await cdp.send("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
        })
        return r.get("result", {}).get("value")

    # 3. Fill #name-input with "Token Test Alpha"
    print("3. Filling #name-input...")
    await evaluate("""
        (() => {
            const el = document.querySelector('#name-input');
            el.focus();
            el.value = 'Token Test Alpha';
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
        })()
    """)
    name_val = await evaluate("document.querySelector('#name-input').value")
    print(f"   Value: {name_val}")

    # 4. Fill #email-input with "alpha@token.test"
    print("4. Filling #email-input...")
    await evaluate("""
        (() => {
            const el = document.querySelector('#email-input');
            el.focus();
            el.value = 'alpha@token.test';
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
        })()
    """)
    email_val = await evaluate("document.querySelector('#email-input').value")
    print(f"   Value: {email_val}")

    # 5. Click checkbox #check1
    print("5. Clicking checkbox #check1...")
    await evaluate("document.querySelector('#check1').click()")
    checked = await evaluate("document.querySelector('#check1').checked")
    print(f"   Checked: {checked}")

    # 6. Click submit button
    print("6. Clicking #submit-btn...")
    await evaluate("document.querySelector('#submit-btn').click()")
    await asyncio.sleep(0.3)

    # 7. Verify #result
    result_text = await evaluate("document.querySelector('#result').textContent")
    print(f"7. Result text: '{result_text}'")
    assert result_text == "Submitted: Token Test Alpha / alpha@token.test", f"Unexpected: {result_text}"
    print("   PASS")

    # 8. Scroll #far-btn into view and click it
    print("8. Scrolling to and clicking #far-btn...")
    await evaluate("document.querySelector('#far-btn').scrollIntoView({behavior: 'instant'})")
    await asyncio.sleep(0.3)
    await evaluate("document.querySelector('#far-btn').click()")
    await asyncio.sleep(0.3)

    # 9. Verify #result says "Far button clicked!"
    result_text = await evaluate("document.querySelector('#result').textContent")
    print(f"9. Result text: '{result_text}'")
    assert result_text == "Far button clicked!", f"Unexpected: {result_text}"
    print("   PASS")

    # 10. Take final screenshot
    print("10. Taking after screenshot...")
    result = await cdp.send("Page.captureScreenshot", {"format": "png"})
    with open("/tmp/token_test_a_after.png", "wb") as f:
        f.write(base64.b64decode(result["data"]))
    print("    Saved /tmp/token_test_a_after.png")

    await cdp.close()
    print("\nAll steps completed successfully!")


asyncio.run(main())
