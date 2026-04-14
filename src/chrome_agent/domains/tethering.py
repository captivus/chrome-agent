"""CDP Tethering domain.

The Tethering domain defines methods and events for browser port binding.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


class Tethering:
    """The Tethering domain defines methods and events for browser port binding."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def bind(self, port: int) -> dict:
        """Request browser port binding."""
        params: dict[str, Any] = {}
        params["port"] = port
        return await self._client.send(method="Tethering.bind", params=params)

    async def unbind(self, port: int) -> dict:
        """Request browser port unbinding."""
        params: dict[str, Any] = {}
        params["port"] = port
        return await self._client.send(method="Tethering.unbind", params=params)
