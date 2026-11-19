"""Virtual X displays that chrome-agent starts, shares and removes itself.

A headed browser opening on the user's desktop takes focus from them, and
headless is no substitute (sites detect it). So an agent's browser goes on a
virtual X display: a real headed Chrome, drawn into an Xvfb nobody looks at.

chrome-agent manages those displays itself:

- **Find or start.** ``acquire_display`` reuses a display chrome-agent already
  manages, or starts a new Xvfb on the first free number from ``FIRST_DISPLAY``
  up (clear of the :9x numbers people pick by hand). A file lock serializes
  concurrent launches so two agents do not race for one number.
- **Shared.** Every agent browser goes on the same display while it is up, so
  one Xvfb serves many instances.
- **Removed with its last browser.** Each managed display has a small detached
  *keeper* process (``python -m chrome_agent.virtual_display``). It checks
  every few seconds whether any process still runs with ``DISPLAY`` set to
  that display (Chrome's helpers carry it, so this sees a browser however it
  was stopped -- ``stop``, a closed window, a crash, a kill) and stops the
  Xvfb once nothing has used it for two checks in a row.

Xvfb's own ``-terminate`` (exit when the last client leaves) looks like the
obvious tool and is unusable: the server exits on *any* connection closing,
including a bare socket probe (``desktop.display_running``) and any brief gap
before a browser connects.

A launch *claims* the display (touches ``<n>.claim``) before starting Chrome;
the keeper leaves a display alone for ``CLAIM_GRACE`` seconds after a claim, so
a browser that is still starting is never pulled out from under. Each managed
display is recorded in ``<n>.json`` (Xvfb's pid, start time and command line),
which is how ``status``, ``save`` and ``cleanup`` recognize one, and how
``cleanup`` re-arms a keeper that was killed.
"""

import fcntl
import json
import os
import shutil
import signal
import subprocess
import sys
import time

from .utils import process_is_ours, process_start_time

# Outside /tmp/chrome-agent on purpose: every launch sweeps that directory for
# orphaned profiles, and an older chrome-agent would take this for one.
# CHROME_AGENT_DISPLAY_DIR moves it (tests use it to keep their displays apart
# from real ones; the keeper inherits it).
STATE_DIR = os.environ.get("CHROME_AGENT_DISPLAY_DIR") or "/tmp/chrome-agent-displays"
FIRST_DISPLAY = 100
LAST_DISPLAY = 199
SCREEN = "1920x1080x24"
CHECK_INTERVAL = 2.0
CLAIM_GRACE = 30.0
START_TIMEOUT = 10.0


class VirtualDisplayError(RuntimeError):
    """A virtual display could not be provided."""


INSTALL_HINT = (
    "an agent's browser goes on a virtual X display, which needs Xvfb, and "
    "Xvfb is not installed (Debian/Ubuntu: sudo apt install xvfb; Fedora: "
    "sudo dnf install xorg-x11-server-Xvfb; Arch: sudo pacman -S "
    "xorg-server-xvfb). Or launch with --display desktop to use your screen, "
    "or --headless for no window at all"
)


def _state_dir() -> str:
    os.makedirs(STATE_DIR, exist_ok=True)
    return STATE_DIR


def _number(display: str) -> str:
    return display.split(":", 1)[-1].split(".", 1)[0]


def _record_path(display: str) -> str:
    return os.path.join(STATE_DIR, f"{_number(display)}.json")


def _claim_path(display: str) -> str:
    return os.path.join(STATE_DIR, f"{_number(display)}.claim")


def _read_record(display: str) -> dict | None:
    try:
        with open(_record_path(display)) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _server_alive(record: dict) -> bool:
    if not process_is_ours(pid=record["pid"], expected_start=record.get("start")):
        return False
    # An exited Xvfb whose parent (a long-running launcher, e.g. a test run)
    # has not reaped it still answers signal 0; it is no server.
    try:
        with open(f"/proc/{record['pid']}/stat") as f:
            return f.read().rsplit(")", 1)[1].split()[0] != "Z"
    except (OSError, IndexError):
        return False


def managed_displays() -> dict[str, dict]:
    """Every live display chrome-agent manages: {":100": its record}."""
    found = {}
    try:
        names = os.listdir(STATE_DIR)
    except OSError:
        return found
    for name in names:
        if not name.endswith(".json"):
            continue
        display = f":{name[:-5]}"
        record = _read_record(display)
        if record and _server_alive(record):
            found[display] = record
    return found


def is_managed(display: str | None) -> bool:
    if not display:
        return False
    record = _read_record(display)
    return bool(record) and _server_alive(record)


def claim(display: str) -> None:
    """Tell the keeper a browser is about to start on ``display``."""
    path = _claim_path(display)
    with open(path, "a"):
        pass
    os.utime(path)


def _keeper_pids(display: str) -> list[int]:
    wanted = ["-m", "chrome_agent.virtual_display", f":{_number(display)}"]
    pids = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            with open(f"/proc/{entry}/cmdline", "rb") as f:
                argv = [a.decode(errors="replace") for a in f.read().split(b"\0") if a]
        except OSError:
            continue
        if argv[1:4] == wanted:
            pids.append(int(entry))
    return pids


def _spawn_keeper(display: str) -> None:
    subprocess.Popen(
        [sys.executable, "-m", "chrome_agent.virtual_display", display],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True,
    )


def _number_free(n: int) -> bool:
    """Nothing answers on :n. A socket or lock file left by a server that was
    killed (one in a sandbox dies with it) does not count: Xvfb clears stale
    ones itself, and refuses a lock a live server holds -- ``_start`` then
    moves on to the next number."""
    from .desktop import display_running

    return not display_running(f":{n}")


def _start(n: int) -> dict | None:
    """Start an Xvfb on :n and wait for it. Returns its record, or None if
    it did not come up (the number was taken in the meantime)."""
    from .desktop import display_running

    display = f":{n}"
    argv = [shutil.which("Xvfb") or "Xvfb", display, "-screen", "0", SCREEN, "-nolisten", "tcp"]
    log = open(os.path.join(_state_dir(), f"{n}.log"), "w")
    try:
        process = subprocess.Popen(
            argv, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
            start_new_session=True,
        )
    finally:
        log.close()
    record = {
        "display": display, "pid": process.pid,
        "start": process_start_time(pid=process.pid), "argv": argv,
        "started": time.time(),
    }
    deadline = time.monotonic() + START_TIMEOUT
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return None
        if display_running(display):
            return record
        time.sleep(0.05)
    process.kill()
    return None


def acquire_display() -> str:
    """A managed virtual display for a browser about to launch: an existing
    one if chrome-agent already runs one, else a new Xvfb. The display is
    claimed before it is returned (see the module docstring)."""
    if not sys.platform.startswith("linux"):
        raise VirtualDisplayError(
            "virtual displays need X11 (Linux); on this platform launch with "
            "--display desktop or --headless"
        )
    if shutil.which("Xvfb") is None:
        raise VirtualDisplayError(INSTALL_HINT)

    with open(os.path.join(_state_dir(), ".lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for display in sorted(managed_displays(), key=lambda d: int(_number(d))):
            claim(display)
            if not _keeper_pids(display):
                _spawn_keeper(display)
            return display
        for n in range(FIRST_DISPLAY, LAST_DISPLAY + 1):
            if not _number_free(n):
                continue
            record = _start(n)
            if record is None:
                continue
            display = record["display"]
            with open(_record_path(display), "w") as f:
                json.dump(record, f)
            claim(display)
            _spawn_keeper(display)
            return display
    raise VirtualDisplayError(
        f"could not start Xvfb on any display :{FIRST_DISPLAY}-:{LAST_DISPLAY} "
        f"(see {STATE_DIR}/<n>.log)"
    )


def display_users(display: str, exclude: set[int] = frozenset()) -> list[int]:
    """PIDs of our processes running with DISPLAY set to ``display``."""
    number = _number(display)
    wanted = {f"DISPLAY=:{number}".encode(), f"DISPLAY=:{number}.0".encode()}
    users = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit() or int(entry) in exclude:
            continue
        try:
            with open(f"/proc/{entry}/environ", "rb") as f:
                items = f.read().split(b"\0")
        except OSError:
            continue
        if any(item in wanted for item in items):
            users.append(int(entry))
    return users


def _claimed_recently(display: str) -> bool:
    try:
        return time.time() - os.path.getmtime(_claim_path(display)) < CLAIM_GRACE
    except OSError:
        return False


def _forget(display: str) -> None:
    for path in (_record_path(display), _claim_path(display),
                 os.path.join(STATE_DIR, f"{_number(display)}.log")):
        try:
            os.remove(path)
        except OSError:
            pass


def stop_display(display: str) -> bool:
    """Stop a managed display's Xvfb (verified by pid and start time)."""
    record = _read_record(display)
    if not record:
        return False
    if _server_alive(record):
        try:
            os.kill(record["pid"], signal.SIGTERM)
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + 5
        while _server_alive(record) and time.monotonic() < deadline:
            time.sleep(0.1)
        if _server_alive(record):
            os.kill(record["pid"], signal.SIGKILL)
    _forget(display)
    return True


def keep(display: str) -> None:
    """The keeper loop: stop the display once nothing has used it for two
    checks in a row, and no launch has claimed it recently."""
    idle_checks = 0
    while True:
        record = _read_record(display)
        if not record or not _server_alive(record):
            _forget(display)
            return
        busy = _claimed_recently(display) or display_users(
            display, exclude={os.getpid(), record["pid"]}
        )
        idle_checks = 0 if busy else idle_checks + 1
        if idle_checks >= 2:
            with open(os.path.join(_state_dir(), ".lock"), "w") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                # Re-check under the lock: a launch may have just claimed it.
                if not _claimed_recently(display):
                    stop_display(display)
                    return
            idle_checks = 0
        time.sleep(CHECK_INTERVAL)


def rearm_keepers() -> list[str]:
    """Start a keeper for every managed display that has lost its own (the
    keeper was killed), and drop the records of displays that are gone (one
    started inside a sandbox dies with it, keeper and all). Returns the
    re-armed displays. Used by ``cleanup``."""
    from .desktop import display_running

    try:
        names = os.listdir(STATE_DIR)
    except OSError:
        names = []
    for name in names:
        if name.endswith(".json"):
            display = f":{name[:-5]}"
            record = _read_record(display)
            if not (record and _server_alive(record)) and not display_running(display):
                _forget(display)
    rearmed = []
    for display in managed_displays():
        if not _keeper_pids(display):
            _spawn_keeper(display)
            rearmed.append(display)
    return rearmed


def main() -> None:
    """Entry point: ``python -m chrome_agent.virtual_display :N``."""
    if len(sys.argv) != 2:
        print("usage: python -m chrome_agent.virtual_display :N", file=sys.stderr)
        sys.exit(2)
    try:
        keep(sys.argv[1])
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
