"""CDP Memory domain.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


# Memory pressure level.
PressureLevel = str  # Literal enum: "moderate", "critical"

# Heap profile sample.
SamplingProfileNode = dict  # Object type

# Array of heap profile samples.
SamplingProfile = dict  # Object type

# Executable module information
Module = dict  # Object type

# DOM object counter data.
DOMCounter = dict  # Object type

class Memory:
    """CDP Memory domain."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def get_dom_counters(self) -> dict:
        """Retruns current DOM object counters."""
        return await self._client.send(method="Memory.getDOMCounters")

    async def get_dom_counters_for_leak_detection(self) -> dict:
        """Retruns DOM object counters after preparing renderer for leak detection."""
        return await self._client.send(method="Memory.getDOMCountersForLeakDetection")

    async def prepare_for_leak_detection(self) -> dict:
        """Prepares for leak detection by terminating workers, stopping spellcheckers,
dropping non-essential internal caches, running garbage collections, etc.
        """
        return await self._client.send(method="Memory.prepareForLeakDetection")

    async def forcibly_purge_java_script_memory(self) -> dict:
        """Simulate OomIntervention by purging V8 memory."""
        return await self._client.send(method="Memory.forciblyPurgeJavaScriptMemory")

    async def set_pressure_notifications_suppressed(self, suppressed: bool) -> dict:
        """Enable/disable suppressing memory pressure notifications in all processes."""
        params: dict[str, Any] = {}
        params["suppressed"] = suppressed
        return await self._client.send(method="Memory.setPressureNotificationsSuppressed", params=params)

    async def simulate_pressure_notification(self, level: PressureLevel) -> dict:
        """Simulate a memory pressure notification in all processes."""
        params: dict[str, Any] = {}
        params["level"] = level
        return await self._client.send(method="Memory.simulatePressureNotification", params=params)

    async def start_sampling(self, sampling_interval: int | None = None, suppress_randomness: bool | None = None) -> dict:
        """Start collecting native memory profile."""
        params: dict[str, Any] = {}
        if sampling_interval is not None:
            params["samplingInterval"] = sampling_interval
        if suppress_randomness is not None:
            params["suppressRandomness"] = suppress_randomness
        return await self._client.send(method="Memory.startSampling", params=params)

    async def stop_sampling(self) -> dict:
        """Stop collecting native memory profile."""
        return await self._client.send(method="Memory.stopSampling")

    async def get_all_time_sampling_profile(self) -> dict:
        """Retrieve native memory allocations profile
collected since renderer process startup.
        """
        return await self._client.send(method="Memory.getAllTimeSamplingProfile")

    async def get_browser_sampling_profile(self) -> dict:
        """Retrieve native memory allocations profile
collected since browser process startup.
        """
        return await self._client.send(method="Memory.getBrowserSamplingProfile")

    async def get_sampling_profile(self) -> dict:
        """Retrieve native memory allocations profile collected since last
`startSampling` call.
        """
        return await self._client.send(method="Memory.getSamplingProfile")
