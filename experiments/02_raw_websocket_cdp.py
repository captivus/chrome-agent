"""Experiment 2: Raw CDP over websocket -- no Playwright at all.

Questions to answer:
- Can we connect directly to Chrome's CDP websocket?
- How hard is it to send commands and receive responses?
- Can we handle events (subscriptions)?
- What's the latency vs Playwright?
- How much code does a minimal CDP client take?

Success criteria:
- WebSocket connects to Chrome's CDP endpoint
- Can send Page.captureScreenshot and get image data back
- Can subscribe to and receive events
- Latency is comparable to or better than Playwright path
"""

import asyncio
import base64
import json
import time
import urllib.request

import websockets


class MinimalCDPClient:
    """Bare-minimum CDP client over websocket. ~30 lines of real logic."""

    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self._ws = None
        self._id = 0
        self._pending = {}  # id -> Future
        self._event_handlers = {}  # method -> [callbacks]

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
                self._pending.pop(msg["id"]).set_result(msg.get("result", {}))
            elif "method" in msg:
                for cb in self._event_handlers.get(msg["method"], []):
                    cb(msg.get("params", {}))

    async def close(self):
        if self._ws:
            await self._ws.close()


def get_ws_url(port: int = 9222, *, target: str = "page") -> str:
    """Get a WebSocket debugger URL from Chrome's CDP endpoints.

    target="browser" returns the browser-level endpoint (/json/version).
    target="page" returns the first page target (/json list).
    Page-level targets support Page.*, DOM.*, etc.
    Browser-level targets support Target.*, Browser.*, etc.
    """
    if target == "browser":
        req = urllib.request.Request(f"http://localhost:{port}/json/version")
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read())
            return data["webSocketDebuggerUrl"]
    else:
        req = urllib.request.Request(f"http://localhost:{port}/json")
        with urllib.request.urlopen(req, timeout=2) as resp:
            targets = json.loads(resp.read())
            for t in targets:
                if t.get("type") == "page":
                    return t["webSocketDebuggerUrl"]
            raise RuntimeError("No page targets found")


async def main():
    ws_url = get_ws_url(target="page")
    print(f"WebSocket URL: {ws_url}\n")

    cdp = MinimalCDPClient(ws_url)
    await cdp.connect()

    try:
        # --- Test 1: Navigate ---
        print("=" * 60)
        print("TEST 1: Navigate via raw CDP")
        print("=" * 60)
        t0 = time.perf_counter()
        result = await cdp.send("Page.navigate", {"url": "https://example.com"})
        nav_time = time.perf_counter() - t0
        print(f"Navigation sent in {nav_time*1000:.1f}ms")
        print(f"Frame ID: {result.get('frameId', 'N/A')}")

        # Wait for load
        await asyncio.sleep(2)

        # --- Test 2: Screenshot ---
        print("\n" + "=" * 60)
        print("TEST 2: Page.captureScreenshot via raw websocket")
        print("=" * 60)
        t0 = time.perf_counter()
        result = await cdp.send("Page.captureScreenshot", {"format": "png"})
        ss_time = time.perf_counter() - t0
        data = base64.b64decode(result["data"])
        with open("/tmp/exp02_raw_ws.png", "wb") as f:
            f.write(data)
        print(f"Screenshot: {ss_time*1000:.1f}ms, {len(data)} bytes")

        # --- Test 3: Screencast ---
        print("\n" + "=" * 60)
        print("TEST 3: Screencast via raw websocket")
        print("=" * 60)
        frames = []

        def on_frame(params):
            frames.append({
                "size": len(params.get("data", "")),
                "session_id": params.get("sessionId"),
            })
            # ACK the frame
            asyncio.ensure_future(
                cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})
            )

        cdp.on("Page.screencastFrame", on_frame)

        await cdp.send("Page.startScreencast", {
            "format": "jpeg",
            "quality": 60,
            "maxWidth": 800,
            "maxHeight": 600,
            "everyNthFrame": 1,
        })
        print("Screencast started...")

        # Generate some visual changes
        await cdp.send("Runtime.evaluate", {
            "expression": "document.body.style.backgroundColor = 'lightblue'"
        })
        await asyncio.sleep(0.5)
        await cdp.send("Runtime.evaluate", {
            "expression": "document.body.style.backgroundColor = 'white'"
        })
        await asyncio.sleep(1.5)

        await cdp.send("Page.stopScreencast")
        print(f"Frames received: {len(frames)}")
        for i, f in enumerate(frames[:5]):
            print(f"  Frame {i}: ~{f['size']} chars base64, session_id={f['session_id']}")

        # --- Test 4: Performance metrics ---
        print("\n" + "=" * 60)
        print("TEST 4: Performance.getMetrics via raw websocket")
        print("=" * 60)
        await cdp.send("Performance.enable")
        result = await cdp.send("Performance.getMetrics")
        metrics = result.get("metrics", [])
        print(f"Got {len(metrics)} metrics:")
        for m in metrics[:10]:
            print(f"  {m['name']}: {m['value']}")

        # --- Test 5: Evaluate JS ---
        print("\n" + "=" * 60)
        print("TEST 5: Runtime.evaluate")
        print("=" * 60)
        t0 = time.perf_counter()
        result = await cdp.send("Runtime.evaluate", {
            "expression": "document.title",
            "returnByValue": True,
        })
        eval_time = time.perf_counter() - t0
        print(f"Title: {result['result']['value']} ({eval_time*1000:.1f}ms)")

        # --- Summary ---
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Raw WS CDP client:     ~40 lines of code")
        print(f"Navigation:            WORKS")
        print(f"Screenshot:            WORKS ({len(data)} bytes, {ss_time*1000:.1f}ms)")
        print(f"Screencast:            {'WORKS' if frames else 'FAILED'} ({len(frames)} frames)")
        print(f"Performance metrics:   {'WORKS' if metrics else 'FAILED'} ({len(metrics)} metrics)")
        print(f"JS evaluation:         WORKS ({eval_time*1000:.1f}ms)")

    finally:
        await cdp.close()


if __name__ == "__main__":
    asyncio.run(main())
