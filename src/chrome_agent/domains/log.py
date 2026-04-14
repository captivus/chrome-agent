"""CDP Log domain.

Provides access to log entries.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


# Log entry.
LogEntry = dict  # Object type

# Violation configuration setting.
ViolationSetting = dict  # Object type

class Log:
    """Provides access to log entries."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def clear(self) -> dict:
        """Clears the log."""
        return await self._client.send(method="Log.clear")

    async def disable(self) -> dict:
        """Disables log domain, prevents further log entries from being reported to the client."""
        return await self._client.send(method="Log.disable")

    async def enable(self) -> dict:
        """Enables log domain, sends the entries collected so far to the client by means of the
`entryAdded` notification.
        """
        return await self._client.send(method="Log.enable")

    async def start_violations_report(self, config: list[ViolationSetting]) -> dict:
        """start violation reporting."""
        params: dict[str, Any] = {}
        params["config"] = config
        return await self._client.send(method="Log.startViolationsReport", params=params)

    async def stop_violations_report(self) -> dict:
        """Stop violation reporting."""
        return await self._client.send(method="Log.stopViolationsReport")
