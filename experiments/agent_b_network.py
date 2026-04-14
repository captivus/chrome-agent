"""
Raw CDP network capture experiment.

Uses only raw CDP over WebSocket (no abstraction layer) to:
1. Enable the Network domain
2. Navigate to https://example.com
3. Capture all network requests and responses during page load
4. Print URL, method, status code, and response size for each request
5. Disable the Network domain

CDP commands and events used (from Network.pdl and Page.pdl):
- Network.enable / Network.disable
- Network.requestWillBeSent (event) -- captures request URL and method
- Network.responseReceived (event) -- captures response status via Response object
- Network.loadingFinished (event) -- captures encodedDataLength (response size)
- Page.enable / Page.navigate
- Page.loadEventFired (event) -- signals page load completion
"""

import asyncio
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
    """Hit the CDP /json endpoint and return the webSocketDebuggerUrl for the first page target."""
    raw = urllib.request.urlopen("http://localhost:9222/json").read()
    targets = json.loads(raw)
    for target in targets:
        if target.get("type") == "page":
            return target["webSocketDebuggerUrl"]
    raise RuntimeError("No page target found at localhost:9222")


async def main():
    ws_url = get_page_ws_url()
    print(f"Connecting to: {ws_url}")

    client = CDPClient(ws_url=ws_url)
    await client.connect()
    print("Connected to CDP WebSocket.\n")

    # Storage for captured network data, keyed by requestId
    requests = {}  # requestId -> {url, method}
    responses = {}  # requestId -> {status, statusText, mimeType}
    sizes = {}  # requestId -> encodedDataLength

    # Event to signal page load completion
    load_event = asyncio.Event()

    # --- Register event handlers ---

    def on_request_will_be_sent(params):
        request_id = params["requestId"]
        request = params["request"]
        requests[request_id] = {
            "url": request["url"],
            "method": request["method"],
        }

    def on_response_received(params):
        request_id = params["requestId"]
        response = params["response"]
        responses[request_id] = {
            "status": response["status"],
            "statusText": response["statusText"],
            "mimeType": response["mimeType"],
        }

    def on_loading_finished(params):
        request_id = params["requestId"]
        sizes[request_id] = params["encodedDataLength"]

    def on_load_event_fired(params):
        load_event.set()

    client.on("Network.requestWillBeSent", on_request_will_be_sent)
    client.on("Network.responseReceived", on_response_received)
    client.on("Network.loadingFinished", on_loading_finished)
    client.on("Page.loadEventFired", on_load_event_fired)

    # --- Step 1: Enable Network and Page domains ---
    print("Step 1: Enabling Network domain...")
    await client.send("Network.enable")
    print("  Network domain enabled.")

    print("  Enabling Page domain (needed for loadEventFired)...")
    await client.send("Page.enable")
    print("  Page domain enabled.\n")

    # --- Step 2: Navigate to example.com ---
    print("Step 2: Navigating to https://example.com ...")
    result = await client.send("Page.navigate", {"url": "https://example.com"})
    frame_id = result.get("frameId", "unknown")
    print(f"  Navigation initiated (frameId: {frame_id})\n")

    # --- Step 3: Wait for page load to complete ---
    print("Step 3: Waiting for page load event...")
    try:
        await asyncio.wait_for(load_event.wait(), timeout=15)
        print("  Page load event fired.\n")
    except asyncio.TimeoutError:
        print("  WARNING: Timed out waiting for load event after 15s. Proceeding with captured data.\n")

    # Give a short grace period for any final loadingFinished events
    await asyncio.sleep(1)

    # --- Step 4: Print captured network data ---
    print("Step 4: Network requests captured during page load:")
    print("=" * 90)
    print(f"{'Method':<8} {'Status':<8} {'Size (bytes)':<14} {'URL'}")
    print("-" * 90)

    # Iterate over all requests that were captured
    for request_id, req_info in requests.items():
        url = req_info["url"]
        method = req_info["method"]

        resp_info = responses.get(request_id, {})
        status = resp_info.get("status", "N/A")

        size = sizes.get(request_id, "N/A")

        print(f"{method:<8} {str(status):<8} {str(size):<14} {url}")

    print("=" * 90)
    print(f"\nTotal requests captured: {len(requests)}")
    print(f"Total responses received: {len(responses)}")
    print(f"Total loadingFinished events: {len(sizes)}")

    # --- Step 5: Disable Network domain ---
    print("\nStep 5: Disabling Network domain...")
    await client.send("Network.disable")
    print("  Network domain disabled.")

    await client.close()
    print("\nDone. Connection closed.")


if __name__ == "__main__":
    asyncio.run(main())
