"""CDP DOMStorage domain.

Query and modify DOM storage.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


SerializedStorageKey = str

# DOM Storage identifier.
StorageId = dict  # Object type

Item = list[str]

class DOMStorage:
    """Query and modify DOM storage."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def clear(self, storage_id: StorageId) -> dict:
        params: dict[str, Any] = {}
        params["storageId"] = storage_id
        return await self._client.send(method="DOMStorage.clear", params=params)

    async def disable(self) -> dict:
        """Disables storage tracking, prevents storage events from being sent to the client."""
        return await self._client.send(method="DOMStorage.disable")

    async def enable(self) -> dict:
        """Enables storage tracking, storage events will now be delivered to the client."""
        return await self._client.send(method="DOMStorage.enable")

    async def get_dom_storage_items(self, storage_id: StorageId) -> dict:
        params: dict[str, Any] = {}
        params["storageId"] = storage_id
        return await self._client.send(method="DOMStorage.getDOMStorageItems", params=params)

    async def remove_dom_storage_item(self, storage_id: StorageId, key: str) -> dict:
        params: dict[str, Any] = {}
        params["storageId"] = storage_id
        params["key"] = key
        return await self._client.send(method="DOMStorage.removeDOMStorageItem", params=params)

    async def set_dom_storage_item(
        self,
        storage_id: StorageId,
        key: str,
        value: str,
    ) -> dict:
        params: dict[str, Any] = {}
        params["storageId"] = storage_id
        params["key"] = key
        params["value"] = value
        return await self._client.send(method="DOMStorage.setDOMStorageItem", params=params)
