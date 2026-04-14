"""CDP ServiceWorker domain.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


RegistrationID = str

# ServiceWorker registration.
ServiceWorkerRegistration = dict  # Object type

ServiceWorkerVersionRunningStatus = str  # Literal enum: "stopped", "starting", "running", "stopping"

ServiceWorkerVersionStatus = str  # Literal enum: "new", "installing", "installed", "activating", "activated", "redundant"

# ServiceWorker version.
ServiceWorkerVersion = dict  # Object type

# ServiceWorker error message.
ServiceWorkerErrorMessage = dict  # Object type

class ServiceWorker:
    """CDP ServiceWorker domain."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def deliver_push_message(
        self,
        origin: str,
        registration_id: RegistrationID,
        data: str,
    ) -> dict:
        params: dict[str, Any] = {}
        params["origin"] = origin
        params["registrationId"] = registration_id
        params["data"] = data
        return await self._client.send(method="ServiceWorker.deliverPushMessage", params=params)

    async def disable(self) -> dict:
        return await self._client.send(method="ServiceWorker.disable")

    async def dispatch_sync_event(
        self,
        origin: str,
        registration_id: RegistrationID,
        tag: str,
        last_chance: bool,
    ) -> dict:
        params: dict[str, Any] = {}
        params["origin"] = origin
        params["registrationId"] = registration_id
        params["tag"] = tag
        params["lastChance"] = last_chance
        return await self._client.send(method="ServiceWorker.dispatchSyncEvent", params=params)

    async def dispatch_periodic_sync_event(
        self,
        origin: str,
        registration_id: RegistrationID,
        tag: str,
    ) -> dict:
        params: dict[str, Any] = {}
        params["origin"] = origin
        params["registrationId"] = registration_id
        params["tag"] = tag
        return await self._client.send(method="ServiceWorker.dispatchPeriodicSyncEvent", params=params)

    async def enable(self) -> dict:
        return await self._client.send(method="ServiceWorker.enable")

    async def set_force_update_on_page_load(self, force_update_on_page_load: bool) -> dict:
        params: dict[str, Any] = {}
        params["forceUpdateOnPageLoad"] = force_update_on_page_load
        return await self._client.send(method="ServiceWorker.setForceUpdateOnPageLoad", params=params)

    async def skip_waiting(self, scope_url: str) -> dict:
        params: dict[str, Any] = {}
        params["scopeURL"] = scope_url
        return await self._client.send(method="ServiceWorker.skipWaiting", params=params)

    async def start_worker(self, scope_url: str) -> dict:
        params: dict[str, Any] = {}
        params["scopeURL"] = scope_url
        return await self._client.send(method="ServiceWorker.startWorker", params=params)

    async def stop_all_workers(self) -> dict:
        return await self._client.send(method="ServiceWorker.stopAllWorkers")

    async def stop_worker(self, version_id: str) -> dict:
        params: dict[str, Any] = {}
        params["versionId"] = version_id
        return await self._client.send(method="ServiceWorker.stopWorker", params=params)

    async def unregister(self, scope_url: str) -> dict:
        params: dict[str, Any] = {}
        params["scopeURL"] = scope_url
        return await self._client.send(method="ServiceWorker.unregister", params=params)

    async def update_registration(self, scope_url: str) -> dict:
        params: dict[str, Any] = {}
        params["scopeURL"] = scope_url
        return await self._client.send(method="ServiceWorker.updateRegistration", params=params)
