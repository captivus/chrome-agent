"""CDP WebAudio domain.

This domain allows inspection of Web Audio API.
https://webaudio.github.io/web-audio-api/

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


GraphObjectId = str

# Enum of BaseAudioContext types
ContextType = str  # Literal enum: "realtime", "offline"

# Enum of AudioContextState from the spec
ContextState = str  # Literal enum: "suspended", "running", "closed", "interrupted"

NodeType = str

# Enum of AudioNode::ChannelCountMode from the spec
ChannelCountMode = str  # Literal enum: "clamped-max", "explicit", "max"

# Enum of AudioNode::ChannelInterpretation from the spec
ChannelInterpretation = str  # Literal enum: "discrete", "speakers"

ParamType = str

# Enum of AudioParam::AutomationRate from the spec
AutomationRate = str  # Literal enum: "a-rate", "k-rate"

# Fields in AudioContext that change in real-time.
ContextRealtimeData = dict  # Object type

# Protocol object for BaseAudioContext
BaseAudioContext = dict  # Object type

# Protocol object for AudioListener
AudioListener = dict  # Object type

# Protocol object for AudioNode
AudioNode = dict  # Object type

# Protocol object for AudioParam
AudioParam = dict  # Object type

class WebAudio:
    """This domain allows inspection of Web Audio API.
https://webaudio.github.io/web-audio-api/"""

    def __init__(self, client: CDPClient):
        self._client = client

    async def enable(self) -> dict:
        """Enables the WebAudio domain and starts sending context lifetime events."""
        return await self._client.send(method="WebAudio.enable")

    async def disable(self) -> dict:
        """Disables the WebAudio domain."""
        return await self._client.send(method="WebAudio.disable")

    async def get_realtime_data(self, context_id: GraphObjectId) -> dict:
        """Fetch the realtime data from the registered contexts."""
        params: dict[str, Any] = {}
        params["contextId"] = context_id
        return await self._client.send(method="WebAudio.getRealtimeData", params=params)
