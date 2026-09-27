"""Save and restore browser sessions (snapshots).

A snapshot captures everything needed to bring a browser instance back as it
was: its profile (cookies, localStorage, IndexedDB, logins -- minus caches),
its windows and tabs, every cookie as the browser holds it in memory
(including session cookies that never reach disk), the Chrome flags and
environment it was launched with, its name, port, working directory and
virtual desktop, and the ``attach`` observers that were subscribed to it.

Layout, under ``$XDG_DATA_HOME/chrome-agent/snapshots`` (mode 0700)::

    <name>/<stamp>/info.json         plaintext summary (no URLs, no secrets)
    <name>/<stamp>/state.enc         encrypted: tabs, cookies, launch, observers
    <name>/<stamp>/profile.tar.enc   encrypted: the profile directory
    batches/<stamp>.json             which versions one `save --all` wrote

Snapshots are immutable: a restore extracts a copy, so closing the restored
browser (whose supervisor deletes its profile) never touches the snapshot.
Each save writes a new ``<stamp>`` version; "overwrite" means the previous
latest version is removed once the new one is safely written.

Consistency. ``stop=True`` closes the browser cleanly before copying, so every
database is complete on disk -- use it before a reboot. A live save copies the
files while Chrome runs, without taking any lock (most of Chrome's SQLite
databases are held under exclusive locks, and holding a read lock on the rest
could make Chrome's own writes fail); each file is re-read if it changed during
the copy. Cookies do not depend on that copy: they are captured from the
running browser over CDP and set again on restore.
"""

import asyncio
import fnmatch
import io
import json
import os
import re
import shlex
import shutil
import signal
import stat
import subprocess
import tarfile
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from . import desktop as desktops
from .snapcrypto import (
    DecryptingReader,
    EncryptingWriter,
    decrypt_bytes,
    encrypt_bytes,
    get_key,
)

FORMAT = 1
_STAMP_RE = re.compile(r"^\d{8}T\d{6}Z(-\d+)?$")

# Directories that are caches or machine-local runtime state: rebuilt by Chrome,
# large (the on-device AI model alone is ~4 GB), and never part of a login.
_EXCLUDE_DIRS = {
    "Cache", "Code Cache", "GPUCache", "GrShaderCache", "GraphiteDawnCache",
    "ShaderCache", "DawnGraphiteCache", "DawnWebGPUCache", "GPUPersistentCache",
    "OptGuideOnDeviceModel", "component_crx_cache", "extensions_crx_cache",
    "Crashpad", "BrowserMetrics", "CacheStorage", "ScriptCache",
    # Components Chrome's updater downloads on its own (~100 MB even in a fresh
    # profile): ML models, the TTS engine, Safe Browsing and other lists.
    "optimization_guide_model_store", "WasmTtsEngine", "Safe Browsing",
    "OnDeviceHeadSuggestModel", "hyphen-data", "ZxcvbnData",
    # Chrome's own session-restore files. Tabs are restored from the snapshot's
    # tab list instead; left in, a crash-state copy would make Chrome offer to
    # reopen the old tabs on top of the restored ones.
    "Sessions",
}
_EXCLUDE_FILE_PREFIXES = ("Singleton", ".org.chromium.")
_EXCLUDE_FILE_SUFFIXES = (".pma", ".tmp")

# Chrome flags chrome-agent itself supplies on every launch; everything else on
# a browser's command line is what the user asked for and is replayed.
_BASE_FLAGS = (
    "--remote-debugging-port=", "--user-data-dir=", "--no-first-run",
    "--no-default-browser-check", "--password-store=basic",
)


class SnapshotError(Exception):
    """A save or restore that cannot proceed; the message says why."""


# --------------------------------------------------------------------------
# Store layout
# --------------------------------------------------------------------------

def snapshot_root() -> str:
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "share"
    )
    return os.path.join(base, "chrome-agent", "snapshots")


def _ensure_root() -> str:
    root = snapshot_root()
    os.makedirs(root, mode=0o700, exist_ok=True)
    os.chmod(root, 0o700)
    return root


@dataclass
class Version:
    """One saved version of a snapshot."""
    name: str
    stamp: str
    path: str
    info: dict

    @property
    def ref(self) -> str:
        return f"{self.name}@{self.stamp}"


def _new_stamp(name_dir: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate, n = stamp, 1
    while os.path.exists(os.path.join(name_dir, candidate)):
        n += 1
        candidate = f"{stamp}-{n}"
    return candidate


def _read_info(path: str) -> dict | None:
    try:
        with open(os.path.join(path, "info.json")) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def list_versions(pattern: str | None = None) -> list[Version]:
    """Every saved version, oldest first within each name, names sorted.

    ``pattern`` filters by snapshot name (a glob, or a literal name).
    """
    root = snapshot_root()
    if not os.path.isdir(root):
        return []
    versions = []
    for name in sorted(os.listdir(root)):
        name_dir = os.path.join(root, name)
        if name == "batches" or not os.path.isdir(name_dir):
            continue
        if pattern is not None and not fnmatch.fnmatchcase(name, pattern):
            continue
        for stamp in sorted(os.listdir(name_dir)):
            if not _STAMP_RE.match(stamp):
                continue  # in-progress (.tmp-*) or foreign entries
            path = os.path.join(name_dir, stamp)
            info = _read_info(path)
            if info is not None:
                versions.append(Version(name=name, stamp=stamp, path=path, info=info))
    return versions


def latest_version(name: str) -> Version | None:
    versions = [v for v in list_versions() if v.name == name]
    return versions[-1] if versions else None


def resolve_refs(ref: str) -> list[Version]:
    """Resolve ``name``, ``name@stamp`` or a name glob to versions.

    A bare name or glob selects the LATEST version of each matching name; an
    ``@stamp`` selects that exact version.
    """
    name, _, stamp = ref.partition("@")
    versions = list_versions(pattern=name)
    if stamp:
        chosen = [v for v in versions if v.stamp == stamp]
    else:
        latest: dict[str, Version] = {}
        for v in versions:
            latest[v.name] = v
        chosen = list(latest.values())
    if not chosen:
        available = sorted({v.name for v in list_versions()})
        hint = f" Saved: {', '.join(available)}" if available else " No snapshots saved."
        raise SnapshotError(f"No snapshot matches '{ref}'.{hint}")
    return chosen


def read_state(version: Version, key: bytes | None = None) -> dict:
    key = key or get_key(create=False)
    with open(os.path.join(version.path, "state.enc"), "rb") as f:
        return json.loads(decrypt_bytes(f.read(), key))


def remove_version(version: Version) -> None:
    shutil.rmtree(version.path)
    name_dir = os.path.dirname(version.path)
    try:
        os.rmdir(name_dir)  # only succeeds once the last version is gone
    except OSError:
        pass


def parse_age(text: str) -> timedelta:
    match = re.fullmatch(r"(\d+)\s*([mhdw])", text.strip())
    if not match:
        raise SnapshotError(f"invalid age '{text}' (use e.g. 45m, 12h, 30d, 2w)")
    units = {"m": "minutes", "h": "hours", "d": "days", "w": "weeks"}
    return timedelta(**{units[match.group(2)]: int(match.group(1))})


def version_age(version: Version) -> timedelta:
    saved = datetime.fromisoformat(version.info["saved_at"])
    return datetime.now(timezone.utc) - saved


# --------------------------------------------------------------------------
# Batches (save --all) and the ports they reserve
# --------------------------------------------------------------------------

def _batch_dir() -> str:
    return os.path.join(snapshot_root(), "batches")


def write_batch(versions: list[Version]) -> str:
    os.makedirs(_batch_dir(), mode=0o700, exist_ok=True)
    stamp = _new_stamp(_batch_dir())
    path = os.path.join(_batch_dir(), f"{stamp}.json")
    with open(path, "w") as f:
        json.dump({
            "stamp": stamp,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "entries": [{"name": v.name, "stamp": v.stamp} for v in versions],
        }, f, indent=2)
    return path


def latest_batch() -> dict | None:
    directory = _batch_dir()
    if not os.path.isdir(directory):
        return None
    files = sorted(f for f in os.listdir(directory) if f.endswith(".json"))
    for filename in reversed(files):
        try:
            with open(os.path.join(directory, filename)) as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
    return None


def batch_versions(batch: dict) -> list[Version]:
    """The versions a batch names that still exist (some may have been removed)."""
    wanted = {(e["name"], e["stamp"]) for e in batch.get("entries", [])}
    return [v for v in list_versions() if (v.name, v.stamp) in wanted]


def reserved_ports() -> set[int]:
    """Ports the latest `save --all` batch will restore onto, while unclaimed.

    A fresh launch skips these so it cannot take a port a saved session needs.
    A port whose instance name is registered again (restored) is no longer
    reserved -- the live registry entry already holds it. Never raises: this
    runs on every launch and must not be able to break one.
    """
    try:
        batch = latest_batch()
        if not batch:
            return set()
        from .registry import REGISTRY_PATH, _load_registry
        registered = set(_load_registry(REGISTRY_PATH))
        return {
            v.info["port"] for v in batch_versions(batch)
            if v.info.get("port") and v.info.get("instance") not in registered
        }
    except Exception:
        return set()


# --------------------------------------------------------------------------
# Inspecting a running instance from outside it
# --------------------------------------------------------------------------

def _read_argv(pid: int | str) -> list[str]:
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            raw = f.read()
    except OSError:
        return []
    return [part.decode(errors="replace") for part in raw.split(b"\0") if part]


def _chrome_tokens(pid: int | str) -> list[str]:
    # Chrome rewrites its argv into one space-joined string; tokenize on
    # whitespace (see registry._cdp_port_claimants for the same caveat).
    return " ".join(_read_argv(pid)).split()


def _chrome_main_pid(port: int) -> int | None:
    """The browser process (not a renderer/helper) serving CDP ``port``."""
    needle = f"--remote-debugging-port={port}"
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        tokens = _chrome_tokens(entry)
        if needle in tokens and not any(t.startswith("--type=") for t in tokens):
            return int(entry)
    return None


def _effective_profile_dir(tokens: list[str], registered: str) -> str:
    """The profile Chrome actually uses: the LAST --user-data-dir wins.

    A user can pass their own after `--` (`launch -- --user-data-dir=...`), in
    which case the registered session dir sits empty and the real profile is
    elsewhere.
    """
    dirs = [t.split("=", 1)[1] for t in tokens if t.startswith("--user-data-dir=")]
    return dirs[-1] if dirs else registered


def _supervisor_pids(name: str) -> list[tuple[int, list[str]]]:
    found = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        argv = _read_argv(entry)
        if "chrome_agent.supervisor" in argv:
            i = argv.index("chrome_agent.supervisor")
            if len(argv) > i + 2 and argv[i + 2] == name:
                found.append((int(entry), argv))
    return found


def _launch_record(entry: dict, name: str, tokens: list[str], pid: int | None) -> dict:
    """How the instance was launched, from the registry or, for instances
    launched before chrome-agent recorded it, from the live process."""
    record = entry.get("launch")
    if record is None:
        headless = "--headless=new" in tokens or "--headless" in tokens
        chrome_args = [
            t for t in tokens[1:]
            if not t.startswith(_BASE_FLAGS) and t not in ("--headless=new", "--headless")
        ]
        env = {}
        if pid is not None:
            try:
                with open(f"/proc/{pid}/environ", "rb") as f:
                    for item in f.read().split(b"\0"):
                        if item.startswith(b"TZ="):
                            env["TZ"] = item[3:].decode(errors="replace")
            except OSError:
                pass
        supervisors = _supervisor_pids(name)
        border = supervisors[0][1][-1] == "1" if supervisors else not headless
        record = {
            "headless": headless, "chrome_args": chrome_args,
            "env": env, "window_border": border,
        }
    # The profile location is handled separately (profile_override), never
    # replayed as a raw flag.
    return {
        **record,
        "chrome_args": [a for a in record.get("chrome_args", [])
                        if not a.startswith("--user-data-dir=")],
    }


# --------------------------------------------------------------------------
# Live capture over CDP
# --------------------------------------------------------------------------

_COOKIE_PARAM_FIELDS = (
    "name", "value", "domain", "path", "secure", "httpOnly", "sameSite",
    "expires", "priority", "sourceScheme", "sourcePort", "partitionKey",
)


def _cookie_param(cookie: dict) -> dict:
    """A Network.Cookie as read, reshaped into the CookieParam that sets it."""
    param = {k: cookie[k] for k in _COOKIE_PARAM_FIELDS if k in cookie}
    if cookie.get("session") or param.get("expires", -1) < 0:
        param.pop("expires", None)
    return param


def _strip_marker(title: str, name: str) -> str:
    """Drop the window border's title prefix ("🤖 name — ") from a tab title.

    Chrome trims the prefix's trailing space when the page has no title.
    """
    prefix = f"\U0001F916 {name} —"
    return title[len(prefix):].lstrip() if title.startswith(prefix) else title


async def _capture_live(port: int, name: str) -> dict:
    """Windows, tabs (in window order, with the active one marked) and cookies."""
    from .cdp_client import CDPClient, get_ws_url

    async with CDPClient(ws_url=get_ws_url(port=port, target_type="browser")) as cdp:
        targets = (await cdp.send(method="Target.getTargets")).get("targetInfos", [])
        pages = [
            t for t in targets
            if t.get("type") == "page" and not t.get("url", "").startswith("devtools://")
        ]
        windows: dict[int, dict] = {}
        for target in pages:
            try:
                win = await cdp.send(
                    method="Browser.getWindowForTarget",
                    params={"targetId": target["targetId"]},
                )
                window_id, bounds = win["windowId"], win.get("bounds", {})
            except Exception:
                window_id, bounds = 0, {}
            window = windows.setdefault(window_id, {
                "windowId": window_id, "bounds": bounds, "tabs": [],
            })
            active = await _is_visible(cdp, target["targetId"])
            if active:
                # The X window's title is this tab's raw title; used to pair
                # windows with desktops, not stored.
                window["_title"] = target.get("title", "")
            window["tabs"].append({
                "targetId": target["targetId"],
                "url": target.get("url", ""),
                "title": _strip_marker(target.get("title", ""), name),
                "active": active,
            })
        cookies = (await cdp.send(method="Storage.getCookies")).get("cookies", [])

    ordered = [windows[k] for k in sorted(windows)]
    return {"windows": ordered, "cookies": [_cookie_param(c) for c in cookies]}


async def _is_visible(cdp, target_id: str) -> bool:
    """Whether a tab is its window's active tab (the only visible one)."""
    try:
        session = (await cdp.send(
            method="Target.attachToTarget",
            params={"targetId": target_id, "flatten": True},
        ))["sessionId"]
    except Exception:
        return False
    try:
        result = await asyncio.wait_for(cdp.send(
            method="Runtime.evaluate",
            params={"expression": "document.visibilityState", "returnByValue": True},
            session_id=session,
        ), timeout=2.0)
        return result.get("result", {}).get("value") == "visible"
    except Exception:
        return False  # discarded/frozen tabs do not answer; they are not active
    finally:
        try:
            await cdp.send(method="Target.detachFromTarget", params={"sessionId": session})
        except Exception:
            pass


def _capture_desktops(pid: int | None, windows: list[dict]) -> dict:
    """Which virtual desktop each window is on: {windowId: desktop}."""
    if pid is None or not desktops.available():
        return {}
    x_windows = desktops.browser_windows(pid)
    matched = desktops.match_windows(
        x_windows,
        [{"windowId": w["windowId"], "bounds": w["bounds"], "title": w.get("_title")} for w in windows],
    )
    return {str(cdp_id): xw["desktop"] for cdp_id, xw in matched.items()}


# --------------------------------------------------------------------------
# Attach observers
# --------------------------------------------------------------------------

_TARGET_FLAGS = ("--target", "--target-id", "--target-index", "--url")


def _fd_info(pid: int | str, fd: int) -> tuple[str | None, bool]:
    try:
        path = os.readlink(f"/proc/{pid}/fd/{fd}")
    except OSError:
        return None, False
    append = False
    try:
        with open(f"/proc/{pid}/fdinfo/{fd}") as f:
            for line in f:
                if line.startswith("flags:"):
                    append = bool(int(line.split()[1], 8) & os.O_APPEND)
    except (OSError, ValueError, IndexError):
        pass
    return path, append


def _is_attach_argv(argv: list[str]) -> int | None:
    """Index of 'attach' in a chrome-agent attach command line, else None."""
    if "attach" not in argv:
        return None
    i = argv.index("attach")
    launcher = " ".join(argv[:i])
    if "chrome-agent" in launcher or "chrome_agent" in launcher:
        return i
    return None


def _capture_subscriptions(name: str, windows: list[dict]) -> list[dict]:
    """Every `chrome-agent attach` process observing this instance.

    Each is recorded with its events, its tab (as a position in the saved tab
    list, since target ids change on restore), where its output went, and --
    when it runs inside a shell loop that re-attaches on disconnect -- that
    wrapper, which is what should be restarted.
    """
    from .registry import is_pattern

    tabs = [tab for window in windows for tab in window["tabs"]]
    by_sorted_id = sorted(tabs, key=lambda t: t["targetId"])
    found, seen_wrappers = [], set()
    me = os.getpid()
    for entry in os.listdir("/proc"):
        if not entry.isdigit() or int(entry) == me:
            continue
        argv = _read_argv(entry)
        i = _is_attach_argv(argv)
        if i is None or len(argv) <= i + 1:
            continue
        inst = argv[i + 1]
        if not (inst == name or (is_pattern(inst) and fnmatch.fnmatchcase(name, inst))):
            continue
        attach_argv = argv[i:]
        events = [a[1:] for a in attach_argv if a.startswith("+")]

        tab_position, flag, spec = None, None, None
        for j, arg in enumerate(attach_argv):
            if arg in _TARGET_FLAGS and j + 1 < len(attach_argv):
                flag, spec = arg, attach_argv[j + 1]
        if flag in ("--target-index",) or (flag == "--target" and spec.isdigit() and len(spec) < 8):
            k = int(spec) - 1
            if 0 <= k < len(by_sorted_id):
                tab_position = tabs.index(by_sorted_id[k])
        elif flag in ("--target-id", "--target"):
            hits = [t for t in tabs if t["targetId"].upper().startswith(spec.upper())]
            if len(hits) == 1:
                tab_position = tabs.index(hits[0])

        stdout, append = _fd_info(entry, 1)
        stderr, _ = _fd_info(entry, 2)
        try:
            cwd = os.readlink(f"/proc/{entry}/cwd")
        except OSError:
            cwd = None

        wrapper = None
        try:
            with open(f"/proc/{entry}/stat") as f:
                ppid = f.read().rsplit(")", 1)[1].split()[1]
            parent = _read_argv(ppid)
            shell = os.path.basename(parent[0]) if parent else ""
            if shell in ("sh", "bash", "zsh", "dash") and "-c" in parent and any(
                "attach" in part for part in parent
            ):
                wrapper = {"argv": parent, "cwd": os.readlink(f"/proc/{ppid}/cwd")}
        except (OSError, IndexError):
            pass
        # One record per observer: a shell loop is recorded once, and an
        # attach seen twice (e.g. `uv run` and the Python it spawns) once.
        key = tuple(wrapper["argv"]) if wrapper is not None else (tuple(attach_argv), stdout)
        if key in seen_wrappers:
            continue
        seen_wrappers.add(key)

        file_backed = bool(stdout and stdout.startswith("/") and os.path.isfile(stdout))
        found.append({
            "argv": attach_argv,
            "events": events,
            "target_flag": flag,
            "target_spec": spec,
            "tab_position": tab_position,
            "cwd": cwd,
            "stdout": stdout if file_backed else None,
            "stdout_append": append,
            "stderr_to_stdout": file_backed and stderr == stdout,
            "wrapper": wrapper,
        })
    return found


# --------------------------------------------------------------------------
# Profile archive
# --------------------------------------------------------------------------

def _excluded_file(filename: str) -> bool:
    return filename.startswith(_EXCLUDE_FILE_PREFIXES) or filename.endswith(
        _EXCLUDE_FILE_SUFFIXES
    )


def _read_stable(path: str, attempts: int = 3) -> bytes | None:
    """Read a file, re-reading if it changed underneath (live saves)."""
    for _ in range(attempts):
        before = os.stat(path)
        with open(path, "rb") as f:
            data = f.read()
        after = os.stat(path)
        if (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns):
            return data
    return data  # still changing: keep the last read, as a crash would


def write_profile_archive(profile_dir: str, out_path: str, key: bytes) -> dict:
    """Tar the profile (minus caches) through the encryptor into ``out_path``."""
    files = total = 0
    with open(out_path, "wb") as sink:
        writer = EncryptingWriter(sink, key)
        with tarfile.open(fileobj=writer, mode="w|") as tar:
            for root, dirs, filenames in os.walk(profile_dir):
                dirs[:] = sorted(d for d in dirs if d not in _EXCLUDE_DIRS)
                for filename in sorted(filenames):
                    if _excluded_file(filename):
                        continue
                    path = os.path.join(root, filename)
                    try:
                        st = os.lstat(path)
                    except FileNotFoundError:
                        continue  # removed mid-walk (live save)
                    if not stat.S_ISREG(st.st_mode):
                        continue  # sockets, FIFOs and the Singleton* symlinks
                    try:
                        data = _read_stable(path)
                    except FileNotFoundError:
                        continue
                    info = tarfile.TarInfo(os.path.relpath(path, profile_dir))
                    info.size = len(data)
                    info.mtime = int(st.st_mtime)
                    info.mode = 0o600
                    tar.addfile(info, io.BytesIO(data))
                    files += 1
                    total += len(data)
        writer.close()
    return {"files": files, "bytes": total}


def extract_profile_archive(archive_path: str, dest: str, key: bytes) -> None:
    with open(archive_path, "rb") as source:
        reader = io.BufferedReader(DecryptingReader(source, key), buffer_size=1 << 20)
        with tarfile.open(fileobj=reader, mode="r|") as tar:
            if hasattr(tarfile, "data_filter"):
                tar.extractall(dest, filter="data")
            else:  # pragma: no cover - Python < 3.11.4
                tar.extractall(dest)


def _mark_clean_exit(profile_dir: str) -> None:
    """Record a clean exit so Chrome does not offer to 'restore pages'."""
    prefs_path = os.path.join(profile_dir, "Default", "Preferences")
    try:
        with open(prefs_path) as f:
            prefs = json.load(f)
    except (OSError, json.JSONDecodeError):
        return
    profile = prefs.setdefault("profile", {})
    profile["exit_type"] = "Normal"
    profile["exited_cleanly"] = True
    with open(prefs_path, "w") as f:
        json.dump(prefs, f)


# --------------------------------------------------------------------------
# Save
# --------------------------------------------------------------------------

@dataclass
class SavePlan:
    """What saving one instance involves, gathered before anything is written."""
    name: str
    entry: dict
    port: int
    pid: int | None
    profile_dir: str
    registered_dir: str
    working_dir: str | None
    launch: dict


def plan_save(instance_name: str) -> SavePlan:
    from .registry import REGISTRY_PATH, _load_registry, lookup
    from .utils import process_is_ours

    info = lookup(instance_name=instance_name)
    if not info.alive:
        raise SnapshotError(f"{instance_name} is not running; only a live browser can be saved")
    entry = _load_registry(REGISTRY_PATH)[instance_name]
    pid = info.pid if process_is_ours(pid=info.pid, expected_start=info.pid_start) else None
    main_pid = _chrome_main_pid(info.port) or pid
    tokens = _chrome_tokens(main_pid) if main_pid else []
    working_dir = entry.get("working_dir")
    if not working_dir and main_pid:
        try:
            working_dir = os.readlink(f"/proc/{main_pid}/cwd")
        except OSError:
            working_dir = None
    launch = _launch_record(entry, instance_name, tokens, main_pid)

    # The display is read from the live browser every time, never trusted from
    # the launch record: only a virtual display is pinned (see desktop.py).
    launch["env"] = {k: v for k, v in launch.get("env", {}).items() if k != "DISPLAY"}
    launch.pop("virtual_display", None)
    display = desktops.process_display(main_pid) if main_pid and not launch.get("headless") else None
    server = desktops.virtual_display_server(display) if display else None
    if server:
        launch["env"]["DISPLAY"] = display
        launch["virtual_display"] = {"display": display, "server": server}

    return SavePlan(
        name=instance_name,
        entry=entry,
        port=info.port,
        pid=main_pid,
        profile_dir=_effective_profile_dir(tokens, info.user_data_dir),
        registered_dir=info.user_data_dir,
        working_dir=working_dir,
        launch=launch,
    )


def _stop_for_save(plan: SavePlan) -> None:
    """Close the browser cleanly without letting anything delete its profile.

    The per-instance supervisor deletes the profile the moment the browser
    exits, so it is stopped first (this also covers supervisors still running
    an older chrome-agent). Then Browser.close, and wait for every Chrome
    process on the profile to exit so its files are complete on disk.
    """
    from .cdp_client import CDPClient, get_ws_url

    for pid, _ in _supervisor_pids(plan.name):
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 5
    while _supervisor_pids(plan.name) and time.monotonic() < deadline:
        time.sleep(0.1)

    async def _close():
        async with CDPClient(ws_url=get_ws_url(port=plan.port, target_type="browser")) as cdp:
            await cdp.send(method="Browser.close")

    try:
        asyncio.run(_close())
    except Exception:
        if plan.pid is not None:
            try:
                os.kill(plan.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

    needle = f"--user-data-dir={plan.profile_dir}"

    def holders() -> list[int]:
        return [
            int(e) for e in os.listdir("/proc")
            if e.isdigit() and needle in _chrome_tokens(e)
        ]

    deadline = time.monotonic() + 20
    while holders():
        if time.monotonic() > deadline:
            raise SnapshotError(
                f"{plan.name}: Chrome did not exit within 20s after Browser.close; "
                f"profile left in place at {plan.profile_dir}"
            )
        time.sleep(0.2)


def save_instance(
    plan: SavePlan,
    *,
    stop: bool = False,
    snapshot_name: str | None = None,
    replace: Version | None = None,
) -> Version:
    """Save one instance as a new version; with ``replace``, drop that version
    once the new one is written."""
    from .registry import REGISTRY_PATH, _load_registry, _save_registry

    key = get_key(create=True)
    live = asyncio.run(_capture_live(plan.port, plan.name))
    on_virtual = "virtual_display" in plan.launch
    desktop_map = {} if on_virtual else _capture_desktops(plan.pid, live["windows"])
    subscriptions = _capture_subscriptions(plan.name, live["windows"])
    for window in live["windows"]:
        window.pop("_title", None)
    primary = desktop_map.get(str(live["windows"][0]["windowId"])) if live["windows"] else None

    if stop:
        _stop_for_save(plan)

    name = snapshot_name or plan.name
    name_dir = os.path.join(_ensure_root(), name)
    os.makedirs(name_dir, mode=0o700, exist_ok=True)
    stamp = _new_stamp(name_dir)
    staging = os.path.join(name_dir, f".tmp-{stamp}")
    os.makedirs(staging, mode=0o700)
    try:
        archive = write_profile_archive(
            plan.profile_dir, os.path.join(staging, "profile.tar.enc"), key
        )
        saved_at = datetime.now(timezone.utc).isoformat()
        override = plan.profile_dir if plan.profile_dir != plan.registered_dir else None
        state = {
            "format": FORMAT,
            "instance": plan.name,
            "saved_at": saved_at,
            "origin_dir": plan.working_dir,
            "port": plan.port,
            "browser_version": plan.entry.get("browser_version", ""),
            "launch": plan.launch,
            "profile_override": override,
            "windows": live["windows"],
            "cookies": live["cookies"],
            "desktops": desktop_map,
            "subscriptions": subscriptions,
            "mode": "stopped" if stop else "live",
        }
        with open(os.path.join(staging, "state.enc"), "wb") as f:
            f.write(encrypt_bytes(json.dumps(state).encode(), key))
        info = {
            "format": FORMAT,
            "name": name,
            "instance": plan.name,
            "stamp": stamp,
            "saved_at": saved_at,
            "origin_dir": plan.working_dir,
            "port": plan.port,
            "browser_version": state["browser_version"],
            "headless": plan.launch.get("headless", False),
            "desktop": primary,
            "windows": len(live["windows"]),
            "tabs": sum(len(w["tabs"]) for w in live["windows"]),
            "cookies": len(live["cookies"]),
            "subscriptions": len(subscriptions),
            "profile_files": archive["files"],
            "profile_bytes": archive["bytes"],
            "size_bytes": sum(
                os.path.getsize(os.path.join(staging, f)) for f in os.listdir(staging)
            ),
            "mode": state["mode"],
        }
        with open(os.path.join(staging, "info.json"), "w") as f:
            json.dump(info, f, indent=2)
        final = os.path.join(name_dir, stamp)
        os.rename(staging, final)
    except BaseException as exc:
        shutil.rmtree(staging, ignore_errors=True)
        if stop:
            # The browser is closed and its supervisor gone, so the next
            # launch's cleanup would delete the profile as an orphan. Move it
            # out of chrome-agent's session root first.
            rescue = os.path.join(tempfile.gettempdir(), "chrome-agent-rescue", f"{plan.name}-{stamp}")
            os.makedirs(os.path.dirname(rescue), exist_ok=True)
            shutil.move(plan.profile_dir, rescue)
            raise SnapshotError(
                f"{plan.name}: save failed after the browser was stopped ({exc}); "
                f"its profile was moved to {rescue}"
            ) from exc
        raise

    if replace is not None and os.path.isdir(replace.path):
        shutil.rmtree(replace.path)

    if stop:
        # Retire the instance exactly as its supervisor would have, now that
        # the profile is safely in the snapshot.
        registry = _load_registry(REGISTRY_PATH)
        if registry.pop(plan.name, None) is not None:
            _save_registry(registry, REGISTRY_PATH)
        if plan.registered_dir.startswith("/tmp/chrome-agent/"):
            shutil.rmtree(plan.registered_dir, ignore_errors=True)

    return Version(name=name, stamp=stamp, path=final, info=info)


# --------------------------------------------------------------------------
# Restore
# --------------------------------------------------------------------------

def _process_running(argv: list[str]) -> bool:
    for entry in os.listdir("/proc"):
        if entry.isdigit() and _read_argv(entry) == argv:
            return True
    return False


def _attach_running(attach_argv: list[str]) -> bool:
    """Whether an identical `chrome-agent attach ...` is already running,
    however it was invoked (installed script, python -m, uv run)."""
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        argv = _read_argv(entry)
        i = _is_attach_argv(argv)
        if i is not None and argv[i:] == attach_argv:
            return True
    return False


def _rewrite_target(argv: list[str], flag: str, spec: str, new_id: str) -> list[str]:
    out, i = [], 0
    while i < len(argv):
        if argv[i] == flag and i + 1 < len(argv) and argv[i + 1] == spec:
            out += ["--target-id", new_id]
            i += 2
        else:
            out.append(argv[i])
            i += 1
    return out


def _restore_subscriptions(
    subscriptions: list[dict], id_map: dict[int, str], reattach: bool,
) -> list[dict]:
    """Restart file-backed observers; hand back the command for the rest."""
    report = []
    for sub in subscriptions:
        new_id = id_map.get(sub["tab_position"]) if sub["tab_position"] is not None else None
        remap = new_id is not None and sub["target_flag"] in ("--target", "--target-id", "--target-index")
        argv = sub["argv"]
        if remap:
            argv = _rewrite_target(argv, sub["target_flag"], sub["target_spec"], new_id)
        command = shlex.join(["chrome-agent", *argv])

        wrapper = sub.get("wrapper")
        if wrapper is not None:
            wargv = list(wrapper["argv"])
            if remap:
                old = f"{sub['target_flag']} {sub['target_spec']}"
                wargv = [part.replace(old, f"--target-id {new_id}") for part in wargv]
            command = shlex.join(wargv)
            if not sub.get("stdout"):
                # The loop fed a pipe (e.g. an agent reading the stream); a
                # restarted copy would have no reader. Hand the command back.
                report.append({"command": command, "status": "run this to resume"})
            elif not reattach:
                report.append({"command": command, "status": "not restarted (--no-reattach)"})
            elif _process_running(wargv):
                report.append({"command": command, "status": "already running"})
            else:
                subprocess.Popen(
                    wargv, cwd=wrapper.get("cwd") or None,
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, start_new_session=True,
                )
                report.append({"command": command, "status": "restarted"})
            continue

        if sub.get("stdout") and reattach:
            full = [shutil.which("chrome-agent") or "chrome-agent", *argv]
            if _attach_running(argv):
                report.append({"command": command, "status": "already running"})
                continue
            out = open(sub["stdout"], "ab" if sub.get("stdout_append") else "wb")
            subprocess.Popen(
                full, cwd=sub.get("cwd") or None, stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=out if sub.get("stderr_to_stdout") else subprocess.DEVNULL,
                start_new_session=True,
            )
            out.close()
            report.append({"command": f"{command} >> {shlex.quote(sub['stdout'])}", "status": "restarted"})
        else:
            report.append({
                "command": command + (f" >> {shlex.quote(sub['stdout'])}" if sub.get("stdout") else ""),
                "status": "run this to resume" if not sub.get("stdout") else "not restarted (--no-reattach)",
            })
    return report


async def _new_x_window(pid: int | None, known: set[str]) -> str | None:
    """The browser's X window that appeared since ``known`` was taken."""
    if pid is None or not desktops.available():
        return None
    for _ in range(30):
        for xw in desktops.browser_windows(pid):
            if xw["window"] not in known:
                return xw["window"]
        await asyncio.sleep(0.1)
    return None


async def _restore_tabs(
    port: int, state: dict, headless: bool, pid: int | None = None,
) -> tuple[dict[int, str], list[dict], int]:
    """Recreate windows and tabs, set cookies first so pages load logged in.

    Returns ({saved tab position: new targetId}, [placed windows], cookies rejected).
    """
    from .cdp_client import CDPClient, get_ws_url

    id_map: dict[int, str] = {}
    placed: list[dict] = []
    async with CDPClient(ws_url=get_ws_url(port=port, target_type="browser")) as cdp:
        cookie_failures = 0
        if state.get("cookies"):
            try:
                await cdp.send(method="Storage.setCookies", params={"cookies": state["cookies"]})
            except Exception:
                # One cookie Chrome rejects fails the whole batch; fall back to
                # setting them one at a time so the rest still land.
                for cookie in state["cookies"]:
                    try:
                        await cdp.send(method="Storage.setCookies", params={"cookies": [cookie]})
                    except Exception:
                        cookie_failures += 1

        initial = [
            t["targetId"]
            for t in (await cdp.send(method="Target.getTargets"))["targetInfos"]
            if t.get("type") == "page"
        ]

        track = not headless and pid is not None and desktops.available()
        known = {xw["window"] for xw in desktops.browser_windows(pid)} if track else set()
        position = 0
        for w, window in enumerate(state.get("windows", [])):
            new_ids = []
            x_window = None
            for t, tab in enumerate(window["tabs"]):
                params: dict = {"url": tab["url"] or "about:blank"}
                if w > 0 and t == 0 and not headless:
                    params["newWindow"] = True
                    bounds = window.get("bounds") or {}
                    if bounds.get("windowState", "normal") == "normal":
                        for k in ("left", "top", "width", "height"):
                            if k in bounds:
                                params[k] = bounds[k]
                else:
                    params["background"] = True
                target_id = (await cdp.send(method="Target.createTarget", params=params))["targetId"]
                if track and params.get("newWindow"):
                    # Pair this Chrome window with its X window as it appears:
                    # exact, where matching afterwards could only guess.
                    x_window = await _new_x_window(pid, known)
                    if x_window:
                        known.add(x_window)
                new_ids.append(target_id)
                id_map[position] = target_id
                position += 1
            if not new_ids:
                continue
            if w == 0:
                for target_id in initial:
                    try:
                        await cdp.send(method="Target.closeTarget", params={"targetId": target_id})
                    except Exception:
                        pass
            active = next(
                (new_ids[i] for i, tab in enumerate(window["tabs"]) if tab.get("active")),
                new_ids[0],
            )
            window_id = None
            if not headless:
                try:
                    found = await cdp.send(method="Browser.getWindowForTarget", params={"targetId": active})
                    window_id = found["windowId"]
                    bounds = dict(window.get("bounds") or {})
                    state_name = bounds.pop("windowState", "normal")
                    if state_name == "normal" and bounds:
                        await cdp.send(method="Browser.setWindowBounds", params={
                            "windowId": window_id, "bounds": {**bounds, "windowState": "normal"},
                        })
                    elif state_name != "normal":
                        await cdp.send(method="Browser.setWindowBounds", params={
                            "windowId": window_id, "bounds": {"windowState": state_name},
                        })
                except Exception:
                    pass
            try:
                await cdp.send(method="Target.activateTarget", params={"targetId": active})
            except Exception:
                pass
            placed.append({
                "windowId": window_id,
                "saved_windowId": window["windowId"],
                "x_window": x_window,
            })
    return id_map, placed, cookie_failures


def check_restorable(
    version: Version, state: dict, any_port: bool, replace_profile: bool = False,
    start_display: bool = False,
) -> str | None:
    """Why this version cannot be restored right now, or None."""
    from .registry import InstanceNotFoundError, _port_is_listening, lookup

    instance = state["instance"]
    try:
        if lookup(instance_name=instance).alive:
            return f"{instance} is already running (stop it first, or it was already restored)"
    except InstanceNotFoundError:
        pass
    if not any_port and _port_is_listening(state["port"]):
        return (
            f"port {state['port']} is in use by another process "
            f"(pass --any-port to restore {instance} on a different port)"
        )
    virtual = state["launch"].get("virtual_display")
    if virtual and not start_display and not desktops.display_running(virtual["display"]):
        return (
            f"it ran on virtual display {virtual['display']}, which is not running "
            f"(pass --start-display to start it with: {shlex.join(virtual['server'])})"
        )
    override = state.get("profile_override")
    if override and os.path.isdir(override) and os.listdir(override) and not replace_profile:
        return (
            f"its profile directory {override} already exists and is not empty "
            f"(pass --replace-profile to move it aside and restore the snapshot)"
        )
    return None


def restore_version(
    version: Version,
    *,
    any_port: bool = False,
    desktop_mode: str = "terminal",
    reattach: bool = True,
    replace_profile: bool = False,
    start_display: bool = False,
    key: bytes | None = None,
) -> dict:
    """Bring a saved version back as a running instance. Returns a report."""
    from .launcher import _SESSION_ROOT, launch_browser
    from .registry import _port_is_listening

    key = key or get_key(create=False)
    state = read_state(version, key)
    problem = check_restorable(version, state, any_port, replace_profile, start_display)
    if problem:
        raise SnapshotError(f"cannot restore {version.ref}: {problem}")

    warnings = []
    launch = state["launch"]
    headless = launch.get("headless", False)
    virtual = launch.get("virtual_display")
    if virtual and not desktops.display_running(virtual["display"]):
        if not desktops.start_display(virtual["server"], virtual["display"]):
            raise SnapshotError(
                f"cannot restore {version.ref}: started {shlex.join(virtual['server'])} "
                f"but display {virtual['display']} did not come up"
            )
        warnings.append(f"started virtual display {virtual['display']}")
    port = state["port"]
    if _port_is_listening(port):
        port = None  # --any-port: allocate a fresh one
        warnings.append(f"port {state['port']} was in use; restored on a new port")

    from .launcher import find_chrome_binary
    installed = _installed_chrome_version(find_chrome_binary())
    saved_major = _major(state.get("browser_version", ""))
    if installed and saved_major and _major(installed) < saved_major:
        warnings.append(
            f"saved with {state['browser_version']} but {installed} is installed; "
            f"an older Chrome may refuse a newer profile"
        )

    override = state.get("profile_override")
    os.makedirs(_SESSION_ROOT, exist_ok=True)
    if override:
        if os.path.isdir(override) and os.listdir(override):
            # --replace-profile: never delete a profile the user pointed
            # Chrome at; move it aside where it can be recovered.
            aside = f"{override.rstrip('/')}.pre-restore-{datetime.now().strftime('%Y%m%dT%H%M%S')}"
            os.rename(override, aside)
            warnings.append(f"existing profile moved aside to {aside}")
        os.makedirs(override, exist_ok=True)
        profile_dir = override
    else:
        profile_dir = tempfile.mkdtemp(prefix="session-", dir=_SESSION_ROOT)
    try:
        extract_profile_archive(os.path.join(version.path, "profile.tar.enc"), profile_dir, key)
    except BaseException:
        # A corrupt or truncated archive is only detected at its end, after
        # most files are written; leave no half-restored profile behind.
        shutil.rmtree(profile_dir, ignore_errors=True)
        raise
    _mark_clean_exit(profile_dir)

    working_dir = state.get("origin_dir")
    if not working_dir or not os.path.isdir(working_dir):
        warnings.append(f"original directory {working_dir} is gone; using the current one")
        working_dir = os.getcwd()

    windows = state.get("windows", [])
    desktop_map = state.get("desktops", {})
    primary_desktop = (
        desktop_map.get(str(windows[0]["windowId"])) if windows else None
    )
    target_desktop = primary_desktop if desktop_mode == "saved" else None

    extra_args = list(launch.get("chrome_args", []))
    if override:
        extra_args.append(f"--user-data-dir={override}")
    info = asyncio.run(launch_browser(
        port_override=port,
        headless=headless,
        working_dir=working_dir,
        extra_args=extra_args,
        window_border=launch.get("window_border", True),
        profile_dir=None if override else profile_dir,
        instance_name=state["instance"],
        desktop=target_desktop,
        env_overrides=launch.get("env") or None,
    ))

    id_map, placed, cookie_failures = asyncio.run(_restore_tabs(info.port, state, headless, info.pid))
    if cookie_failures:
        warnings.append(f"{cookie_failures} cookie(s) were rejected by Chrome and not restored")

    # Windows beyond the first open wherever the window manager puts them.
    # Send each to its saved desktop (mode "saved") or alongside the first
    # window (mode "terminal"), keeping windows that shared a desktop together.
    if not headless and not virtual and len(placed) > 1 and desktops.available():
        # The first window is the only one launch placed; it is on "base".
        others = {p["x_window"] for p in placed[1:] if p["x_window"]}
        firsts = [xw for xw in desktops.browser_windows(info.pid) if xw["window"] not in others]
        base = firsts[0]["desktop"] if firsts else None
        for p in placed[1:]:
            if not p["x_window"]:
                continue
            saved = desktop_map.get(str(p["saved_windowId"]))
            if desktop_mode == "saved" and saved is not None:
                desktops.move_window(p["x_window"], saved)
            elif base is not None:
                offset = 0 if saved is None or primary_desktop is None else saved - primary_desktop
                desktops.move_window(p["x_window"], base + offset)

    subscriptions = _restore_subscriptions(state.get("subscriptions", []), id_map, reattach)

    return {
        "snapshot": version.ref,
        "name": info.name,
        "port": info.port,
        "pid": info.pid,
        "tabs": len(id_map),
        "windows": len(placed),
        "cookies": len(state.get("cookies", [])),
        "display": virtual["display"] if virtual else None,
        "subscriptions": subscriptions,
        "warnings": warnings,
    }


def _major(version: str) -> int | None:
    match = re.search(r"(\d+)\.", version or "")
    return int(match.group(1)) if match else None


def _installed_chrome_version(binary: str | None) -> str | None:
    if not binary:
        return None
    try:
        out = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=10)
        match = re.search(r"(\d+\.\d+\.\d+\.\d+)", out.stdout)
        return match.group(1) if match else None
    except Exception:
        return None
