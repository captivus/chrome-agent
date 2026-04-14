"""CDP SystemInfo domain.

The SystemInfo domain defines methods and events for querying low-level system information.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


# Describes a single graphics processor (GPU).
GPUDevice = dict  # Object type

# Describes the width and height dimensions of an entity.
Size = dict  # Object type

# Describes a supported video decoding profile with its associated minimum and
# maximum resolutions.
VideoDecodeAcceleratorCapability = dict  # Object type

# Describes a supported video encoding profile with its associated maximum
# resolution and maximum framerate.
VideoEncodeAcceleratorCapability = dict  # Object type

# YUV subsampling type of the pixels of a given image.
SubsamplingFormat = str  # Literal enum: "yuv420", "yuv422", "yuv444"

# Image format of a given image.
ImageType = str  # Literal enum: "jpeg", "webp", "unknown"

# Provides information about the GPU(s) on the system.
GPUInfo = dict  # Object type

# Represents process info.
ProcessInfo = dict  # Object type

class SystemInfo:
    """The SystemInfo domain defines methods and events for querying low-level system information."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def get_info(self) -> dict:
        """Returns information about the system."""
        return await self._client.send(method="SystemInfo.getInfo")

    async def get_feature_state(self, feature_state: str) -> dict:
        """Returns information about the feature state."""
        params: dict[str, Any] = {}
        params["featureState"] = feature_state
        return await self._client.send(method="SystemInfo.getFeatureState", params=params)

    async def get_process_info(self) -> dict:
        """Returns information about all running processes."""
        return await self._client.send(method="SystemInfo.getProcessInfo")
