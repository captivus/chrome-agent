"""Shared utilities for chrome-agent.

Functions in this module are used by multiple feature modules and must
not have dependencies on other chrome-agent modules to avoid circular imports.
"""

import os
import subprocess


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


def process_is_ours(pid: int, expected_start: str | None = None) -> bool:
    """Whether ``pid`` is a live process belonging to this user -- and, when
    an ``expected_start`` token is given, the same process originally
    recorded, not a later occupant of a recycled PID.

    chrome-agent launches Chrome as the invoking user, so a PID this user
    cannot signal is never one of our browsers. That is why this differs from
    ``process_is_running``, which deliberately treats PermissionError as
    "running": here PermissionError means "running but not ours". The
    distinction matters for PIDs recorded from inside a PID-namespaced
    sandbox (e.g. an agent CLI's bwrap): the namespace-local PID aliases to
    an unrelated host process -- often a root kernel thread -- which must
    never be treated as, or signalled as, our browser.
    """
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    if expected_start is not None:
        actual = process_start_time(pid=pid)
        if actual is not None and actual != expected_start:
            return False
    return True


def process_start_time(pid: int) -> str | None:
    """Opaque start-time identity token for a live process, or None.

    Two processes that ever shared a PID are told apart by start time, so
    (pid, start-token) is a durable process identity across PID reuse.
    Linux: field 22 of ``/proc/<pid>/stat`` (clock ticks since boot).
    Elsewhere: ``ps -o lstart=`` where available. Returns None when
    undeterminable -- callers treat that as "no identity evidence", never as
    a mismatch.
    """
    try:
        with open(f"/proc/{pid}/stat") as f:
            stat = f.read()
        # Fields after the (comm) -- which may itself contain spaces/parens --
        # start at field 3; starttime is field 22, i.e. index 19 here.
        return stat.rsplit(")", 1)[1].split()[19]
    except (OSError, IndexError):
        pass
    try:
        result = subprocess.run(
            ["ps", "-o", "lstart=", "-p", str(pid)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        value = result.stdout.strip()
        return value or None
    except Exception:
        return None
