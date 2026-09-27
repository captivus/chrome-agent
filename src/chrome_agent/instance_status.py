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


def get_instance_status(
    *,
    instance_name: str | None = None,
    registry_path: str | None = None,
) -> list[InstanceStatus]:
    """Get status for all instances, one named instance, or a matched set.

    When instance_name is provided it may be a literal name (returning a
    single-element list, raising InstanceNotFoundError if not found) or a glob
    pattern, which returns every matching instance in name order.
    When instance_name is None, returns all registered instances.

    Each instance is enriched with live page target data from Chrome.
    Dead instances have empty target lists.
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

        if status.alive and status.targets:
            for target in status.targets:
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
            "targets": [
                {
                    "id": t.short_id,
                    "full_id": t.target_id,
                    "index": t.index,
                    "url": t.url,
                    "title": t.title,
                }
                for t in status.targets
            ],
        }
        data.append(entry)
    return json.dumps(data, indent=2)
