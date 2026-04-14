"""CDP Extensions domain.

Defines commands and events for browser extensions.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


# Storage areas.
StorageArea = str  # Literal enum: "session", "local", "sync", "managed"

class Extensions:
    """Defines commands and events for browser extensions."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def trigger_action(self, id_: str, target_id: str) -> dict:
        """Runs an extension default action.
Available if the client is connected using the --remote-debugging-pipe
flag and the --enable-unsafe-extension-debugging flag is set.
        """
        params: dict[str, Any] = {}
        params["id"] = id_
        params["targetId"] = target_id
        return await self._client.send(method="Extensions.triggerAction", params=params)

    async def load_unpacked(self, path: str, enable_in_incognito: bool | None = None) -> dict:
        """Installs an unpacked extension from the filesystem similar to
--load-extension CLI flags. Returns extension ID once the extension
has been installed. Available if the client is connected using the
--remote-debugging-pipe flag and the --enable-unsafe-extension-debugging
flag is set.
        """
        params: dict[str, Any] = {}
        params["path"] = path
        if enable_in_incognito is not None:
            params["enableInIncognito"] = enable_in_incognito
        return await self._client.send(method="Extensions.loadUnpacked", params=params)

    async def uninstall(self, id_: str) -> dict:
        """Uninstalls an unpacked extension (others not supported) from the profile.
Available if the client is connected using the --remote-debugging-pipe flag
and the --enable-unsafe-extension-debugging.
        """
        params: dict[str, Any] = {}
        params["id"] = id_
        return await self._client.send(method="Extensions.uninstall", params=params)

    async def get_storage_items(
        self,
        id_: str,
        storage_area: StorageArea,
        keys: list[str] | None = None,
    ) -> dict:
        """Gets data from extension storage in the given `storageArea`. If `keys` is
specified, these are used to filter the result.
        """
        params: dict[str, Any] = {}
        params["id"] = id_
        params["storageArea"] = storage_area
        if keys is not None:
            params["keys"] = keys
        return await self._client.send(method="Extensions.getStorageItems", params=params)

    async def remove_storage_items(
        self,
        id_: str,
        storage_area: StorageArea,
        keys: list[str],
    ) -> dict:
        """Removes `keys` from extension storage in the given `storageArea`."""
        params: dict[str, Any] = {}
        params["id"] = id_
        params["storageArea"] = storage_area
        params["keys"] = keys
        return await self._client.send(method="Extensions.removeStorageItems", params=params)

    async def clear_storage_items(self, id_: str, storage_area: StorageArea) -> dict:
        """Clears extension storage in the given `storageArea`."""
        params: dict[str, Any] = {}
        params["id"] = id_
        params["storageArea"] = storage_area
        return await self._client.send(method="Extensions.clearStorageItems", params=params)

    async def set_storage_items(
        self,
        id_: str,
        storage_area: StorageArea,
        values: dict,
    ) -> dict:
        """Sets `values` in extension storage in the given `storageArea`. The provided `values`
will be merged with existing values in the storage area.
        """
        params: dict[str, Any] = {}
        params["id"] = id_
        params["storageArea"] = storage_area
        params["values"] = values
        return await self._client.send(method="Extensions.setStorageItems", params=params)
