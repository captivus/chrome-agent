"""CDP Overlay domain.

This domain provides various functionality related to drawing atop the inspected page.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


# Configuration data for drawing the source order of an elements children.
SourceOrderConfig = dict  # Object type

# Configuration data for the highlighting of Grid elements.
GridHighlightConfig = dict  # Object type

# Configuration data for the highlighting of Flex container elements.
FlexContainerHighlightConfig = dict  # Object type

# Configuration data for the highlighting of Flex item elements.
FlexItemHighlightConfig = dict  # Object type

# Style information for drawing a line.
LineStyle = dict  # Object type

# Style information for drawing a box.
BoxStyle = dict  # Object type

ContrastAlgorithm = str  # Literal enum: "aa", "aaa", "apca"

# Configuration data for the highlighting of page elements.
HighlightConfig = dict  # Object type

ColorFormat = str  # Literal enum: "rgb", "hsl", "hwb", "hex"

# Configurations for Persistent Grid Highlight
GridNodeHighlightConfig = dict  # Object type

FlexNodeHighlightConfig = dict  # Object type

ScrollSnapContainerHighlightConfig = dict  # Object type

ScrollSnapHighlightConfig = dict  # Object type

# Configuration for dual screen hinge
HingeConfig = dict  # Object type

# Configuration for Window Controls Overlay
WindowControlsOverlayConfig = dict  # Object type

ContainerQueryHighlightConfig = dict  # Object type

ContainerQueryContainerHighlightConfig = dict  # Object type

IsolatedElementHighlightConfig = dict  # Object type

IsolationModeHighlightConfig = dict  # Object type

InspectMode = str  # Literal enum: "searchForNode", "searchForUAShadowDOM", "captureAreaScreenshot", "none"

InspectedElementAnchorConfig = dict  # Object type

class Overlay:
    """This domain provides various functionality related to drawing atop the inspected page."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def disable(self) -> dict:
        """Disables domain notifications."""
        return await self._client.send(method="Overlay.disable")

    async def enable(self) -> dict:
        """Enables domain notifications."""
        return await self._client.send(method="Overlay.enable")

    async def get_highlight_object_for_test(
        self,
        node_id: str,
        include_distance: bool | None = None,
        include_style: bool | None = None,
        color_format: ColorFormat | None = None,
        show_accessibility_info: bool | None = None,
    ) -> dict:
        """For testing."""
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        if include_distance is not None:
            params["includeDistance"] = include_distance
        if include_style is not None:
            params["includeStyle"] = include_style
        if color_format is not None:
            params["colorFormat"] = color_format
        if show_accessibility_info is not None:
            params["showAccessibilityInfo"] = show_accessibility_info
        return await self._client.send(method="Overlay.getHighlightObjectForTest", params=params)

    async def get_grid_highlight_objects_for_test(self, node_ids: list[str]) -> dict:
        """For Persistent Grid testing."""
        params: dict[str, Any] = {}
        params["nodeIds"] = node_ids
        return await self._client.send(method="Overlay.getGridHighlightObjectsForTest", params=params)

    async def get_source_order_highlight_object_for_test(self, node_id: str) -> dict:
        """For Source Order Viewer testing."""
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        return await self._client.send(method="Overlay.getSourceOrderHighlightObjectForTest", params=params)

    async def hide_highlight(self) -> dict:
        """Hides any highlight."""
        return await self._client.send(method="Overlay.hideHighlight")

    async def highlight_frame(
        self,
        frame_id: str,
        content_color: str | None = None,
        content_outline_color: str | None = None,
    ) -> dict:
        """Highlights owner element of the frame with given id.
Deprecated: Doesn't work reliably and cannot be fixed due to process
separation (the owner node might be in a different process). Determine
the owner node in the client and use highlightNode.
        """
        params: dict[str, Any] = {}
        params["frameId"] = frame_id
        if content_color is not None:
            params["contentColor"] = content_color
        if content_outline_color is not None:
            params["contentOutlineColor"] = content_outline_color
        return await self._client.send(method="Overlay.highlightFrame", params=params)

    async def highlight_node(
        self,
        highlight_config: HighlightConfig,
        node_id: str | None = None,
        backend_node_id: str | None = None,
        object_id: str | None = None,
        selector: str | None = None,
    ) -> dict:
        """Highlights DOM node with given id or with the given JavaScript object wrapper. Either nodeId or
objectId must be specified.
        """
        params: dict[str, Any] = {}
        params["highlightConfig"] = highlight_config
        if node_id is not None:
            params["nodeId"] = node_id
        if backend_node_id is not None:
            params["backendNodeId"] = backend_node_id
        if object_id is not None:
            params["objectId"] = object_id
        if selector is not None:
            params["selector"] = selector
        return await self._client.send(method="Overlay.highlightNode", params=params)

    async def highlight_quad(
        self,
        quad: str,
        color: str | None = None,
        outline_color: str | None = None,
    ) -> dict:
        """Highlights given quad. Coordinates are absolute with respect to the main frame viewport."""
        params: dict[str, Any] = {}
        params["quad"] = quad
        if color is not None:
            params["color"] = color
        if outline_color is not None:
            params["outlineColor"] = outline_color
        return await self._client.send(method="Overlay.highlightQuad", params=params)

    async def highlight_rect(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        color: str | None = None,
        outline_color: str | None = None,
    ) -> dict:
        """Highlights given rectangle. Coordinates are absolute with respect to the main frame viewport.
Issue: the method does not handle device pixel ratio (DPR) correctly.
The coordinates currently have to be adjusted by the client
if DPR is not 1 (see crbug.com/437807128).
        """
        params: dict[str, Any] = {}
        params["x"] = x
        params["y"] = y
        params["width"] = width
        params["height"] = height
        if color is not None:
            params["color"] = color
        if outline_color is not None:
            params["outlineColor"] = outline_color
        return await self._client.send(method="Overlay.highlightRect", params=params)

    async def highlight_source_order(
        self,
        source_order_config: SourceOrderConfig,
        node_id: str | None = None,
        backend_node_id: str | None = None,
        object_id: str | None = None,
    ) -> dict:
        """Highlights the source order of the children of the DOM node with given id or with the given
JavaScript object wrapper. Either nodeId or objectId must be specified.
        """
        params: dict[str, Any] = {}
        params["sourceOrderConfig"] = source_order_config
        if node_id is not None:
            params["nodeId"] = node_id
        if backend_node_id is not None:
            params["backendNodeId"] = backend_node_id
        if object_id is not None:
            params["objectId"] = object_id
        return await self._client.send(method="Overlay.highlightSourceOrder", params=params)

    async def set_inspect_mode(self, mode: InspectMode, highlight_config: HighlightConfig | None = None) -> dict:
        """Enters the 'inspect' mode. In this mode, elements that user is hovering over are highlighted.
Backend then generates 'inspectNodeRequested' event upon element selection.
        """
        params: dict[str, Any] = {}
        params["mode"] = mode
        if highlight_config is not None:
            params["highlightConfig"] = highlight_config
        return await self._client.send(method="Overlay.setInspectMode", params=params)

    async def set_show_ad_highlights(self, show: bool) -> dict:
        """Highlights owner element of all frames detected to be ads."""
        params: dict[str, Any] = {}
        params["show"] = show
        return await self._client.send(method="Overlay.setShowAdHighlights", params=params)

    async def set_paused_in_debugger_message(self, message: str | None = None) -> dict:
        params: dict[str, Any] = {}
        if message is not None:
            params["message"] = message
        return await self._client.send(method="Overlay.setPausedInDebuggerMessage", params=params)

    async def set_show_debug_borders(self, show: bool) -> dict:
        """Requests that backend shows debug borders on layers"""
        params: dict[str, Any] = {}
        params["show"] = show
        return await self._client.send(method="Overlay.setShowDebugBorders", params=params)

    async def set_show_fps_counter(self, show: bool) -> dict:
        """Requests that backend shows the FPS counter"""
        params: dict[str, Any] = {}
        params["show"] = show
        return await self._client.send(method="Overlay.setShowFPSCounter", params=params)

    async def set_show_grid_overlays(self, grid_node_highlight_configs: list[GridNodeHighlightConfig]) -> dict:
        """Highlight multiple elements with the CSS Grid overlay."""
        params: dict[str, Any] = {}
        params["gridNodeHighlightConfigs"] = grid_node_highlight_configs
        return await self._client.send(method="Overlay.setShowGridOverlays", params=params)

    async def set_show_flex_overlays(self, flex_node_highlight_configs: list[FlexNodeHighlightConfig]) -> dict:
        params: dict[str, Any] = {}
        params["flexNodeHighlightConfigs"] = flex_node_highlight_configs
        return await self._client.send(method="Overlay.setShowFlexOverlays", params=params)

    async def set_show_scroll_snap_overlays(self, scroll_snap_highlight_configs: list[ScrollSnapHighlightConfig]) -> dict:
        params: dict[str, Any] = {}
        params["scrollSnapHighlightConfigs"] = scroll_snap_highlight_configs
        return await self._client.send(method="Overlay.setShowScrollSnapOverlays", params=params)

    async def set_show_container_query_overlays(self, container_query_highlight_configs: list[ContainerQueryHighlightConfig]) -> dict:
        params: dict[str, Any] = {}
        params["containerQueryHighlightConfigs"] = container_query_highlight_configs
        return await self._client.send(method="Overlay.setShowContainerQueryOverlays", params=params)

    async def set_show_inspected_element_anchor(self, inspected_element_anchor_config: InspectedElementAnchorConfig) -> dict:
        params: dict[str, Any] = {}
        params["inspectedElementAnchorConfig"] = inspected_element_anchor_config
        return await self._client.send(method="Overlay.setShowInspectedElementAnchor", params=params)

    async def set_show_paint_rects(self, result: bool) -> dict:
        """Requests that backend shows paint rectangles"""
        params: dict[str, Any] = {}
        params["result"] = result
        return await self._client.send(method="Overlay.setShowPaintRects", params=params)

    async def set_show_layout_shift_regions(self, result: bool) -> dict:
        """Requests that backend shows layout shift regions"""
        params: dict[str, Any] = {}
        params["result"] = result
        return await self._client.send(method="Overlay.setShowLayoutShiftRegions", params=params)

    async def set_show_scroll_bottleneck_rects(self, show: bool) -> dict:
        """Requests that backend shows scroll bottleneck rects"""
        params: dict[str, Any] = {}
        params["show"] = show
        return await self._client.send(method="Overlay.setShowScrollBottleneckRects", params=params)

    async def set_show_hit_test_borders(self, show: bool) -> dict:
        """Deprecated, no longer has any effect."""
        params: dict[str, Any] = {}
        params["show"] = show
        return await self._client.send(method="Overlay.setShowHitTestBorders", params=params)

    async def set_show_web_vitals(self, show: bool) -> dict:
        """Deprecated, no longer has any effect."""
        params: dict[str, Any] = {}
        params["show"] = show
        return await self._client.send(method="Overlay.setShowWebVitals", params=params)

    async def set_show_viewport_size_on_resize(self, show: bool) -> dict:
        """Paints viewport size upon main frame resize."""
        params: dict[str, Any] = {}
        params["show"] = show
        return await self._client.send(method="Overlay.setShowViewportSizeOnResize", params=params)

    async def set_show_hinge(self, hinge_config: HingeConfig | None = None) -> dict:
        """Add a dual screen device hinge"""
        params: dict[str, Any] = {}
        if hinge_config is not None:
            params["hingeConfig"] = hinge_config
        return await self._client.send(method="Overlay.setShowHinge", params=params)

    async def set_show_isolated_elements(self, isolated_element_highlight_configs: list[IsolatedElementHighlightConfig]) -> dict:
        """Show elements in isolation mode with overlays."""
        params: dict[str, Any] = {}
        params["isolatedElementHighlightConfigs"] = isolated_element_highlight_configs
        return await self._client.send(method="Overlay.setShowIsolatedElements", params=params)

    async def set_show_window_controls_overlay(self, window_controls_overlay_config: WindowControlsOverlayConfig | None = None) -> dict:
        """Show Window Controls Overlay for PWA"""
        params: dict[str, Any] = {}
        if window_controls_overlay_config is not None:
            params["windowControlsOverlayConfig"] = window_controls_overlay_config
        return await self._client.send(method="Overlay.setShowWindowControlsOverlay", params=params)
