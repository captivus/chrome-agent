"""Shared utilities for chrome-agent.

Functions in this module are used by multiple feature modules and must
not have dependencies on other chrome-agent modules to avoid circular imports.
"""

import os
import subprocess
import sys

_IS_WINDOWS = sys.platform == "win32"

if _IS_WINDOWS:
    import ctypes

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)

    def _win_pid_exists(pid: int) -> bool:
        """Liveness probe for Windows.

        os.kill(pid, 0) is a POSIX idiom; on Windows signal 0 is
        CTRL_C_EVENT and the call raises OSError WinError 87 for ordinary
        processes, so probe with OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION)
        instead. ERROR_ACCESS_DENIED (5) still proves the process exists.
        """
        handle = _k32.OpenProcess(0x1000, False, pid)
        if handle:
            _k32.CloseHandle(handle)
            return True
        return ctypes.get_last_error() == 5

    class _FILETIME(ctypes.Structure):
        _fields_ = [
            ("dwLowDateTime", ctypes.c_uint32),
            ("dwHighDateTime", ctypes.c_uint32),
        ]


def process_is_running(pid: int) -> bool:
    """Check if a process with the given PID is running.

    Uses signal 0 (existence check without killing).
    Returns True if the process exists, False if it does not.
    Returns True on PermissionError (process exists but we can't signal it).
    """
    if _IS_WINDOWS:
        return _win_pid_exists(pid)
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
    if _IS_WINDOWS:
        if not _win_pid_exists(pid):
            return False
    else:
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
    Windows: GetProcessTimes creation FILETIME.
    Elsewhere: ``ps -o lstart=`` where available. Returns None when
    undeterminable -- callers treat that as "no identity evidence", never as
    a mismatch.
    """
    if _IS_WINDOWS:
        handle = _k32.OpenProcess(0x1000, False, pid)
        if not handle:
            return None
        try:
            creation, exit_, kernel, user = (
                _FILETIME(), _FILETIME(), _FILETIME(), _FILETIME()
            )
            ok = _k32.GetProcessTimes(
                handle,
                ctypes.byref(creation),
                ctypes.byref(exit_),
                ctypes.byref(kernel),
                ctypes.byref(user),
            )
            if not ok:
                return None
            return f"{creation.dwHighDateTime:08x}-{creation.dwLowDateTime:08x}"
        finally:
            _k32.CloseHandle(handle)
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
