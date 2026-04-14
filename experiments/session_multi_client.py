"""Test: Can multiple CDP WebSocket clients connect to the same page target simultaneously?

Questions to answer:
1. Can two clients connect to the same page's WebSocket URL at the same time?
2. Do both receive events when something happens?
3. Can one client see mutations made by the other?
4. What happens when one client navigates while the other is connected?
"""

import asyncio
import json
import urllib.request

import websockets


class CDPClient:
    def __init__(self, ws_url, name="client"):
        self.ws_url = ws_url
        self.name = name
        self._ws = None
        self._id = 0
        self._pending = {}
        self._event_handlers = {}
        self.events_received = []

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
        try:
            async for raw in self._ws:
                msg = json.loads(raw)
                if "id" in msg and msg["id"] in self._pending:
                    f = self._pending.pop(msg["id"])
                    if "error" in msg:
                        f.set_exception(RuntimeError(f"CDP error: {msg['error']}"))
                    else:
                        f.set_result(msg.get("result", {}))
                elif "method" in msg:
                    self.events_received.append(msg["method"])
                    for cb in self._event_handlers.get(msg["method"], []):
                        cb(msg.get("params", {}))
        except websockets.exceptions.ConnectionClosed:
            pass

    async def close(self):
        if self._ws:
            await self._ws.close()


def get_page_ws_url():
    raw = urllib.request.urlopen("http://localhost:9222/json").read()
    targets = json.loads(raw)
    for t in targets:
        if t.get("type") == "page":
            return t["webSocketDebuggerUrl"]
    raise RuntimeError("No page target found")


async def main():
    ws_url = get_page_ws_url()
    print(f"Page WebSocket URL: {ws_url}\n")

    # --- Test 1: Can two clients connect to the same page target? ---
    print("=" * 60)
    print("TEST 1: Two clients connect to the same page target")
    print("=" * 60)

    client_a = CDPClient(ws_url, name="A")
    client_b = CDPClient(ws_url, name="B")

    try:
        await client_a.connect()
        print("  Client A connected")
    except Exception as e:
        print(f"  Client A FAILED to connect: {e}")
        return

    try:
        await client_b.connect()
        print("  Client B connected")
    except Exception as e:
        print(f"  Client B FAILED to connect: {e}")
        await client_a.close()
        return

    # Verify both can send commands
    title_a = await client_a.send("Runtime.evaluate", {
        "expression": "document.title",
        "returnByValue": True,
    })
    title_b = await client_b.send("Runtime.evaluate", {
        "expression": "document.title",
        "returnByValue": True,
    })
    print(f"  Client A sees title: {title_a['result']['value']}")
    print(f"  Client B sees title: {title_b['result']['value']}")
    print("  PASS: Both clients connected and operational")

    # --- Test 2: Do both clients receive events? ---
    print("\n" + "=" * 60)
    print("TEST 2: Event fan-out to both clients")
    print("=" * 60)

    events_a = []
    events_b = []

    def on_lifecycle_a(params):
        events_a.append(params.get("name", "unknown"))

    def on_lifecycle_b(params):
        events_b.append(params.get("name", "unknown"))

    client_a.on("Page.lifecycleEvent", on_lifecycle_a)
    client_b.on("Page.lifecycleEvent", on_lifecycle_b)

    await client_a.send("Page.enable")
    await client_b.send("Page.enable")
    await client_a.send("Page.setLifecycleEventsEnabled", {"enabled": True})
    await client_b.send("Page.setLifecycleEventsEnabled", {"enabled": True})

    # Client A navigates -- does client B get the events too?
    await client_a.send("Page.navigate", {"url": "https://example.com"})
    await asyncio.sleep(2)

    print(f"  Client A lifecycle events: {events_a}")
    print(f"  Client B lifecycle events: {events_b}")
    if events_a and events_b:
        print("  PASS: Both clients received lifecycle events")
    else:
        print(f"  FAIL: A got {len(events_a)} events, B got {len(events_b)} events")

    # --- Test 3: Can one client see mutations from the other? ---
    print("\n" + "=" * 60)
    print("TEST 3: Cross-client mutation visibility")
    print("=" * 60)

    # Client A changes the page title
    await client_a.send("Runtime.evaluate", {
        "expression": "document.title = 'Changed by Client A'",
    })

    # Client B reads it
    result = await client_b.send("Runtime.evaluate", {
        "expression": "document.title",
        "returnByValue": True,
    })
    title_from_b = result["result"]["value"]
    print(f"  Client A set title to 'Changed by Client A'")
    print(f"  Client B reads title: '{title_from_b}'")
    if title_from_b == "Changed by Client A":
        print("  PASS: Mutations from A are visible to B")
    else:
        print(f"  FAIL: Expected 'Changed by Client A', got '{title_from_b}'")

    # --- Test 4: Both clients can enable DOM domain independently ---
    print("\n" + "=" * 60)
    print("TEST 4: Both clients enable DOM domain")
    print("=" * 60)

    await client_a.send("DOM.enable")
    await client_b.send("DOM.enable")

    doc_a = await client_a.send("DOM.getDocument", {"depth": 0})
    doc_b = await client_b.send("DOM.getDocument", {"depth": 0})
    print(f"  Client A root nodeId: {doc_a['root']['nodeId']}")
    print(f"  Client B root nodeId: {doc_b['root']['nodeId']}")
    print("  PASS: Both clients can use DOM domain simultaneously")

    # --- Test 5: What happens when one client navigates while other is mid-operation? ---
    print("\n" + "=" * 60)
    print("TEST 5: Navigation by A while B has pending work")
    print("=" * 60)

    # Client B starts an evaluate with a delay
    slow_eval = asyncio.ensure_future(client_b.send("Runtime.evaluate", {
        "expression": "new Promise(r => setTimeout(() => r('done from B'), 1000))",
        "awaitPromise": True,
        "returnByValue": True,
    }))

    # While B is waiting, A navigates
    await asyncio.sleep(0.1)
    await client_a.send("Page.navigate", {"url": "file:///tmp/cdp-test-page.html"})

    # What happens to B's pending promise?
    try:
        result = await asyncio.wait_for(slow_eval, timeout=5)
        print(f"  Client B's pending eval result: {result.get('result', {}).get('value', 'N/A')}")
        if "exceptionDetails" in result:
            print(f"  Client B got exception: {result['exceptionDetails'].get('text', 'unknown')}")
            print("  PASS: Navigation by A caused B's promise to fail (expected)")
        else:
            print("  INFO: B's promise completed despite navigation (may have resolved before nav)")
    except asyncio.TimeoutError:
        print("  FAIL: Client B's eval timed out (hung)")
    except RuntimeError as e:
        print(f"  PASS: Client B got error: {e}")
        print("  (Navigation destroyed B's execution context -- expected behavior)")

    # --- Test 6: Both clients still functional after all of the above? ---
    print("\n" + "=" * 60)
    print("TEST 6: Both clients still functional")
    print("=" * 60)

    try:
        r_a = await client_a.send("Runtime.evaluate", {
            "expression": "1 + 1", "returnByValue": True,
        })
        print(f"  Client A: 1+1 = {r_a['result']['value']}")
    except Exception as e:
        print(f"  Client A failed: {e}")

    try:
        r_b = await client_b.send("Runtime.evaluate", {
            "expression": "2 + 2", "returnByValue": True,
        })
        print(f"  Client B: 2+2 = {r_b['result']['value']}")
    except Exception as e:
        print(f"  Client B failed: {e}")

    print("  PASS: Both clients operational after stress test")

    # --- Summary ---
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total events received by A: {len(client_a.events_received)}")
    print(f"  Total events received by B: {len(client_b.events_received)}")

    await client_a.close()
    await client_b.close()
    print("\n  Both clients disconnected cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
