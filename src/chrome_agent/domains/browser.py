"""CDP Browser domain.

The Browser domain defines methods and events for browser managing.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


BrowserContextID = str

WindowID = int

# The state of the browser window.
WindowState = str  # Literal enum: "normal", "minimized", "maximized", "fullscreen"

# Browser window bounds information
Bounds = dict  # Object type

PermissionType = str  # Literal enum: "ar", "audioCapture", "automaticFullscreen", "backgroundFetch", "backgroundSync", "cameraPanTiltZoom", "capturedSurfaceControl", "clipboardReadWrite", "clipboardSanitizedWrite", "displayCapture", "durableStorage", "geolocation", "handTracking", "idleDetection", "keyboardLock", "localFonts", "localNetwork", "localNetworkAccess", "loopbackNetwork", "midi", "midiSysex", "nfc", "notifications", "paymentHandler", "periodicBackgroundSync", "pointerLock", "protectedMediaIdentifier", "sensors", "smartCard", "speakerSelection", "storageAccess", "topLevelStorageAccess", "videoCapture", "vr", "wakeLockScreen", "wakeLockSystem", "webAppInstallation", "webPrinting", "windowManagement"

PermissionSetting = str  # Literal enum: "granted", "denied", "prompt"

# Definition of PermissionDescriptor defined in the Permissions API:
# https://w3c.github.io/permissions/#dom-permissiondescriptor.
PermissionDescriptor = dict  # Object type

# Browser command ids used by executeBrowserCommand.
BrowserCommandId = str  # Literal enum: "openTabSearch", "closeTabSearch", "openGlic"

# Chrome histogram bucket.
Bucket = dict  # Object type

# Chrome histogram.
Histogram = dict  # Object type

PrivacySandboxAPI = str  # Literal enum: "BiddingAndAuctionServices", "TrustedKeyValue"

class Browser:
    """The Browser domain defines methods and events for browser managing."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def set_permission(
        self,
        permission: PermissionDescriptor,
        setting: PermissionSetting,
        origin: str | None = None,
        embedded_origin: str | None = None,
        browser_context_id: BrowserContextID | None = None,
    ) -> dict:
        """Set permission settings for given embedding and embedded origins."""
        params: dict[str, Any] = {}
        params["permission"] = permission
        params["setting"] = setting
        if origin is not None:
            params["origin"] = origin
        if embedded_origin is not None:
            params["embeddedOrigin"] = embedded_origin
        if browser_context_id is not None:
            params["browserContextId"] = browser_context_id
        return await self._client.send(method="Browser.setPermission", params=params)

    async def grant_permissions(
        self,
        permissions: list[PermissionType],
        origin: str | None = None,
        browser_context_id: BrowserContextID | None = None,
    ) -> dict:
        """Grant specific permissions to the given origin and reject all others. Deprecated. Use
setPermission instead.
        """
        params: dict[str, Any] = {}
        params["permissions"] = permissions
        if origin is not None:
            params["origin"] = origin
        if browser_context_id is not None:
            params["browserContextId"] = browser_context_id
        return await self._client.send(method="Browser.grantPermissions", params=params)

    async def reset_permissions(self, browser_context_id: BrowserContextID | None = None) -> dict:
        """Reset all permission management for all origins."""
        params: dict[str, Any] = {}
        if browser_context_id is not None:
            params["browserContextId"] = browser_context_id
        return await self._client.send(method="Browser.resetPermissions", params=params)

    async def set_download_behavior(
        self,
        behavior: str,
        browser_context_id: BrowserContextID | None = None,
        download_path: str | None = None,
        events_enabled: bool | None = None,
    ) -> dict:
        """Set the behavior when downloading a file."""
        params: dict[str, Any] = {}
        params["behavior"] = behavior
        if browser_context_id is not None:
            params["browserContextId"] = browser_context_id
        if download_path is not None:
            params["downloadPath"] = download_path
        if events_enabled is not None:
            params["eventsEnabled"] = events_enabled
        return await self._client.send(method="Browser.setDownloadBehavior", params=params)

    async def cancel_download(self, guid: str, browser_context_id: BrowserContextID | None = None) -> dict:
        """Cancel a download if in progress"""
        params: dict[str, Any] = {}
        params["guid"] = guid
        if browser_context_id is not None:
            params["browserContextId"] = browser_context_id
        return await self._client.send(method="Browser.cancelDownload", params=params)

    async def close(self) -> dict:
        """Close browser gracefully."""
        return await self._client.send(method="Browser.close")

    async def crash(self) -> dict:
        """Crashes browser on the main thread."""
        return await self._client.send(method="Browser.crash")

    async def crash_gpu_process(self) -> dict:
        """Crashes GPU process."""
        return await self._client.send(method="Browser.crashGpuProcess")

    async def get_version(self) -> dict:
        """Returns version information."""
        return await self._client.send(method="Browser.getVersion")

    async def get_browser_command_line(self) -> dict:
        """Returns the command line switches for the browser process if, and only if
--enable-automation is on the commandline.
        """
        return await self._client.send(method="Browser.getBrowserCommandLine")

    async def get_histograms(self, query: str | None = None, delta: bool | None = None) -> dict:
        """Get Chrome histograms."""
        params: dict[str, Any] = {}
        if query is not None:
            params["query"] = query
        if delta is not None:
            params["delta"] = delta
        return await self._client.send(method="Browser.getHistograms", params=params)

    async def get_histogram(self, name: str, delta: bool | None = None) -> dict:
        """Get a Chrome histogram by name."""
        params: dict[str, Any] = {}
        params["name"] = name
        if delta is not None:
            params["delta"] = delta
        return await self._client.send(method="Browser.getHistogram", params=params)

    async def get_window_bounds(self, window_id: WindowID) -> dict:
        """Get position and size of the browser window."""
        params: dict[str, Any] = {}
        params["windowId"] = window_id
        return await self._client.send(method="Browser.getWindowBounds", params=params)

    async def get_window_for_target(self, target_id: str | None = None) -> dict:
        """Get the browser window that contains the devtools target."""
        params: dict[str, Any] = {}
        if target_id is not None:
            params["targetId"] = target_id
        return await self._client.send(method="Browser.getWindowForTarget", params=params)

    async def set_window_bounds(self, window_id: WindowID, bounds: Bounds) -> dict:
        """Set position and/or size of the browser window."""
        params: dict[str, Any] = {}
        params["windowId"] = window_id
        params["bounds"] = bounds
        return await self._client.send(method="Browser.setWindowBounds", params=params)

    async def set_contents_size(
        self,
        window_id: WindowID,
        width: int | None = None,
        height: int | None = None,
    ) -> dict:
        """Set size of the browser contents resizing browser window as necessary."""
        params: dict[str, Any] = {}
        params["windowId"] = window_id
        if width is not None:
            params["width"] = width
        if height is not None:
            params["height"] = height
        return await self._client.send(method="Browser.setContentsSize", params=params)

    async def set_dock_tile(self, badge_label: str | None = None, image: str | None = None) -> dict:
        """Set dock tile details, platform-specific."""
        params: dict[str, Any] = {}
        if badge_label is not None:
            params["badgeLabel"] = badge_label
        if image is not None:
            params["image"] = image
        return await self._client.send(method="Browser.setDockTile", params=params)

    async def execute_browser_command(self, command_id: BrowserCommandId) -> dict:
        """Invoke custom browser commands used by telemetry."""
        params: dict[str, Any] = {}
        params["commandId"] = command_id
        return await self._client.send(method="Browser.executeBrowserCommand", params=params)

    async def add_privacy_sandbox_enrollment_override(self, url: str) -> dict:
        """Allows a site to use privacy sandbox features that require enrollment
without the site actually being enrolled. Only supported on page targets.
        """
        params: dict[str, Any] = {}
        params["url"] = url
        return await self._client.send(method="Browser.addPrivacySandboxEnrollmentOverride", params=params)

    async def add_privacy_sandbox_coordinator_key_config(
        self,
        api: PrivacySandboxAPI,
        coordinator_origin: str,
        key_config: str,
        browser_context_id: BrowserContextID | None = None,
    ) -> dict:
        """Configures encryption keys used with a given privacy sandbox API to talk
to a trusted coordinator.  Since this is intended for test automation only,
coordinatorOrigin must be a .test domain. No existing coordinator
configuration for the origin may exist.
        """
        params: dict[str, Any] = {}
        params["api"] = api
        params["coordinatorOrigin"] = coordinator_origin
        params["keyConfig"] = key_config
        if browser_context_id is not None:
            params["browserContextId"] = browser_context_id
        return await self._client.send(method="Browser.addPrivacySandboxCoordinatorKeyConfig", params=params)
