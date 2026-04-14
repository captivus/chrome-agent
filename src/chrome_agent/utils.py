"""Shared utilities for chrome-agent.

Functions in this module are used by multiple feature modules and must
not have dependencies on other chrome-agent modules to avoid circular imports.
"""

import os


def process_is_running(pid: int) -> bool:
    """Check if a process with the given PID is running.

    Uses signal 0 (existence check without killing).
    Returns True if the process exists, False if it does not.
    Returns True on PermissionError (process exists but we can't signal it).
    """
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
