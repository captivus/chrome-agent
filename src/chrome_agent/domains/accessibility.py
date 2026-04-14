"""CDP Accessibility domain.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


AXNodeId = str

# Enum of possible property types.
AXValueType = str  # Literal enum: "boolean", "tristate", "booleanOrUndefined", "idref", "idrefList", "integer", "node", "nodeList", "number", "string", "computedString", "token", "tokenList", "domRelation", "role", "internalRole", "valueUndefined"

# Enum of possible property sources.
AXValueSourceType = str  # Literal enum: "attribute", "implicit", "style", "contents", "placeholder", "relatedElement"

# Enum of possible native property sources (as a subtype of a particular AXValueSourceType).
AXValueNativeSourceType = str  # Literal enum: "description", "figcaption", "label", "labelfor", "labelwrapped", "legend", "rubyannotation", "tablecaption", "title", "other"

# A single source for a computed AX property.
AXValueSource = dict  # Object type

AXRelatedNode = dict  # Object type

AXProperty = dict  # Object type

# A single computed AX property.
AXValue = dict  # Object type

# Values of AXProperty name:
# - from 'busy' to 'roledescription': states which apply to every AX node
# - from 'live' to 'root': attributes which apply to nodes in live regions
# - from 'autocomplete' to 'valuetext': attributes which apply to widgets
# - from 'checked' to 'selected': states which apply to widgets
# - from 'activedescendant' to 'owns': relationships between elements other than parent/child/sibling
# - from 'activeFullscreenElement' to 'uninteresting': reasons why this noode is hidden
AXPropertyName = str  # Literal enum: "actions", "busy", "disabled", "editable", "focusable", "focused", "hidden", "hiddenRoot", "invalid", "keyshortcuts", "settable", "roledescription", "live", "atomic", "relevant", "root", "autocomplete", "hasPopup", "level", "multiselectable", "orientation", "multiline", "readonly", "required", "valuemin", "valuemax", "valuetext", "checked", "expanded", "modal", "pressed", "selected", "activedescendant", "controls", "describedby", "details", "errormessage", "flowto", "labelledby", "owns", "url", "activeFullscreenElement", "activeModalDialog", "activeAriaModalDialog", "ariaHiddenElement", "ariaHiddenSubtree", "emptyAlt", "emptyText", "inertElement", "inertSubtree", "labelContainer", "labelFor", "notRendered", "notVisible", "presentationalRole", "probablyPresentational", "inactiveCarouselTabContent", "uninteresting"

# A node in the accessibility tree.
AXNode = dict  # Object type

class Accessibility:
    """CDP Accessibility domain."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def disable(self) -> dict:
        """Disables the accessibility domain."""
        return await self._client.send(method="Accessibility.disable")

    async def enable(self) -> dict:
        """Enables the accessibility domain which causes `AXNodeId`s to remain consistent between method calls.
This turns on accessibility for the page, which can impact performance until accessibility is disabled.
        """
        return await self._client.send(method="Accessibility.enable")

    async def get_partial_ax_tree(
        self,
        node_id: str | None = None,
        backend_node_id: str | None = None,
        object_id: str | None = None,
        fetch_relatives: bool | None = None,
    ) -> dict:
        """Fetches the accessibility node and partial accessibility tree for this DOM node, if it exists."""
        params: dict[str, Any] = {}
        if node_id is not None:
            params["nodeId"] = node_id
        if backend_node_id is not None:
            params["backendNodeId"] = backend_node_id
        if object_id is not None:
            params["objectId"] = object_id
        if fetch_relatives is not None:
            params["fetchRelatives"] = fetch_relatives
        return await self._client.send(method="Accessibility.getPartialAXTree", params=params)

    async def get_full_ax_tree(self, depth: int | None = None, frame_id: str | None = None) -> dict:
        """Fetches the entire accessibility tree for the root Document"""
        params: dict[str, Any] = {}
        if depth is not None:
            params["depth"] = depth
        if frame_id is not None:
            params["frameId"] = frame_id
        return await self._client.send(method="Accessibility.getFullAXTree", params=params)

    async def get_root_ax_node(self, frame_id: str | None = None) -> dict:
        """Fetches the root node.
Requires `enable()` to have been called previously.
        """
        params: dict[str, Any] = {}
        if frame_id is not None:
            params["frameId"] = frame_id
        return await self._client.send(method="Accessibility.getRootAXNode", params=params)

    async def get_ax_node_and_ancestors(
        self,
        node_id: str | None = None,
        backend_node_id: str | None = None,
        object_id: str | None = None,
    ) -> dict:
        """Fetches a node and all ancestors up to and including the root.
Requires `enable()` to have been called previously.
        """
        params: dict[str, Any] = {}
        if node_id is not None:
            params["nodeId"] = node_id
        if backend_node_id is not None:
            params["backendNodeId"] = backend_node_id
        if object_id is not None:
            params["objectId"] = object_id
        return await self._client.send(method="Accessibility.getAXNodeAndAncestors", params=params)

    async def get_child_ax_nodes(self, id_: AXNodeId, frame_id: str | None = None) -> dict:
        """Fetches a particular accessibility node by AXNodeId.
Requires `enable()` to have been called previously.
        """
        params: dict[str, Any] = {}
        params["id"] = id_
        if frame_id is not None:
            params["frameId"] = frame_id
        return await self._client.send(method="Accessibility.getChildAXNodes", params=params)

    async def query_ax_tree(
        self,
        node_id: str | None = None,
        backend_node_id: str | None = None,
        object_id: str | None = None,
        accessible_name: str | None = None,
        role: str | None = None,
    ) -> dict:
        """Query a DOM node's accessibility subtree for accessible name and role.
This command computes the name and role for all nodes in the subtree, including those that are
ignored for accessibility, and returns those that match the specified name and role. If no DOM
node is specified, or the DOM node does not exist, the command returns an error. If neither
`accessibleName` or `role` is specified, it returns all the accessibility nodes in the subtree.
        """
        params: dict[str, Any] = {}
        if node_id is not None:
            params["nodeId"] = node_id
        if backend_node_id is not None:
            params["backendNodeId"] = backend_node_id
        if object_id is not None:
            params["objectId"] = object_id
        if accessible_name is not None:
            params["accessibleName"] = accessible_name
        if role is not None:
            params["role"] = role
        return await self._client.send(method="Accessibility.queryAXTree", params=params)
