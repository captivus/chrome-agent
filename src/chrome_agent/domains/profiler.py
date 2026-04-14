"""CDP Profiler domain.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


# Profile node. Holds callsite information, execution statistics and child nodes.
ProfileNode = dict  # Object type

# Profile.
Profile = dict  # Object type

# Specifies a number of samples attributed to a certain source position.
PositionTickInfo = dict  # Object type

# Coverage data for a source range.
CoverageRange = dict  # Object type

# Coverage data for a JavaScript function.
FunctionCoverage = dict  # Object type

# Coverage data for a JavaScript script.
ScriptCoverage = dict  # Object type

class Profiler:
    """CDP Profiler domain."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def disable(self) -> dict:
        return await self._client.send(method="Profiler.disable")

    async def enable(self) -> dict:
        return await self._client.send(method="Profiler.enable")

    async def get_best_effort_coverage(self) -> dict:
        """Collect coverage data for the current isolate. The coverage data may be incomplete due to
garbage collection.
        """
        return await self._client.send(method="Profiler.getBestEffortCoverage")

    async def set_sampling_interval(self, interval: int) -> dict:
        """Changes CPU profiler sampling interval. Must be called before CPU profiles recording started."""
        params: dict[str, Any] = {}
        params["interval"] = interval
        return await self._client.send(method="Profiler.setSamplingInterval", params=params)

    async def start(self) -> dict:
        return await self._client.send(method="Profiler.start")

    async def start_precise_coverage(
        self,
        call_count: bool | None = None,
        detailed: bool | None = None,
        allow_triggered_updates: bool | None = None,
    ) -> dict:
        """Enable precise code coverage. Coverage data for JavaScript executed before enabling precise code
coverage may be incomplete. Enabling prevents running optimized code and resets execution
counters.
        """
        params: dict[str, Any] = {}
        if call_count is not None:
            params["callCount"] = call_count
        if detailed is not None:
            params["detailed"] = detailed
        if allow_triggered_updates is not None:
            params["allowTriggeredUpdates"] = allow_triggered_updates
        return await self._client.send(method="Profiler.startPreciseCoverage", params=params)

    async def stop(self) -> dict:
        return await self._client.send(method="Profiler.stop")

    async def stop_precise_coverage(self) -> dict:
        """Disable precise code coverage. Disabling releases unnecessary execution count records and allows
executing optimized code.
        """
        return await self._client.send(method="Profiler.stopPreciseCoverage")

    async def take_precise_coverage(self) -> dict:
        """Collect coverage data for the current isolate, and resets execution counters. Precise code
coverage needs to have started.
        """
        return await self._client.send(method="Profiler.takePreciseCoverage")
