"""CDP DOMSnapshot domain.

This domain facilitates obtaining document snapshots with DOM, layout, and style information.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


# A Node in the DOM tree.
DOMNode = dict  # Object type

# Details of post layout rendered text positions. The exact layout should not be regarded as
# stable and may change between versions.
InlineTextBox = dict  # Object type

# Details of an element in the DOM tree with a LayoutObject.
LayoutTreeNode = dict  # Object type

# A subset of the full ComputedStyle as defined by the request whitelist.
ComputedStyle = dict  # Object type

# A name/value pair.
NameValue = dict  # Object type

StringIndex = int

ArrayOfStrings = list[StringIndex]

# Data that is only present on rare nodes.
RareStringData = dict  # Object type

RareBooleanData = dict  # Object type

RareIntegerData = dict  # Object type

Rectangle = list[float]

# Document snapshot.
DocumentSnapshot = dict  # Object type

# Table containing nodes.
NodeTreeSnapshot = dict  # Object type

# Table of details of an element in the DOM tree with a LayoutObject.
LayoutTreeSnapshot = dict  # Object type

# Table of details of the post layout rendered text positions. The exact layout should not be regarded as
# stable and may change between versions.
TextBoxSnapshot = dict  # Object type

class DOMSnapshot:
    """This domain facilitates obtaining document snapshots with DOM, layout, and style information."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def disable(self) -> dict:
        """Disables DOM snapshot agent for the given page."""
        return await self._client.send(method="DOMSnapshot.disable")

    async def enable(self) -> dict:
        """Enables DOM snapshot agent for the given page."""
        return await self._client.send(method="DOMSnapshot.enable")

    async def get_snapshot(
        self,
        computed_style_whitelist: list[str],
        include_event_listeners: bool | None = None,
        include_paint_order: bool | None = None,
        include_user_agent_shadow_tree: bool | None = None,
    ) -> dict:
        """Returns a document snapshot, including the full DOM tree of the root node (including iframes,
template contents, and imported documents) in a flattened array, as well as layout and
white-listed computed style information for the nodes. Shadow DOM in the returned DOM tree is
flattened.
        """
        params: dict[str, Any] = {}
        params["computedStyleWhitelist"] = computed_style_whitelist
        if include_event_listeners is not None:
            params["includeEventListeners"] = include_event_listeners
        if include_paint_order is not None:
            params["includePaintOrder"] = include_paint_order
        if include_user_agent_shadow_tree is not None:
            params["includeUserAgentShadowTree"] = include_user_agent_shadow_tree
        return await self._client.send(method="DOMSnapshot.getSnapshot", params=params)

    async def capture_snapshot(
        self,
        computed_styles: list[str],
        include_paint_order: bool | None = None,
        include_dom_rects: bool | None = None,
        include_blended_background_colors: bool | None = None,
        include_text_color_opacities: bool | None = None,
    ) -> dict:
        """Returns a document snapshot, including the full DOM tree of the root node (including iframes,
template contents, and imported documents) in a flattened array, as well as layout and
white-listed computed style information for the nodes. Shadow DOM in the returned DOM tree is
flattened.
        """
        params: dict[str, Any] = {}
        params["computedStyles"] = computed_styles
        if include_paint_order is not None:
            params["includePaintOrder"] = include_paint_order
        if include_dom_rects is not None:
            params["includeDOMRects"] = include_dom_rects
        if include_blended_background_colors is not None:
            params["includeBlendedBackgroundColors"] = include_blended_background_colors
        if include_text_color_opacities is not None:
            params["includeTextColorOpacities"] = include_text_color_opacities
        return await self._client.send(method="DOMSnapshot.captureSnapshot", params=params)
