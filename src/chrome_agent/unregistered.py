"""Browsers chrome-agent launched that are no longer in its registry.

A browser drops out of the registry when its entry is lost: before the registry
lock, two concurrent writers lost each other's changes, and a supervisor that
outlived its own browser could retire a newer instance that reused its name.
An unregistered browser is invisible to ``status``, cannot be addressed by
name, and gets no owner check, so it runs until someone kills it. On
2026-11-21 nine such browsers had been running overnight; one burned a CPU
core.

They are found by their profile: chrome-agent gives every browser it launches
a profile directory ``/tmp/chrome-agent/session-*``, and the main Chrome
process carries it as ``--user-data-dir``. A browser using such a profile
that no registry entry names is unregistered. ``status`` reports them;
``cleanup --unregistered`` stops them, each verified again by pid, start time
and profile immediately before it is signalled -- never by name or pattern.

Caveat: a test or tool that keeps its own registry file (``registry_path``)
still puts its profiles under ``/tmp/chrome-agent``, so its browsers read as
unregistered here. That is why stopping is only ever an explicit request.
"""

from __future__ import annotations

import os
import shutil
import signal
import time
from dataclasses import asdict, dataclass, field

from .utils import process_is_ours, process_start_time

SESSION_ROOT = "/tmp/chrome-agent"

# A launch registers its browser a moment after Chrome starts (after the
# launch lock is released), so a very young browser may simply not be
# registered YET. Anything younger than this is left out.
MIN_AGE_SECONDS = 60.0


@dataclass
class UnregisteredBrowser:
    pid: int
    pid_start: str | None
    user_data_dir: str
    port: int | None
    started: float | None  # epoch seconds
    profile_exists: bool
    supervisors: list[dict] = field(default_factory=list)  # [{"pid", "name", "port"}]

    def to_dict(self) -> dict:
        return asdict(self)


def _tokens(pid: str) -> list[str]:
    with open(f"/proc/{pid}/cmdline", "rb") as f:
        return f.read().replace(b"\0", b" ").decode(errors="replace").split()


def _argv(pid: str) -> list[str]:
    with open(f"/proc/{pid}/cmdline", "rb") as f:
        return [a.decode(errors="replace") for a in f.read().split(b"\0") if a]


def _process_started(pid: int) -> float | None:
    """Epoch seconds at which ``pid`` started (Linux), else None."""
    try:
        with open(f"/proc/{pid}/stat") as f:
            ticks = int(f.read().rsplit(")", 1)[1].split()[19])
        with open("/proc/stat") as f:
            btime = next(int(line.split()[1]) for line in f if line.startswith("btime"))
        return btime + ticks / os.sysconf("SC_CLK_TCK")
    except (OSError, ValueError, StopIteration, IndexError):
        return None


def _supervisor_processes() -> list[dict]:
    """Every chrome-agent supervisor process: pid, port, name, profile (if passed)."""
    found = []
    try:
        entries = os.listdir("/proc")
    except OSError:
        return found
    for entry in entries:
        if not entry.isdigit():
            continue
        try:
            argv = _argv(entry)
        except OSError:
            continue
        if "chrome_agent.supervisor" not in argv:
            continue
        i = argv.index("chrome_agent.supervisor")
        rest = argv[i + 1:]
        if len(rest) < 4 or not rest[0].isdigit():
            continue
        found.append({
            "pid": int(entry), "port": int(rest[0]), "name": rest[1],
            "registry": rest[2], "user_data_dir": rest[4] if len(rest) > 4 else None,
        })
    return found


def _registered(registry_paths: list[str]) -> tuple[set[str], dict[str, int]]:
    """Profile dirs named by the registries, and their name -> port map."""
    from .registry import _load_registry

    dirs: set[str] = set()
    ports: dict[str, int] = {}
    for path in registry_paths:
        for name, entry in _load_registry(path).items():
            if entry.get("user_data_dir"):
                dirs.add(entry["user_data_dir"])
            ports[f"{path}\0{name}"] = entry.get("port")
    return dirs, ports


def find_unregistered(
    registry_paths: list[str] | None = None,
    *,
    session_root: str = SESSION_ROOT,
    min_age: float = MIN_AGE_SECONDS,
) -> list[UnregisteredBrowser]:
    """Live browsers on chrome-agent profiles that no registry entry names."""
    from .registry import REGISTRY_PATH

    registry_paths = registry_paths or [REGISTRY_PATH]
    registered_dirs, registered_ports = _registered(registry_paths)
    prefix = os.path.join(session_root, "session-")
    supervisors = _supervisor_processes()
    now = time.time()
    found = []
    try:
        entries = os.listdir("/proc")
    except OSError:
        return found
    for entry in entries:
        if not entry.isdigit():
            continue
        try:
            tokens = _tokens(entry)
        except OSError:
            continue
        if any(t.startswith("--type=") for t in tokens):
            continue  # a renderer/helper, not the browser process
        udd = next((t.split("=", 1)[1] for t in tokens if t.startswith("--user-data-dir=")), None)
        if udd is None or not udd.startswith(prefix) or udd in registered_dirs:
            continue
        pid = int(entry)
        if not process_is_ours(pid=pid):
            continue
        started = _process_started(pid)
        if started is not None and now - started < min_age:
            continue
        port_tok = next((t.split("=", 1)[1] for t in tokens if t.startswith("--remote-debugging-port=")), None)
        port = int(port_tok) if port_tok and port_tok.isdigit() else None
        found.append(UnregisteredBrowser(
            pid=pid, pid_start=process_start_time(pid=pid), user_data_dir=udd, port=port,
            started=started, profile_exists=os.path.isdir(udd),
            supervisors=[
                {"pid": s["pid"], "name": s["name"], "port": s["port"]}
                for s in supervisors
                if _supervises(s, udd, port, registered_ports)
            ],
        ))
    found.sort(key=lambda b: (b.port or 0, b.pid))
    return found


def _supervises(sup: dict, udd: str, port: int | None, registered_ports: dict[str, int]) -> bool:
    """Whether supervisor ``sup`` is (or would act as) this browser's.

    A supervisor told its profile is matched by it. A legacy one (started by an
    older chrome-agent, told only port and name) is counted when it watches
    this port and its name is not a registered instance on that same port --
    such a supervisor would, once this browser closes, retire whatever entry
    then carries its name.
    """
    if sup["user_data_dir"] is not None:
        return sup["user_data_dir"] == udd
    if port is None or sup["port"] != port:
        return False
    return registered_ports.get(f"{sup['registry']}\0{sup['name']}") != port


def _still_same(browser: UnregisteredBrowser) -> bool:
    """Re-verify, immediately before signalling, that the pid is that browser."""
    if not process_is_ours(pid=browser.pid, expected_start=browser.pid_start):
        return False
    try:
        tokens = _tokens(str(browser.pid))
    except OSError:
        return False
    return f"--user-data-dir={browser.user_data_dir}" in tokens


def _terminate(pid: int, still_ours, timeout: float = 5.0) -> bool:
    """SIGTERM ``pid`` and wait for it; True once it is gone."""
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return True
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not still_ours():
            return True
        time.sleep(0.1)
    return not still_ours()


def stop_unregistered(browser: UnregisteredBrowser, *, session_root: str = SESSION_ROOT) -> str:
    """Stop one unregistered browser, its stale supervisors first.

    The supervisors go first because a legacy one retires by NAME when its
    browser closes, which could remove a live instance that now carries that
    name. Every process is re-verified (pid + start time + argv) right before
    it is signalled. The profile directory is removed once the browser is gone.
    """
    if not _still_same(browser):
        return f"pid {browser.pid} is no longer the browser on {browser.user_data_dir}; left alone"
    notes = []
    for sup in browser.supervisors:
        sup_start = process_start_time(pid=sup["pid"])

        def sup_alive(pid=sup["pid"], start=sup_start, port=sup["port"], name=sup["name"]):
            if not process_is_ours(pid=pid, expected_start=start):
                return False
            try:
                argv = _argv(str(pid))
            except OSError:
                return False
            return "chrome_agent.supervisor" in argv and str(port) in argv and name in argv

        if sup_alive():
            _terminate(sup["pid"], sup_alive)
            notes.append(f"supervisor {sup['pid']} ({sup['name']})")

    def browser_alive():
        return _still_same(browser)

    gone = _terminate(browser.pid, browser_alive)
    where = f"port {browser.port}" if browser.port else "no port"
    if not gone:
        return f"browser pid {browser.pid} ({where}) did not exit after SIGTERM; left running"
    if browser.user_data_dir.startswith(os.path.join(session_root, "session-")):
        shutil.rmtree(browser.user_data_dir, ignore_errors=True)
    stopped = ", ".join([f"browser {browser.pid} ({where})"] + notes)
    return f"Stopped {stopped}; removed {browser.user_data_dir}"


def describe(browser: UnregisteredBrowser) -> str:
    started = (
        time.strftime("%Y-%m-%d %H:%M", time.localtime(browser.started))
        if browser.started else "?"
    )
    sups = ", ".join(f"{s['name']} (pid {s['pid']})" for s in browser.supervisors) or "none"
    gone = "" if browser.profile_exists else " (profile dir deleted)"
    return (
        f"pid {browser.pid}  port {browser.port or '-'}  started {started}  "
        f"profile {browser.user_data_dir}{gone}  supervisor: {sups}"
    )
