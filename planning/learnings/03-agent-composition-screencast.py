"""
Raw CDP screencast experiment: device emulation, screencast capture, layout metrics.
Uses only raw WebSocket CDP commands -- no abstraction layers.
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
    """Fetch the WebSocket debugger URL for the first page target."""
    resp = urllib.request.urlopen("http://localhost:9222/json")
    targets = json.loads(resp.read().decode())
    for target in targets:
        if target.get("type") == "page":
            return target["webSocketDebuggerUrl"]
    raise RuntimeError("No page target found at localhost:9222")


async def main():
    ws_url = get_page_ws_url()
    print(f"Connecting to: {ws_url}")

    client = CDPClient(ws_url=ws_url)
    await client.connect()
    print("Connected to CDP")

    # Step 1: Set device emulation to iPhone 12 Pro dimensions
    print("\n--- Step 1: Setting device emulation (iPhone 12 Pro: 390x844, scale=3, mobile) ---")
    await client.send(
        method="Emulation.setDeviceMetricsOverride",
        params={
            "width": 390,
            "height": 844,
            "deviceScaleFactor": 3,
            "mobile": True,
        },
    )
    print("Device metrics override set.")

    # Step 2: Navigate to example.com
    print("\n--- Step 2: Navigating to https://example.com ---")
    nav_result = await client.send(
        method="Page.navigate",
        params={"url": "https://example.com"},
    )
    print(f"Navigation result: frameId={nav_result.get('frameId')}, loaderId={nav_result.get('loaderId')}")

    # Wait for the page to settle
    await asyncio.sleep(2)

    # Step 3: Start screencast, collect 3 frames, stop screencast
    print("\n--- Step 3: Starting screencast (jpeg, quality=80) ---")
    frames = []
    frame_event = asyncio.Event()

    def on_screencast_frame(params):
        session_id = params["sessionId"]
        frame_data = params["data"]
        metadata = params["metadata"]
        frames.append({"data": frame_data, "metadata": metadata, "sessionId": session_id})
        print(f"  Received frame {len(frames)}: sessionId={session_id}, "
              f"size={metadata.get('deviceWidth')}x{metadata.get('deviceHeight')}, "
              f"timestamp={metadata.get('timestamp')}")
        # Acknowledge the frame so the browser sends the next one
        asyncio.ensure_future(client.send(
            method="Page.screencastFrameAck",
            params={"sessionId": session_id},
        ))
        if len(frames) >= 3:
            frame_event.set()

    client.on("Page.screencastFrame", on_screencast_frame)

    await client.send(
        method="Page.startScreencast",
        params={
            "format": "jpeg",
            "quality": 80,
            "maxWidth": 390,
            "maxHeight": 844,
            "everyNthFrame": 1,
        },
    )
    print("Screencast started. Waiting for 3 frames...")

    # The screencast only sends frames on visual changes. Inject DOM mutations
    # to force repaints so we reliably get 3 frames.
    for i in range(5):
        await asyncio.sleep(0.5)
        if len(frames) >= 3:
            break
        # Inject a visual change via Runtime.evaluate to trigger a new frame
        await client.send(
            method="Runtime.evaluate",
            params={
                "expression": f"document.body.style.backgroundColor = "
                              f"'rgb({50 + i * 40}, {100 + i * 30}, {150 + i * 20})'",
            },
        )

    # Wait for frames with a timeout
    try:
        await asyncio.wait_for(frame_event.wait(), timeout=5)
    except asyncio.TimeoutError:
        print(f"Timeout waiting for frames. Collected {len(frames)} frame(s).")

    await client.send(method="Page.stopScreencast")
    print(f"Screencast stopped. Total frames collected: {len(frames)}")

    # Step 4: Save first frame as /tmp/agent_d_frame.jpg
    print("\n--- Step 4: Saving first frame to /tmp/agent_d_frame.jpg ---")
    if frames:
        image_bytes = base64.b64decode(frames[0]["data"])
        output_path = "/tmp/agent_d_frame.jpg"
        with open(output_path, "wb") as f:
            f.write(image_bytes)
        print(f"Saved {len(image_bytes)} bytes to {output_path}")
    else:
        print("No frames captured -- nothing to save.")

    # Step 5: Get layout metrics and print viewport dimensions
    print("\n--- Step 5: Layout metrics ---")
    metrics = await client.send(method="Page.getLayoutMetrics")
    css_layout = metrics.get("cssLayoutViewport", {})
    css_visual = metrics.get("cssVisualViewport", {})
    css_content = metrics.get("cssContentSize", {})
    print(f"CSS Layout Viewport: width={css_layout.get('clientWidth')}, height={css_layout.get('clientHeight')}")
    print(f"CSS Visual Viewport: width={css_visual.get('clientWidth')}, height={css_visual.get('clientHeight')}, "
          f"zoom={css_visual.get('zoom')}, scale={css_visual.get('scale')}")
    print(f"CSS Content Size: width={css_content.get('width')}, height={css_content.get('height')}")

    # Step 6: Reset device emulation back to default
    print("\n--- Step 6: Clearing device metrics override (reset to default) ---")
    await client.send(method="Emulation.clearDeviceMetricsOverride")
    print("Device emulation reset.")

    await client.close()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
