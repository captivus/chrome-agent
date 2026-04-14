"""CDP Storage domain.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


SerializedStorageKey = str

# Enum of possible storage types.
StorageType = str  # Literal enum: "cookies", "file_systems", "indexeddb", "local_storage", "shader_cache", "websql", "service_workers", "cache_storage", "interest_groups", "shared_storage", "storage_buckets", "all", "other"

# Usage for a storage type.
UsageForType = dict  # Object type

# Pair of issuer origin and number of available (signed, but not used) Trust
# Tokens from that issuer.
TrustTokens = dict  # Object type

InterestGroupAuctionId = str

# Enum of interest group access types.
InterestGroupAccessType = str  # Literal enum: "join", "leave", "update", "loaded", "bid", "win", "additionalBid", "additionalBidWin", "topLevelBid", "topLevelAdditionalBid", "clear"

# Enum of auction events.
InterestGroupAuctionEventType = str  # Literal enum: "started", "configResolved"

# Enum of network fetches auctions can do.
InterestGroupAuctionFetchType = str  # Literal enum: "bidderJs", "bidderWasm", "sellerJs", "bidderTrustedSignals", "sellerTrustedSignals"

# Enum of shared storage access scopes.
SharedStorageAccessScope = str  # Literal enum: "window", "sharedStorageWorklet", "protectedAudienceWorklet", "header"

# Enum of shared storage access methods.
SharedStorageAccessMethod = str  # Literal enum: "addModule", "createWorklet", "selectURL", "run", "batchUpdate", "set", "append", "delete", "clear", "get", "keys", "values", "entries", "length", "remainingBudget"

# Struct for a single key-value pair in an origin's shared storage.
SharedStorageEntry = dict  # Object type

# Details for an origin's shared storage.
SharedStorageMetadata = dict  # Object type

# Represents a dictionary object passed in as privateAggregationConfig to
# run or selectURL.
SharedStoragePrivateAggregationConfig = dict  # Object type

# Pair of reporting metadata details for a candidate URL for `selectURL()`.
SharedStorageReportingMetadata = dict  # Object type

# Bundles a candidate URL with its reporting metadata.
SharedStorageUrlWithMetadata = dict  # Object type

# Bundles the parameters for shared storage access events whose
# presence/absence can vary according to SharedStorageAccessType.
SharedStorageAccessParams = dict  # Object type

StorageBucketsDurability = str  # Literal enum: "relaxed", "strict"

StorageBucket = dict  # Object type

StorageBucketInfo = dict  # Object type

AttributionReportingSourceType = str  # Literal enum: "navigation", "event"

UnsignedInt64AsBase10 = str

UnsignedInt128AsBase16 = str

SignedInt64AsBase10 = str

AttributionReportingFilterDataEntry = dict  # Object type

AttributionReportingFilterConfig = dict  # Object type

AttributionReportingFilterPair = dict  # Object type

AttributionReportingAggregationKeysEntry = dict  # Object type

AttributionReportingEventReportWindows = dict  # Object type

AttributionReportingTriggerDataMatching = str  # Literal enum: "exact", "modulus"

AttributionReportingAggregatableDebugReportingData = dict  # Object type

AttributionReportingAggregatableDebugReportingConfig = dict  # Object type

AttributionScopesData = dict  # Object type

AttributionReportingNamedBudgetDef = dict  # Object type

AttributionReportingSourceRegistration = dict  # Object type

AttributionReportingSourceRegistrationResult = str  # Literal enum: "success", "internalError", "insufficientSourceCapacity", "insufficientUniqueDestinationCapacity", "excessiveReportingOrigins", "prohibitedByBrowserPolicy", "successNoised", "destinationReportingLimitReached", "destinationGlobalLimitReached", "destinationBothLimitsReached", "reportingOriginsPerSiteLimitReached", "exceedsMaxChannelCapacity", "exceedsMaxScopesChannelCapacity", "exceedsMaxTriggerStateCardinality", "exceedsMaxEventStatesLimit", "destinationPerDayReportingLimitReached"

AttributionReportingSourceRegistrationTimeConfig = str  # Literal enum: "include", "exclude"

AttributionReportingAggregatableValueDictEntry = dict  # Object type

AttributionReportingAggregatableValueEntry = dict  # Object type

AttributionReportingEventTriggerData = dict  # Object type

AttributionReportingAggregatableTriggerData = dict  # Object type

AttributionReportingAggregatableDedupKey = dict  # Object type

AttributionReportingNamedBudgetCandidate = dict  # Object type

AttributionReportingTriggerRegistration = dict  # Object type

AttributionReportingEventLevelResult = str  # Literal enum: "success", "successDroppedLowerPriority", "internalError", "noCapacityForAttributionDestination", "noMatchingSources", "deduplicated", "excessiveAttributions", "priorityTooLow", "neverAttributedSource", "excessiveReportingOrigins", "noMatchingSourceFilterData", "prohibitedByBrowserPolicy", "noMatchingConfigurations", "excessiveReports", "falselyAttributedSource", "reportWindowPassed", "notRegistered", "reportWindowNotStarted", "noMatchingTriggerData"

AttributionReportingAggregatableResult = str  # Literal enum: "success", "internalError", "noCapacityForAttributionDestination", "noMatchingSources", "excessiveAttributions", "excessiveReportingOrigins", "noHistograms", "insufficientBudget", "insufficientNamedBudget", "noMatchingSourceFilterData", "notRegistered", "prohibitedByBrowserPolicy", "deduplicated", "reportWindowPassed", "excessiveReports"

AttributionReportingReportResult = str  # Literal enum: "sent", "prohibited", "failedToAssemble", "expired"

# A single Related Website Set object.
RelatedWebsiteSet = dict  # Object type

class Storage:
    """CDP Storage domain."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def get_storage_key_for_frame(self, frame_id: str) -> dict:
        """Returns a storage key given a frame id.
Deprecated. Please use Storage.getStorageKey instead.
        """
        params: dict[str, Any] = {}
        params["frameId"] = frame_id
        return await self._client.send(method="Storage.getStorageKeyForFrame", params=params)

    async def get_storage_key(self, frame_id: str | None = None) -> dict:
        """Returns storage key for the given frame. If no frame ID is provided,
the storage key of the target executing this command is returned.
        """
        params: dict[str, Any] = {}
        if frame_id is not None:
            params["frameId"] = frame_id
        return await self._client.send(method="Storage.getStorageKey", params=params)

    async def clear_data_for_origin(self, origin: str, storage_types: str) -> dict:
        """Clears storage for origin."""
        params: dict[str, Any] = {}
        params["origin"] = origin
        params["storageTypes"] = storage_types
        return await self._client.send(method="Storage.clearDataForOrigin", params=params)

    async def clear_data_for_storage_key(self, storage_key: str, storage_types: str) -> dict:
        """Clears storage for storage key."""
        params: dict[str, Any] = {}
        params["storageKey"] = storage_key
        params["storageTypes"] = storage_types
        return await self._client.send(method="Storage.clearDataForStorageKey", params=params)

    async def get_cookies(self, browser_context_id: str | None = None) -> dict:
        """Returns all browser cookies."""
        params: dict[str, Any] = {}
        if browser_context_id is not None:
            params["browserContextId"] = browser_context_id
        return await self._client.send(method="Storage.getCookies", params=params)

    async def set_cookies(self, cookies: list[str], browser_context_id: str | None = None) -> dict:
        """Sets given cookies."""
        params: dict[str, Any] = {}
        params["cookies"] = cookies
        if browser_context_id is not None:
            params["browserContextId"] = browser_context_id
        return await self._client.send(method="Storage.setCookies", params=params)

    async def clear_cookies(self, browser_context_id: str | None = None) -> dict:
        """Clears cookies."""
        params: dict[str, Any] = {}
        if browser_context_id is not None:
            params["browserContextId"] = browser_context_id
        return await self._client.send(method="Storage.clearCookies", params=params)

    async def get_usage_and_quota(self, origin: str) -> dict:
        """Returns usage and quota in bytes."""
        params: dict[str, Any] = {}
        params["origin"] = origin
        return await self._client.send(method="Storage.getUsageAndQuota", params=params)

    async def override_quota_for_origin(self, origin: str, quota_size: float | None = None) -> dict:
        """Override quota for the specified origin"""
        params: dict[str, Any] = {}
        params["origin"] = origin
        if quota_size is not None:
            params["quotaSize"] = quota_size
        return await self._client.send(method="Storage.overrideQuotaForOrigin", params=params)

    async def track_cache_storage_for_origin(self, origin: str) -> dict:
        """Registers origin to be notified when an update occurs to its cache storage list."""
        params: dict[str, Any] = {}
        params["origin"] = origin
        return await self._client.send(method="Storage.trackCacheStorageForOrigin", params=params)

    async def track_cache_storage_for_storage_key(self, storage_key: str) -> dict:
        """Registers storage key to be notified when an update occurs to its cache storage list."""
        params: dict[str, Any] = {}
        params["storageKey"] = storage_key
        return await self._client.send(method="Storage.trackCacheStorageForStorageKey", params=params)

    async def track_indexed_db_for_origin(self, origin: str) -> dict:
        """Registers origin to be notified when an update occurs to its IndexedDB."""
        params: dict[str, Any] = {}
        params["origin"] = origin
        return await self._client.send(method="Storage.trackIndexedDBForOrigin", params=params)

    async def track_indexed_db_for_storage_key(self, storage_key: str) -> dict:
        """Registers storage key to be notified when an update occurs to its IndexedDB."""
        params: dict[str, Any] = {}
        params["storageKey"] = storage_key
        return await self._client.send(method="Storage.trackIndexedDBForStorageKey", params=params)

    async def untrack_cache_storage_for_origin(self, origin: str) -> dict:
        """Unregisters origin from receiving notifications for cache storage."""
        params: dict[str, Any] = {}
        params["origin"] = origin
        return await self._client.send(method="Storage.untrackCacheStorageForOrigin", params=params)

    async def untrack_cache_storage_for_storage_key(self, storage_key: str) -> dict:
        """Unregisters storage key from receiving notifications for cache storage."""
        params: dict[str, Any] = {}
        params["storageKey"] = storage_key
        return await self._client.send(method="Storage.untrackCacheStorageForStorageKey", params=params)

    async def untrack_indexed_db_for_origin(self, origin: str) -> dict:
        """Unregisters origin from receiving notifications for IndexedDB."""
        params: dict[str, Any] = {}
        params["origin"] = origin
        return await self._client.send(method="Storage.untrackIndexedDBForOrigin", params=params)

    async def untrack_indexed_db_for_storage_key(self, storage_key: str) -> dict:
        """Unregisters storage key from receiving notifications for IndexedDB."""
        params: dict[str, Any] = {}
        params["storageKey"] = storage_key
        return await self._client.send(method="Storage.untrackIndexedDBForStorageKey", params=params)

    async def get_trust_tokens(self) -> dict:
        """Returns the number of stored Trust Tokens per issuer for the
current browsing context.
        """
        return await self._client.send(method="Storage.getTrustTokens")

    async def clear_trust_tokens(self, issuer_origin: str) -> dict:
        """Removes all Trust Tokens issued by the provided issuerOrigin.
Leaves other stored data, including the issuer's Redemption Records, intact.
        """
        params: dict[str, Any] = {}
        params["issuerOrigin"] = issuer_origin
        return await self._client.send(method="Storage.clearTrustTokens", params=params)

    async def get_interest_group_details(self, owner_origin: str, name: str) -> dict:
        """Gets details for a named interest group."""
        params: dict[str, Any] = {}
        params["ownerOrigin"] = owner_origin
        params["name"] = name
        return await self._client.send(method="Storage.getInterestGroupDetails", params=params)

    async def set_interest_group_tracking(self, enable: bool) -> dict:
        """Enables/Disables issuing of interestGroupAccessed events."""
        params: dict[str, Any] = {}
        params["enable"] = enable
        return await self._client.send(method="Storage.setInterestGroupTracking", params=params)

    async def set_interest_group_auction_tracking(self, enable: bool) -> dict:
        """Enables/Disables issuing of interestGroupAuctionEventOccurred and
interestGroupAuctionNetworkRequestCreated.
        """
        params: dict[str, Any] = {}
        params["enable"] = enable
        return await self._client.send(method="Storage.setInterestGroupAuctionTracking", params=params)

    async def get_shared_storage_metadata(self, owner_origin: str) -> dict:
        """Gets metadata for an origin's shared storage."""
        params: dict[str, Any] = {}
        params["ownerOrigin"] = owner_origin
        return await self._client.send(method="Storage.getSharedStorageMetadata", params=params)

    async def get_shared_storage_entries(self, owner_origin: str) -> dict:
        """Gets the entries in an given origin's shared storage."""
        params: dict[str, Any] = {}
        params["ownerOrigin"] = owner_origin
        return await self._client.send(method="Storage.getSharedStorageEntries", params=params)

    async def set_shared_storage_entry(
        self,
        owner_origin: str,
        key: str,
        value: str,
        ignore_if_present: bool | None = None,
    ) -> dict:
        """Sets entry with `key` and `value` for a given origin's shared storage."""
        params: dict[str, Any] = {}
        params["ownerOrigin"] = owner_origin
        params["key"] = key
        params["value"] = value
        if ignore_if_present is not None:
            params["ignoreIfPresent"] = ignore_if_present
        return await self._client.send(method="Storage.setSharedStorageEntry", params=params)

    async def delete_shared_storage_entry(self, owner_origin: str, key: str) -> dict:
        """Deletes entry for `key` (if it exists) for a given origin's shared storage."""
        params: dict[str, Any] = {}
        params["ownerOrigin"] = owner_origin
        params["key"] = key
        return await self._client.send(method="Storage.deleteSharedStorageEntry", params=params)

    async def clear_shared_storage_entries(self, owner_origin: str) -> dict:
        """Clears all entries for a given origin's shared storage."""
        params: dict[str, Any] = {}
        params["ownerOrigin"] = owner_origin
        return await self._client.send(method="Storage.clearSharedStorageEntries", params=params)

    async def reset_shared_storage_budget(self, owner_origin: str) -> dict:
        """Resets the budget for `ownerOrigin` by clearing all budget withdrawals."""
        params: dict[str, Any] = {}
        params["ownerOrigin"] = owner_origin
        return await self._client.send(method="Storage.resetSharedStorageBudget", params=params)

    async def set_shared_storage_tracking(self, enable: bool) -> dict:
        """Enables/disables issuing of sharedStorageAccessed events."""
        params: dict[str, Any] = {}
        params["enable"] = enable
        return await self._client.send(method="Storage.setSharedStorageTracking", params=params)

    async def set_storage_bucket_tracking(self, storage_key: str, enable: bool) -> dict:
        """Set tracking for a storage key's buckets."""
        params: dict[str, Any] = {}
        params["storageKey"] = storage_key
        params["enable"] = enable
        return await self._client.send(method="Storage.setStorageBucketTracking", params=params)

    async def delete_storage_bucket(self, bucket: StorageBucket) -> dict:
        """Deletes the Storage Bucket with the given storage key and bucket name."""
        params: dict[str, Any] = {}
        params["bucket"] = bucket
        return await self._client.send(method="Storage.deleteStorageBucket", params=params)

    async def run_bounce_tracking_mitigations(self) -> dict:
        """Deletes state for sites identified as potential bounce trackers, immediately."""
        return await self._client.send(method="Storage.runBounceTrackingMitigations")

    async def set_attribution_reporting_local_testing_mode(self, enabled: bool) -> dict:
        """https://wicg.github.io/attribution-reporting-api/"""
        params: dict[str, Any] = {}
        params["enabled"] = enabled
        return await self._client.send(method="Storage.setAttributionReportingLocalTestingMode", params=params)

    async def set_attribution_reporting_tracking(self, enable: bool) -> dict:
        """Enables/disables issuing of Attribution Reporting events."""
        params: dict[str, Any] = {}
        params["enable"] = enable
        return await self._client.send(method="Storage.setAttributionReportingTracking", params=params)

    async def send_pending_attribution_reports(self) -> dict:
        """Sends all pending Attribution Reports immediately, regardless of their
scheduled report time.
        """
        return await self._client.send(method="Storage.sendPendingAttributionReports")

    async def get_related_website_sets(self) -> dict:
        """Returns the effective Related Website Sets in use by this profile for the browser
session. The effective Related Website Sets will not change during a browser session.
        """
        return await self._client.send(method="Storage.getRelatedWebsiteSets")

    async def get_affected_urls_for_third_party_cookie_metadata(self, first_party_url: str, third_party_urls: list[str]) -> dict:
        """Returns the list of URLs from a page and its embedded resources that match
existing grace period URL pattern rules.
https://developers.google.com/privacy-sandbox/cookies/temporary-exceptions/grace-period
        """
        params: dict[str, Any] = {}
        params["firstPartyUrl"] = first_party_url
        params["thirdPartyUrls"] = third_party_urls
        return await self._client.send(method="Storage.getAffectedUrlsForThirdPartyCookieMetadata", params=params)

    async def set_protected_audience_k_anonymity(
        self,
        owner: str,
        name: str,
        hashes: list[str],
    ) -> dict:
        params: dict[str, Any] = {}
        params["owner"] = owner
        params["name"] = name
        params["hashes"] = hashes
        return await self._client.send(method="Storage.setProtectedAudienceKAnonymity", params=params)
