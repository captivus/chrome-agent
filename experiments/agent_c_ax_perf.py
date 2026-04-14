"""
Raw CDP experiment: Accessibility tree, Performance metrics, and DOM snapshot.
Uses only raw WebSocket CDP commands -- no abstraction layers.
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
    """Hit the CDP /json endpoint and return the WebSocket URL for the first page target."""
    raw = urllib.request.urlopen("http://localhost:9222/json").read()
    targets = json.loads(raw)
    for target in targets:
        if target.get("type") == "page":
            return target["webSocketDebuggerUrl"]
    raise RuntimeError("No page target found")


async def main():
    ws_url = get_page_ws_url()
    print(f"Connecting to: {ws_url}\n")

    client = CDPClient(ws_url=ws_url)
    await client.connect()

    # ── 1. Accessibility tree ──────────────────────────────────────────
    print("=" * 60)
    print("1. ACCESSIBILITY TREE")
    print("=" * 60)

    await client.send(method="Accessibility.enable")
    ax_result = await client.send(method="Accessibility.getFullAXTree")
    ax_nodes = ax_result.get("nodes", [])

    ignored_count = sum(1 for n in ax_nodes if n.get("ignored"))
    not_ignored_count = len(ax_nodes) - ignored_count

    # Collect roles from non-ignored nodes
    role_counts = {}
    for node in ax_nodes:
        if not node.get("ignored"):
            role_val = node.get("role", {}).get("value", "(none)")
            role_counts[role_val] = role_counts.get(role_val, 0) + 1

    print(f"  Total AX nodes:       {len(ax_nodes)}")
    print(f"  Ignored nodes:        {ignored_count}")
    print(f"  Meaningful nodes:     {not_ignored_count}")
    print(f"  Roles present:")
    for role, count in sorted(role_counts.items()):
        print(f"    {role}: {count}")

    # Show a few named nodes as examples
    named_nodes = [
        n for n in ax_nodes
        if not n.get("ignored") and n.get("name", {}).get("value")
    ]
    if named_nodes:
        print(f"  Sample named nodes (up to 5):")
        for n in named_nodes[:5]:
            role = n.get("role", {}).get("value", "?")
            name = n.get("name", {}).get("value", "?")
            print(f"    [{role}] \"{name}\"")

    # ── 2. Performance metrics ─────────────────────────────────────────
    print()
    print("=" * 60)
    print("2. PERFORMANCE METRICS")
    print("=" * 60)

    await client.send(method="Performance.enable")
    perf_result = await client.send(method="Performance.getMetrics")
    metrics = perf_result.get("metrics", [])

    print(f"  Total metrics:        {len(metrics)}")
    print(f"  Available metrics:")
    for m in metrics:
        name = m["name"]
        value = m["value"]
        # Format large numbers with commas, floats with reasonable precision
        if isinstance(value, float) and value != int(value):
            formatted = f"{value:.4f}"
        else:
            formatted = f"{int(value):,}"
        print(f"    {name}: {formatted}")

    # ── 3. DOM snapshot with layout info ───────────────────────────────
    print()
    print("=" * 60)
    print("3. DOM SNAPSHOT")
    print("=" * 60)

    snapshot_result = await client.send(
        method="DOMSnapshot.captureSnapshot",
        params={
            "computedStyles": ["display", "visibility", "width", "height"],
            "includeDOMRects": True,
            "includePaintOrder": True,
        },
    )

    documents = snapshot_result.get("documents", [])
    strings = snapshot_result.get("strings", [])

    print(f"  Documents in snapshot: {len(documents)}")
    print(f"  Shared string table:   {len(strings)} entries")

    for i, doc in enumerate(documents):
        nodes = doc.get("nodes", {})
        layout = doc.get("layout", {})
        text_boxes = doc.get("textBoxes", {})

        # Node count is the length of any of the parallel arrays in NodeTreeSnapshot
        node_count = len(nodes.get("nodeType", []))
        layout_node_count = len(layout.get("nodeIndex", []))
        text_box_count = len(text_boxes.get("layoutIndex", []))

        # Count node types
        node_type_names = {
            1: "ELEMENT",
            3: "TEXT",
            8: "COMMENT",
            9: "DOCUMENT",
            10: "DOCUMENT_TYPE",
        }
        type_counts = {}
        for nt in nodes.get("nodeType", []):
            label = node_type_names.get(nt, f"TYPE_{nt}")
            type_counts[label] = type_counts.get(label, 0) + 1

        # Resolve document URL from string table
        doc_url_idx = doc.get("documentURL", 0)
        doc_url = strings[doc_url_idx] if doc_url_idx < len(strings) else "(unknown)"

        print(f"\n  Document {i}: {doc_url}")
        print(f"    Total DOM nodes:      {node_count}")
        print(f"    Layout nodes:         {layout_node_count}")
        print(f"    Text boxes:           {text_box_count}")
        print(f"    Node type breakdown:")
        for label, count in sorted(type_counts.items()):
            print(f"      {label}: {count}")

        # Show elements with their bounding boxes (first few)
        bounds = layout.get("bounds", [])
        node_indices = layout.get("nodeIndex", [])
        node_names = nodes.get("nodeName", [])

        if bounds and node_indices:
            print(f"    Sample layout bounds (up to 5):")
            for j in range(min(5, len(bounds))):
                dom_idx = node_indices[j]
                name_idx = node_names[dom_idx] if dom_idx < len(node_names) else 0
                name = strings[name_idx] if name_idx < len(strings) else "?"
                rect = bounds[j]
                print(f"      <{name}> at [{rect[0]:.0f}, {rect[1]:.0f}, {rect[2]:.0f}, {rect[3]:.0f}]")

    await client.close()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
