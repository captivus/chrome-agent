"""CDP Console domain.

This domain is deprecated - use Runtime or Log instead.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


# Console message.
ConsoleMessage = dict  # Object type

class Console:
    """This domain is deprecated - use Runtime or Log instead."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def clear_messages(self) -> dict:
        """Does nothing."""
        return await self._client.send(method="Console.clearMessages")

    async def disable(self) -> dict:
        """Disables console domain, prevents further console messages from being reported to the client."""
        return await self._client.send(method="Console.disable")

    async def enable(self) -> dict:
        """Enables console domain, sends the messages collected so far to the client by means of the
`messageAdded` notification.
        """
        return await self._client.send(method="Console.enable")
