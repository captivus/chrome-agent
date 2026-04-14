"""Raw CDP test: fill form, click submit, verify result, take screenshots."""

import asyncio
import json
import base64
import urllib.request

import websockets


class CDPClient:
    def __init__(self, ws_url):
        self.ws_url = ws_url
        self._ws = None
        self._id = 0
        self._pending = {}
        self._event_handlers = {}

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

    def on(self, event, callback):
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


def get_page_ws_url():
    """Get the WebSocket debugger URL for the first 'page' target."""
    data = urllib.request.urlopen("http://localhost:9222/json").read()
    targets = json.loads(data)
    for target in targets:
        if target.get("type") == "page":
            return target["webSocketDebuggerUrl"]
    raise RuntimeError("No page target found")


async def screenshot(client, path):
    """Capture a screenshot and save to the given path."""
    result = await client.send("Page.captureScreenshot", {"format": "png"})
    png_data = base64.b64decode(result["data"])
    with open(path, "wb") as f:
        f.write(png_data)
    print(f"Screenshot saved to {path} ({len(png_data)} bytes)")


async def evaluate(client, expression):
    """Evaluate a JS expression and return the value."""
    result = await client.send(
        "Runtime.evaluate",
        {"expression": expression, "returnByValue": True},
    )
    return result["result"].get("value")


async def main():
    ws_url = get_page_ws_url()
    print(f"Connecting to: {ws_url}")

    client = CDPClient(ws_url=ws_url)
    await client.connect()

    # Enable Page domain for screenshots
    await client.send("Page.enable")
    await client.send("Runtime.enable")

    # 1. Screenshot before
    await screenshot(client=client, path="/tmp/cdp_test_before.png")

    # 2. Fill #name-input with "CDP Test User"
    # First clear, then set the value and dispatch input event
    await evaluate(
        client=client,
        expression="""
        (() => {
            const el = document.querySelector('#name-input');
            el.focus();
            el.value = 'CDP Test User';
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
            return el.value;
        })()
        """,
    )
    print("Filled #name-input with 'CDP Test User'")

    # 3. Fill #email-input with "cdp@test.com"
    await evaluate(
        client=client,
        expression="""
        (() => {
            const el = document.querySelector('#email-input');
            el.focus();
            el.value = 'cdp@test.com';
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
            return el.value;
        })()
        """,
    )
    print("Filled #email-input with 'cdp@test.com'")

    # 4. Click the checkbox #check1
    await evaluate(
        client=client,
        expression="document.querySelector('#check1').click()",
    )
    checked = await evaluate(
        client=client,
        expression="document.querySelector('#check1').checked",
    )
    print(f"Clicked #check1 (checked={checked})")

    # 5. Click #submit-btn
    await evaluate(
        client=client,
        expression="document.querySelector('#submit-btn').click()",
    )
    print("Clicked #submit-btn")

    # Small delay to let any handler run
    await asyncio.sleep(0.2)

    # 6. Read #result div and verify
    result_text = await evaluate(
        client=client,
        expression="document.querySelector('#result').textContent",
    )
    print(f"Result text: '{result_text}'")

    expected = "Submitted: CDP Test User / cdp@test.com"
    if result_text and result_text.strip() == expected:
        print(f"PASS: Result matches expected value")
    else:
        print(f"FAIL: Expected '{expected}', got '{result_text}'")

    # 7. Screenshot after
    await screenshot(client=client, path="/tmp/cdp_test_after.png")

    await client.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
