"""CDP Tracing domain.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


MemoryDumpConfig = dict

TraceConfig = dict  # Object type

# Data format of a trace. Can be either the legacy JSON format or the
# protocol buffer format. Note that the JSON format will be deprecated soon.
StreamFormat = str  # Literal enum: "json", "proto"

# Compression type to use for traces returned via streams.
StreamCompression = str  # Literal enum: "none", "gzip"

# Details exposed when memory request explicitly declared.
# Keep consistent with memory_dump_request_args.h and
# memory_instrumentation.mojom
MemoryDumpLevelOfDetail = str  # Literal enum: "background", "light", "detailed"

# Backend type to use for tracing. `chrome` uses the Chrome-integrated
# tracing service and is supported on all platforms. `system` is only
# supported on Chrome OS and uses the Perfetto system tracing service.
# `auto` chooses `system` when the perfettoConfig provided to Tracing.start
# specifies at least one non-Chrome data source; otherwise uses `chrome`.
TracingBackend = str  # Literal enum: "auto", "chrome", "system"

class Tracing:
    """CDP Tracing domain."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def end(self) -> dict:
        """Stop trace events collection."""
        return await self._client.send(method="Tracing.end")

    async def get_categories(self) -> dict:
        """Gets supported tracing categories."""
        return await self._client.send(method="Tracing.getCategories")

    async def get_track_event_descriptor(self) -> dict:
        """Return a descriptor for all available tracing categories."""
        return await self._client.send(method="Tracing.getTrackEventDescriptor")

    async def record_clock_sync_marker(self, sync_id: str) -> dict:
        """Record a clock sync marker in the trace."""
        params: dict[str, Any] = {}
        params["syncId"] = sync_id
        return await self._client.send(method="Tracing.recordClockSyncMarker", params=params)

    async def request_memory_dump(self, deterministic: bool | None = None, level_of_detail: MemoryDumpLevelOfDetail | None = None) -> dict:
        """Request a global memory dump."""
        params: dict[str, Any] = {}
        if deterministic is not None:
            params["deterministic"] = deterministic
        if level_of_detail is not None:
            params["levelOfDetail"] = level_of_detail
        return await self._client.send(method="Tracing.requestMemoryDump", params=params)

    async def start(
        self,
        categories: str | None = None,
        options: str | None = None,
        buffer_usage_reporting_interval: float | None = None,
        transfer_mode: str | None = None,
        stream_format: StreamFormat | None = None,
        stream_compression: StreamCompression | None = None,
        trace_config: TraceConfig | None = None,
        perfetto_config: str | None = None,
        tracing_backend: TracingBackend | None = None,
    ) -> dict:
        """Start trace events collection."""
        params: dict[str, Any] = {}
        if categories is not None:
            params["categories"] = categories
        if options is not None:
            params["options"] = options
        if buffer_usage_reporting_interval is not None:
            params["bufferUsageReportingInterval"] = buffer_usage_reporting_interval
        if transfer_mode is not None:
            params["transferMode"] = transfer_mode
        if stream_format is not None:
            params["streamFormat"] = stream_format
        if stream_compression is not None:
            params["streamCompression"] = stream_compression
        if trace_config is not None:
            params["traceConfig"] = trace_config
        if perfetto_config is not None:
            params["perfettoConfig"] = perfetto_config
        if tracing_backend is not None:
            params["tracingBackend"] = tracing_backend
        return await self._client.send(method="Tracing.start", params=params)
