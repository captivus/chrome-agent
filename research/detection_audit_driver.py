"""Detection audit driver for chrome-agent.

Drives three browser configurations against bot.sannysoft.com + CreepJS and a
custom in-page probe, to measure what each leaks to a website's automation
detection. Headed Chrome, isolated temp registry, dedicated ports.

Run: uv run python research/detection_audit_driver.py
Writes structured results to stdout (JSON) and screenshots to /tmp/ca_audit_*.
"""

import asyncio
import base64
import json
import os
import signal

from chrome_agent.launcher import launch_browser
from chrome_agent.cdp_client import CDPClient, get_ws_url

REG = "/tmp/ca_audit_registry.json"
FP = "/tmp/ca_audit_fp.json"

# The proposed window-border marker (border + corner badge + title prefix).
MARKER_JS = r"""
(() => {
  const NAME = "chrome-agent-audit", COLOR = "#ff2d55";
  const PREFIX = "🤖 " + NAME + " — ";
  const fixTitle = () => { try { const t = document.title || ""; if (!t.startsWith(PREFIX)) document.title = PREFIX + t; } catch (e) {} };
  const draw = () => {
    if (!document.documentElement) return;
    if (document.getElementById("__ca_marker__")) return;
    const f = document.createElement("div"); f.id = "__ca_marker__";
    f.style.cssText = "position:fixed;inset:0;border:6px solid " + COLOR + ";box-sizing:border-box;pointer-events:none;z-index:2147483647";
    const b = document.createElement("div"); b.textContent = "🤖 " + NAME;
    b.style.cssText = "position:absolute;top:0;left:0;background:" + COLOR + ";color:#fff;font:600 12px/1.4 system-ui,sans-serif;padding:3px 8px;pointer-events:none";
    f.appendChild(b); document.documentElement.appendChild(f);
  };
  const start = () => {
    const el = document.querySelector("title");
    if (el) new MutationObserver(fixTitle).observe(el, {childList:true, characterData:true, subtree:true});
    if (document.head) new MutationObserver(fixTitle).observe(document.head, {childList:true, subtree:true});
    fixTitle(); draw();
  };
  if (document.documentElement) start(); else document.addEventListener("DOMContentLoaded", start);
  new MutationObserver(draw).observe(document.documentElement || document, {childList:true});
})();
"""

# Custom probe: the exact vectors hypothesized as detectable.
PROBE_JS = r"""
(() => {
  const natget = (proto, prop) => {
    try { const d = Object.getOwnPropertyDescriptor(proto, prop);
      return d && d.get ? (d.get.toString().includes("[native code]") ? "native" : "SPOOFED(" + d.get.toString().slice(0,40) + ")") : "no-getter";
    } catch (e) { return "err"; }
  };
  return {
    webdriver: navigator.webdriver,
    webdriver_own_property: Object.prototype.hasOwnProperty.call(navigator, "webdriver"),
    platform: navigator.platform,
    platform_getter: natget(Navigator.prototype, "platform"),
    vendor: navigator.vendor,
    vendor_getter: natget(Navigator.prototype, "vendor"),
    chrome_present: !!window.chrome,
    chrome_runtime: !!(window.chrome && window.chrome.runtime),
    chrome_keys: window.chrome ? Object.keys(window.chrome) : null,
    languages: navigator.languages,
    plugins_len: navigator.plugins.length,
    ua_has_headless: /headless/i.test(navigator.userAgent),
    ua: navigator.userAgent,
    marker_div_findable: !!document.getElementById("__ca_marker__"),
    title: document.title,
  };
})()
"""


async def evaluate(cdp, expr, session_id=None):
    r = await cdp.send(method="Runtime.evaluate",
                       params={"expression": expr, "returnByValue": True},
                       session_id=session_id)
    return r["result"]["value"]


async def screenshot(cdp, path, session_id=None):
    r = await cdp.send(method="Page.captureScreenshot", params={"format": "png"}, session_id=session_id)
    with open(path, "wb") as f:
        f.write(base64.b64decode(r["data"]))


async def run_config(label, *, fingerprint=None, inject_marker=False, port):
    info = await launch_browser(port_override=port, fingerprint=fingerprint,
                                headless=False, pin_to_desktop=False, registry_path=REG)
    out = {"config": label, "port": port}
    try:
        ws = get_ws_url(port=port, target_type="page")
        cdp = CDPClient(ws_url=ws)
        await cdp.connect()
        await cdp.send(method="Page.enable")
        if inject_marker:
            await cdp.send(method="Page.addScriptToEvaluateOnNewDocument", params={"source": MARKER_JS})

        # sannysoft
        await cdp.send(method="Page.navigate", params={"url": "https://bot.sannysoft.com/"})
        await asyncio.sleep(4)
        out["probe"] = await evaluate(cdp, PROBE_JS)
        body = await evaluate(cdp, "document.body.innerText.slice(0,1400)")
        out["sannysoft_text"] = body
        await screenshot(cdp, f"/tmp/ca_audit_{label}_sannysoft.png")

        # creepjs (sophisticated detector; screenshot + best-effort score)
        await cdp.send(method="Page.navigate", params={"url": "https://abrahamjuliot.github.io/creepjs/"})
        await asyncio.sleep(9)
        await screenshot(cdp, f"/tmp/ca_audit_{label}_creepjs.png")
        out["creepjs_text"] = await evaluate(cdp, "document.body.innerText.replace(/\\n+/g,' | ').slice(0,600)")

        await cdp.close()
    finally:
        try:
            os.kill(info.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        await asyncio.sleep(1)
    return out


async def main():
    if os.path.exists(REG):
        os.remove(REG)
    results = []
    results.append(await run_config("A_vanilla", port=9410))
    results.append(await run_config("B_fingerprint", fingerprint=FP, port=9411))
    results.append(await run_config("C_window_border", inject_marker=True, port=9412))
    print(json.dumps(results, indent=2, ensure_ascii=False))


asyncio.run(main())
