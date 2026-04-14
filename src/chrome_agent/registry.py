"""Instance registry for chrome-agent.

Manages named browser instances: auto-allocates ports, derives names
from directory basenames, stores name-to-port-to-PID mappings, supports
lookup by name, and detects/cleans up stale entries.

Registry data is stored under /tmp/chrome-agent/registry.json by default.
All public functions accept an optional registry_path parameter for test
isolation.
"""

import json
import logging
import os
import re
import shutil
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .utils import process_is_running

logger = logging.getLogger(__name__)

REGISTRY_PATH = "/tmp/chrome-agent/registry.json"
BASE_PORT = 9222
MAX_PORT = BASE_PORT + 100


@dataclass
class InstanceInfo:
    """Information about a registered browser instance."""
    name: str
    port: int
    pid: int
    browser_version: str
    user_data_dir: str = ""
    alive: bool = True


class InstanceNotFoundError(Exception):
    """Named instance not found in the registry."""
    def __init__(self, name: str, available: list[str]):
        self.name = name
        self.available = available
        if available:
            avail_str = ", ".join(available)
            super().__init__(
                f"Instance '{name}' not found. Available: {avail_str}"
            )
        else:
            super().__init__(
                f"Instance '{name}' not found. No instances registered. "
                f"Launch one with: chrome-agent launch"
            )


def _resolve_path(registry_path: str | None) -> str:
    """Resolve registry path, using default if None."""
    return registry_path if registry_path is not None else REGISTRY_PATH


def _load_registry(registry_path: str) -> dict:
    """Load the registry from disk. Returns empty dict on missing or corrupt file."""
    if not os.path.exists(registry_path):
        return {}
    try:
        with open(registry_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Corrupted registry at %s, resetting to empty: %s", registry_path, exc)
        return {}


def _save_registry(registry: dict, registry_path: str) -> None:
    """Save the registry atomically via temp-file-and-rename."""
    os.makedirs(os.path.dirname(registry_path), exist_ok=True)
    tmp_path = registry_path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(registry, f, indent=2)
    os.rename(tmp_path, registry_path)


def _port_is_listening(port: int) -> bool:
    """Quick socket check for an active listener on a port."""
    try:
        sock = socket.create_connection(("localhost", port), timeout=0.1)
        sock.close()
        return True
    except (ConnectionRefusedError, OSError):
        return False


def _derive_base_name(working_dir: str) -> str:
    """Derive a cleaned base name from a directory path.

    Lowercases, replaces spaces with hyphens, strips non-alphanumeric
    characters (keeping hyphens and dots), collapses multiple hyphens,
    and strips leading/trailing hyphens and dots.
    Falls back to "chrome" for empty/unusable names.
    """
    basename = os.path.basename(working_dir)
    cleaned = basename.lower()
    cleaned = cleaned.replace(" ", "-")
    cleaned = re.sub(r"[^a-z0-9.\-]", "", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    cleaned = cleaned.strip("-.")
    if not cleaned:
        cleaned = "chrome"
    return cleaned


def _derive_unique_name(base_name: str, registry: dict) -> str:
    """Find the next available suffixed name (base-01, base-02, etc.)."""
    suffix = 1
    while True:
        candidate = f"{base_name}-{suffix:02d}"
        if candidate not in registry:
            return candidate
        suffix += 1


def allocate_port(registry: dict) -> int:
    """Find the next available port starting from BASE_PORT.

    Skips ports used by live registry entries and ports with active
    listeners. Raises RuntimeError if no ports available in range.
    """
    used_ports = set()
    for entry in registry.values():
        if process_is_running(entry["pid"]):
            used_ports.add(entry["port"])

    port = BASE_PORT
    while port < MAX_PORT:
        if port not in used_ports and not _port_is_listening(port):
            return port
        port += 1

    raise RuntimeError(f"No available ports in range {BASE_PORT}-{MAX_PORT}")


def register(
    working_dir: str,
    pid: int,
    browser_version: str,
    user_data_dir: str,
    port_override: int | None = None,
    registry_path: str | None = None,
) -> InstanceInfo:
    """Register a new browser instance in the registry.

    Derives the instance name from working_dir basename.
    Auto-allocates a port unless port_override is specified.
    """
    path = _resolve_path(registry_path)
    registry = _load_registry(path)

    if port_override is not None:
        port = port_override
    else:
        port = allocate_port(registry)

    base_name = _derive_base_name(working_dir)
    instance_name = _derive_unique_name(base_name, registry)

    registry[instance_name] = {
        "port": port,
        "pid": pid,
        "browser_version": browser_version,
        "user_data_dir": user_data_dir,
        "launched": datetime.now(timezone.utc).isoformat(),
    }
    _save_registry(registry, path)

    logger.info("Registered instance %s on port %d (pid %d)", instance_name, port, pid)

    return InstanceInfo(
        name=instance_name,
        port=port,
        pid=pid,
        browser_version=browser_version,
        user_data_dir=user_data_dir,
    )


def lookup(
    instance_name: str,
    registry_path: str | None = None,
) -> InstanceInfo:
    """Look up a registered instance by name.

    Raises InstanceNotFoundError if the name is not in the registry.
    Checks PID liveness and sets alive accordingly.
    """
    path = _resolve_path(registry_path)
    registry = _load_registry(path)

    if instance_name not in registry:
        raise InstanceNotFoundError(
            name=instance_name,
            available=list(registry.keys()),
        )

    entry = registry[instance_name]
    alive = process_is_running(entry["pid"])

    return InstanceInfo(
        name=instance_name,
        port=entry["port"],
        pid=entry["pid"],
        browser_version=entry.get("browser_version", ""),
        user_data_dir=entry.get("user_data_dir", ""),
        alive=alive,
    )


def enumerate_instances(
    registry_path: str | None = None,
) -> list[InstanceInfo]:
    """List all registered instances with liveness status."""
    path = _resolve_path(registry_path)
    registry = _load_registry(path)

    results = []
    for name, entry in registry.items():
        alive = process_is_running(entry["pid"])
        results.append(InstanceInfo(
            name=name,
            port=entry["port"],
            pid=entry["pid"],
            browser_version=entry.get("browser_version", ""),
            user_data_dir=entry.get("user_data_dir", ""),
            alive=alive,
        ))
    return results


def cleanup(
    registry_path: str | None = None,
) -> list[str]:
    """Remove stale registry entries and their session directories.

    Returns the list of removed instance names.
    """
    path = _resolve_path(registry_path)
    registry = _load_registry(path)

    removed = []
    for name, entry in list(registry.items()):
        if not process_is_running(entry["pid"]):
            del registry[name]
            removed.append(name)
            session_dir = entry.get("user_data_dir")
            if session_dir and os.path.exists(session_dir):
                shutil.rmtree(session_dir, ignore_errors=True)
            logger.info("Cleaned up stale instance %s", name)

    _save_registry(registry, path)
    return removed
