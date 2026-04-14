"""CDP Cast domain.

A domain for interacting with Cast, Presentation API, and Remote Playback API
functionalities.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


Sink = dict  # Object type

class Cast:
    """A domain for interacting with Cast, Presentation API, and Remote Playback API
functionalities."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def enable(self, presentation_url: str | None = None) -> dict:
        """Starts observing for sinks that can be used for tab mirroring, and if set,
sinks compatible with |presentationUrl| as well. When sinks are found, a
|sinksUpdated| event is fired.
Also starts observing for issue messages. When an issue is added or removed,
an |issueUpdated| event is fired.
        """
        params: dict[str, Any] = {}
        if presentation_url is not None:
            params["presentationUrl"] = presentation_url
        return await self._client.send(method="Cast.enable", params=params)

    async def disable(self) -> dict:
        """Stops observing for sinks and issues."""
        return await self._client.send(method="Cast.disable")

    async def set_sink_to_use(self, sink_name: str) -> dict:
        """Sets a sink to be used when the web page requests the browser to choose a
sink via Presentation API, Remote Playback API, or Cast SDK.
        """
        params: dict[str, Any] = {}
        params["sinkName"] = sink_name
        return await self._client.send(method="Cast.setSinkToUse", params=params)

    async def start_desktop_mirroring(self, sink_name: str) -> dict:
        """Starts mirroring the desktop to the sink."""
        params: dict[str, Any] = {}
        params["sinkName"] = sink_name
        return await self._client.send(method="Cast.startDesktopMirroring", params=params)

    async def start_tab_mirroring(self, sink_name: str) -> dict:
        """Starts mirroring the tab to the sink."""
        params: dict[str, Any] = {}
        params["sinkName"] = sink_name
        return await self._client.send(method="Cast.startTabMirroring", params=params)

    async def stop_casting(self, sink_name: str) -> dict:
        """Stops the active Cast session on the sink."""
        params: dict[str, Any] = {}
        params["sinkName"] = sink_name
        return await self._client.send(method="Cast.stopCasting", params=params)
