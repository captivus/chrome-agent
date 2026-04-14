"""CDP Network domain.

Network domain allows tracking network activities of the page. It exposes information about http,
file, data and other requests and responses, their headers, bodies, timing, etc.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


# Resource type as it was perceived by the rendering engine.
ResourceType = str  # Literal enum: "Document", "Stylesheet", "Image", "Media", "Font", "Script", "TextTrack", "XHR", "Fetch", "Prefetch", "EventSource", "WebSocket", "Manifest", "SignedExchange", "Ping", "CSPViolationReport", "Preflight", "FedCM", "Other"

LoaderId = str

RequestId = str

InterceptionId = str

# Network level fetch failure reason.
ErrorReason = str  # Literal enum: "Failed", "Aborted", "TimedOut", "AccessDenied", "ConnectionClosed", "ConnectionReset", "ConnectionRefused", "ConnectionAborted", "ConnectionFailed", "NameNotResolved", "InternetDisconnected", "AddressUnreachable", "BlockedByClient", "BlockedByResponse"

TimeSinceEpoch = float

MonotonicTime = float

Headers = dict

# The underlying connection technology that the browser is supposedly using.
ConnectionType = str  # Literal enum: "none", "cellular2g", "cellular3g", "cellular4g", "bluetooth", "ethernet", "wifi", "wimax", "other"

# Represents the cookie's 'SameSite' status:
# https://tools.ietf.org/html/draft-west-first-party-cookies
CookieSameSite = str  # Literal enum: "Strict", "Lax", "None"

# Represents the cookie's 'Priority' status:
# https://tools.ietf.org/html/draft-west-cookie-priority-00
CookiePriority = str  # Literal enum: "Low", "Medium", "High"

# Represents the source scheme of the origin that originally set the cookie.
# A value of "Unset" allows protocol clients to emulate legacy cookie scope for the scheme.
# This is a temporary ability and it will be removed in the future.
CookieSourceScheme = str  # Literal enum: "Unset", "NonSecure", "Secure"

# Timing information for the request.
ResourceTiming = dict  # Object type

# Loading priority of a resource request.
ResourcePriority = str  # Literal enum: "VeryLow", "Low", "Medium", "High", "VeryHigh"

# The render blocking behavior of a resource request.
RenderBlockingBehavior = str  # Literal enum: "Blocking", "InBodyParserBlocking", "NonBlocking", "NonBlockingDynamic", "PotentiallyBlocking"

# Post data entry for HTTP request
PostDataEntry = dict  # Object type

# HTTP request data.
Request = dict  # Object type

# Details of a signed certificate timestamp (SCT).
SignedCertificateTimestamp = dict  # Object type

# Security details about a request.
SecurityDetails = dict  # Object type

# Whether the request complied with Certificate Transparency policy.
CertificateTransparencyCompliance = str  # Literal enum: "unknown", "not-compliant", "compliant"

# The reason why request was blocked.
BlockedReason = str  # Literal enum: "other", "csp", "mixed-content", "origin", "inspector", "integrity", "subresource-filter", "content-type", "coep-frame-resource-needs-coep-header", "coop-sandboxed-iframe-cannot-navigate-to-coop-page", "corp-not-same-origin", "corp-not-same-origin-after-defaulted-to-same-origin-by-coep", "corp-not-same-origin-after-defaulted-to-same-origin-by-dip", "corp-not-same-origin-after-defaulted-to-same-origin-by-coep-and-dip", "corp-not-same-site", "sri-message-signature-mismatch"

# The reason why request was blocked.
CorsError = str  # Literal enum: "DisallowedByMode", "InvalidResponse", "WildcardOriginNotAllowed", "MissingAllowOriginHeader", "MultipleAllowOriginValues", "InvalidAllowOriginValue", "AllowOriginMismatch", "InvalidAllowCredentials", "CorsDisabledScheme", "PreflightInvalidStatus", "PreflightDisallowedRedirect", "PreflightWildcardOriginNotAllowed", "PreflightMissingAllowOriginHeader", "PreflightMultipleAllowOriginValues", "PreflightInvalidAllowOriginValue", "PreflightAllowOriginMismatch", "PreflightInvalidAllowCredentials", "PreflightMissingAllowExternal", "PreflightInvalidAllowExternal", "InvalidAllowMethodsPreflightResponse", "InvalidAllowHeadersPreflightResponse", "MethodDisallowedByPreflightResponse", "HeaderDisallowedByPreflightResponse", "RedirectContainsCredentials", "InsecureLocalNetwork", "InvalidLocalNetworkAccess", "NoCorsRedirectModeNotFollow", "LocalNetworkAccessPermissionDenied"

CorsErrorStatus = dict  # Object type

# Source of serviceworker response.
ServiceWorkerResponseSource = str  # Literal enum: "cache-storage", "http-cache", "fallback-code", "network"

# Determines what type of Trust Token operation is executed and
# depending on the type, some additional parameters. The values
# are specified in third_party/blink/renderer/core/fetch/trust_token.idl.
TrustTokenParams = dict  # Object type

TrustTokenOperationType = str  # Literal enum: "Issuance", "Redemption", "Signing"

# The reason why Chrome uses a specific transport protocol for HTTP semantics.
AlternateProtocolUsage = str  # Literal enum: "alternativeJobWonWithoutRace", "alternativeJobWonRace", "mainJobWonRace", "mappingMissing", "broken", "dnsAlpnH3JobWonWithoutRace", "dnsAlpnH3JobWonRace", "unspecifiedReason"

# Source of service worker router.
ServiceWorkerRouterSource = str  # Literal enum: "network", "cache", "fetch-event", "race-network-and-fetch-handler", "race-network-and-cache"

ServiceWorkerRouterInfo = dict  # Object type

# HTTP response data.
Response = dict  # Object type

# WebSocket request data.
WebSocketRequest = dict  # Object type

# WebSocket response data.
WebSocketResponse = dict  # Object type

# WebSocket message data. This represents an entire WebSocket message, not just a fragmented frame as the name suggests.
WebSocketFrame = dict  # Object type

# Information about the cached resource.
CachedResource = dict  # Object type

# Information about the request initiator.
Initiator = dict  # Object type

# cookiePartitionKey object
# The representation of the components of the key that are created by the cookiePartitionKey class contained in net/cookies/cookie_partition_key.h.
CookiePartitionKey = dict  # Object type

# Cookie object
Cookie = dict  # Object type

# Types of reasons why a cookie may not be stored from a response.
SetCookieBlockedReason = str  # Literal enum: "SecureOnly", "SameSiteStrict", "SameSiteLax", "SameSiteUnspecifiedTreatedAsLax", "SameSiteNoneInsecure", "UserPreferences", "ThirdPartyPhaseout", "ThirdPartyBlockedInFirstPartySet", "SyntaxError", "SchemeNotSupported", "OverwriteSecure", "InvalidDomain", "InvalidPrefix", "UnknownError", "SchemefulSameSiteStrict", "SchemefulSameSiteLax", "SchemefulSameSiteUnspecifiedTreatedAsLax", "NameValuePairExceedsMaxSize", "DisallowedCharacter", "NoCookieContent"

# Types of reasons why a cookie may not be sent with a request.
CookieBlockedReason = str  # Literal enum: "SecureOnly", "NotOnPath", "DomainMismatch", "SameSiteStrict", "SameSiteLax", "SameSiteUnspecifiedTreatedAsLax", "SameSiteNoneInsecure", "UserPreferences", "ThirdPartyPhaseout", "ThirdPartyBlockedInFirstPartySet", "UnknownError", "SchemefulSameSiteStrict", "SchemefulSameSiteLax", "SchemefulSameSiteUnspecifiedTreatedAsLax", "NameValuePairExceedsMaxSize", "PortMismatch", "SchemeMismatch", "AnonymousContext"

# Types of reasons why a cookie should have been blocked by 3PCD but is exempted for the request.
CookieExemptionReason = str  # Literal enum: "None", "UserSetting", "TPCDMetadata", "TPCDDeprecationTrial", "TopLevelTPCDDeprecationTrial", "TPCDHeuristics", "EnterprisePolicy", "StorageAccess", "TopLevelStorageAccess", "Scheme", "SameSiteNoneCookiesInSandbox"

# A cookie which was not stored from a response with the corresponding reason.
BlockedSetCookieWithReason = dict  # Object type

# A cookie should have been blocked by 3PCD but is exempted and stored from a response with the
# corresponding reason. A cookie could only have at most one exemption reason.
ExemptedSetCookieWithReason = dict  # Object type

# A cookie associated with the request which may or may not be sent with it.
# Includes the cookies itself and reasons for blocking or exemption.
AssociatedCookie = dict  # Object type

# Cookie parameter object
CookieParam = dict  # Object type

# Authorization challenge for HTTP status code 401 or 407.
AuthChallenge = dict  # Object type

# Response to an AuthChallenge.
AuthChallengeResponse = dict  # Object type

# Stages of the interception to begin intercepting. Request will intercept before the request is
# sent. Response will intercept after the response is received.
InterceptionStage = str  # Literal enum: "Request", "HeadersReceived"

# Request pattern for interception.
RequestPattern = dict  # Object type

# Information about a signed exchange signature.
# https://wicg.github.io/webpackage/draft-yasskin-httpbis-origin-signed-exchanges-impl.html#rfc.section.3.1
SignedExchangeSignature = dict  # Object type

# Information about a signed exchange header.
# https://wicg.github.io/webpackage/draft-yasskin-httpbis-origin-signed-exchanges-impl.html#cbor-representation
SignedExchangeHeader = dict  # Object type

# Field type for a signed exchange related error.
SignedExchangeErrorField = str  # Literal enum: "signatureSig", "signatureIntegrity", "signatureCertUrl", "signatureCertSha256", "signatureValidityUrl", "signatureTimestamps"

# Information about a signed exchange response.
SignedExchangeError = dict  # Object type

# Information about a signed exchange response.
SignedExchangeInfo = dict  # Object type

# List of content encodings supported by the backend.
ContentEncoding = str  # Literal enum: "deflate", "gzip", "br", "zstd"

NetworkConditions = dict  # Object type

BlockPattern = dict  # Object type

DirectSocketDnsQueryType = str  # Literal enum: "ipv4", "ipv6"

DirectTCPSocketOptions = dict  # Object type

DirectUDPSocketOptions = dict  # Object type

DirectUDPMessage = dict  # Object type

LocalNetworkAccessRequestPolicy = str  # Literal enum: "Allow", "BlockFromInsecureToMorePrivate", "WarnFromInsecureToMorePrivate", "PermissionBlock", "PermissionWarn"

IPAddressSpace = str  # Literal enum: "Loopback", "Local", "Public", "Unknown"

ConnectTiming = dict  # Object type

ClientSecurityState = dict  # Object type

CrossOriginOpenerPolicyValue = str  # Literal enum: "SameOrigin", "SameOriginAllowPopups", "RestrictProperties", "UnsafeNone", "SameOriginPlusCoep", "RestrictPropertiesPlusCoep", "NoopenerAllowPopups"

CrossOriginOpenerPolicyStatus = dict  # Object type

CrossOriginEmbedderPolicyValue = str  # Literal enum: "None", "Credentialless", "RequireCorp"

CrossOriginEmbedderPolicyStatus = dict  # Object type

ContentSecurityPolicySource = str  # Literal enum: "HTTP", "Meta"

ContentSecurityPolicyStatus = dict  # Object type

SecurityIsolationStatus = dict  # Object type

# The status of a Reporting API report.
ReportStatus = str  # Literal enum: "Queued", "Pending", "MarkedForRemoval", "Success"

ReportId = str

# An object representing a report generated by the Reporting API.
ReportingApiReport = dict  # Object type

ReportingApiEndpoint = dict  # Object type

# Unique identifier for a device bound session.
DeviceBoundSessionKey = dict  # Object type

# How a device bound session was used during a request.
DeviceBoundSessionWithUsage = dict  # Object type

# A device bound session's cookie craving.
DeviceBoundSessionCookieCraving = dict  # Object type

# A device bound session's inclusion URL rule.
DeviceBoundSessionUrlRule = dict  # Object type

# A device bound session's inclusion rules.
DeviceBoundSessionInclusionRules = dict  # Object type

# A device bound session.
DeviceBoundSession = dict  # Object type

DeviceBoundSessionEventId = str

# A fetch result for a device bound session creation or refresh.
DeviceBoundSessionFetchResult = str  # Literal enum: "Success", "KeyError", "SigningError", "ServerRequestedTermination", "InvalidSessionId", "InvalidChallenge", "TooManyChallenges", "InvalidFetcherUrl", "InvalidRefreshUrl", "TransientHttpError", "ScopeOriginSameSiteMismatch", "RefreshUrlSameSiteMismatch", "MismatchedSessionId", "MissingScope", "NoCredentials", "SubdomainRegistrationWellKnownUnavailable", "SubdomainRegistrationUnauthorized", "SubdomainRegistrationWellKnownMalformed", "SessionProviderWellKnownUnavailable", "RelyingPartyWellKnownUnavailable", "FederatedKeyThumbprintMismatch", "InvalidFederatedSessionUrl", "InvalidFederatedKey", "TooManyRelyingOriginLabels", "BoundCookieSetForbidden", "NetError", "ProxyError", "EmptySessionConfig", "InvalidCredentialsConfig", "InvalidCredentialsType", "InvalidCredentialsEmptyName", "InvalidCredentialsCookie", "PersistentHttpError", "RegistrationAttemptedChallenge", "InvalidScopeOrigin", "ScopeOriginContainsPath", "RefreshInitiatorNotString", "RefreshInitiatorInvalidHostPattern", "InvalidScopeSpecification", "MissingScopeSpecificationType", "EmptyScopeSpecificationDomain", "EmptyScopeSpecificationPath", "InvalidScopeSpecificationType", "InvalidScopeIncludeSite", "MissingScopeIncludeSite", "FederatedNotAuthorizedByProvider", "FederatedNotAuthorizedByRelyingParty", "SessionProviderWellKnownMalformed", "SessionProviderWellKnownHasProviderOrigin", "RelyingPartyWellKnownMalformed", "RelyingPartyWellKnownHasRelyingOrigins", "InvalidFederatedSessionProviderSessionMissing", "InvalidFederatedSessionWrongProviderOrigin", "InvalidCredentialsCookieCreationTime", "InvalidCredentialsCookieName", "InvalidCredentialsCookieParsing", "InvalidCredentialsCookieUnpermittedAttribute", "InvalidCredentialsCookieInvalidDomain", "InvalidCredentialsCookiePrefix", "InvalidScopeRulePath", "InvalidScopeRuleHostPattern", "ScopeRuleOriginScopedHostPatternMismatch", "ScopeRuleSiteScopedHostPatternMismatch", "SigningQuotaExceeded", "InvalidConfigJson", "InvalidFederatedSessionProviderFailedToRestoreKey", "FailedToUnwrapKey", "SessionDeletedDuringRefresh"

# Session event details specific to creation.
CreationEventDetails = dict  # Object type

# Session event details specific to refresh.
RefreshEventDetails = dict  # Object type

# Session event details specific to termination.
TerminationEventDetails = dict  # Object type

# Session event details specific to challenges.
ChallengeEventDetails = dict  # Object type

# An object providing the result of a network resource load.
LoadNetworkResourcePageResult = dict  # Object type

# An options object that may be extended later to better support CORS,
# CORB and streaming.
LoadNetworkResourceOptions = dict  # Object type

class Network:
    """Network domain allows tracking network activities of the page. It exposes information about http,
file, data and other requests and responses, their headers, bodies, timing, etc."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def set_accepted_encodings(self, encodings: list[ContentEncoding]) -> dict:
        """Sets a list of content encodings that will be accepted. Empty list means no encoding is accepted."""
        params: dict[str, Any] = {}
        params["encodings"] = encodings
        return await self._client.send(method="Network.setAcceptedEncodings", params=params)

    async def clear_accepted_encodings_override(self) -> dict:
        """Clears accepted encodings set by setAcceptedEncodings"""
        return await self._client.send(method="Network.clearAcceptedEncodingsOverride")

    async def can_clear_browser_cache(self) -> dict:
        """Tells whether clearing browser cache is supported."""
        return await self._client.send(method="Network.canClearBrowserCache")

    async def can_clear_browser_cookies(self) -> dict:
        """Tells whether clearing browser cookies is supported."""
        return await self._client.send(method="Network.canClearBrowserCookies")

    async def can_emulate_network_conditions(self) -> dict:
        """Tells whether emulation of network conditions is supported."""
        return await self._client.send(method="Network.canEmulateNetworkConditions")

    async def clear_browser_cache(self) -> dict:
        """Clears browser cache."""
        return await self._client.send(method="Network.clearBrowserCache")

    async def clear_browser_cookies(self) -> dict:
        """Clears browser cookies."""
        return await self._client.send(method="Network.clearBrowserCookies")

    async def continue_intercepted_request(
        self,
        interception_id: InterceptionId,
        error_reason: ErrorReason | None = None,
        raw_response: str | None = None,
        url: str | None = None,
        method: str | None = None,
        post_data: str | None = None,
        headers: Headers | None = None,
        auth_challenge_response: AuthChallengeResponse | None = None,
    ) -> dict:
        """Response to Network.requestIntercepted which either modifies the request to continue with any
modifications, or blocks it, or completes it with the provided response bytes. If a network
fetch occurs as a result which encounters a redirect an additional Network.requestIntercepted
event will be sent with the same InterceptionId.
Deprecated, use Fetch.continueRequest, Fetch.fulfillRequest and Fetch.failRequest instead.
        """
        params: dict[str, Any] = {}
        params["interceptionId"] = interception_id
        if error_reason is not None:
            params["errorReason"] = error_reason
        if raw_response is not None:
            params["rawResponse"] = raw_response
        if url is not None:
            params["url"] = url
        if method is not None:
            params["method"] = method
        if post_data is not None:
            params["postData"] = post_data
        if headers is not None:
            params["headers"] = headers
        if auth_challenge_response is not None:
            params["authChallengeResponse"] = auth_challenge_response
        return await self._client.send(method="Network.continueInterceptedRequest", params=params)

    async def delete_cookies(
        self,
        name: str,
        url: str | None = None,
        domain: str | None = None,
        path: str | None = None,
        partition_key: CookiePartitionKey | None = None,
    ) -> dict:
        """Deletes browser cookies with matching name and url or domain/path/partitionKey pair."""
        params: dict[str, Any] = {}
        params["name"] = name
        if url is not None:
            params["url"] = url
        if domain is not None:
            params["domain"] = domain
        if path is not None:
            params["path"] = path
        if partition_key is not None:
            params["partitionKey"] = partition_key
        return await self._client.send(method="Network.deleteCookies", params=params)

    async def disable(self) -> dict:
        """Disables network tracking, prevents network events from being sent to the client."""
        return await self._client.send(method="Network.disable")

    async def emulate_network_conditions(
        self,
        offline: bool,
        latency: float,
        download_throughput: float,
        upload_throughput: float,
        connection_type: ConnectionType | None = None,
        packet_loss: float | None = None,
        packet_queue_length: int | None = None,
        packet_reordering: bool | None = None,
    ) -> dict:
        """Activates emulation of network conditions. This command is deprecated in favor of the emulateNetworkConditionsByRule
and overrideNetworkState commands, which can be used together to the same effect.
        """
        params: dict[str, Any] = {}
        params["offline"] = offline
        params["latency"] = latency
        params["downloadThroughput"] = download_throughput
        params["uploadThroughput"] = upload_throughput
        if connection_type is not None:
            params["connectionType"] = connection_type
        if packet_loss is not None:
            params["packetLoss"] = packet_loss
        if packet_queue_length is not None:
            params["packetQueueLength"] = packet_queue_length
        if packet_reordering is not None:
            params["packetReordering"] = packet_reordering
        return await self._client.send(method="Network.emulateNetworkConditions", params=params)

    async def emulate_network_conditions_by_rule(self, offline: bool, matched_network_conditions: list[NetworkConditions]) -> dict:
        """Activates emulation of network conditions for individual requests using URL match patterns. Unlike the deprecated
Network.emulateNetworkConditions this method does not affect `navigator` state. Use Network.overrideNetworkState to
explicitly modify `navigator` behavior.
        """
        params: dict[str, Any] = {}
        params["offline"] = offline
        params["matchedNetworkConditions"] = matched_network_conditions
        return await self._client.send(method="Network.emulateNetworkConditionsByRule", params=params)

    async def override_network_state(
        self,
        offline: bool,
        latency: float,
        download_throughput: float,
        upload_throughput: float,
        connection_type: ConnectionType | None = None,
    ) -> dict:
        """Override the state of navigator.onLine and navigator.connection."""
        params: dict[str, Any] = {}
        params["offline"] = offline
        params["latency"] = latency
        params["downloadThroughput"] = download_throughput
        params["uploadThroughput"] = upload_throughput
        if connection_type is not None:
            params["connectionType"] = connection_type
        return await self._client.send(method="Network.overrideNetworkState", params=params)

    async def enable(
        self,
        max_total_buffer_size: int | None = None,
        max_resource_buffer_size: int | None = None,
        max_post_data_size: int | None = None,
        report_direct_socket_traffic: bool | None = None,
        enable_durable_messages: bool | None = None,
    ) -> dict:
        """Enables network tracking, network events will now be delivered to the client."""
        params: dict[str, Any] = {}
        if max_total_buffer_size is not None:
            params["maxTotalBufferSize"] = max_total_buffer_size
        if max_resource_buffer_size is not None:
            params["maxResourceBufferSize"] = max_resource_buffer_size
        if max_post_data_size is not None:
            params["maxPostDataSize"] = max_post_data_size
        if report_direct_socket_traffic is not None:
            params["reportDirectSocketTraffic"] = report_direct_socket_traffic
        if enable_durable_messages is not None:
            params["enableDurableMessages"] = enable_durable_messages
        return await self._client.send(method="Network.enable", params=params)

    async def configure_durable_messages(self, max_total_buffer_size: int | None = None, max_resource_buffer_size: int | None = None) -> dict:
        """Configures storing response bodies outside of renderer, so that these survive
a cross-process navigation.
If maxTotalBufferSize is not set, durable messages are disabled.
        """
        params: dict[str, Any] = {}
        if max_total_buffer_size is not None:
            params["maxTotalBufferSize"] = max_total_buffer_size
        if max_resource_buffer_size is not None:
            params["maxResourceBufferSize"] = max_resource_buffer_size
        return await self._client.send(method="Network.configureDurableMessages", params=params)

    async def get_all_cookies(self) -> dict:
        """Returns all browser cookies. Depending on the backend support, will return detailed cookie
information in the `cookies` field.
Deprecated. Use Storage.getCookies instead.
        """
        return await self._client.send(method="Network.getAllCookies")

    async def get_certificate(self, origin: str) -> dict:
        """Returns the DER-encoded certificate."""
        params: dict[str, Any] = {}
        params["origin"] = origin
        return await self._client.send(method="Network.getCertificate", params=params)

    async def get_cookies(self, urls: list[str] | None = None) -> dict:
        """Returns all browser cookies for the current URL. Depending on the backend support, will return
detailed cookie information in the `cookies` field.
        """
        params: dict[str, Any] = {}
        if urls is not None:
            params["urls"] = urls
        return await self._client.send(method="Network.getCookies", params=params)

    async def get_response_body(self, request_id: RequestId) -> dict:
        """Returns content served for the given request."""
        params: dict[str, Any] = {}
        params["requestId"] = request_id
        return await self._client.send(method="Network.getResponseBody", params=params)

    async def get_request_post_data(self, request_id: RequestId) -> dict:
        """Returns post data sent with the request. Returns an error when no data was sent with the request."""
        params: dict[str, Any] = {}
        params["requestId"] = request_id
        return await self._client.send(method="Network.getRequestPostData", params=params)

    async def get_response_body_for_interception(self, interception_id: InterceptionId) -> dict:
        """Returns content served for the given currently intercepted request."""
        params: dict[str, Any] = {}
        params["interceptionId"] = interception_id
        return await self._client.send(method="Network.getResponseBodyForInterception", params=params)

    async def take_response_body_for_interception_as_stream(self, interception_id: InterceptionId) -> dict:
        """Returns a handle to the stream representing the response body. Note that after this command,
the intercepted request can't be continued as is -- you either need to cancel it or to provide
the response body. The stream only supports sequential read, IO.read will fail if the position
is specified.
        """
        params: dict[str, Any] = {}
        params["interceptionId"] = interception_id
        return await self._client.send(method="Network.takeResponseBodyForInterceptionAsStream", params=params)

    async def replay_xhr(self, request_id: RequestId) -> dict:
        """This method sends a new XMLHttpRequest which is identical to the original one. The following
parameters should be identical: method, url, async, request body, extra headers, withCredentials
attribute, user, password.
        """
        params: dict[str, Any] = {}
        params["requestId"] = request_id
        return await self._client.send(method="Network.replayXHR", params=params)

    async def search_in_response_body(
        self,
        request_id: RequestId,
        query: str,
        case_sensitive: bool | None = None,
        is_regex: bool | None = None,
    ) -> dict:
        """Searches for given string in response content."""
        params: dict[str, Any] = {}
        params["requestId"] = request_id
        params["query"] = query
        if case_sensitive is not None:
            params["caseSensitive"] = case_sensitive
        if is_regex is not None:
            params["isRegex"] = is_regex
        return await self._client.send(method="Network.searchInResponseBody", params=params)

    async def set_blocked_ur_ls(self, url_patterns: list[BlockPattern] | None = None, urls: list[str] | None = None) -> dict:
        """Blocks URLs from loading."""
        params: dict[str, Any] = {}
        if url_patterns is not None:
            params["urlPatterns"] = url_patterns
        if urls is not None:
            params["urls"] = urls
        return await self._client.send(method="Network.setBlockedURLs", params=params)

    async def set_bypass_service_worker(self, bypass: bool) -> dict:
        """Toggles ignoring of service worker for each request."""
        params: dict[str, Any] = {}
        params["bypass"] = bypass
        return await self._client.send(method="Network.setBypassServiceWorker", params=params)

    async def set_cache_disabled(self, cache_disabled: bool) -> dict:
        """Toggles ignoring cache for each request. If `true`, cache will not be used."""
        params: dict[str, Any] = {}
        params["cacheDisabled"] = cache_disabled
        return await self._client.send(method="Network.setCacheDisabled", params=params)

    async def set_cookie(
        self,
        name: str,
        value: str,
        url: str | None = None,
        domain: str | None = None,
        path: str | None = None,
        secure: bool | None = None,
        http_only: bool | None = None,
        same_site: CookieSameSite | None = None,
        expires: TimeSinceEpoch | None = None,
        priority: CookiePriority | None = None,
        source_scheme: CookieSourceScheme | None = None,
        source_port: int | None = None,
        partition_key: CookiePartitionKey | None = None,
    ) -> dict:
        """Sets a cookie with the given cookie data; may overwrite equivalent cookies if they exist."""
        params: dict[str, Any] = {}
        params["name"] = name
        params["value"] = value
        if url is not None:
            params["url"] = url
        if domain is not None:
            params["domain"] = domain
        if path is not None:
            params["path"] = path
        if secure is not None:
            params["secure"] = secure
        if http_only is not None:
            params["httpOnly"] = http_only
        if same_site is not None:
            params["sameSite"] = same_site
        if expires is not None:
            params["expires"] = expires
        if priority is not None:
            params["priority"] = priority
        if source_scheme is not None:
            params["sourceScheme"] = source_scheme
        if source_port is not None:
            params["sourcePort"] = source_port
        if partition_key is not None:
            params["partitionKey"] = partition_key
        return await self._client.send(method="Network.setCookie", params=params)

    async def set_cookies(self, cookies: list[CookieParam]) -> dict:
        """Sets given cookies."""
        params: dict[str, Any] = {}
        params["cookies"] = cookies
        return await self._client.send(method="Network.setCookies", params=params)

    async def set_extra_http_headers(self, headers: Headers) -> dict:
        """Specifies whether to always send extra HTTP headers with the requests from this page."""
        params: dict[str, Any] = {}
        params["headers"] = headers
        return await self._client.send(method="Network.setExtraHTTPHeaders", params=params)

    async def set_attach_debug_stack(self, enabled: bool) -> dict:
        """Specifies whether to attach a page script stack id in requests"""
        params: dict[str, Any] = {}
        params["enabled"] = enabled
        return await self._client.send(method="Network.setAttachDebugStack", params=params)

    async def set_request_interception(self, patterns: list[RequestPattern]) -> dict:
        """Sets the requests to intercept that match the provided patterns and optionally resource types.
Deprecated, please use Fetch.enable instead.
        """
        params: dict[str, Any] = {}
        params["patterns"] = patterns
        return await self._client.send(method="Network.setRequestInterception", params=params)

    async def set_user_agent_override(
        self,
        user_agent: str,
        accept_language: str | None = None,
        platform: str | None = None,
        user_agent_metadata: str | None = None,
    ) -> dict:
        """Allows overriding user agent with the given string."""
        params: dict[str, Any] = {}
        params["userAgent"] = user_agent
        if accept_language is not None:
            params["acceptLanguage"] = accept_language
        if platform is not None:
            params["platform"] = platform
        if user_agent_metadata is not None:
            params["userAgentMetadata"] = user_agent_metadata
        return await self._client.send(method="Network.setUserAgentOverride", params=params)

    async def stream_resource_content(self, request_id: RequestId) -> dict:
        """Enables streaming of the response for the given requestId.
If enabled, the dataReceived event contains the data that was received during streaming.
        """
        params: dict[str, Any] = {}
        params["requestId"] = request_id
        return await self._client.send(method="Network.streamResourceContent", params=params)

    async def get_security_isolation_status(self, frame_id: str | None = None) -> dict:
        """Returns information about the COEP/COOP isolation status."""
        params: dict[str, Any] = {}
        if frame_id is not None:
            params["frameId"] = frame_id
        return await self._client.send(method="Network.getSecurityIsolationStatus", params=params)

    async def enable_reporting_api(self, enable: bool) -> dict:
        """Enables tracking for the Reporting API, events generated by the Reporting API will now be delivered to the client.
Enabling triggers 'reportingApiReportAdded' for all existing reports.
        """
        params: dict[str, Any] = {}
        params["enable"] = enable
        return await self._client.send(method="Network.enableReportingApi", params=params)

    async def enable_device_bound_sessions(self, enable: bool) -> dict:
        """Sets up tracking device bound sessions and fetching of initial set of sessions."""
        params: dict[str, Any] = {}
        params["enable"] = enable
        return await self._client.send(method="Network.enableDeviceBoundSessions", params=params)

    async def fetch_schemeful_site(self, origin: str) -> dict:
        """Fetches the schemeful site for a specific origin."""
        params: dict[str, Any] = {}
        params["origin"] = origin
        return await self._client.send(method="Network.fetchSchemefulSite", params=params)

    async def load_network_resource(
        self,
        url: str,
        options: LoadNetworkResourceOptions,
        frame_id: str | None = None,
    ) -> dict:
        """Fetches the resource and returns the content."""
        params: dict[str, Any] = {}
        params["url"] = url
        params["options"] = options
        if frame_id is not None:
            params["frameId"] = frame_id
        return await self._client.send(method="Network.loadNetworkResource", params=params)

    async def set_cookie_controls(
        self,
        enable_third_party_cookie_restriction: bool,
        disable_third_party_cookie_metadata: bool,
        disable_third_party_cookie_heuristics: bool,
    ) -> dict:
        """Sets Controls for third-party cookie access
Page reload is required before the new cookie behavior will be observed
        """
        params: dict[str, Any] = {}
        params["enableThirdPartyCookieRestriction"] = enable_third_party_cookie_restriction
        params["disableThirdPartyCookieMetadata"] = disable_third_party_cookie_metadata
        params["disableThirdPartyCookieHeuristics"] = disable_third_party_cookie_heuristics
        return await self._client.send(method="Network.setCookieControls", params=params)
