"""CDP DeviceOrientation domain.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


class DeviceOrientation:
    """CDP DeviceOrientation domain."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def clear_device_orientation_override(self) -> dict:
        """Clears the overridden Device Orientation."""
        return await self._client.send(method="DeviceOrientation.clearDeviceOrientationOverride")

    async def set_device_orientation_override(
        self,
        alpha: float,
        beta: float,
        gamma: float,
    ) -> dict:
        """Overrides the Device Orientation."""
        params: dict[str, Any] = {}
        params["alpha"] = alpha
        params["beta"] = beta
        params["gamma"] = gamma
        return await self._client.send(method="DeviceOrientation.setDeviceOrientationOverride", params=params)
