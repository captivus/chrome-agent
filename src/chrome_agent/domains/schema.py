"""CDP Schema domain.

This domain is deprecated.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


# Description of the protocol domain.
Domain = dict  # Object type

class Schema:
    """This domain is deprecated."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def get_domains(self) -> dict:
        """Returns supported domains."""
        return await self._client.send(method="Schema.getDomains")
