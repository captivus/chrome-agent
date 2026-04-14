"""Experiment 1: Can Playwright's CDPSession send raw CDP commands in attach mode?

Questions to answer:
- Does page.context.new_cdp_session() work when connected via connect_over_cdp?
- Can we call Page.captureScreenshot directly (bypassing Playwright's screenshot)?
- Can we call Page.startScreencast and receive screencastFrame events?
- Can we call Performance.getMetrics?
- What does the latency look like vs Playwright's own methods?

Success criteria:
- CDPSession connects without error
- Raw Page.captureScreenshot returns base64 image data
- Page.startScreencast emits at least one screencastFrame event
- Performance.getMetrics returns metric data
"""

import asyncio
import base64
import time

from playwright.async_api import async_playwright


async def main():
    pw = await async_playwright().start()

    try:
        browser = await pw.chromium.connect_over_cdp("http://localhost:9222")
        page = browser.contexts[0].pages[0]

        # Navigate somewhere with actual content
        await page.goto("https://example.com")
        print(f"Page loaded: {page.url}\n")

        # --- Test 1: Get a CDPSession ---
        print("=" * 60)
        print("TEST 1: Create CDPSession from attached page")
        print("=" * 60)
        try:
            cdp = await page.context.new_cdp_session(page)
            print(f"SUCCESS: CDPSession created, type={type(cdp).__name__}")
        except Exception as e:
            print(f"FAILED: {type(e).__name__}: {e}")
            await pw.stop()
            return

        # --- Test 2: Raw Page.captureScreenshot vs Playwright screenshot ---
        print("\n" + "=" * 60)
        print("TEST 2: Raw CDP captureScreenshot vs Playwright screenshot")
        print("=" * 60)

        # Playwright's method
        t0 = time.perf_counter()
        await page.screenshot(path="/tmp/exp01_playwright.png")
        pw_time = time.perf_counter() - t0
        print(f"Playwright screenshot: {pw_time*1000:.1f}ms")

        # Raw CDP method
        t0 = time.perf_counter()
        result = await cdp.send("Page.captureScreenshot", {"format": "png"})
        cdp_time = time.perf_counter() - t0
        data = base64.b64decode(result["data"])
        with open("/tmp/exp01_cdp_raw.png", "wb") as f:
            f.write(data)
        print(f"Raw CDP screenshot:   {cdp_time*1000:.1f}ms")
        print(f"Raw CDP returned {len(data)} bytes")

        # --- Test 3: Page.startScreencast ---
        print("\n" + "=" * 60)
        print("TEST 3: Page.startScreencast (frame streaming)")
        print("=" * 60)

        frames_received = []

        def on_screencast_frame(params):
            frames_received.append({
                "size": len(params["data"]),
                "session_id": params["sessionId"],
                "metadata": params.get("metadata", {}),
            })
            # Must ACK each frame to keep receiving
            asyncio.ensure_future(
                cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})
            )

        cdp.on("Page.screencastFrame", on_screencast_frame)

        await cdp.send("Page.startScreencast", {
            "format": "jpeg",
            "quality": 60,
            "maxWidth": 800,
            "maxHeight": 600,
            "everyNthFrame": 1,
        })
        print("Screencast started, waiting 2 seconds for frames...")

        # Trigger some activity to generate frames
        await page.evaluate("window.scrollTo(0, 100)")
        await asyncio.sleep(0.5)
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(1.5)

        await cdp.send("Page.stopScreencast")
        print(f"Screencast stopped. Frames received: {len(frames_received)}")
        for i, frame in enumerate(frames_received[:5]):
            print(f"  Frame {i}: {frame['size']} bytes, session_id={frame['session_id']}")
            if frame["metadata"]:
                meta = frame["metadata"]
                print(f"    offset: ({meta.get('offsetTop', '?')}, {meta.get('offsetLeft', '?')})")
                print(f"    size: {meta.get('pageScaleFactor', '?')}x scale")

        # --- Test 4: Performance.getMetrics ---
        print("\n" + "=" * 60)
        print("TEST 4: Performance.getMetrics")
        print("=" * 60)

        await cdp.send("Performance.enable")
        result = await cdp.send("Performance.getMetrics")
        metrics = result.get("metrics", [])
        print(f"Got {len(metrics)} metrics:")
        for m in metrics[:10]:
            print(f"  {m['name']}: {m['value']}")
        if len(metrics) > 10:
            print(f"  ... ({len(metrics) - 10} more)")

        # --- Test 5: Network domain enable + check ---
        print("\n" + "=" * 60)
        print("TEST 5: Network domain (enable + intercept info)")
        print("=" * 60)

        requests_seen = []

        def on_request(params):
            requests_seen.append(params.get("request", {}).get("url", "unknown"))

        cdp.on("Network.requestWillBeSent", on_request)
        await cdp.send("Network.enable")
        print("Network domain enabled, navigating to trigger requests...")

        await page.goto("https://example.com")
        await asyncio.sleep(1)

        print(f"Requests captured: {len(requests_seen)}")
        for url in requests_seen[:5]:
            print(f"  {url}")

        await cdp.send("Network.disable")

        # --- Summary ---
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"CDPSession from attach mode: WORKS")
        print(f"Raw captureScreenshot:       WORKS ({len(data)} bytes)")
        print(f"Screencast frame streaming:  {'WORKS' if frames_received else 'FAILED'} ({len(frames_received)} frames)")
        print(f"Performance metrics:         {'WORKS' if metrics else 'FAILED'} ({len(metrics)} metrics)")
        print(f"Network request capture:     {'WORKS' if requests_seen else 'FAILED'} ({len(requests_seen)} requests)")

    finally:
        await pw.stop()


if __name__ == "__main__":
    asyncio.run(main())
