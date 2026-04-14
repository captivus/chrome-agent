"""CDP Animation domain.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


# Animation instance.
Animation = dict  # Object type

# Timeline instance
ViewOrScrollTimeline = dict  # Object type

# AnimationEffect instance
AnimationEffect = dict  # Object type

# Keyframes Rule
KeyframesRule = dict  # Object type

# Keyframe Style
KeyframeStyle = dict  # Object type

class Animation:
    """CDP Animation domain."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def disable(self) -> dict:
        """Disables animation domain notifications."""
        return await self._client.send(method="Animation.disable")

    async def enable(self) -> dict:
        """Enables animation domain notifications."""
        return await self._client.send(method="Animation.enable")

    async def get_current_time(self, id_: str) -> dict:
        """Returns the current time of the an animation."""
        params: dict[str, Any] = {}
        params["id"] = id_
        return await self._client.send(method="Animation.getCurrentTime", params=params)

    async def get_playback_rate(self) -> dict:
        """Gets the playback rate of the document timeline."""
        return await self._client.send(method="Animation.getPlaybackRate")

    async def release_animations(self, animations: list[str]) -> dict:
        """Releases a set of animations to no longer be manipulated."""
        params: dict[str, Any] = {}
        params["animations"] = animations
        return await self._client.send(method="Animation.releaseAnimations", params=params)

    async def resolve_animation(self, animation_id: str) -> dict:
        """Gets the remote object of the Animation."""
        params: dict[str, Any] = {}
        params["animationId"] = animation_id
        return await self._client.send(method="Animation.resolveAnimation", params=params)

    async def seek_animations(self, animations: list[str], current_time: float) -> dict:
        """Seek a set of animations to a particular time within each animation."""
        params: dict[str, Any] = {}
        params["animations"] = animations
        params["currentTime"] = current_time
        return await self._client.send(method="Animation.seekAnimations", params=params)

    async def set_paused(self, animations: list[str], paused: bool) -> dict:
        """Sets the paused state of a set of animations."""
        params: dict[str, Any] = {}
        params["animations"] = animations
        params["paused"] = paused
        return await self._client.send(method="Animation.setPaused", params=params)

    async def set_playback_rate(self, playback_rate: float) -> dict:
        """Sets the playback rate of the document timeline."""
        params: dict[str, Any] = {}
        params["playbackRate"] = playback_rate
        return await self._client.send(method="Animation.setPlaybackRate", params=params)

    async def set_timing(
        self,
        animation_id: str,
        duration: float,
        delay: float,
    ) -> dict:
        """Sets the timing of an animation node."""
        params: dict[str, Any] = {}
        params["animationId"] = animation_id
        params["duration"] = duration
        params["delay"] = delay
        return await self._client.send(method="Animation.setTiming", params=params)
