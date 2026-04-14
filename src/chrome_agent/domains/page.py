"""CDP Page domain.

Actions and events related to the inspected page belong to the page domain.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


FrameId = str

# Indicates whether a frame has been identified as an ad.
AdFrameType = str  # Literal enum: "none", "child", "root"

AdFrameExplanation = str  # Literal enum: "ParentIsAd", "CreatedByAdScript", "MatchedBlockingRule"

# Indicates whether a frame has been identified as an ad and why.
AdFrameStatus = dict  # Object type

# Identifies the script which caused a script or frame to be labelled as an
# ad.
AdScriptId = dict  # Object type

# Encapsulates the script ancestry and the root script filterlist rule that
# caused the frame to be labelled as an ad. Only created when `ancestryChain`
# is not empty.
AdScriptAncestry = dict  # Object type

# Indicates whether the frame is a secure context and why it is the case.
SecureContextType = str  # Literal enum: "Secure", "SecureLocalhost", "InsecureScheme", "InsecureAncestor"

# Indicates whether the frame is cross-origin isolated and why it is the case.
CrossOriginIsolatedContextType = str  # Literal enum: "Isolated", "NotIsolated", "NotIsolatedFeatureDisabled"

GatedAPIFeatures = str  # Literal enum: "SharedArrayBuffers", "SharedArrayBuffersTransferAllowed", "PerformanceMeasureMemory", "PerformanceProfile"

# All Permissions Policy features. This enum should match the one defined
# in services/network/public/cpp/permissions_policy/permissions_policy_features.json5.
# LINT.IfChange(PermissionsPolicyFeature)
PermissionsPolicyFeature = str  # Literal enum: "accelerometer", "all-screens-capture", "ambient-light-sensor", "aria-notify", "attribution-reporting", "autofill", "autoplay", "bluetooth", "browsing-topics", "camera", "captured-surface-control", "ch-dpr", "ch-device-memory", "ch-downlink", "ch-ect", "ch-prefers-color-scheme", "ch-prefers-reduced-motion", "ch-prefers-reduced-transparency", "ch-rtt", "ch-save-data", "ch-ua", "ch-ua-arch", "ch-ua-bitness", "ch-ua-high-entropy-values", "ch-ua-platform", "ch-ua-model", "ch-ua-mobile", "ch-ua-form-factors", "ch-ua-full-version", "ch-ua-full-version-list", "ch-ua-platform-version", "ch-ua-wow64", "ch-viewport-height", "ch-viewport-width", "ch-width", "clipboard-read", "clipboard-write", "compute-pressure", "controlled-frame", "cross-origin-isolated", "deferred-fetch", "deferred-fetch-minimal", "device-attributes", "digital-credentials-create", "digital-credentials-get", "direct-sockets", "direct-sockets-multicast", "direct-sockets-private", "display-capture", "document-domain", "encrypted-media", "execution-while-out-of-viewport", "execution-while-not-rendered", "fenced-unpartitioned-storage-read", "focus-without-user-activation", "fullscreen", "frobulate", "gamepad", "geolocation", "gyroscope", "hid", "identity-credentials-get", "idle-detection", "interest-cohort", "join-ad-interest-group", "keyboard-map", "language-detector", "language-model", "local-fonts", "local-network", "local-network-access", "loopback-network", "magnetometer", "manual-text", "media-playback-while-not-visible", "microphone", "midi", "on-device-speech-recognition", "otp-credentials", "payment", "picture-in-picture", "private-aggregation", "private-state-token-issuance", "private-state-token-redemption", "publickey-credentials-create", "publickey-credentials-get", "record-ad-auction-events", "rewriter", "run-ad-auction", "screen-wake-lock", "serial", "shared-storage", "shared-storage-select-url", "smart-card", "speaker-selection", "storage-access", "sub-apps", "summarizer", "sync-xhr", "translator", "unload", "usb", "usb-unrestricted", "vertical-scroll", "web-app-installation", "web-printing", "web-share", "window-management", "writer", "xr-spatial-tracking"

# Reason for a permissions policy feature to be disabled.
PermissionsPolicyBlockReason = str  # Literal enum: "Header", "IframeAttribute", "InFencedFrameTree", "InIsolatedApp"

PermissionsPolicyBlockLocator = dict  # Object type

PermissionsPolicyFeatureState = dict  # Object type

# Origin Trial(https://www.chromium.org/blink/origin-trials) support.
# Status for an Origin Trial token.
OriginTrialTokenStatus = str  # Literal enum: "Success", "NotSupported", "Insecure", "Expired", "WrongOrigin", "InvalidSignature", "Malformed", "WrongVersion", "FeatureDisabled", "TokenDisabled", "FeatureDisabledForUser", "UnknownTrial"

# Status for an Origin Trial.
OriginTrialStatus = str  # Literal enum: "Enabled", "ValidTokenNotProvided", "OSNotSupported", "TrialNotAllowed"

OriginTrialUsageRestriction = str  # Literal enum: "None", "Subset"

OriginTrialToken = dict  # Object type

OriginTrialTokenWithStatus = dict  # Object type

OriginTrial = dict  # Object type

# Additional information about the frame document's security origin.
SecurityOriginDetails = dict  # Object type

# Information about the Frame on the page.
Frame = dict  # Object type

# Information about the Resource on the page.
FrameResource = dict  # Object type

# Information about the Frame hierarchy along with their cached resources.
FrameResourceTree = dict  # Object type

# Information about the Frame hierarchy.
FrameTree = dict  # Object type

ScriptIdentifier = str

# Transition type.
TransitionType = str  # Literal enum: "link", "typed", "address_bar", "auto_bookmark", "auto_subframe", "manual_subframe", "generated", "auto_toplevel", "form_submit", "reload", "keyword", "keyword_generated", "other"

# Navigation history entry.
NavigationEntry = dict  # Object type

# Screencast frame metadata.
ScreencastFrameMetadata = dict  # Object type

# Javascript dialog type.
DialogType = str  # Literal enum: "alert", "confirm", "prompt", "beforeunload"

# Error while paring app manifest.
AppManifestError = dict  # Object type

# Parsed app manifest properties.
AppManifestParsedProperties = dict  # Object type

# Layout viewport position and dimensions.
LayoutViewport = dict  # Object type

# Visual viewport position, dimensions, and scale.
VisualViewport = dict  # Object type

# Viewport for capturing screenshot.
Viewport = dict  # Object type

# Generic font families collection.
FontFamilies = dict  # Object type

# Font families collection for a script.
ScriptFontFamilies = dict  # Object type

# Default font sizes.
FontSizes = dict  # Object type

ClientNavigationReason = str  # Literal enum: "anchorClick", "formSubmissionGet", "formSubmissionPost", "httpHeaderRefresh", "initialFrameNavigation", "metaTagRefresh", "other", "pageBlockInterstitial", "reload", "scriptInitiated"

ClientNavigationDisposition = str  # Literal enum: "currentTab", "newTab", "newWindow", "download"

InstallabilityErrorArgument = dict  # Object type

# The installability error
InstallabilityError = dict  # Object type

# The referring-policy used for the navigation.
ReferrerPolicy = str  # Literal enum: "noReferrer", "noReferrerWhenDowngrade", "origin", "originWhenCrossOrigin", "sameOrigin", "strictOrigin", "strictOriginWhenCrossOrigin", "unsafeUrl"

# Per-script compilation cache parameters for `Page.produceCompilationCache`
CompilationCacheParams = dict  # Object type

FileFilter = dict  # Object type

FileHandler = dict  # Object type

# The image definition used in both icon and screenshot.
ImageResource = dict  # Object type

LaunchHandler = dict  # Object type

ProtocolHandler = dict  # Object type

RelatedApplication = dict  # Object type

ScopeExtension = dict  # Object type

Screenshot = dict  # Object type

ShareTarget = dict  # Object type

Shortcut = dict  # Object type

WebAppManifest = dict  # Object type

# The type of a frameNavigated event.
NavigationType = str  # Literal enum: "Navigation", "BackForwardCacheRestore"

# List of not restored reasons for back-forward cache.
BackForwardCacheNotRestoredReason = str  # Literal enum: "NotPrimaryMainFrame", "BackForwardCacheDisabled", "RelatedActiveContentsExist", "HTTPStatusNotOK", "SchemeNotHTTPOrHTTPS", "Loading", "WasGrantedMediaAccess", "DisableForRenderFrameHostCalled", "DomainNotAllowed", "HTTPMethodNotGET", "SubframeIsNavigating", "Timeout", "CacheLimit", "JavaScriptExecution", "RendererProcessKilled", "RendererProcessCrashed", "SchedulerTrackedFeatureUsed", "ConflictingBrowsingInstance", "CacheFlushed", "ServiceWorkerVersionActivation", "SessionRestored", "ServiceWorkerPostMessage", "EnteredBackForwardCacheBeforeServiceWorkerHostAdded", "RenderFrameHostReused_SameSite", "RenderFrameHostReused_CrossSite", "ServiceWorkerClaim", "IgnoreEventAndEvict", "HaveInnerContents", "TimeoutPuttingInCache", "BackForwardCacheDisabledByLowMemory", "BackForwardCacheDisabledByCommandLine", "NetworkRequestDatapipeDrainedAsBytesConsumer", "NetworkRequestRedirected", "NetworkRequestTimeout", "NetworkExceedsBufferLimit", "NavigationCancelledWhileRestoring", "NotMostRecentNavigationEntry", "BackForwardCacheDisabledForPrerender", "UserAgentOverrideDiffers", "ForegroundCacheLimit", "BrowsingInstanceNotSwapped", "BackForwardCacheDisabledForDelegate", "UnloadHandlerExistsInMainFrame", "UnloadHandlerExistsInSubFrame", "ServiceWorkerUnregistration", "CacheControlNoStore", "CacheControlNoStoreCookieModified", "CacheControlNoStoreHTTPOnlyCookieModified", "NoResponseHead", "Unknown", "ActivationNavigationsDisallowedForBug1234857", "ErrorDocument", "FencedFramesEmbedder", "CookieDisabled", "HTTPAuthRequired", "CookieFlushed", "BroadcastChannelOnMessage", "WebViewSettingsChanged", "WebViewJavaScriptObjectChanged", "WebViewMessageListenerInjected", "WebViewSafeBrowsingAllowlistChanged", "WebViewDocumentStartJavascriptChanged", "WebSocket", "WebTransport", "WebRTC", "MainResourceHasCacheControlNoStore", "MainResourceHasCacheControlNoCache", "SubresourceHasCacheControlNoStore", "SubresourceHasCacheControlNoCache", "ContainsPlugins", "DocumentLoaded", "OutstandingNetworkRequestOthers", "RequestedMIDIPermission", "RequestedAudioCapturePermission", "RequestedVideoCapturePermission", "RequestedBackForwardCacheBlockedSensors", "RequestedBackgroundWorkPermission", "BroadcastChannel", "WebXR", "SharedWorker", "SharedWorkerMessage", "SharedWorkerWithNoActiveClient", "WebLocks", "WebLocksContention", "WebHID", "WebBluetooth", "WebShare", "RequestedStorageAccessGrant", "WebNfc", "OutstandingNetworkRequestFetch", "OutstandingNetworkRequestXHR", "AppBanner", "Printing", "WebDatabase", "PictureInPicture", "SpeechRecognizer", "IdleManager", "PaymentManager", "SpeechSynthesis", "KeyboardLock", "WebOTPService", "OutstandingNetworkRequestDirectSocket", "InjectedJavascript", "InjectedStyleSheet", "KeepaliveRequest", "IndexedDBEvent", "Dummy", "JsNetworkRequestReceivedCacheControlNoStoreResource", "WebRTCUsedWithCCNS", "WebTransportUsedWithCCNS", "WebSocketUsedWithCCNS", "SmartCard", "LiveMediaStreamTrack", "UnloadHandler", "ParserAborted", "ContentSecurityHandler", "ContentWebAuthenticationAPI", "ContentFileChooser", "ContentSerial", "ContentFileSystemAccess", "ContentMediaDevicesDispatcherHost", "ContentWebBluetooth", "ContentWebUSB", "ContentMediaSessionService", "ContentScreenReader", "ContentDiscarded", "EmbedderPopupBlockerTabHelper", "EmbedderSafeBrowsingTriggeredPopupBlocker", "EmbedderSafeBrowsingThreatDetails", "EmbedderAppBannerManager", "EmbedderDomDistillerViewerSource", "EmbedderDomDistillerSelfDeletingRequestDelegate", "EmbedderOomInterventionTabHelper", "EmbedderOfflinePage", "EmbedderChromePasswordManagerClientBindCredentialManager", "EmbedderPermissionRequestManager", "EmbedderModalDialog", "EmbedderExtensions", "EmbedderExtensionMessaging", "EmbedderExtensionMessagingForOpenPort", "EmbedderExtensionSentMessageToCachedFrame", "RequestedByWebViewClient", "PostMessageByWebViewClient", "CacheControlNoStoreDeviceBoundSessionTerminated", "CacheLimitPrunedOnModerateMemoryPressure", "CacheLimitPrunedOnCriticalMemoryPressure"

# Types of not restored reasons for back-forward cache.
BackForwardCacheNotRestoredReasonType = str  # Literal enum: "SupportPending", "PageSupportNeeded", "Circumstantial"

BackForwardCacheBlockingDetails = dict  # Object type

BackForwardCacheNotRestoredExplanation = dict  # Object type

BackForwardCacheNotRestoredExplanationTree = dict  # Object type

class Page:
    """Actions and events related to the inspected page belong to the page domain."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def add_script_to_evaluate_on_load(self, script_source: str) -> dict:
        """Deprecated, please use addScriptToEvaluateOnNewDocument instead."""
        params: dict[str, Any] = {}
        params["scriptSource"] = script_source
        return await self._client.send(method="Page.addScriptToEvaluateOnLoad", params=params)

    async def add_script_to_evaluate_on_new_document(
        self,
        source: str,
        world_name: str | None = None,
        include_command_line_api: bool | None = None,
        run_immediately: bool | None = None,
    ) -> dict:
        """Evaluates given script in every frame upon creation (before loading frame's scripts)."""
        params: dict[str, Any] = {}
        params["source"] = source
        if world_name is not None:
            params["worldName"] = world_name
        if include_command_line_api is not None:
            params["includeCommandLineAPI"] = include_command_line_api
        if run_immediately is not None:
            params["runImmediately"] = run_immediately
        return await self._client.send(method="Page.addScriptToEvaluateOnNewDocument", params=params)

    async def bring_to_front(self) -> dict:
        """Brings page to front (activates tab)."""
        return await self._client.send(method="Page.bringToFront")

    async def capture_screenshot(
        self,
        format_: str | None = None,
        quality: int | None = None,
        clip: Viewport | None = None,
        from_surface: bool | None = None,
        capture_beyond_viewport: bool | None = None,
        optimize_for_speed: bool | None = None,
    ) -> dict:
        """Capture page screenshot."""
        params: dict[str, Any] = {}
        if format_ is not None:
            params["format"] = format_
        if quality is not None:
            params["quality"] = quality
        if clip is not None:
            params["clip"] = clip
        if from_surface is not None:
            params["fromSurface"] = from_surface
        if capture_beyond_viewport is not None:
            params["captureBeyondViewport"] = capture_beyond_viewport
        if optimize_for_speed is not None:
            params["optimizeForSpeed"] = optimize_for_speed
        return await self._client.send(method="Page.captureScreenshot", params=params)

    async def capture_snapshot(self, format_: str | None = None) -> dict:
        """Returns a snapshot of the page as a string. For MHTML format, the serialization includes
iframes, shadow DOM, external resources, and element-inline styles.
        """
        params: dict[str, Any] = {}
        if format_ is not None:
            params["format"] = format_
        return await self._client.send(method="Page.captureSnapshot", params=params)

    async def clear_device_metrics_override(self) -> dict:
        """Clears the overridden device metrics."""
        return await self._client.send(method="Page.clearDeviceMetricsOverride")

    async def clear_device_orientation_override(self) -> dict:
        """Clears the overridden Device Orientation."""
        return await self._client.send(method="Page.clearDeviceOrientationOverride")

    async def clear_geolocation_override(self) -> dict:
        """Clears the overridden Geolocation Position and Error."""
        return await self._client.send(method="Page.clearGeolocationOverride")

    async def create_isolated_world(
        self,
        frame_id: FrameId,
        world_name: str | None = None,
        grant_univeral_access: bool | None = None,
    ) -> dict:
        """Creates an isolated world for the given frame."""
        params: dict[str, Any] = {}
        params["frameId"] = frame_id
        if world_name is not None:
            params["worldName"] = world_name
        if grant_univeral_access is not None:
            params["grantUniveralAccess"] = grant_univeral_access
        return await self._client.send(method="Page.createIsolatedWorld", params=params)

    async def delete_cookie(self, cookie_name: str, url: str) -> dict:
        """Deletes browser cookie with given name, domain and path."""
        params: dict[str, Any] = {}
        params["cookieName"] = cookie_name
        params["url"] = url
        return await self._client.send(method="Page.deleteCookie", params=params)

    async def disable(self) -> dict:
        """Disables page domain notifications."""
        return await self._client.send(method="Page.disable")

    async def enable(self, enable_file_chooser_opened_event: bool | None = None) -> dict:
        """Enables page domain notifications."""
        params: dict[str, Any] = {}
        if enable_file_chooser_opened_event is not None:
            params["enableFileChooserOpenedEvent"] = enable_file_chooser_opened_event
        return await self._client.send(method="Page.enable", params=params)

    async def get_app_manifest(self, manifest_id: str | None = None) -> dict:
        """Gets the processed manifest for this current document.
  This API always waits for the manifest to be loaded.
  If manifestId is provided, and it does not match the manifest of the
    current document, this API errors out.
  If there is not a loaded page, this API errors out immediately.
        """
        params: dict[str, Any] = {}
        if manifest_id is not None:
            params["manifestId"] = manifest_id
        return await self._client.send(method="Page.getAppManifest", params=params)

    async def get_installability_errors(self) -> dict:
        return await self._client.send(method="Page.getInstallabilityErrors")

    async def get_manifest_icons(self) -> dict:
        """Deprecated because it's not guaranteed that the returned icon is in fact the one used for PWA installation."""
        return await self._client.send(method="Page.getManifestIcons")

    async def get_app_id(self) -> dict:
        """Returns the unique (PWA) app id.
Only returns values if the feature flag 'WebAppEnableManifestId' is enabled
        """
        return await self._client.send(method="Page.getAppId")

    async def get_ad_script_ancestry(self, frame_id: FrameId) -> dict:
        params: dict[str, Any] = {}
        params["frameId"] = frame_id
        return await self._client.send(method="Page.getAdScriptAncestry", params=params)

    async def get_frame_tree(self) -> dict:
        """Returns present frame tree structure."""
        return await self._client.send(method="Page.getFrameTree")

    async def get_layout_metrics(self) -> dict:
        """Returns metrics relating to the layouting of the page, such as viewport bounds/scale."""
        return await self._client.send(method="Page.getLayoutMetrics")

    async def get_navigation_history(self) -> dict:
        """Returns navigation history for the current page."""
        return await self._client.send(method="Page.getNavigationHistory")

    async def reset_navigation_history(self) -> dict:
        """Resets navigation history for the current page."""
        return await self._client.send(method="Page.resetNavigationHistory")

    async def get_resource_content(self, frame_id: FrameId, url: str) -> dict:
        """Returns content of the given resource."""
        params: dict[str, Any] = {}
        params["frameId"] = frame_id
        params["url"] = url
        return await self._client.send(method="Page.getResourceContent", params=params)

    async def get_resource_tree(self) -> dict:
        """Returns present frame / resource tree structure."""
        return await self._client.send(method="Page.getResourceTree")

    async def handle_java_script_dialog(self, accept: bool, prompt_text: str | None = None) -> dict:
        """Accepts or dismisses a JavaScript initiated dialog (alert, confirm, prompt, or onbeforeunload)."""
        params: dict[str, Any] = {}
        params["accept"] = accept
        if prompt_text is not None:
            params["promptText"] = prompt_text
        return await self._client.send(method="Page.handleJavaScriptDialog", params=params)

    async def navigate(
        self,
        url: str,
        referrer: str | None = None,
        transition_type: TransitionType | None = None,
        frame_id: FrameId | None = None,
        referrer_policy: ReferrerPolicy | None = None,
    ) -> dict:
        """Navigates current page to the given URL."""
        params: dict[str, Any] = {}
        params["url"] = url
        if referrer is not None:
            params["referrer"] = referrer
        if transition_type is not None:
            params["transitionType"] = transition_type
        if frame_id is not None:
            params["frameId"] = frame_id
        if referrer_policy is not None:
            params["referrerPolicy"] = referrer_policy
        return await self._client.send(method="Page.navigate", params=params)

    async def navigate_to_history_entry(self, entry_id: int) -> dict:
        """Navigates current page to the given history entry."""
        params: dict[str, Any] = {}
        params["entryId"] = entry_id
        return await self._client.send(method="Page.navigateToHistoryEntry", params=params)

    async def print_to_pdf(
        self,
        landscape: bool | None = None,
        display_header_footer: bool | None = None,
        print_background: bool | None = None,
        scale: float | None = None,
        paper_width: float | None = None,
        paper_height: float | None = None,
        margin_top: float | None = None,
        margin_bottom: float | None = None,
        margin_left: float | None = None,
        margin_right: float | None = None,
        page_ranges: str | None = None,
        header_template: str | None = None,
        footer_template: str | None = None,
        prefer_css_page_size: bool | None = None,
        transfer_mode: str | None = None,
        generate_tagged_pdf: bool | None = None,
        generate_document_outline: bool | None = None,
    ) -> dict:
        """Print page as PDF."""
        params: dict[str, Any] = {}
        if landscape is not None:
            params["landscape"] = landscape
        if display_header_footer is not None:
            params["displayHeaderFooter"] = display_header_footer
        if print_background is not None:
            params["printBackground"] = print_background
        if scale is not None:
            params["scale"] = scale
        if paper_width is not None:
            params["paperWidth"] = paper_width
        if paper_height is not None:
            params["paperHeight"] = paper_height
        if margin_top is not None:
            params["marginTop"] = margin_top
        if margin_bottom is not None:
            params["marginBottom"] = margin_bottom
        if margin_left is not None:
            params["marginLeft"] = margin_left
        if margin_right is not None:
            params["marginRight"] = margin_right
        if page_ranges is not None:
            params["pageRanges"] = page_ranges
        if header_template is not None:
            params["headerTemplate"] = header_template
        if footer_template is not None:
            params["footerTemplate"] = footer_template
        if prefer_css_page_size is not None:
            params["preferCSSPageSize"] = prefer_css_page_size
        if transfer_mode is not None:
            params["transferMode"] = transfer_mode
        if generate_tagged_pdf is not None:
            params["generateTaggedPDF"] = generate_tagged_pdf
        if generate_document_outline is not None:
            params["generateDocumentOutline"] = generate_document_outline
        return await self._client.send(method="Page.printToPDF", params=params)

    async def reload(
        self,
        ignore_cache: bool | None = None,
        script_to_evaluate_on_load: str | None = None,
        loader_id: str | None = None,
    ) -> dict:
        """Reloads given page optionally ignoring the cache."""
        params: dict[str, Any] = {}
        if ignore_cache is not None:
            params["ignoreCache"] = ignore_cache
        if script_to_evaluate_on_load is not None:
            params["scriptToEvaluateOnLoad"] = script_to_evaluate_on_load
        if loader_id is not None:
            params["loaderId"] = loader_id
        return await self._client.send(method="Page.reload", params=params)

    async def remove_script_to_evaluate_on_load(self, identifier: ScriptIdentifier) -> dict:
        """Deprecated, please use removeScriptToEvaluateOnNewDocument instead."""
        params: dict[str, Any] = {}
        params["identifier"] = identifier
        return await self._client.send(method="Page.removeScriptToEvaluateOnLoad", params=params)

    async def remove_script_to_evaluate_on_new_document(self, identifier: ScriptIdentifier) -> dict:
        """Removes given script from the list."""
        params: dict[str, Any] = {}
        params["identifier"] = identifier
        return await self._client.send(method="Page.removeScriptToEvaluateOnNewDocument", params=params)

    async def screencast_frame_ack(self, session_id: int) -> dict:
        """Acknowledges that a screencast frame has been received by the frontend."""
        params: dict[str, Any] = {}
        params["sessionId"] = session_id
        return await self._client.send(method="Page.screencastFrameAck", params=params)

    async def search_in_resource(
        self,
        frame_id: FrameId,
        url: str,
        query: str,
        case_sensitive: bool | None = None,
        is_regex: bool | None = None,
    ) -> dict:
        """Searches for given string in resource content."""
        params: dict[str, Any] = {}
        params["frameId"] = frame_id
        params["url"] = url
        params["query"] = query
        if case_sensitive is not None:
            params["caseSensitive"] = case_sensitive
        if is_regex is not None:
            params["isRegex"] = is_regex
        return await self._client.send(method="Page.searchInResource", params=params)

    async def set_ad_blocking_enabled(self, enabled: bool) -> dict:
        """Enable Chrome's experimental ad filter on all sites."""
        params: dict[str, Any] = {}
        params["enabled"] = enabled
        return await self._client.send(method="Page.setAdBlockingEnabled", params=params)

    async def set_bypass_csp(self, enabled: bool) -> dict:
        """Enable page Content Security Policy by-passing."""
        params: dict[str, Any] = {}
        params["enabled"] = enabled
        return await self._client.send(method="Page.setBypassCSP", params=params)

    async def get_permissions_policy_state(self, frame_id: FrameId) -> dict:
        """Get Permissions Policy state on given frame."""
        params: dict[str, Any] = {}
        params["frameId"] = frame_id
        return await self._client.send(method="Page.getPermissionsPolicyState", params=params)

    async def get_origin_trials(self, frame_id: FrameId) -> dict:
        """Get Origin Trials on given frame."""
        params: dict[str, Any] = {}
        params["frameId"] = frame_id
        return await self._client.send(method="Page.getOriginTrials", params=params)

    async def set_device_metrics_override(
        self,
        width: int,
        height: int,
        device_scale_factor: float,
        mobile: bool,
        scale: float | None = None,
        screen_width: int | None = None,
        screen_height: int | None = None,
        position_x: int | None = None,
        position_y: int | None = None,
        dont_set_visible_size: bool | None = None,
        screen_orientation: str | None = None,
        viewport: Viewport | None = None,
    ) -> dict:
        """Overrides the values of device screen dimensions (window.screen.width, window.screen.height,
window.innerWidth, window.innerHeight, and "device-width"/"device-height"-related CSS media
query results).
        """
        params: dict[str, Any] = {}
        params["width"] = width
        params["height"] = height
        params["deviceScaleFactor"] = device_scale_factor
        params["mobile"] = mobile
        if scale is not None:
            params["scale"] = scale
        if screen_width is not None:
            params["screenWidth"] = screen_width
        if screen_height is not None:
            params["screenHeight"] = screen_height
        if position_x is not None:
            params["positionX"] = position_x
        if position_y is not None:
            params["positionY"] = position_y
        if dont_set_visible_size is not None:
            params["dontSetVisibleSize"] = dont_set_visible_size
        if screen_orientation is not None:
            params["screenOrientation"] = screen_orientation
        if viewport is not None:
            params["viewport"] = viewport
        return await self._client.send(method="Page.setDeviceMetricsOverride", params=params)

    async def set_device_orientation_override(
        self,
        alpha: float,
        beta: float,
        gamma: float,
    ) -> dict:
        """Overrides the Device Orientation."""
        params: dict[str, Any] = {}
        params["alpha"] = alpha
        params["beta"] = beta
        params["gamma"] = gamma
        return await self._client.send(method="Page.setDeviceOrientationOverride", params=params)

    async def set_font_families(self, font_families: FontFamilies, for_scripts: list[ScriptFontFamilies] | None = None) -> dict:
        """Set generic font families."""
        params: dict[str, Any] = {}
        params["fontFamilies"] = font_families
        if for_scripts is not None:
            params["forScripts"] = for_scripts
        return await self._client.send(method="Page.setFontFamilies", params=params)

    async def set_font_sizes(self, font_sizes: FontSizes) -> dict:
        """Set default font sizes."""
        params: dict[str, Any] = {}
        params["fontSizes"] = font_sizes
        return await self._client.send(method="Page.setFontSizes", params=params)

    async def set_document_content(self, frame_id: FrameId, html: str) -> dict:
        """Sets given markup as the document's HTML."""
        params: dict[str, Any] = {}
        params["frameId"] = frame_id
        params["html"] = html
        return await self._client.send(method="Page.setDocumentContent", params=params)

    async def set_download_behavior(self, behavior: str, download_path: str | None = None) -> dict:
        """Set the behavior when downloading a file."""
        params: dict[str, Any] = {}
        params["behavior"] = behavior
        if download_path is not None:
            params["downloadPath"] = download_path
        return await self._client.send(method="Page.setDownloadBehavior", params=params)

    async def set_geolocation_override(
        self,
        latitude: float | None = None,
        longitude: float | None = None,
        accuracy: float | None = None,
    ) -> dict:
        """Overrides the Geolocation Position or Error. Omitting any of the parameters emulates position
unavailable.
        """
        params: dict[str, Any] = {}
        if latitude is not None:
            params["latitude"] = latitude
        if longitude is not None:
            params["longitude"] = longitude
        if accuracy is not None:
            params["accuracy"] = accuracy
        return await self._client.send(method="Page.setGeolocationOverride", params=params)

    async def set_lifecycle_events_enabled(self, enabled: bool) -> dict:
        """Controls whether page will emit lifecycle events."""
        params: dict[str, Any] = {}
        params["enabled"] = enabled
        return await self._client.send(method="Page.setLifecycleEventsEnabled", params=params)

    async def set_touch_emulation_enabled(self, enabled: bool, configuration: str | None = None) -> dict:
        """Toggles mouse event-based touch event emulation."""
        params: dict[str, Any] = {}
        params["enabled"] = enabled
        if configuration is not None:
            params["configuration"] = configuration
        return await self._client.send(method="Page.setTouchEmulationEnabled", params=params)

    async def start_screencast(
        self,
        format_: str | None = None,
        quality: int | None = None,
        max_width: int | None = None,
        max_height: int | None = None,
        every_nth_frame: int | None = None,
    ) -> dict:
        """Starts sending each frame using the `screencastFrame` event."""
        params: dict[str, Any] = {}
        if format_ is not None:
            params["format"] = format_
        if quality is not None:
            params["quality"] = quality
        if max_width is not None:
            params["maxWidth"] = max_width
        if max_height is not None:
            params["maxHeight"] = max_height
        if every_nth_frame is not None:
            params["everyNthFrame"] = every_nth_frame
        return await self._client.send(method="Page.startScreencast", params=params)

    async def stop_loading(self) -> dict:
        """Force the page stop all navigations and pending resource fetches."""
        return await self._client.send(method="Page.stopLoading")

    async def crash(self) -> dict:
        """Crashes renderer on the IO thread, generates minidumps."""
        return await self._client.send(method="Page.crash")

    async def close(self) -> dict:
        """Tries to close page, running its beforeunload hooks, if any."""
        return await self._client.send(method="Page.close")

    async def set_web_lifecycle_state(self, state: str) -> dict:
        """Tries to update the web lifecycle state of the page.
It will transition the page to the given state according to:
https://github.com/WICG/web-lifecycle/
        """
        params: dict[str, Any] = {}
        params["state"] = state
        return await self._client.send(method="Page.setWebLifecycleState", params=params)

    async def stop_screencast(self) -> dict:
        """Stops sending each frame in the `screencastFrame`."""
        return await self._client.send(method="Page.stopScreencast")

    async def produce_compilation_cache(self, scripts: list[CompilationCacheParams]) -> dict:
        """Requests backend to produce compilation cache for the specified scripts.
`scripts` are appended to the list of scripts for which the cache
would be produced. The list may be reset during page navigation.
When script with a matching URL is encountered, the cache is optionally
produced upon backend discretion, based on internal heuristics.
See also: `Page.compilationCacheProduced`.
        """
        params: dict[str, Any] = {}
        params["scripts"] = scripts
        return await self._client.send(method="Page.produceCompilationCache", params=params)

    async def add_compilation_cache(self, url: str, data: str) -> dict:
        """Seeds compilation cache for given url. Compilation cache does not survive
cross-process navigation.
        """
        params: dict[str, Any] = {}
        params["url"] = url
        params["data"] = data
        return await self._client.send(method="Page.addCompilationCache", params=params)

    async def clear_compilation_cache(self) -> dict:
        """Clears seeded compilation cache."""
        return await self._client.send(method="Page.clearCompilationCache")

    async def set_spc_transaction_mode(self, mode: str) -> dict:
        """Sets the Secure Payment Confirmation transaction mode.
https://w3c.github.io/secure-payment-confirmation/#sctn-automation-set-spc-transaction-mode
        """
        params: dict[str, Any] = {}
        params["mode"] = mode
        return await self._client.send(method="Page.setSPCTransactionMode", params=params)

    async def set_rph_registration_mode(self, mode: str) -> dict:
        """Extensions for Custom Handlers API:
https://html.spec.whatwg.org/multipage/system-state.html#rph-automation
        """
        params: dict[str, Any] = {}
        params["mode"] = mode
        return await self._client.send(method="Page.setRPHRegistrationMode", params=params)

    async def generate_test_report(self, message: str, group: str | None = None) -> dict:
        """Generates a report for testing."""
        params: dict[str, Any] = {}
        params["message"] = message
        if group is not None:
            params["group"] = group
        return await self._client.send(method="Page.generateTestReport", params=params)

    async def wait_for_debugger(self) -> dict:
        """Pauses page execution. Can be resumed using generic Runtime.runIfWaitingForDebugger."""
        return await self._client.send(method="Page.waitForDebugger")

    async def set_intercept_file_chooser_dialog(self, enabled: bool, cancel: bool | None = None) -> dict:
        """Intercept file chooser requests and transfer control to protocol clients.
When file chooser interception is enabled, native file chooser dialog is not shown.
Instead, a protocol event `Page.fileChooserOpened` is emitted.
        """
        params: dict[str, Any] = {}
        params["enabled"] = enabled
        if cancel is not None:
            params["cancel"] = cancel
        return await self._client.send(method="Page.setInterceptFileChooserDialog", params=params)

    async def set_prerendering_allowed(self, is_allowed: bool) -> dict:
        """Enable/disable prerendering manually.

This command is a short-term solution for https://crbug.com/1440085.
See https://docs.google.com/document/d/12HVmFxYj5Jc-eJr5OmWsa2bqTJsbgGLKI6ZIyx0_wpA
for more details.

TODO(https://crbug.com/1440085): Remove this once Puppeteer supports tab targets.
        """
        params: dict[str, Any] = {}
        params["isAllowed"] = is_allowed
        return await self._client.send(method="Page.setPrerenderingAllowed", params=params)

    async def get_annotated_page_content(self, include_actionable_information: bool | None = None) -> dict:
        """Get the annotated page content for the main frame.
This is an experimental command that is subject to change.
        """
        params: dict[str, Any] = {}
        if include_actionable_information is not None:
            params["includeActionableInformation"] = include_actionable_information
        return await self._client.send(method="Page.getAnnotatedPageContent", params=params)
