"""CDP Preload domain.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


RuleSetId = str

# Corresponds to SpeculationRuleSet
RuleSet = dict  # Object type

RuleSetErrorType = str  # Literal enum: "SourceIsNotJsonObject", "InvalidRulesSkipped", "InvalidRulesetLevelTag"

# The type of preloading attempted. It corresponds to
# mojom::SpeculationAction (although PrefetchWithSubresources is omitted as it
# isn't being used by clients).
SpeculationAction = str  # Literal enum: "Prefetch", "Prerender", "PrerenderUntilScript"

# Corresponds to mojom::SpeculationTargetHint.
# See https://github.com/WICG/nav-speculation/blob/main/triggers.md#window-name-targeting-hints
SpeculationTargetHint = str  # Literal enum: "Blank", "Self"

# A key that identifies a preloading attempt.
# 
# The url used is the url specified by the trigger (i.e. the initial URL), and
# not the final url that is navigated to. For example, prerendering allows
# same-origin main frame navigations during the attempt, but the attempt is
# still keyed with the initial URL.
PreloadingAttemptKey = dict  # Object type

# Lists sources for a preloading attempt, specifically the ids of rule sets
# that had a speculation rule that triggered the attempt, and the
# BackendNodeIds of <a href> or <area href> elements that triggered the
# attempt (in the case of attempts triggered by a document rule). It is
# possible for multiple rule sets and links to trigger a single attempt.
PreloadingAttemptSource = dict  # Object type

PreloadPipelineId = str

# List of FinalStatus reasons for Prerender2.
PrerenderFinalStatus = str  # Literal enum: "Activated", "Destroyed", "LowEndDevice", "InvalidSchemeRedirect", "InvalidSchemeNavigation", "NavigationRequestBlockedByCsp", "MojoBinderPolicy", "RendererProcessCrashed", "RendererProcessKilled", "Download", "TriggerDestroyed", "NavigationNotCommitted", "NavigationBadHttpStatus", "ClientCertRequested", "NavigationRequestNetworkError", "CancelAllHostsForTesting", "DidFailLoad", "Stop", "SslCertificateError", "LoginAuthRequested", "UaChangeRequiresReload", "BlockedByClient", "AudioOutputDeviceRequested", "MixedContent", "TriggerBackgrounded", "MemoryLimitExceeded", "DataSaverEnabled", "TriggerUrlHasEffectiveUrl", "ActivatedBeforeStarted", "InactivePageRestriction", "StartFailed", "TimeoutBackgrounded", "CrossSiteRedirectInInitialNavigation", "CrossSiteNavigationInInitialNavigation", "SameSiteCrossOriginRedirectNotOptInInInitialNavigation", "SameSiteCrossOriginNavigationNotOptInInInitialNavigation", "ActivationNavigationParameterMismatch", "ActivatedInBackground", "EmbedderHostDisallowed", "ActivationNavigationDestroyedBeforeSuccess", "TabClosedByUserGesture", "TabClosedWithoutUserGesture", "PrimaryMainFrameRendererProcessCrashed", "PrimaryMainFrameRendererProcessKilled", "ActivationFramePolicyNotCompatible", "PreloadingDisabled", "BatterySaverEnabled", "ActivatedDuringMainFrameNavigation", "PreloadingUnsupportedByWebContents", "CrossSiteRedirectInMainFrameNavigation", "CrossSiteNavigationInMainFrameNavigation", "SameSiteCrossOriginRedirectNotOptInInMainFrameNavigation", "SameSiteCrossOriginNavigationNotOptInInMainFrameNavigation", "MemoryPressureOnTrigger", "MemoryPressureAfterTriggered", "PrerenderingDisabledByDevTools", "SpeculationRuleRemoved", "ActivatedWithAuxiliaryBrowsingContexts", "MaxNumOfRunningEagerPrerendersExceeded", "MaxNumOfRunningNonEagerPrerendersExceeded", "MaxNumOfRunningEmbedderPrerendersExceeded", "PrerenderingUrlHasEffectiveUrl", "RedirectedPrerenderingUrlHasEffectiveUrl", "ActivationUrlHasEffectiveUrl", "JavaScriptInterfaceAdded", "JavaScriptInterfaceRemoved", "AllPrerenderingCanceled", "WindowClosed", "SlowNetwork", "OtherPrerenderedPageActivated", "V8OptimizerDisabled", "PrerenderFailedDuringPrefetch", "BrowsingDataRemoved", "PrerenderHostReused"

# Preloading status values, see also PreloadingTriggeringOutcome. This
# status is shared by prefetchStatusUpdated and prerenderStatusUpdated.
PreloadingStatus = str  # Literal enum: "Pending", "Running", "Ready", "Success", "Failure", "NotSupported"

# TODO(https://crbug.com/1384419): revisit the list of PrefetchStatus and
# filter out the ones that aren't necessary to the developers.
PrefetchStatus = str  # Literal enum: "PrefetchAllowed", "PrefetchFailedIneligibleRedirect", "PrefetchFailedInvalidRedirect", "PrefetchFailedMIMENotSupported", "PrefetchFailedNetError", "PrefetchFailedNon2XX", "PrefetchEvictedAfterBrowsingDataRemoved", "PrefetchEvictedAfterCandidateRemoved", "PrefetchEvictedForNewerPrefetch", "PrefetchHeldback", "PrefetchIneligibleRetryAfter", "PrefetchIsPrivacyDecoy", "PrefetchIsStale", "PrefetchNotEligibleBrowserContextOffTheRecord", "PrefetchNotEligibleDataSaverEnabled", "PrefetchNotEligibleExistingProxy", "PrefetchNotEligibleHostIsNonUnique", "PrefetchNotEligibleNonDefaultStoragePartition", "PrefetchNotEligibleSameSiteCrossOriginPrefetchRequiredProxy", "PrefetchNotEligibleSchemeIsNotHttps", "PrefetchNotEligibleUserHasCookies", "PrefetchNotEligibleUserHasServiceWorker", "PrefetchNotEligibleUserHasServiceWorkerNoFetchHandler", "PrefetchNotEligibleRedirectFromServiceWorker", "PrefetchNotEligibleRedirectToServiceWorker", "PrefetchNotEligibleBatterySaverEnabled", "PrefetchNotEligiblePreloadingDisabled", "PrefetchNotFinishedInTime", "PrefetchNotStarted", "PrefetchNotUsedCookiesChanged", "PrefetchProxyNotAvailable", "PrefetchResponseUsed", "PrefetchSuccessfulButNotUsed", "PrefetchNotUsedProbeFailed"

# Information of headers to be displayed when the header mismatch occurred.
PrerenderMismatchedHeaders = dict  # Object type

class Preload:
    """CDP Preload domain."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def enable(self) -> dict:
        return await self._client.send(method="Preload.enable")

    async def disable(self) -> dict:
        return await self._client.send(method="Preload.disable")
