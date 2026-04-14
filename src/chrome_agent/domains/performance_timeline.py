"""CDP PerformanceTimeline domain.

Reporting of performance timeline events, as specified in
https://w3c.github.io/performance-timeline/#dom-performanceobserver.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


# See https://github.com/WICG/LargestContentfulPaint and largest_contentful_paint.idl
LargestContentfulPaint = dict  # Object type

LayoutShiftAttribution = dict  # Object type

# See https://wicg.github.io/layout-instability/#sec-layout-shift and layout_shift.idl
LayoutShift = dict  # Object type

TimelineEvent = dict  # Object type

class PerformanceTimeline:
    """Reporting of performance timeline events, as specified in
https://w3c.github.io/performance-timeline/#dom-performanceobserver."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def enable(self, event_types: list[str]) -> dict:
        """Previously buffered events would be reported before method returns.
See also: timelineEventAdded
        """
        params: dict[str, Any] = {}
        params["eventTypes"] = event_types
        return await self._client.send(method="PerformanceTimeline.enable", params=params)
