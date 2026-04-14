"""CDP DeviceAccess domain.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


RequestId = str

DeviceId = str

# Device information displayed in a user prompt to select a device.
PromptDevice = dict  # Object type

class DeviceAccess:
    """CDP DeviceAccess domain."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def enable(self) -> dict:
        """Enable events in this domain."""
        return await self._client.send(method="DeviceAccess.enable")

    async def disable(self) -> dict:
        """Disable events in this domain."""
        return await self._client.send(method="DeviceAccess.disable")

    async def select_prompt(self, id_: RequestId, device_id: DeviceId) -> dict:
        """Select a device in response to a DeviceAccess.deviceRequestPrompted event."""
        params: dict[str, Any] = {}
        params["id"] = id_
        params["deviceId"] = device_id
        return await self._client.send(method="DeviceAccess.selectPrompt", params=params)

    async def cancel_prompt(self, id_: RequestId) -> dict:
        """Cancel a prompt in response to a DeviceAccess.deviceRequestPrompted event."""
        params: dict[str, Any] = {}
        params["id"] = id_
        return await self._client.send(method="DeviceAccess.cancelPrompt", params=params)
