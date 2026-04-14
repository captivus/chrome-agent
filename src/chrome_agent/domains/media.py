"""CDP Media domain.

This domain allows detailed inspection of media elements.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


PlayerId = str

Timestamp = float

# Have one type per entry in MediaLogRecord::Type
# Corresponds to kMessage
PlayerMessage = dict  # Object type

# Corresponds to kMediaPropertyChange
PlayerProperty = dict  # Object type

# Corresponds to kMediaEventTriggered
PlayerEvent = dict  # Object type

# Represents logged source line numbers reported in an error.
# NOTE: file and line are from chromium c++ implementation code, not js.
PlayerErrorSourceLocation = dict  # Object type

# Corresponds to kMediaError
PlayerError = dict  # Object type

Player = dict  # Object type

class Media:
    """This domain allows detailed inspection of media elements."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def enable(self) -> dict:
        """Enables the Media domain"""
        return await self._client.send(method="Media.enable")

    async def disable(self) -> dict:
        """Disables the Media domain."""
        return await self._client.send(method="Media.disable")
