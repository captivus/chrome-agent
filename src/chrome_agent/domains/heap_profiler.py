"""CDP HeapProfiler domain.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


HeapSnapshotObjectId = str

# Sampling Heap Profile node. Holds callsite information, allocation statistics and child nodes.
SamplingHeapProfileNode = dict  # Object type

# A single sample from a sampling profile.
SamplingHeapProfileSample = dict  # Object type

# Sampling profile.
SamplingHeapProfile = dict  # Object type

class HeapProfiler:
    """CDP HeapProfiler domain."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def add_inspected_heap_object(self, heap_object_id: HeapSnapshotObjectId) -> dict:
        """Enables console to refer to the node with given id via $x (see Command Line API for more details
$x functions).
        """
        params: dict[str, Any] = {}
        params["heapObjectId"] = heap_object_id
        return await self._client.send(method="HeapProfiler.addInspectedHeapObject", params=params)

    async def collect_garbage(self) -> dict:
        return await self._client.send(method="HeapProfiler.collectGarbage")

    async def disable(self) -> dict:
        return await self._client.send(method="HeapProfiler.disable")

    async def enable(self) -> dict:
        return await self._client.send(method="HeapProfiler.enable")

    async def get_heap_object_id(self, object_id: str) -> dict:
        params: dict[str, Any] = {}
        params["objectId"] = object_id
        return await self._client.send(method="HeapProfiler.getHeapObjectId", params=params)

    async def get_object_by_heap_object_id(self, object_id: HeapSnapshotObjectId, object_group: str | None = None) -> dict:
        params: dict[str, Any] = {}
        params["objectId"] = object_id
        if object_group is not None:
            params["objectGroup"] = object_group
        return await self._client.send(method="HeapProfiler.getObjectByHeapObjectId", params=params)

    async def get_sampling_profile(self) -> dict:
        return await self._client.send(method="HeapProfiler.getSamplingProfile")

    async def start_sampling(
        self,
        sampling_interval: float | None = None,
        stack_depth: float | None = None,
        include_objects_collected_by_major_gc: bool | None = None,
        include_objects_collected_by_minor_gc: bool | None = None,
    ) -> dict:
        params: dict[str, Any] = {}
        if sampling_interval is not None:
            params["samplingInterval"] = sampling_interval
        if stack_depth is not None:
            params["stackDepth"] = stack_depth
        if include_objects_collected_by_major_gc is not None:
            params["includeObjectsCollectedByMajorGC"] = include_objects_collected_by_major_gc
        if include_objects_collected_by_minor_gc is not None:
            params["includeObjectsCollectedByMinorGC"] = include_objects_collected_by_minor_gc
        return await self._client.send(method="HeapProfiler.startSampling", params=params)

    async def start_tracking_heap_objects(self, track_allocations: bool | None = None) -> dict:
        params: dict[str, Any] = {}
        if track_allocations is not None:
            params["trackAllocations"] = track_allocations
        return await self._client.send(method="HeapProfiler.startTrackingHeapObjects", params=params)

    async def stop_sampling(self) -> dict:
        return await self._client.send(method="HeapProfiler.stopSampling")

    async def stop_tracking_heap_objects(
        self,
        report_progress: bool | None = None,
        treat_global_objects_as_roots: bool | None = None,
        capture_numeric_value: bool | None = None,
        expose_internals: bool | None = None,
    ) -> dict:
        params: dict[str, Any] = {}
        if report_progress is not None:
            params["reportProgress"] = report_progress
        if treat_global_objects_as_roots is not None:
            params["treatGlobalObjectsAsRoots"] = treat_global_objects_as_roots
        if capture_numeric_value is not None:
            params["captureNumericValue"] = capture_numeric_value
        if expose_internals is not None:
            params["exposeInternals"] = expose_internals
        return await self._client.send(method="HeapProfiler.stopTrackingHeapObjects", params=params)

    async def take_heap_snapshot(
        self,
        report_progress: bool | None = None,
        treat_global_objects_as_roots: bool | None = None,
        capture_numeric_value: bool | None = None,
        expose_internals: bool | None = None,
    ) -> dict:
        params: dict[str, Any] = {}
        if report_progress is not None:
            params["reportProgress"] = report_progress
        if treat_global_objects_as_roots is not None:
            params["treatGlobalObjectsAsRoots"] = treat_global_objects_as_roots
        if capture_numeric_value is not None:
            params["captureNumericValue"] = capture_numeric_value
        if expose_internals is not None:
            params["exposeInternals"] = expose_internals
        return await self._client.send(method="HeapProfiler.takeHeapSnapshot", params=params)
