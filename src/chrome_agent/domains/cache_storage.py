"""CDP CacheStorage domain.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


CacheId = str

# type of HTTP response cached
CachedResponseType = str  # Literal enum: "basic", "cors", "default", "error", "opaqueResponse", "opaqueRedirect"

# Data entry.
DataEntry = dict  # Object type

# Cache identifier.
Cache = dict  # Object type

Header = dict  # Object type

# Cached response
CachedResponse = dict  # Object type

class CacheStorage:
    """CDP CacheStorage domain."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def delete_cache(self, cache_id: CacheId) -> dict:
        """Deletes a cache."""
        params: dict[str, Any] = {}
        params["cacheId"] = cache_id
        return await self._client.send(method="CacheStorage.deleteCache", params=params)

    async def delete_entry(self, cache_id: CacheId, request: str) -> dict:
        """Deletes a cache entry."""
        params: dict[str, Any] = {}
        params["cacheId"] = cache_id
        params["request"] = request
        return await self._client.send(method="CacheStorage.deleteEntry", params=params)

    async def request_cache_names(
        self,
        security_origin: str | None = None,
        storage_key: str | None = None,
        storage_bucket: str | None = None,
    ) -> dict:
        """Requests cache names."""
        params: dict[str, Any] = {}
        if security_origin is not None:
            params["securityOrigin"] = security_origin
        if storage_key is not None:
            params["storageKey"] = storage_key
        if storage_bucket is not None:
            params["storageBucket"] = storage_bucket
        return await self._client.send(method="CacheStorage.requestCacheNames", params=params)

    async def request_cached_response(
        self,
        cache_id: CacheId,
        request_url: str,
        request_headers: list[Header],
    ) -> dict:
        """Fetches cache entry."""
        params: dict[str, Any] = {}
        params["cacheId"] = cache_id
        params["requestURL"] = request_url
        params["requestHeaders"] = request_headers
        return await self._client.send(method="CacheStorage.requestCachedResponse", params=params)

    async def request_entries(
        self,
        cache_id: CacheId,
        skip_count: int | None = None,
        page_size: int | None = None,
        path_filter: str | None = None,
    ) -> dict:
        """Requests data from cache."""
        params: dict[str, Any] = {}
        params["cacheId"] = cache_id
        if skip_count is not None:
            params["skipCount"] = skip_count
        if page_size is not None:
            params["pageSize"] = page_size
        if path_filter is not None:
            params["pathFilter"] = path_filter
        return await self._client.send(method="CacheStorage.requestEntries", params=params)
