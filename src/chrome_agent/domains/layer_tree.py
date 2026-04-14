"""CDP LayerTree domain.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


LayerId = str

SnapshotId = str

# Rectangle where scrolling happens on the main thread.
ScrollRect = dict  # Object type

# Sticky position constraints.
StickyPositionConstraint = dict  # Object type

# Serialized fragment of layer picture along with its offset within the layer.
PictureTile = dict  # Object type

# Information about a compositing layer.
Layer = dict  # Object type

PaintProfile = list[float]

class LayerTree:
    """CDP LayerTree domain."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def compositing_reasons(self, layer_id: LayerId) -> dict:
        """Provides the reasons why the given layer was composited."""
        params: dict[str, Any] = {}
        params["layerId"] = layer_id
        return await self._client.send(method="LayerTree.compositingReasons", params=params)

    async def disable(self) -> dict:
        """Disables compositing tree inspection."""
        return await self._client.send(method="LayerTree.disable")

    async def enable(self) -> dict:
        """Enables compositing tree inspection."""
        return await self._client.send(method="LayerTree.enable")

    async def load_snapshot(self, tiles: list[PictureTile]) -> dict:
        """Returns the snapshot identifier."""
        params: dict[str, Any] = {}
        params["tiles"] = tiles
        return await self._client.send(method="LayerTree.loadSnapshot", params=params)

    async def make_snapshot(self, layer_id: LayerId) -> dict:
        """Returns the layer snapshot identifier."""
        params: dict[str, Any] = {}
        params["layerId"] = layer_id
        return await self._client.send(method="LayerTree.makeSnapshot", params=params)

    async def profile_snapshot(
        self,
        snapshot_id: SnapshotId,
        min_repeat_count: int | None = None,
        min_duration: float | None = None,
        clip_rect: str | None = None,
    ) -> dict:
        params: dict[str, Any] = {}
        params["snapshotId"] = snapshot_id
        if min_repeat_count is not None:
            params["minRepeatCount"] = min_repeat_count
        if min_duration is not None:
            params["minDuration"] = min_duration
        if clip_rect is not None:
            params["clipRect"] = clip_rect
        return await self._client.send(method="LayerTree.profileSnapshot", params=params)

    async def release_snapshot(self, snapshot_id: SnapshotId) -> dict:
        """Releases layer snapshot captured by the back-end."""
        params: dict[str, Any] = {}
        params["snapshotId"] = snapshot_id
        return await self._client.send(method="LayerTree.releaseSnapshot", params=params)

    async def replay_snapshot(
        self,
        snapshot_id: SnapshotId,
        from_step: int | None = None,
        to_step: int | None = None,
        scale: float | None = None,
    ) -> dict:
        """Replays the layer snapshot and returns the resulting bitmap."""
        params: dict[str, Any] = {}
        params["snapshotId"] = snapshot_id
        if from_step is not None:
            params["fromStep"] = from_step
        if to_step is not None:
            params["toStep"] = to_step
        if scale is not None:
            params["scale"] = scale
        return await self._client.send(method="LayerTree.replaySnapshot", params=params)

    async def snapshot_command_log(self, snapshot_id: SnapshotId) -> dict:
        """Replays the layer snapshot and returns canvas log."""
        params: dict[str, Any] = {}
        params["snapshotId"] = snapshot_id
        return await self._client.send(method="LayerTree.snapshotCommandLog", params=params)
