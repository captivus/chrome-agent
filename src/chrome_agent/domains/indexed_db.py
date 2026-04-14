"""CDP IndexedDB domain.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


# Database with an array of object stores.
DatabaseWithObjectStores = dict  # Object type

# Object store.
ObjectStore = dict  # Object type

# Object store index.
ObjectStoreIndex = dict  # Object type

# Key.
Key = dict  # Object type

# Key range.
KeyRange = dict  # Object type

# Data entry.
DataEntry = dict  # Object type

# Key path.
KeyPath = dict  # Object type

class IndexedDB:
    """CDP IndexedDB domain."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def clear_object_store(
        self,
        database_name: str,
        object_store_name: str,
        security_origin: str | None = None,
        storage_key: str | None = None,
        storage_bucket: str | None = None,
    ) -> dict:
        """Clears all entries from an object store."""
        params: dict[str, Any] = {}
        params["databaseName"] = database_name
        params["objectStoreName"] = object_store_name
        if security_origin is not None:
            params["securityOrigin"] = security_origin
        if storage_key is not None:
            params["storageKey"] = storage_key
        if storage_bucket is not None:
            params["storageBucket"] = storage_bucket
        return await self._client.send(method="IndexedDB.clearObjectStore", params=params)

    async def delete_database(
        self,
        database_name: str,
        security_origin: str | None = None,
        storage_key: str | None = None,
        storage_bucket: str | None = None,
    ) -> dict:
        """Deletes a database."""
        params: dict[str, Any] = {}
        params["databaseName"] = database_name
        if security_origin is not None:
            params["securityOrigin"] = security_origin
        if storage_key is not None:
            params["storageKey"] = storage_key
        if storage_bucket is not None:
            params["storageBucket"] = storage_bucket
        return await self._client.send(method="IndexedDB.deleteDatabase", params=params)

    async def delete_object_store_entries(
        self,
        database_name: str,
        object_store_name: str,
        key_range: KeyRange,
        security_origin: str | None = None,
        storage_key: str | None = None,
        storage_bucket: str | None = None,
    ) -> dict:
        """Delete a range of entries from an object store"""
        params: dict[str, Any] = {}
        params["databaseName"] = database_name
        params["objectStoreName"] = object_store_name
        params["keyRange"] = key_range
        if security_origin is not None:
            params["securityOrigin"] = security_origin
        if storage_key is not None:
            params["storageKey"] = storage_key
        if storage_bucket is not None:
            params["storageBucket"] = storage_bucket
        return await self._client.send(method="IndexedDB.deleteObjectStoreEntries", params=params)

    async def disable(self) -> dict:
        """Disables events from backend."""
        return await self._client.send(method="IndexedDB.disable")

    async def enable(self) -> dict:
        """Enables events from backend."""
        return await self._client.send(method="IndexedDB.enable")

    async def request_data(
        self,
        database_name: str,
        object_store_name: str,
        skip_count: int,
        page_size: int,
        security_origin: str | None = None,
        storage_key: str | None = None,
        storage_bucket: str | None = None,
        index_name: str | None = None,
        key_range: KeyRange | None = None,
    ) -> dict:
        """Requests data from object store or index."""
        params: dict[str, Any] = {}
        params["databaseName"] = database_name
        params["objectStoreName"] = object_store_name
        params["skipCount"] = skip_count
        params["pageSize"] = page_size
        if security_origin is not None:
            params["securityOrigin"] = security_origin
        if storage_key is not None:
            params["storageKey"] = storage_key
        if storage_bucket is not None:
            params["storageBucket"] = storage_bucket
        if index_name is not None:
            params["indexName"] = index_name
        if key_range is not None:
            params["keyRange"] = key_range
        return await self._client.send(method="IndexedDB.requestData", params=params)

    async def get_metadata(
        self,
        database_name: str,
        object_store_name: str,
        security_origin: str | None = None,
        storage_key: str | None = None,
        storage_bucket: str | None = None,
    ) -> dict:
        """Gets metadata of an object store."""
        params: dict[str, Any] = {}
        params["databaseName"] = database_name
        params["objectStoreName"] = object_store_name
        if security_origin is not None:
            params["securityOrigin"] = security_origin
        if storage_key is not None:
            params["storageKey"] = storage_key
        if storage_bucket is not None:
            params["storageBucket"] = storage_bucket
        return await self._client.send(method="IndexedDB.getMetadata", params=params)

    async def request_database(
        self,
        database_name: str,
        security_origin: str | None = None,
        storage_key: str | None = None,
        storage_bucket: str | None = None,
    ) -> dict:
        """Requests database with given name in given frame."""
        params: dict[str, Any] = {}
        params["databaseName"] = database_name
        if security_origin is not None:
            params["securityOrigin"] = security_origin
        if storage_key is not None:
            params["storageKey"] = storage_key
        if storage_bucket is not None:
            params["storageBucket"] = storage_bucket
        return await self._client.send(method="IndexedDB.requestDatabase", params=params)

    async def request_database_names(
        self,
        security_origin: str | None = None,
        storage_key: str | None = None,
        storage_bucket: str | None = None,
    ) -> dict:
        """Requests database names for given security origin."""
        params: dict[str, Any] = {}
        if security_origin is not None:
            params["securityOrigin"] = security_origin
        if storage_key is not None:
            params["storageKey"] = storage_key
        if storage_bucket is not None:
            params["storageBucket"] = storage_bucket
        return await self._client.send(method="IndexedDB.requestDatabaseNames", params=params)
