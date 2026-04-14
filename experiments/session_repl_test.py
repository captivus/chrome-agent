"""Test harness for session_repl.py.

Measures per-command latency over a persistent REPL connection vs. fresh
WebSocket connections to quantify the session persistence benefit.

Design: to make the comparison fair, we pre-navigate to example.com in both
paths so that network I/O doesn't confound the timing. The timed commands
are all fast local operations (screenshot, JS evaluation, DOM queries).
"""

import json
import subprocess
import sys
import time
import urllib.request

import websockets
import asyncio


REPL_SCRIPT = "/home/captivus/projects/chrome-agent/experiments/session_repl.py"

# Commands to benchmark (method, params_dict_or_None, label)
COMMANDS = [
    ("Page.captureScreenshot", {"format": "png"}, "screenshot"),
    ("Runtime.evaluate", {"expression": "document.title", "returnByValue": True}, "eval: title"),
    ("Runtime.evaluate", {"expression": "window.location.href", "returnByValue": True}, "eval: href"),
    ("Runtime.evaluate", {"expression": "navigator.userAgent", "returnByValue": True}, "eval: UA"),
    ("Runtime.evaluate", {"expression": "document.querySelectorAll('*').length", "returnByValue": True}, "eval: DOM count"),
]


def get_page_ws_url(port: int = 9222) -> str:
    req = urllib.request.Request(f"http://localhost:{port}/json")
    with urllib.request.urlopen(req, timeout=5) as resp:
        targets = json.loads(resp.read())
        for t in targets:
            if t.get("type") == "page":
                return t["webSocketDebuggerUrl"]
        raise RuntimeError("No page targets found")


def format_line(method: str, params: dict | None) -> str:
    """Format a command line for the REPL."""
    if params:
        return f"{method} {json.dumps(params)}\n"
    return f"{method}\n"


def send_repl_cmd(proc, method: str, params: dict | None = None) -> tuple[dict, float]:
    """Send a command to the REPL subprocess and return (response, latency_ms)."""
    line = format_line(method=method, params=params)
    t0 = time.perf_counter()
    proc.stdin.write(line.encode())
    proc.stdin.flush()
    resp_line = proc.stdout.readline().decode().strip()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    resp = json.loads(resp_line)
    return resp, elapsed_ms


def test_repl_session() -> list[dict]:
    """Run commands through session_repl.py, measure per-command latency."""
    proc = subprocess.Popen(
        [sys.executable, "-u", REPL_SCRIPT],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    results = []

    try:
        # Wait for ready signal
        ready_line = proc.stdout.readline().decode().strip()
        ready = json.loads(ready_line)
        assert ready.get("status") == "ready", f"Expected ready, got: {ready}"
        print("  REPL is ready.")

        # Warmup: navigate to example.com and wait for load
        print("  Warming up (navigating to example.com)...")
        send_repl_cmd(proc, method="Page.navigate", params={"url": "https://example.com"})
        time.sleep(2)  # Let the page fully load

        # Now run timed commands
        for method, params, label in COMMANDS:
            resp, elapsed_ms = send_repl_cmd(proc, method=method, params=params)

            results.append({
                "label": label,
                "method": method,
                "latency_ms": elapsed_ms,
                "success": "error" not in resp,
            })
            print(f"    {label}: {elapsed_ms:.2f}ms")

    finally:
        proc.stdin.close()
        proc.wait(timeout=10)

    return results


async def _single_fresh_connection(method: str, params: dict | None) -> float:
    """Open a fresh WebSocket, enable domains, send one command, close.

    Returns total latency in ms (connect + enable domains + command + close).
    This is what each CLI invocation costs today.
    """
    ws_url = get_page_ws_url()
    t0 = time.perf_counter()

    async with websockets.connect(ws_url, max_size=50 * 1024 * 1024) as ws:
        msg_id = 0

        async def send_cmd(m: str, p: dict | None = None) -> dict:
            nonlocal msg_id
            msg_id += 1
            msg = {"id": msg_id, "method": m}
            if p:
                msg["params"] = p
            await ws.send(json.dumps(msg))
            while True:
                raw = await ws.recv()
                resp = json.loads(raw)
                if resp.get("id") == msg_id:
                    return resp

        # Enable domains (same overhead as REPL startup, but paid each time)
        for domain in ("Page", "DOM", "Runtime"):
            await send_cmd(m=f"{domain}.enable")

        # Send the actual command
        await send_cmd(m=method, p=params)

    elapsed_ms = (time.perf_counter() - t0) * 1000
    return elapsed_ms


def test_fresh_connections() -> list[dict]:
    """Run each command with a fresh WebSocket connection, measure total latency."""
    # Pre-navigate so the page is loaded (same state as REPL test)
    asyncio.run(_warmup_navigate())

    results = []
    for method, params, label in COMMANDS:
        elapsed_ms = asyncio.run(_single_fresh_connection(method=method, params=params))
        results.append({
            "label": label,
            "method": method,
            "latency_ms": elapsed_ms,
        })
        print(f"    {label}: {elapsed_ms:.2f}ms")
    return results


async def _warmup_navigate():
    """Navigate to example.com via a fresh connection so the page is loaded for tests."""
    ws_url = get_page_ws_url()
    async with websockets.connect(ws_url, max_size=50 * 1024 * 1024) as ws:
        msg = {"id": 1, "method": "Page.enable"}
        await ws.send(json.dumps(msg))
        await ws.recv()
        msg = {"id": 2, "method": "Page.navigate", "params": {"url": "https://example.com"}}
        await ws.send(json.dumps(msg))
        await ws.recv()
    await asyncio.sleep(2)


def print_comparison(repl_results: list[dict], fresh_results: list[dict]):
    """Print a side-by-side comparison table."""
    print()
    print("=" * 80)
    print("COMPARISON: REPL (persistent WS) vs Fresh Connection per command")
    print("=" * 80)
    print()
    print("REPL cost = command round-trip only (connection already open)")
    print("Fresh cost = WS connect + enable 3 domains + command + WS close")
    print()
    print(f"{'Command':<25} {'REPL (ms)':>10} {'Fresh (ms)':>11} {'Speedup':>9}")
    print("-" * 60)

    total_repl = 0.0
    total_fresh = 0.0

    for repl, fresh in zip(repl_results, fresh_results):
        label = repl["label"]
        r_ms = repl["latency_ms"]
        f_ms = fresh["latency_ms"]
        speedup = f_ms / r_ms if r_ms > 0 else float("inf")
        total_repl += r_ms
        total_fresh += f_ms
        print(f"{label:<25} {r_ms:>9.2f} {f_ms:>10.2f} {speedup:>8.1f}x")

    print("-" * 60)
    total_speedup = total_fresh / total_repl if total_repl > 0 else float("inf")
    print(f"{'TOTAL':<25} {total_repl:>9.2f} {total_fresh:>10.2f} {total_speedup:>8.1f}x")
    print()
    print(f"Total time saved: {total_fresh - total_repl:.1f}ms across {len(COMMANDS)} commands")
    print(f"Average per-command saving: {(total_fresh - total_repl) / len(COMMANDS):.1f}ms")
    print(f"Connection overhead per invocation: ~{(total_fresh - total_repl) / len(COMMANDS):.1f}ms")


def main():
    print("Phase 1: REPL session (persistent WebSocket)")
    print("-" * 50)
    repl_results = test_repl_session()

    time.sleep(0.5)

    print()
    print("Phase 2: Fresh connections (one WebSocket per command)")
    print("-" * 50)
    fresh_results = test_fresh_connections()

    print_comparison(repl_results=repl_results, fresh_results=fresh_results)


if __name__ == "__main__":
    main()
