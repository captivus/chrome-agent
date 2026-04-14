"""Test harness: compare daemon-proxied CDP vs direct WebSocket CDP.

1. Starts the daemon in a subprocess
2. Sends 5 commands via the thin client
3. Measures per-command latency through the daemon
4. Measures per-command latency via direct WebSocket (new connection each time)
5. Prints a comparison table
6. Shuts down the daemon
"""

import asyncio
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request

import websockets

SOCKET_PATH = "/tmp/chrome-agent-test.sock"
CDP_PORT = 9222

# The 5 commands to benchmark
COMMANDS = [
    ("Page.navigate", {"url": "https://example.com"}),
    ("Page.captureScreenshot", {"format": "png", "quality": 50}),
    ("Runtime.evaluate", {"expression": "document.title", "returnByValue": True}),
    ("Runtime.evaluate", {"expression": "1 + 1", "returnByValue": True}),
    ("Runtime.evaluate", {"expression": "navigator.userAgent", "returnByValue": True}),
]


def get_page_ws_url(*, port: int = CDP_PORT) -> str:
    req = urllib.request.Request(f"http://localhost:{port}/json")
    with urllib.request.urlopen(req, timeout=5) as resp:
        targets = json.loads(resp.read())
        for target in targets:
            if target.get("type") == "page":
                return target["webSocketDebuggerUrl"]
    raise RuntimeError("No page targets found")


# ── Daemon path ─────────────────────────────────────────────────────

async def send_via_daemon(*, method: str, params: dict | None = None) -> dict:
    """Send a single command through the daemon's UNIX socket."""
    reader, writer = await asyncio.open_unix_connection(path=SOCKET_PATH)

    request = {"method": method}
    if params:
        request["params"] = params

    writer.write(json.dumps(request).encode() + b"\n")
    await writer.drain()

    line = await reader.readline()
    writer.close()
    await writer.wait_closed()

    return json.loads(line.decode())


async def benchmark_daemon() -> list[tuple[str, float, dict]]:
    """Run all commands through the daemon, return (label, seconds, result)."""
    results = []
    for method, params in COMMANDS:
        t0 = time.perf_counter()
        result = await send_via_daemon(method=method, params=params)
        elapsed = time.perf_counter() - t0

        # Truncate screenshot data for display
        display_result = dict(result)
        if "data" in display_result and len(str(display_result["data"])) > 100:
            display_result["data"] = f"<{len(display_result['data'])} chars>"

        results.append((method, elapsed, display_result))

        # Small pause after navigation to let the page load
        if method == "Page.navigate":
            await asyncio.sleep(1.0)

    return results


# ── Direct WebSocket path ───────────────────────────────────────────

async def benchmark_direct() -> list[tuple[str, float, dict]]:
    """Run each command via a fresh WebSocket connection (simulates current CLI)."""
    ws_url = get_page_ws_url()
    results = []

    for method, params in COMMANDS:
        t0 = time.perf_counter()

        # New connection for each command -- this is what we're trying to beat
        ws = await websockets.connect(ws_url, max_size=50 * 1024 * 1024)
        msg = {"id": 1, "method": method}
        if params:
            msg["params"] = params
        await ws.send(json.dumps(msg))

        # Read responses until we get our command's response
        while True:
            raw = await ws.recv()
            response = json.loads(raw)
            if response.get("id") == 1:
                break

        await ws.close()
        elapsed = time.perf_counter() - t0

        result = response.get("result", response.get("error", {}))
        display_result = dict(result) if isinstance(result, dict) else {"value": result}
        if "data" in display_result and len(str(display_result["data"])) > 100:
            display_result["data"] = f"<{len(display_result['data'])} chars>"

        results.append((method, elapsed, display_result))

        if method == "Page.navigate":
            await asyncio.sleep(1.0)

    return results


# ── Shutdown ────────────────────────────────────────────────────────

async def shutdown_daemon():
    """Send shutdown command to the daemon."""
    try:
        reader, writer = await asyncio.open_unix_connection(path=SOCKET_PATH)
        writer.write(json.dumps({"method": "__shutdown__"}).encode() + b"\n")
        await writer.drain()
        line = await reader.readline()
        writer.close()
        await writer.wait_closed()
    except Exception:
        pass


# ── Main ────────────────────────────────────────────────────────────

async def run():
    # Start the daemon as a subprocess
    daemon_script = os.path.join(os.path.dirname(__file__), "session_daemon.py")
    daemon_proc = subprocess.Popen(
        [
            sys.executable,
            daemon_script,
            "--port", str(CDP_PORT),
            "--socket", SOCKET_PATH,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for the daemon to be ready (socket file appears)
    for _ in range(50):
        if os.path.exists(SOCKET_PATH):
            break
        await asyncio.sleep(0.1)
    else:
        print("ERROR: Daemon failed to start", file=sys.stderr)
        daemon_proc.kill()
        return

    # Extra moment for the daemon to fully accept connections
    await asyncio.sleep(0.3)

    try:
        print("=" * 70)
        print("SESSION DAEMON BENCHMARK")
        print("=" * 70)

        # ── Benchmark via daemon ────────────────────────────────────
        print("\nBenchmarking: commands via daemon (UNIX socket)...")
        daemon_results = await benchmark_daemon()

        # ── Benchmark via direct WebSocket ──────────────────────────
        print("Benchmarking: commands via direct WebSocket (new conn each)...\n")
        direct_results = await benchmark_direct()

        # ── Print comparison table ──────────────────────────────────
        print("=" * 70)
        print(f"{'Command':<30} {'Daemon (ms)':>12} {'Direct (ms)':>12} {'Speedup':>10}")
        print("-" * 70)

        daemon_total = 0.0
        direct_total = 0.0

        for (method, d_time, _), (_, x_time, _) in zip(
            daemon_results, direct_results
        ):
            speedup = x_time / d_time if d_time > 0 else float("inf")
            print(
                f"{method:<30} {d_time*1000:>11.1f} {x_time*1000:>11.1f} {speedup:>9.1f}x"
            )
            daemon_total += d_time
            direct_total += x_time

        print("-" * 70)
        total_speedup = direct_total / daemon_total if daemon_total > 0 else float("inf")
        print(
            f"{'TOTAL':<30} {daemon_total*1000:>11.1f} {direct_total*1000:>11.1f} {total_speedup:>9.1f}x"
        )

        print("\n" + "=" * 70)
        print("OBSERVATIONS")
        print("=" * 70)
        print(f"  Daemon overhead per command:  ~{(daemon_total / len(COMMANDS))*1000:.1f}ms avg")
        print(f"  Direct WS overhead per cmd:   ~{(direct_total / len(COMMANDS))*1000:.1f}ms avg")
        print(f"  Connection setup saved:       ~{(direct_total - daemon_total)*1000:.1f}ms total")
        print(f"  Overall speedup:              {total_speedup:.1f}x")

    finally:
        # Shutdown the daemon
        await shutdown_daemon()
        await asyncio.sleep(0.5)

        if daemon_proc.poll() is None:
            daemon_proc.send_signal(signal.SIGTERM)
            try:
                daemon_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                daemon_proc.kill()

        # Clean up socket file
        if os.path.exists(SOCKET_PATH):
            os.unlink(SOCKET_PATH)


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
