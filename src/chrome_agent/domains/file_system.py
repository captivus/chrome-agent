"""CDP FileSystem domain.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


File = dict  # Object type

Directory = dict  # Object type

BucketFileSystemLocator = dict  # Object type

class FileSystem:
    """CDP FileSystem domain."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def get_directory(self, bucket_file_system_locator: BucketFileSystemLocator) -> dict:
        params: dict[str, Any] = {}
        params["bucketFileSystemLocator"] = bucket_file_system_locator
        return await self._client.send(method="FileSystem.getDirectory", params=params)
