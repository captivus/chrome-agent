"""CDP Target domain.

Supports additional targets discovery and allows to attach to them.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


TargetID = str

SessionID = str

TargetInfo = dict  # Object type

# A filter used by target query/discovery/auto-attach operations.
FilterEntry = dict  # Object type

TargetFilter = list[FilterEntry]

RemoteLocation = dict  # Object type

# The state of the target window.
WindowState = str  # Literal enum: "normal", "minimized", "maximized", "fullscreen"

class Target:
    """Supports additional targets discovery and allows to attach to them."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def activate_target(self, target_id: TargetID) -> dict:
        """Activates (focuses) the target."""
        params: dict[str, Any] = {}
        params["targetId"] = target_id
        return await self._client.send(method="Target.activateTarget", params=params)

    async def attach_to_target(self, target_id: TargetID, flatten: bool | None = None) -> dict:
        """Attaches to the target with given id."""
        params: dict[str, Any] = {}
        params["targetId"] = target_id
        if flatten is not None:
            params["flatten"] = flatten
        return await self._client.send(method="Target.attachToTarget", params=params)

    async def attach_to_browser_target(self) -> dict:
        """Attaches to the browser target, only uses flat sessionId mode."""
        return await self._client.send(method="Target.attachToBrowserTarget")

    async def close_target(self, target_id: TargetID) -> dict:
        """Closes the target. If the target is a page that gets closed too."""
        params: dict[str, Any] = {}
        params["targetId"] = target_id
        return await self._client.send(method="Target.closeTarget", params=params)

    async def expose_dev_tools_protocol(
        self,
        target_id: TargetID,
        binding_name: str | None = None,
        inherit_permissions: bool | None = None,
    ) -> dict:
        """Inject object to the target's main frame that provides a communication
channel with browser target.

Injected object will be available as `window[bindingName]`.

The object has the following API:
- `binding.send(json)` - a method to send messages over the remote debugging protocol
- `binding.onmessage = json => handleMessage(json)` - a callback that will be called for the protocol notifications and command responses.
        """
        params: dict[str, Any] = {}
        params["targetId"] = target_id
        if binding_name is not None:
            params["bindingName"] = binding_name
        if inherit_permissions is not None:
            params["inheritPermissions"] = inherit_permissions
        return await self._client.send(method="Target.exposeDevToolsProtocol", params=params)

    async def create_browser_context(
        self,
        dispose_on_detach: bool | None = None,
        proxy_server: str | None = None,
        proxy_bypass_list: str | None = None,
        origins_with_universal_network_access: list[str] | None = None,
    ) -> dict:
        """Creates a new empty BrowserContext. Similar to an incognito profile but you can have more than
one.
        """
        params: dict[str, Any] = {}
        if dispose_on_detach is not None:
            params["disposeOnDetach"] = dispose_on_detach
        if proxy_server is not None:
            params["proxyServer"] = proxy_server
        if proxy_bypass_list is not None:
            params["proxyBypassList"] = proxy_bypass_list
        if origins_with_universal_network_access is not None:
            params["originsWithUniversalNetworkAccess"] = origins_with_universal_network_access
        return await self._client.send(method="Target.createBrowserContext", params=params)

    async def get_browser_contexts(self) -> dict:
        """Returns all browser contexts created with `Target.createBrowserContext` method."""
        return await self._client.send(method="Target.getBrowserContexts")

    async def create_target(
        self,
        url: str,
        left: int | None = None,
        top: int | None = None,
        width: int | None = None,
        height: int | None = None,
        window_state: WindowState | None = None,
        browser_context_id: str | None = None,
        enable_begin_frame_control: bool | None = None,
        new_window: bool | None = None,
        background: bool | None = None,
        for_tab: bool | None = None,
        hidden: bool | None = None,
        focus: bool | None = None,
    ) -> dict:
        """Creates a new page."""
        params: dict[str, Any] = {}
        params["url"] = url
        if left is not None:
            params["left"] = left
        if top is not None:
            params["top"] = top
        if width is not None:
            params["width"] = width
        if height is not None:
            params["height"] = height
        if window_state is not None:
            params["windowState"] = window_state
        if browser_context_id is not None:
            params["browserContextId"] = browser_context_id
        if enable_begin_frame_control is not None:
            params["enableBeginFrameControl"] = enable_begin_frame_control
        if new_window is not None:
            params["newWindow"] = new_window
        if background is not None:
            params["background"] = background
        if for_tab is not None:
            params["forTab"] = for_tab
        if hidden is not None:
            params["hidden"] = hidden
        if focus is not None:
            params["focus"] = focus
        return await self._client.send(method="Target.createTarget", params=params)

    async def detach_from_target(self, session_id: SessionID | None = None, target_id: TargetID | None = None) -> dict:
        """Detaches session with given id."""
        params: dict[str, Any] = {}
        if session_id is not None:
            params["sessionId"] = session_id
        if target_id is not None:
            params["targetId"] = target_id
        return await self._client.send(method="Target.detachFromTarget", params=params)

    async def dispose_browser_context(self, browser_context_id: str) -> dict:
        """Deletes a BrowserContext. All the belonging pages will be closed without calling their
beforeunload hooks.
        """
        params: dict[str, Any] = {}
        params["browserContextId"] = browser_context_id
        return await self._client.send(method="Target.disposeBrowserContext", params=params)

    async def get_target_info(self, target_id: TargetID | None = None) -> dict:
        """Returns information about a target."""
        params: dict[str, Any] = {}
        if target_id is not None:
            params["targetId"] = target_id
        return await self._client.send(method="Target.getTargetInfo", params=params)

    async def get_targets(self, filter: TargetFilter | None = None) -> dict:
        """Retrieves a list of available targets."""
        params: dict[str, Any] = {}
        if filter is not None:
            params["filter"] = filter
        return await self._client.send(method="Target.getTargets", params=params)

    async def send_message_to_target(
        self,
        message: str,
        session_id: SessionID | None = None,
        target_id: TargetID | None = None,
    ) -> dict:
        """Sends protocol message over session with given id.
Consider using flat mode instead; see commands attachToTarget, setAutoAttach,
and crbug.com/991325.
        """
        params: dict[str, Any] = {}
        params["message"] = message
        if session_id is not None:
            params["sessionId"] = session_id
        if target_id is not None:
            params["targetId"] = target_id
        return await self._client.send(method="Target.sendMessageToTarget", params=params)

    async def set_auto_attach(
        self,
        auto_attach: bool,
        wait_for_debugger_on_start: bool,
        flatten: bool | None = None,
        filter: TargetFilter | None = None,
    ) -> dict:
        """Controls whether to automatically attach to new targets which are considered
to be directly related to this one (for example, iframes or workers).
When turned on, attaches to all existing related targets as well. When turned off,
automatically detaches from all currently attached targets.
This also clears all targets added by `autoAttachRelated` from the list of targets to watch
for creation of related targets.
You might want to call this recursively for auto-attached targets to attach
to all available targets.
        """
        params: dict[str, Any] = {}
        params["autoAttach"] = auto_attach
        params["waitForDebuggerOnStart"] = wait_for_debugger_on_start
        if flatten is not None:
            params["flatten"] = flatten
        if filter is not None:
            params["filter"] = filter
        return await self._client.send(method="Target.setAutoAttach", params=params)

    async def auto_attach_related(
        self,
        target_id: TargetID,
        wait_for_debugger_on_start: bool,
        filter: TargetFilter | None = None,
    ) -> dict:
        """Adds the specified target to the list of targets that will be monitored for any related target
creation (such as child frames, child workers and new versions of service worker) and reported
through `attachedToTarget`. The specified target is also auto-attached.
This cancels the effect of any previous `setAutoAttach` and is also cancelled by subsequent
`setAutoAttach`. Only available at the Browser target.
        """
        params: dict[str, Any] = {}
        params["targetId"] = target_id
        params["waitForDebuggerOnStart"] = wait_for_debugger_on_start
        if filter is not None:
            params["filter"] = filter
        return await self._client.send(method="Target.autoAttachRelated", params=params)

    async def set_discover_targets(self, discover: bool, filter: TargetFilter | None = None) -> dict:
        """Controls whether to discover available targets and notify via
`targetCreated/targetInfoChanged/targetDestroyed` events.
        """
        params: dict[str, Any] = {}
        params["discover"] = discover
        if filter is not None:
            params["filter"] = filter
        return await self._client.send(method="Target.setDiscoverTargets", params=params)

    async def set_remote_locations(self, locations: list[RemoteLocation]) -> dict:
        """Enables target discovery for the specified locations, when `setDiscoverTargets` was set to
`true`.
        """
        params: dict[str, Any] = {}
        params["locations"] = locations
        return await self._client.send(method="Target.setRemoteLocations", params=params)

    async def get_dev_tools_target(self, target_id: TargetID) -> dict:
        """Gets the targetId of the DevTools page target opened for the given target
(if any).
        """
        params: dict[str, Any] = {}
        params["targetId"] = target_id
        return await self._client.send(method="Target.getDevToolsTarget", params=params)

    async def open_dev_tools(self, target_id: TargetID, panel_id: str | None = None) -> dict:
        """Opens a DevTools window for the target."""
        params: dict[str, Any] = {}
        params["targetId"] = target_id
        if panel_id is not None:
            params["panelId"] = panel_id
        return await self._client.send(method="Target.openDevTools", params=params)
