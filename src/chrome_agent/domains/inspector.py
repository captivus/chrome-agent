"""CDP Inspector domain.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


class Inspector:
    """CDP Inspector domain."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def disable(self) -> dict:
        """Disables inspector domain notifications."""
        return await self._client.send(method="Inspector.disable")

    async def enable(self) -> dict:
        """Enables inspector domain notifications."""
        return await self._client.send(method="Inspector.enable")
