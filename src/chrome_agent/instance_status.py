"""Instance status for chrome-agent.

Lists all registered browser instances with their page targets,
enriching registry data with live browser state (liveness, target
enumeration). Replaces the simple BRW-02 Browser Status.
"""

import json
import logging
import sys
import urllib.request
from dataclasses import dataclass, field

from .registry import (
    InstanceNotFoundError,
    enumerate_instances,
    lookup,
    resolve_instance_names,
)

logger = logging.getLogger(__name__)

TARGET_ID_LENGTH = 8


@dataclass
class PageTarget:
    """A single page target within a browser instance."""
    target_id: str
    short_id: str
    index: int
    url: str
    title: str
    # Where the tab sits on screen: its window (1 = first) and its position
    # in that window (1 = leftmost). None when the order could not be read.
    window: int | None = None
    position: int | None = None


@dataclass
class InstanceStatus:
    """Status of a registered browser instance with its page targets."""
    name: str
    port: int
    alive: bool
    targets: list[PageTarget] = field(default_factory=list)
    # Where the browser renders: {"kind": "headless"}, {"kind": "virtual",
    # "display": ":95", "server": "Xvfb"} (off the user's screen), or
    # {"kind": "desktop", "display": ":1"}. None when dead or undeterminable.
    placement: dict | None = None
    # Whether targets are in on-screen order and numbered by it (see
    # order_targets); False means numbered by target id, the fallback.
    tab_order: bool = False


def query_targets(*, port: int) -> list[PageTarget]:
    """Query Chrome's /json endpoint for page targets.

    Filters for type=="page" only. Returns empty list on any failure.
    """
    try:
        req = urllib.request.Request(f"http://localhost:{port}/json")
        with urllib.request.urlopen(req, timeout=2) as resp:
            all_targets = json.loads(resp.read())
    except Exception:
        return []

    pages = sorted(
        (t for t in all_targets if t.get("type") == "page"),
        key=lambda t: t.get("id", ""),
    )

    results = []
    for index, target in enumerate(pages, start=1):
        target_id = target.get("id", "")
        results.append(PageTarget(
            target_id=target_id,
            short_id=target_id[:TARGET_ID_LENGTH].upper(),
            index=index,
            url=target.get("url", ""),
            title=target.get("title", ""),
        ))
    return results


def order_targets(targets_by_port: dict[int, list[PageTarget]]) -> set[int]:
    """Sort and number each browser's targets in on-screen order, in place.

    CDP has no tab order (see taborder.py), so this briefly loads a helper
    extension into each browser, all browsers at once. Targets are renumbered
    1..N left to right, window by window -- the numbering ``--target-index``
    resolves against (taborder.numbered_pages). A browser whose order cannot
    be read keeps its target-id numbering. Returns the ports that were ordered.
    """
    import asyncio

    from .cdp_client import CDPClient, get_ws_url
    from .taborder import sort_key, tab_positions

    ordered: set[int] = set()

    async def one(port: int, targets: list[PageTarget]) -> None:
        try:
            async with CDPClient(ws_url=get_ws_url(port=port, target_type="browser")) as cdp:
                positions = await tab_positions(cdp)
        except Exception:
            return
        if not positions:
            return
        windows = {w: n for n, w in enumerate(sorted({w for w, _ in positions.values()}), start=1)}
        for target in targets:
            if target.target_id in positions:
                window_id, index = positions[target.target_id]
                target.window, target.position = windows[window_id], index + 1
        targets.sort(key=lambda t: t.target_id)
        targets.sort(key=lambda t: sort_key(positions, t.target_id))
        for number, target in enumerate(targets, start=1):
            target.index = number
        ordered.add(port)

    async def run() -> None:
        await asyncio.gather(*(one(p, t) for p, t in targets_by_port.items() if len(t) > 1))

    asyncio.run(run())
    return ordered


def get_instance_status(
    *,
    instance_name: str | None = None,
    registry_path: str | None = None,
    order_tabs: bool = False,
) -> list[InstanceStatus]:
    """Get status for all instances, one named instance, or a matched set.

    When instance_name is provided it may be a literal name (returning a
    single-element list, raising InstanceNotFoundError if not found) or a glob
    pattern, which returns every matching instance in name order.
    When instance_name is None, returns all registered instances.

    Each instance is enriched with live page target data from Chrome.
    Dead instances have empty target lists. ``order_tabs`` lists each
    browser's tabs in on-screen order (see order_targets); otherwise they are
    numbered by target id.
    """
    if instance_name is not None:
        names = resolve_instance_names(
            name_or_pattern=instance_name,
            registry_path=registry_path,
        )
        instances = [
            lookup(instance_name=name, registry_path=registry_path)
            for name in names
        ]
    else:
        instances = enumerate_instances(registry_path=registry_path)

    from .desktop import browser_placements

    placements = browser_placements([info.port for info in instances if info.alive])

    results = []
    for info in instances:
        if info.alive:
            targets = query_targets(port=info.port)
        else:
            targets = []

        results.append(InstanceStatus(
            name=info.name,
            port=info.port,
            alive=info.alive,
            targets=targets,
            placement=placements.get(info.port) if info.alive else None,
        ))

    if order_tabs:
        ordered = order_targets({s.port: s.targets for s in results if s.alive})
        for status in results:
            status.tab_order = status.port in ordered or len(status.targets) <= 1
            if len(status.targets) == 1:
                # A lone tab needs no lookup: it is the first tab of the only window.
                status.targets[0].window, status.targets[0].position = 1, 1
    return results


def placement_label(placement: dict | None) -> str | None:
    """A short tag for a browser that is NOT on the user's screen, else None.

    Only off-screen placements are worth a tag: a window on a virtual display
    (an Xvfb) or no window at all (headless) is invisible, and easy to lose track
    of. A browser on the user's own desktop is the unremarkable default.
    """
    if not placement:
        return None
    if placement["kind"] == "headless":
        return "headless"
    if placement["kind"] == "virtual":
        return f"{placement['server']} {placement['display']}"
    return None


def format_status_text(statuses: list[InstanceStatus]) -> str:
    """Format instance status as human-readable text."""
    lines = []
    for status in statuses:
        header = f"{status.name}  port {status.port}"
        if not status.alive:
            header += "  DEAD"
        label = placement_label(status.placement)
        if label:
            header += f"  [{label}]"
        lines.append(header)

        if status.alive and len(status.targets) > 1 and not status.tab_order:
            lines.append("  (tab order unavailable: tabs are numbered by target id, not position)")
        if status.alive and status.targets:
            previous_window = status.targets[0].window
            for target in status.targets:
                if target.window != previous_window:
                    lines.append("  --- window")
                    previous_window = target.window
                line = f'  [{target.index}] {target.short_id}  {target.url}  "{target.title}"'
                lines.append(line)

        lines.append("")

    if lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


def format_status_json(statuses: list[InstanceStatus]) -> str:
    """Format instance status as JSON for programmatic consumption."""
    data = []
    for status in statuses:
        entry = {
            "name": status.name,
            "port": status.port,
            "alive": status.alive,
            "display": status.placement,
            "tab_order": status.tab_order,
            "targets": [
                {
                    "id": t.short_id,
                    "full_id": t.target_id,
                    "index": t.index,
                    "url": t.url,
                    "title": t.title,
                    "window": t.window,
                    "position": t.position,
                }
                for t in status.targets
            ],
        }
        data.append(entry)
    return json.dumps(data, indent=2)
