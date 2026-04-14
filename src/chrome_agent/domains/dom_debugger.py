"""CDP DOMDebugger domain.

DOM debugging allows setting breakpoints on particular DOM operations and events. JavaScript
execution will stop on these operations as if there was a regular breakpoint set.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


# DOM breakpoint type.
DOMBreakpointType = str  # Literal enum: "subtree-modified", "attribute-modified", "node-removed"

# CSP Violation type.
CSPViolationType = str  # Literal enum: "trustedtype-sink-violation", "trustedtype-policy-violation"

# Object event listener.
EventListener = dict  # Object type

class DOMDebugger:
    """DOM debugging allows setting breakpoints on particular DOM operations and events. JavaScript
execution will stop on these operations as if there was a regular breakpoint set."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def get_event_listeners(
        self,
        object_id: str,
        depth: int | None = None,
        pierce: bool | None = None,
    ) -> dict:
        """Returns event listeners of the given object."""
        params: dict[str, Any] = {}
        params["objectId"] = object_id
        if depth is not None:
            params["depth"] = depth
        if pierce is not None:
            params["pierce"] = pierce
        return await self._client.send(method="DOMDebugger.getEventListeners", params=params)

    async def remove_dom_breakpoint(self, node_id: str, type_: DOMBreakpointType) -> dict:
        """Removes DOM breakpoint that was set using `setDOMBreakpoint`."""
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        params["type"] = type_
        return await self._client.send(method="DOMDebugger.removeDOMBreakpoint", params=params)

    async def remove_event_listener_breakpoint(self, event_name: str, target_name: str | None = None) -> dict:
        """Removes breakpoint on particular DOM event."""
        params: dict[str, Any] = {}
        params["eventName"] = event_name
        if target_name is not None:
            params["targetName"] = target_name
        return await self._client.send(method="DOMDebugger.removeEventListenerBreakpoint", params=params)

    async def remove_instrumentation_breakpoint(self, event_name: str) -> dict:
        """Removes breakpoint on particular native event."""
        params: dict[str, Any] = {}
        params["eventName"] = event_name
        return await self._client.send(method="DOMDebugger.removeInstrumentationBreakpoint", params=params)

    async def remove_xhr_breakpoint(self, url: str) -> dict:
        """Removes breakpoint from XMLHttpRequest."""
        params: dict[str, Any] = {}
        params["url"] = url
        return await self._client.send(method="DOMDebugger.removeXHRBreakpoint", params=params)

    async def set_break_on_csp_violation(self, violation_types: list[CSPViolationType]) -> dict:
        """Sets breakpoint on particular CSP violations."""
        params: dict[str, Any] = {}
        params["violationTypes"] = violation_types
        return await self._client.send(method="DOMDebugger.setBreakOnCSPViolation", params=params)

    async def set_dom_breakpoint(self, node_id: str, type_: DOMBreakpointType) -> dict:
        """Sets breakpoint on particular operation with DOM."""
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        params["type"] = type_
        return await self._client.send(method="DOMDebugger.setDOMBreakpoint", params=params)

    async def set_event_listener_breakpoint(self, event_name: str, target_name: str | None = None) -> dict:
        """Sets breakpoint on particular DOM event."""
        params: dict[str, Any] = {}
        params["eventName"] = event_name
        if target_name is not None:
            params["targetName"] = target_name
        return await self._client.send(method="DOMDebugger.setEventListenerBreakpoint", params=params)

    async def set_instrumentation_breakpoint(self, event_name: str) -> dict:
        """Sets breakpoint on particular native event."""
        params: dict[str, Any] = {}
        params["eventName"] = event_name
        return await self._client.send(method="DOMDebugger.setInstrumentationBreakpoint", params=params)

    async def set_xhr_breakpoint(self, url: str) -> dict:
        """Sets breakpoint on XMLHttpRequest."""
        params: dict[str, Any] = {}
        params["url"] = url
        return await self._client.send(method="DOMDebugger.setXHRBreakpoint", params=params)
