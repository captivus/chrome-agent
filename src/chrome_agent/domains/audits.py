"""CDP Audits domain.

Audits domain allows investigation of page violations and possible improvements.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


# Information about a cookie that is affected by an inspector issue.
AffectedCookie = dict  # Object type

# Information about a request that is affected by an inspector issue.
AffectedRequest = dict  # Object type

# Information about the frame affected by an inspector issue.
AffectedFrame = dict  # Object type

CookieExclusionReason = str  # Literal enum: "ExcludeSameSiteUnspecifiedTreatedAsLax", "ExcludeSameSiteNoneInsecure", "ExcludeSameSiteLax", "ExcludeSameSiteStrict", "ExcludeDomainNonASCII", "ExcludeThirdPartyCookieBlockedInFirstPartySet", "ExcludeThirdPartyPhaseout", "ExcludePortMismatch", "ExcludeSchemeMismatch"

CookieWarningReason = str  # Literal enum: "WarnSameSiteUnspecifiedCrossSiteContext", "WarnSameSiteNoneInsecure", "WarnSameSiteUnspecifiedLaxAllowUnsafe", "WarnSameSiteStrictLaxDowngradeStrict", "WarnSameSiteStrictCrossDowngradeStrict", "WarnSameSiteStrictCrossDowngradeLax", "WarnSameSiteLaxCrossDowngradeStrict", "WarnSameSiteLaxCrossDowngradeLax", "WarnAttributeValueExceedsMaxSize", "WarnDomainNonASCII", "WarnThirdPartyPhaseout", "WarnCrossSiteRedirectDowngradeChangesInclusion", "WarnDeprecationTrialMetadata", "WarnThirdPartyCookieHeuristic"

CookieOperation = str  # Literal enum: "SetCookie", "ReadCookie"

# Represents the category of insight that a cookie issue falls under.
InsightType = str  # Literal enum: "GitHubResource", "GracePeriod", "Heuristics"

# Information about the suggested solution to a cookie issue.
CookieIssueInsight = dict  # Object type

# This information is currently necessary, as the front-end has a difficult
# time finding a specific cookie. With this, we can convey specific error
# information without the cookie.
CookieIssueDetails = dict  # Object type

MixedContentResolutionStatus = str  # Literal enum: "MixedContentBlocked", "MixedContentAutomaticallyUpgraded", "MixedContentWarning"

MixedContentResourceType = str  # Literal enum: "AttributionSrc", "Audio", "Beacon", "CSPReport", "Download", "EventSource", "Favicon", "Font", "Form", "Frame", "Image", "Import", "JSON", "Manifest", "Ping", "PluginData", "PluginResource", "Prefetch", "Resource", "Script", "ServiceWorker", "SharedWorker", "SpeculationRules", "Stylesheet", "Track", "Video", "Worker", "XMLHttpRequest", "XSLT"

MixedContentIssueDetails = dict  # Object type

# Enum indicating the reason a response has been blocked. These reasons are
# refinements of the net error BLOCKED_BY_RESPONSE.
BlockedByResponseReason = str  # Literal enum: "CoepFrameResourceNeedsCoepHeader", "CoopSandboxedIFrameCannotNavigateToCoopPage", "CorpNotSameOrigin", "CorpNotSameOriginAfterDefaultedToSameOriginByCoep", "CorpNotSameOriginAfterDefaultedToSameOriginByDip", "CorpNotSameOriginAfterDefaultedToSameOriginByCoepAndDip", "CorpNotSameSite", "SRIMessageSignatureMismatch"

# Details for a request that has been blocked with the BLOCKED_BY_RESPONSE
# code. Currently only used for COEP/COOP, but may be extended to include
# some CSP errors in the future.
BlockedByResponseIssueDetails = dict  # Object type

HeavyAdResolutionStatus = str  # Literal enum: "HeavyAdBlocked", "HeavyAdWarning"

HeavyAdReason = str  # Literal enum: "NetworkTotalLimit", "CpuTotalLimit", "CpuPeakLimit"

HeavyAdIssueDetails = dict  # Object type

ContentSecurityPolicyViolationType = str  # Literal enum: "kInlineViolation", "kEvalViolation", "kURLViolation", "kSRIViolation", "kTrustedTypesSinkViolation", "kTrustedTypesPolicyViolation", "kWasmEvalViolation"

SourceCodeLocation = dict  # Object type

ContentSecurityPolicyIssueDetails = dict  # Object type

SharedArrayBufferIssueType = str  # Literal enum: "TransferIssue", "CreationIssue"

# Details for a issue arising from an SAB being instantiated in, or
# transferred to a context that is not cross-origin isolated.
SharedArrayBufferIssueDetails = dict  # Object type

LowTextContrastIssueDetails = dict  # Object type

# Details for a CORS related issue, e.g. a warning or error related to
# CORS RFC1918 enforcement.
CorsIssueDetails = dict  # Object type

AttributionReportingIssueType = str  # Literal enum: "PermissionPolicyDisabled", "UntrustworthyReportingOrigin", "InsecureContext", "InvalidHeader", "InvalidRegisterTriggerHeader", "SourceAndTriggerHeaders", "SourceIgnored", "TriggerIgnored", "OsSourceIgnored", "OsTriggerIgnored", "InvalidRegisterOsSourceHeader", "InvalidRegisterOsTriggerHeader", "WebAndOsHeaders", "NoWebOrOsSupport", "NavigationRegistrationWithoutTransientUserActivation", "InvalidInfoHeader", "NoRegisterSourceHeader", "NoRegisterTriggerHeader", "NoRegisterOsSourceHeader", "NoRegisterOsTriggerHeader", "NavigationRegistrationUniqueScopeAlreadySet"

SharedDictionaryError = str  # Literal enum: "UseErrorCrossOriginNoCorsRequest", "UseErrorDictionaryLoadFailure", "UseErrorMatchingDictionaryNotUsed", "UseErrorUnexpectedContentDictionaryHeader", "WriteErrorCossOriginNoCorsRequest", "WriteErrorDisallowedBySettings", "WriteErrorExpiredResponse", "WriteErrorFeatureDisabled", "WriteErrorInsufficientResources", "WriteErrorInvalidMatchField", "WriteErrorInvalidStructuredHeader", "WriteErrorInvalidTTLField", "WriteErrorNavigationRequest", "WriteErrorNoMatchField", "WriteErrorNonIntegerTTLField", "WriteErrorNonListMatchDestField", "WriteErrorNonSecureContext", "WriteErrorNonStringIdField", "WriteErrorNonStringInMatchDestList", "WriteErrorNonStringMatchField", "WriteErrorNonTokenTypeField", "WriteErrorRequestAborted", "WriteErrorShuttingDown", "WriteErrorTooLongIdField", "WriteErrorUnsupportedType"

SRIMessageSignatureError = str  # Literal enum: "MissingSignatureHeader", "MissingSignatureInputHeader", "InvalidSignatureHeader", "InvalidSignatureInputHeader", "SignatureHeaderValueIsNotByteSequence", "SignatureHeaderValueIsParameterized", "SignatureHeaderValueIsIncorrectLength", "SignatureInputHeaderMissingLabel", "SignatureInputHeaderValueNotInnerList", "SignatureInputHeaderValueMissingComponents", "SignatureInputHeaderInvalidComponentType", "SignatureInputHeaderInvalidComponentName", "SignatureInputHeaderInvalidHeaderComponentParameter", "SignatureInputHeaderInvalidDerivedComponentParameter", "SignatureInputHeaderKeyIdLength", "SignatureInputHeaderInvalidParameter", "SignatureInputHeaderMissingRequiredParameters", "ValidationFailedSignatureExpired", "ValidationFailedInvalidLength", "ValidationFailedSignatureMismatch", "ValidationFailedIntegrityMismatch"

UnencodedDigestError = str  # Literal enum: "MalformedDictionary", "UnknownAlgorithm", "IncorrectDigestType", "IncorrectDigestLength"

ConnectionAllowlistError = str  # Literal enum: "InvalidHeader", "MoreThanOneList", "ItemNotInnerList", "InvalidAllowlistItemType", "ReportingEndpointNotToken", "InvalidUrlPattern"

# Details for issues around "Attribution Reporting API" usage.
# Explainer: https://github.com/WICG/attribution-reporting-api
AttributionReportingIssueDetails = dict  # Object type

# Details for issues about documents in Quirks Mode
# or Limited Quirks Mode that affects page layouting.
QuirksModeIssueDetails = dict  # Object type

NavigatorUserAgentIssueDetails = dict  # Object type

SharedDictionaryIssueDetails = dict  # Object type

SRIMessageSignatureIssueDetails = dict  # Object type

UnencodedDigestIssueDetails = dict  # Object type

ConnectionAllowlistIssueDetails = dict  # Object type

GenericIssueErrorType = str  # Literal enum: "FormLabelForNameError", "FormDuplicateIdForInputError", "FormInputWithNoLabelError", "FormAutocompleteAttributeEmptyError", "FormEmptyIdAndNameAttributesForInputError", "FormAriaLabelledByToNonExistingIdError", "FormInputAssignedAutocompleteValueToIdOrNameAttributeError", "FormLabelHasNeitherForNorNestedInputError", "FormLabelForMatchesNonExistingIdError", "FormInputHasWrongButWellIntendedAutocompleteValueError", "ResponseWasBlockedByORB", "NavigationEntryMarkedSkippable", "AutofillAndManualTextPolicyControlledFeaturesInfo", "AutofillPolicyControlledFeatureInfo", "ManualTextPolicyControlledFeatureInfo"

# Depending on the concrete errorType, different properties are set.
GenericIssueDetails = dict  # Object type

# This issue tracks information needed to print a deprecation message.
# https://source.chromium.org/chromium/chromium/src/+/main:third_party/blink/renderer/core/frame/third_party/blink/renderer/core/frame/deprecation/README.md
DeprecationIssueDetails = dict  # Object type

# This issue warns about sites in the redirect chain of a finished navigation
# that may be flagged as trackers and have their state cleared if they don't
# receive a user interaction. Note that in this context 'site' means eTLD+1.
# For example, if the URL `https://example.test:80/bounce` was in the
# redirect chain, the site reported would be `example.test`.
BounceTrackingIssueDetails = dict  # Object type

# This issue warns about third-party sites that are accessing cookies on the
# current page, and have been permitted due to having a global metadata grant.
# Note that in this context 'site' means eTLD+1. For example, if the URL
# `https://example.test:80/web_page` was accessing cookies, the site reported
# would be `example.test`.
CookieDeprecationMetadataIssueDetails = dict  # Object type

ClientHintIssueReason = str  # Literal enum: "MetaTagAllowListInvalidOrigin", "MetaTagModifiedHTML"

FederatedAuthRequestIssueDetails = dict  # Object type

# Represents the failure reason when a federated authentication reason fails.
# Should be updated alongside RequestIdTokenStatus in
# third_party/blink/public/mojom/devtools/inspector_issue.mojom to include
# all cases except for success.
FederatedAuthRequestIssueReason = str  # Literal enum: "ShouldEmbargo", "TooManyRequests", "WellKnownHttpNotFound", "WellKnownNoResponse", "WellKnownInvalidResponse", "WellKnownListEmpty", "WellKnownInvalidContentType", "ConfigNotInWellKnown", "WellKnownTooBig", "ConfigHttpNotFound", "ConfigNoResponse", "ConfigInvalidResponse", "ConfigInvalidContentType", "ClientMetadataHttpNotFound", "ClientMetadataNoResponse", "ClientMetadataInvalidResponse", "ClientMetadataInvalidContentType", "IdpNotPotentiallyTrustworthy", "DisabledInSettings", "DisabledInFlags", "ErrorFetchingSignin", "InvalidSigninResponse", "AccountsHttpNotFound", "AccountsNoResponse", "AccountsInvalidResponse", "AccountsListEmpty", "AccountsInvalidContentType", "IdTokenHttpNotFound", "IdTokenNoResponse", "IdTokenInvalidResponse", "IdTokenIdpErrorResponse", "IdTokenCrossSiteIdpErrorResponse", "IdTokenInvalidRequest", "IdTokenInvalidContentType", "ErrorIdToken", "Canceled", "RpPageNotVisible", "SilentMediationFailure", "ThirdPartyCookiesBlocked", "NotSignedInWithIdp", "MissingTransientUserActivation", "ReplacedByActiveMode", "InvalidFieldsSpecified", "RelyingPartyOriginIsOpaque", "TypeNotMatching", "UiDismissedNoEmbargo", "CorsError", "SuppressedBySegmentationPlatform"

FederatedAuthUserInfoRequestIssueDetails = dict  # Object type

# Represents the failure reason when a getUserInfo() call fails.
# Should be updated alongside FederatedAuthUserInfoRequestResult in
# third_party/blink/public/mojom/devtools/inspector_issue.mojom.
FederatedAuthUserInfoRequestIssueReason = str  # Literal enum: "NotSameOrigin", "NotIframe", "NotPotentiallyTrustworthy", "NoApiPermission", "NotSignedInWithIdp", "NoAccountSharingPermission", "InvalidConfigOrWellKnown", "InvalidAccountsResponse", "NoReturningUserFromFetchedAccounts"

# This issue tracks client hints related issues. It's used to deprecate old
# features, encourage the use of new ones, and provide general guidance.
ClientHintIssueDetails = dict  # Object type

FailedRequestInfo = dict  # Object type

PartitioningBlobURLInfo = str  # Literal enum: "BlockedCrossPartitionFetching", "EnforceNoopenerForNavigation"

PartitioningBlobURLIssueDetails = dict  # Object type

ElementAccessibilityIssueReason = str  # Literal enum: "DisallowedSelectChild", "DisallowedOptGroupChild", "NonPhrasingContentOptionChild", "InteractiveContentOptionChild", "InteractiveContentLegendChild", "InteractiveContentSummaryDescendant"

# This issue warns about errors in the select or summary element content model.
ElementAccessibilityIssueDetails = dict  # Object type

StyleSheetLoadingIssueReason = str  # Literal enum: "LateImportRule", "RequestFailed"

# This issue warns when a referenced stylesheet couldn't be loaded.
StylesheetLoadingIssueDetails = dict  # Object type

PropertyRuleIssueReason = str  # Literal enum: "InvalidSyntax", "InvalidInitialValue", "InvalidInherits", "InvalidName"

# This issue warns about errors in property rules that lead to property
# registrations being ignored.
PropertyRuleIssueDetails = dict  # Object type

UserReidentificationIssueType = str  # Literal enum: "BlockedFrameNavigation", "BlockedSubresource", "NoisedCanvasReadback"

# This issue warns about uses of APIs that may be considered misuse to
# re-identify users.
UserReidentificationIssueDetails = dict  # Object type

PermissionElementIssueType = str  # Literal enum: "InvalidType", "FencedFrameDisallowed", "CspFrameAncestorsMissing", "PermissionsPolicyBlocked", "PaddingRightUnsupported", "PaddingBottomUnsupported", "InsetBoxShadowUnsupported", "RequestInProgress", "UntrustedEvent", "RegistrationFailed", "TypeNotSupported", "InvalidTypeActivation", "SecurityChecksFailed", "ActivationDisabled", "GeolocationDeprecated", "InvalidDisplayStyle", "NonOpaqueColor", "LowContrast", "FontSizeTooSmall", "FontSizeTooLarge", "InvalidSizeValue"

# This issue warns about improper usage of the <permission> element.
PermissionElementIssueDetails = dict  # Object type

# A unique identifier for the type of issue. Each type may use one of the
# optional fields in InspectorIssueDetails to convey more specific
# information about the kind of issue.
InspectorIssueCode = str  # Literal enum: "CookieIssue", "MixedContentIssue", "BlockedByResponseIssue", "HeavyAdIssue", "ContentSecurityPolicyIssue", "SharedArrayBufferIssue", "LowTextContrastIssue", "CorsIssue", "AttributionReportingIssue", "QuirksModeIssue", "PartitioningBlobURLIssue", "NavigatorUserAgentIssue", "GenericIssue", "DeprecationIssue", "ClientHintIssue", "FederatedAuthRequestIssue", "BounceTrackingIssue", "CookieDeprecationMetadataIssue", "StylesheetLoadingIssue", "FederatedAuthUserInfoRequestIssue", "PropertyRuleIssue", "SharedDictionaryIssue", "ElementAccessibilityIssue", "SRIMessageSignatureIssue", "UnencodedDigestIssue", "ConnectionAllowlistIssue", "UserReidentificationIssue", "PermissionElementIssue"

# This struct holds a list of optional fields with additional information
# specific to the kind of issue. When adding a new issue code, please also
# add a new optional field to this type.
InspectorIssueDetails = dict  # Object type

IssueId = str

# An inspector issue reported from the back-end.
InspectorIssue = dict  # Object type

class Audits:
    """Audits domain allows investigation of page violations and possible improvements."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def get_encoded_response(
        self,
        request_id: str,
        encoding: str,
        quality: float | None = None,
        size_only: bool | None = None,
    ) -> dict:
        """Returns the response body and size if it were re-encoded with the specified settings. Only
applies to images.
        """
        params: dict[str, Any] = {}
        params["requestId"] = request_id
        params["encoding"] = encoding
        if quality is not None:
            params["quality"] = quality
        if size_only is not None:
            params["sizeOnly"] = size_only
        return await self._client.send(method="Audits.getEncodedResponse", params=params)

    async def disable(self) -> dict:
        """Disables issues domain, prevents further issues from being reported to the client."""
        return await self._client.send(method="Audits.disable")

    async def enable(self) -> dict:
        """Enables issues domain, sends the issues collected so far to the client by means of the
`issueAdded` event.
        """
        return await self._client.send(method="Audits.enable")

    async def check_contrast(self, report_aaa: bool | None = None) -> dict:
        """Runs the contrast check for the target page. Found issues are reported
using Audits.issueAdded event.
        """
        params: dict[str, Any] = {}
        if report_aaa is not None:
            params["reportAAA"] = report_aaa
        return await self._client.send(method="Audits.checkContrast", params=params)

    async def check_forms_issues(self) -> dict:
        """Runs the form issues check for the target page. Found issues are reported
using Audits.issueAdded event.
        """
        return await self._client.send(method="Audits.checkFormsIssues")
