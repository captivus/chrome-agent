"""The order of tabs in their windows, which CDP has no command for.

``Target.getTargets`` lists pages in an order of its own: not creation order,
and blind to tabs being dragged or opened beside their opener. Chrome's
extension API does know each tab's window and position, so this loads a tiny
bundled extension over CDP (``Extensions.loadUnpacked``), asks it, and
uninstalls it again. An extension loaded this way does not survive a browser
restart, so it never ends up in a saved profile.

Best effort throughout: when the browser refuses (an older Chrome without the
Extensions domain, extensions disabled by policy or flag), callers get None
and keep CDP's order.
"""

import asyncio
import os

EXTENSION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tab_order_extension")


async def tab_positions(cdp, timeout: float = 3.0) -> dict[str, tuple[int, int]] | None:
    """{targetId: (windowId, index in window)} for every tab, or None.

    ``cdp`` is a connected browser-level CDPClient.
    """
    try:
        ext_id = (await cdp.send(method="Extensions.loadUnpacked", params={"path": EXTENSION_DIR}))["id"]
    except Exception:
        return None
    try:
        worker = None
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while worker is None and loop.time() < deadline:
            targets = (await cdp.send(method="Target.getTargets"))["targetInfos"]
            worker = next(
                (t for t in targets
                 if t.get("type") == "service_worker" and t.get("url", "").startswith(f"chrome-extension://{ext_id}/")),
                None,
            )
            if worker is None:
                await asyncio.sleep(0.05)
        if worker is None:
            return None
        session = (await cdp.send(
            method="Target.attachToTarget", params={"targetId": worker["targetId"], "flatten": True},
        ))["sessionId"]
        try:
            # The worker is listed a moment before its script has run, so
            # tabOrder may not exist yet: ask until it does (null until then).
            while True:
                result = await cdp.send(
                    method="Runtime.evaluate",
                    params={
                        "expression": "typeof tabOrder === 'function' ? tabOrder() : null",
                        "awaitPromise": True, "returnByValue": True,
                    },
                    session_id=session,
                )
                if result.get("result", {}).get("value") is not None or loop.time() >= deadline:
                    break
                await asyncio.sleep(0.02)
        finally:
            try:
                await cdp.send(method="Target.detachFromTarget", params={"sessionId": session})
            except Exception:
                pass
        tabs = result.get("result", {}).get("value")
        if not isinstance(tabs, list):
            return None
        return {t["targetId"]: (t["windowId"], t["index"]) for t in tabs}
    except Exception:
        return None
    finally:
        try:
            await cdp.send(method="Extensions.uninstall", params={"id": ext_id})
        except Exception:
            pass


def sort_key(positions: dict[str, tuple[int, int]] | None, target_id: str) -> tuple:
    """Order by window then position; tabs the extension did not see go last."""
    if positions and target_id in positions:
        return (0, *positions[target_id])
    return (1, 0, 0)


async def numbered_pages(cdp, *, ordered: bool = True) -> tuple[list[dict], bool]:
    """The browser's page targets, numbered as ``status`` and ``--target-index`` number them.

    Each returned targetInfo gains an ``index`` (1-based). With ``ordered``
    and a readable tab order, tabs are numbered by where they sit on screen:
    left to right, window by window. Otherwise -- or when ``ordered`` is
    False, for callers that only match by id or URL and need no numbers --
    they are numbered by target id, the fallback ordering. Returns
    (pages, whether the on-screen order was used).
    """
    targets = (await cdp.send(method="Target.getTargets")).get("targetInfos", [])
    pages = [t for t in targets if t.get("type") == "page"]
    positions = await tab_positions(cdp) if ordered and len(pages) > 1 else None
    pages.sort(key=lambda t: t.get("targetId", ""))
    if positions:
        pages.sort(key=lambda t: sort_key(positions, t["targetId"]))
    for number, page in enumerate(pages, start=1):
        page["index"] = number
    return pages, bool(positions)
