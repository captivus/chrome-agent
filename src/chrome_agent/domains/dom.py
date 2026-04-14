"""CDP DOM domain.

This domain exposes DOM read/write operations. Each DOM Node is represented with its mirror object
that has an `id`. This `id` can be used to get additional information on the Node, resolve it into
the JavaScript object wrapper, etc. It is important that client receives DOM events only for the
nodes that are known to the client. Backend keeps track of the nodes that were sent to the client
and never sends the same node twice. It is client's responsibility to collect information about
the nodes that were sent to the client. Note that `iframe` owner elements will return
corresponding document elements as their child nodes.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


NodeId = int

BackendNodeId = int

StyleSheetId = str

# Backend node with a friendly name.
BackendNode = dict  # Object type

# Pseudo element type.
PseudoType = str  # Literal enum: "first-line", "first-letter", "checkmark", "before", "after", "picker-icon", "interest-hint", "marker", "backdrop", "column", "selection", "search-text", "target-text", "spelling-error", "grammar-error", "highlight", "first-line-inherited", "scroll-marker", "scroll-marker-group", "scroll-button", "scrollbar", "scrollbar-thumb", "scrollbar-button", "scrollbar-track", "scrollbar-track-piece", "scrollbar-corner", "resizer", "input-list-button", "view-transition", "view-transition-group", "view-transition-image-pair", "view-transition-group-children", "view-transition-old", "view-transition-new", "placeholder", "file-selector-button", "details-content", "picker", "permission-icon", "overscroll-area-parent"

# Shadow root type.
ShadowRootType = str  # Literal enum: "user-agent", "open", "closed"

# Document compatibility mode.
CompatibilityMode = str  # Literal enum: "QuirksMode", "LimitedQuirksMode", "NoQuirksMode"

# ContainerSelector physical axes
PhysicalAxes = str  # Literal enum: "Horizontal", "Vertical", "Both"

# ContainerSelector logical axes
LogicalAxes = str  # Literal enum: "Inline", "Block", "Both"

# Physical scroll orientation
ScrollOrientation = str  # Literal enum: "horizontal", "vertical"

# DOM interaction is implemented in terms of mirror objects that represent the actual DOM nodes.
# DOMNode is a base node mirror type.
Node = dict  # Object type

# A structure to hold the top-level node of a detached tree and an array of its retained descendants.
DetachedElementInfo = dict  # Object type

# A structure holding an RGBA color.
RGBA = dict  # Object type

Quad = list[float]

# Box model.
BoxModel = dict  # Object type

# CSS Shape Outside details.
ShapeOutsideInfo = dict  # Object type

# Rectangle.
Rect = dict  # Object type

CSSComputedStyleProperty = dict  # Object type

class DOM:
    """This domain exposes DOM read/write operations. Each DOM Node is represented with its mirror object
that has an `id`. This `id` can be used to get additional information on the Node, resolve it into
the JavaScript object wrapper, etc. It is important that client receives DOM events only for the
nodes that are known to the client. Backend keeps track of the nodes that were sent to the client
and never sends the same node twice. It is client's responsibility to collect information about
the nodes that were sent to the client. Note that `iframe` owner elements will return
corresponding document elements as their child nodes."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def collect_class_names_from_subtree(self, node_id: NodeId) -> dict:
        """Collects class names for the node with given id and all of it's child nodes."""
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        return await self._client.send(method="DOM.collectClassNamesFromSubtree", params=params)

    async def copy_to(
        self,
        node_id: NodeId,
        target_node_id: NodeId,
        insert_before_node_id: NodeId | None = None,
    ) -> dict:
        """Creates a deep copy of the specified node and places it into the target container before the
given anchor.
        """
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        params["targetNodeId"] = target_node_id
        if insert_before_node_id is not None:
            params["insertBeforeNodeId"] = insert_before_node_id
        return await self._client.send(method="DOM.copyTo", params=params)

    async def describe_node(
        self,
        node_id: NodeId | None = None,
        backend_node_id: BackendNodeId | None = None,
        object_id: str | None = None,
        depth: int | None = None,
        pierce: bool | None = None,
    ) -> dict:
        """Describes node given its id, does not require domain to be enabled. Does not start tracking any
objects, can be used for automation.
        """
        params: dict[str, Any] = {}
        if node_id is not None:
            params["nodeId"] = node_id
        if backend_node_id is not None:
            params["backendNodeId"] = backend_node_id
        if object_id is not None:
            params["objectId"] = object_id
        if depth is not None:
            params["depth"] = depth
        if pierce is not None:
            params["pierce"] = pierce
        return await self._client.send(method="DOM.describeNode", params=params)

    async def scroll_into_view_if_needed(
        self,
        node_id: NodeId | None = None,
        backend_node_id: BackendNodeId | None = None,
        object_id: str | None = None,
        rect: Rect | None = None,
    ) -> dict:
        """Scrolls the specified rect of the given node into view if not already visible.
Note: exactly one between nodeId, backendNodeId and objectId should be passed
to identify the node.
        """
        params: dict[str, Any] = {}
        if node_id is not None:
            params["nodeId"] = node_id
        if backend_node_id is not None:
            params["backendNodeId"] = backend_node_id
        if object_id is not None:
            params["objectId"] = object_id
        if rect is not None:
            params["rect"] = rect
        return await self._client.send(method="DOM.scrollIntoViewIfNeeded", params=params)

    async def disable(self) -> dict:
        """Disables DOM agent for the given page."""
        return await self._client.send(method="DOM.disable")

    async def discard_search_results(self, search_id: str) -> dict:
        """Discards search results from the session with the given id. `getSearchResults` should no longer
be called for that search.
        """
        params: dict[str, Any] = {}
        params["searchId"] = search_id
        return await self._client.send(method="DOM.discardSearchResults", params=params)

    async def enable(self, include_whitespace: str | None = None) -> dict:
        """Enables DOM agent for the given page."""
        params: dict[str, Any] = {}
        if include_whitespace is not None:
            params["includeWhitespace"] = include_whitespace
        return await self._client.send(method="DOM.enable", params=params)

    async def focus(
        self,
        node_id: NodeId | None = None,
        backend_node_id: BackendNodeId | None = None,
        object_id: str | None = None,
    ) -> dict:
        """Focuses the given element."""
        params: dict[str, Any] = {}
        if node_id is not None:
            params["nodeId"] = node_id
        if backend_node_id is not None:
            params["backendNodeId"] = backend_node_id
        if object_id is not None:
            params["objectId"] = object_id
        return await self._client.send(method="DOM.focus", params=params)

    async def get_attributes(self, node_id: NodeId) -> dict:
        """Returns attributes for the specified node."""
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        return await self._client.send(method="DOM.getAttributes", params=params)

    async def get_box_model(
        self,
        node_id: NodeId | None = None,
        backend_node_id: BackendNodeId | None = None,
        object_id: str | None = None,
    ) -> dict:
        """Returns boxes for the given node."""
        params: dict[str, Any] = {}
        if node_id is not None:
            params["nodeId"] = node_id
        if backend_node_id is not None:
            params["backendNodeId"] = backend_node_id
        if object_id is not None:
            params["objectId"] = object_id
        return await self._client.send(method="DOM.getBoxModel", params=params)

    async def get_content_quads(
        self,
        node_id: NodeId | None = None,
        backend_node_id: BackendNodeId | None = None,
        object_id: str | None = None,
    ) -> dict:
        """Returns quads that describe node position on the page. This method
might return multiple quads for inline nodes.
        """
        params: dict[str, Any] = {}
        if node_id is not None:
            params["nodeId"] = node_id
        if backend_node_id is not None:
            params["backendNodeId"] = backend_node_id
        if object_id is not None:
            params["objectId"] = object_id
        return await self._client.send(method="DOM.getContentQuads", params=params)

    async def get_document(self, depth: int | None = None, pierce: bool | None = None) -> dict:
        """Returns the root DOM node (and optionally the subtree) to the caller.
Implicitly enables the DOM domain events for the current target.
        """
        params: dict[str, Any] = {}
        if depth is not None:
            params["depth"] = depth
        if pierce is not None:
            params["pierce"] = pierce
        return await self._client.send(method="DOM.getDocument", params=params)

    async def get_flattened_document(self, depth: int | None = None, pierce: bool | None = None) -> dict:
        """Returns the root DOM node (and optionally the subtree) to the caller.
Deprecated, as it is not designed to work well with the rest of the DOM agent.
Use DOMSnapshot.captureSnapshot instead.
        """
        params: dict[str, Any] = {}
        if depth is not None:
            params["depth"] = depth
        if pierce is not None:
            params["pierce"] = pierce
        return await self._client.send(method="DOM.getFlattenedDocument", params=params)

    async def get_nodes_for_subtree_by_style(
        self,
        node_id: NodeId,
        computed_styles: list[CSSComputedStyleProperty],
        pierce: bool | None = None,
    ) -> dict:
        """Finds nodes with a given computed style in a subtree."""
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        params["computedStyles"] = computed_styles
        if pierce is not None:
            params["pierce"] = pierce
        return await self._client.send(method="DOM.getNodesForSubtreeByStyle", params=params)

    async def get_node_for_location(
        self,
        x: int,
        y: int,
        include_user_agent_shadow_dom: bool | None = None,
        ignore_pointer_events_none: bool | None = None,
    ) -> dict:
        """Returns node id at given location. Depending on whether DOM domain is enabled, nodeId is
either returned or not.
        """
        params: dict[str, Any] = {}
        params["x"] = x
        params["y"] = y
        if include_user_agent_shadow_dom is not None:
            params["includeUserAgentShadowDOM"] = include_user_agent_shadow_dom
        if ignore_pointer_events_none is not None:
            params["ignorePointerEventsNone"] = ignore_pointer_events_none
        return await self._client.send(method="DOM.getNodeForLocation", params=params)

    async def get_outer_html(
        self,
        node_id: NodeId | None = None,
        backend_node_id: BackendNodeId | None = None,
        object_id: str | None = None,
        include_shadow_dom: bool | None = None,
    ) -> dict:
        """Returns node's HTML markup."""
        params: dict[str, Any] = {}
        if node_id is not None:
            params["nodeId"] = node_id
        if backend_node_id is not None:
            params["backendNodeId"] = backend_node_id
        if object_id is not None:
            params["objectId"] = object_id
        if include_shadow_dom is not None:
            params["includeShadowDOM"] = include_shadow_dom
        return await self._client.send(method="DOM.getOuterHTML", params=params)

    async def get_relayout_boundary(self, node_id: NodeId) -> dict:
        """Returns the id of the nearest ancestor that is a relayout boundary."""
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        return await self._client.send(method="DOM.getRelayoutBoundary", params=params)

    async def get_search_results(
        self,
        search_id: str,
        from_index: int,
        to_index: int,
    ) -> dict:
        """Returns search results from given `fromIndex` to given `toIndex` from the search with the given
identifier.
        """
        params: dict[str, Any] = {}
        params["searchId"] = search_id
        params["fromIndex"] = from_index
        params["toIndex"] = to_index
        return await self._client.send(method="DOM.getSearchResults", params=params)

    async def hide_highlight(self) -> dict:
        """Hides any highlight."""
        return await self._client.send(method="DOM.hideHighlight")

    async def highlight_node(self) -> dict:
        """Highlights DOM node."""
        return await self._client.send(method="DOM.highlightNode")

    async def highlight_rect(self) -> dict:
        """Highlights given rectangle."""
        return await self._client.send(method="DOM.highlightRect")

    async def mark_undoable_state(self) -> dict:
        """Marks last undoable state."""
        return await self._client.send(method="DOM.markUndoableState")

    async def move_to(
        self,
        node_id: NodeId,
        target_node_id: NodeId,
        insert_before_node_id: NodeId | None = None,
    ) -> dict:
        """Moves node into the new container, places it before the given anchor."""
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        params["targetNodeId"] = target_node_id
        if insert_before_node_id is not None:
            params["insertBeforeNodeId"] = insert_before_node_id
        return await self._client.send(method="DOM.moveTo", params=params)

    async def perform_search(self, query: str, include_user_agent_shadow_dom: bool | None = None) -> dict:
        """Searches for a given string in the DOM tree. Use `getSearchResults` to access search results or
`cancelSearch` to end this search session.
        """
        params: dict[str, Any] = {}
        params["query"] = query
        if include_user_agent_shadow_dom is not None:
            params["includeUserAgentShadowDOM"] = include_user_agent_shadow_dom
        return await self._client.send(method="DOM.performSearch", params=params)

    async def push_node_by_path_to_frontend(self, path: str) -> dict:
        """Requests that the node is sent to the caller given its path. // FIXME, use XPath"""
        params: dict[str, Any] = {}
        params["path"] = path
        return await self._client.send(method="DOM.pushNodeByPathToFrontend", params=params)

    async def push_nodes_by_backend_ids_to_frontend(self, backend_node_ids: list[BackendNodeId]) -> dict:
        """Requests that a batch of nodes is sent to the caller given their backend node ids."""
        params: dict[str, Any] = {}
        params["backendNodeIds"] = backend_node_ids
        return await self._client.send(method="DOM.pushNodesByBackendIdsToFrontend", params=params)

    async def query_selector(self, node_id: NodeId, selector: str) -> dict:
        """Executes `querySelector` on a given node."""
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        params["selector"] = selector
        return await self._client.send(method="DOM.querySelector", params=params)

    async def query_selector_all(self, node_id: NodeId, selector: str) -> dict:
        """Executes `querySelectorAll` on a given node."""
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        params["selector"] = selector
        return await self._client.send(method="DOM.querySelectorAll", params=params)

    async def get_top_layer_elements(self) -> dict:
        """Returns NodeIds of current top layer elements.
Top layer is rendered closest to the user within a viewport, therefore its elements always
appear on top of all other content.
        """
        return await self._client.send(method="DOM.getTopLayerElements")

    async def get_element_by_relation(self, node_id: NodeId, relation: str) -> dict:
        """Returns the NodeId of the matched element according to certain relations."""
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        params["relation"] = relation
        return await self._client.send(method="DOM.getElementByRelation", params=params)

    async def redo(self) -> dict:
        """Re-does the last undone action."""
        return await self._client.send(method="DOM.redo")

    async def remove_attribute(self, node_id: NodeId, name: str) -> dict:
        """Removes attribute with given name from an element with given id."""
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        params["name"] = name
        return await self._client.send(method="DOM.removeAttribute", params=params)

    async def remove_node(self, node_id: NodeId) -> dict:
        """Removes node with given id."""
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        return await self._client.send(method="DOM.removeNode", params=params)

    async def request_child_nodes(
        self,
        node_id: NodeId,
        depth: int | None = None,
        pierce: bool | None = None,
    ) -> dict:
        """Requests that children of the node with given id are returned to the caller in form of
`setChildNodes` events where not only immediate children are retrieved, but all children down to
the specified depth.
        """
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        if depth is not None:
            params["depth"] = depth
        if pierce is not None:
            params["pierce"] = pierce
        return await self._client.send(method="DOM.requestChildNodes", params=params)

    async def request_node(self, object_id: str) -> dict:
        """Requests that the node is sent to the caller given the JavaScript node object reference. All
nodes that form the path from the node to the root are also sent to the client as a series of
`setChildNodes` notifications.
        """
        params: dict[str, Any] = {}
        params["objectId"] = object_id
        return await self._client.send(method="DOM.requestNode", params=params)

    async def resolve_node(
        self,
        node_id: NodeId | None = None,
        backend_node_id: str | None = None,
        object_group: str | None = None,
        execution_context_id: str | None = None,
    ) -> dict:
        """Resolves the JavaScript node object for a given NodeId or BackendNodeId."""
        params: dict[str, Any] = {}
        if node_id is not None:
            params["nodeId"] = node_id
        if backend_node_id is not None:
            params["backendNodeId"] = backend_node_id
        if object_group is not None:
            params["objectGroup"] = object_group
        if execution_context_id is not None:
            params["executionContextId"] = execution_context_id
        return await self._client.send(method="DOM.resolveNode", params=params)

    async def set_attribute_value(
        self,
        node_id: NodeId,
        name: str,
        value: str,
    ) -> dict:
        """Sets attribute for an element with given id."""
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        params["name"] = name
        params["value"] = value
        return await self._client.send(method="DOM.setAttributeValue", params=params)

    async def set_attributes_as_text(
        self,
        node_id: NodeId,
        text: str,
        name: str | None = None,
    ) -> dict:
        """Sets attributes on element with given id. This method is useful when user edits some existing
attribute value and types in several attribute name/value pairs.
        """
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        params["text"] = text
        if name is not None:
            params["name"] = name
        return await self._client.send(method="DOM.setAttributesAsText", params=params)

    async def set_file_input_files(
        self,
        files: list[str],
        node_id: NodeId | None = None,
        backend_node_id: BackendNodeId | None = None,
        object_id: str | None = None,
    ) -> dict:
        """Sets files for the given file input element."""
        params: dict[str, Any] = {}
        params["files"] = files
        if node_id is not None:
            params["nodeId"] = node_id
        if backend_node_id is not None:
            params["backendNodeId"] = backend_node_id
        if object_id is not None:
            params["objectId"] = object_id
        return await self._client.send(method="DOM.setFileInputFiles", params=params)

    async def set_node_stack_traces_enabled(self, enable: bool) -> dict:
        """Sets if stack traces should be captured for Nodes. See `Node.getNodeStackTraces`. Default is disabled."""
        params: dict[str, Any] = {}
        params["enable"] = enable
        return await self._client.send(method="DOM.setNodeStackTracesEnabled", params=params)

    async def get_node_stack_traces(self, node_id: NodeId) -> dict:
        """Gets stack traces associated with a Node. As of now, only provides stack trace for Node creation."""
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        return await self._client.send(method="DOM.getNodeStackTraces", params=params)

    async def get_file_info(self, object_id: str) -> dict:
        """Returns file information for the given
File wrapper.
        """
        params: dict[str, Any] = {}
        params["objectId"] = object_id
        return await self._client.send(method="DOM.getFileInfo", params=params)

    async def get_detached_dom_nodes(self) -> dict:
        """Returns list of detached nodes"""
        return await self._client.send(method="DOM.getDetachedDomNodes")

    async def set_inspected_node(self, node_id: NodeId) -> dict:
        """Enables console to refer to the node with given id via $x (see Command Line API for more details
$x functions).
        """
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        return await self._client.send(method="DOM.setInspectedNode", params=params)

    async def set_node_name(self, node_id: NodeId, name: str) -> dict:
        """Sets node name for a node with given id."""
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        params["name"] = name
        return await self._client.send(method="DOM.setNodeName", params=params)

    async def set_node_value(self, node_id: NodeId, value: str) -> dict:
        """Sets node value for a node with given id."""
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        params["value"] = value
        return await self._client.send(method="DOM.setNodeValue", params=params)

    async def set_outer_html(self, node_id: NodeId, outer_html: str) -> dict:
        """Sets node HTML markup, returns new node id."""
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        params["outerHTML"] = outer_html
        return await self._client.send(method="DOM.setOuterHTML", params=params)

    async def undo(self) -> dict:
        """Undoes the last performed action."""
        return await self._client.send(method="DOM.undo")

    async def get_frame_owner(self, frame_id: str) -> dict:
        """Returns iframe node that owns iframe with the given domain."""
        params: dict[str, Any] = {}
        params["frameId"] = frame_id
        return await self._client.send(method="DOM.getFrameOwner", params=params)

    async def get_container_for_node(
        self,
        node_id: NodeId,
        container_name: str | None = None,
        physical_axes: PhysicalAxes | None = None,
        logical_axes: LogicalAxes | None = None,
        queries_scroll_state: bool | None = None,
        queries_anchored: bool | None = None,
    ) -> dict:
        """Returns the query container of the given node based on container query
conditions: containerName, physical and logical axes, and whether it queries
scroll-state or anchored elements. If no axes are provided and
queriesScrollState is false, the style container is returned, which is the
direct parent or the closest element with a matching container-name.
        """
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        if container_name is not None:
            params["containerName"] = container_name
        if physical_axes is not None:
            params["physicalAxes"] = physical_axes
        if logical_axes is not None:
            params["logicalAxes"] = logical_axes
        if queries_scroll_state is not None:
            params["queriesScrollState"] = queries_scroll_state
        if queries_anchored is not None:
            params["queriesAnchored"] = queries_anchored
        return await self._client.send(method="DOM.getContainerForNode", params=params)

    async def get_querying_descendants_for_container(self, node_id: NodeId) -> dict:
        """Returns the descendants of a container query container that have
container queries against this container.
        """
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        return await self._client.send(method="DOM.getQueryingDescendantsForContainer", params=params)

    async def get_anchor_element(self, node_id: NodeId, anchor_specifier: str | None = None) -> dict:
        """Returns the target anchor element of the given anchor query according to
https://www.w3.org/TR/css-anchor-position-1/#target.
        """
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        if anchor_specifier is not None:
            params["anchorSpecifier"] = anchor_specifier
        return await self._client.send(method="DOM.getAnchorElement", params=params)

    async def force_show_popover(self, node_id: NodeId, enable: bool) -> dict:
        """When enabling, this API force-opens the popover identified by nodeId
and keeps it open until disabled.
        """
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        params["enable"] = enable
        return await self._client.send(method="DOM.forceShowPopover", params=params)
