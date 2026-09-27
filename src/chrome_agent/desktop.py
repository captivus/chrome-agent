"""Virtual-desktop helpers (Linux/X11 via xdotool; silently inert elsewhere).

Used to record which desktop each browser window is on when a session is
saved, and to put the windows back when it is restored.

Dynamic workspaces (GNOME's default) shape the restore: the window manager
keeps exactly one empty workspace at the end and deletes any empty one in the
middle. Moving a window onto that trailing workspace creates a new one after
it, but a window cannot be parked on workspace N while N-1 is empty -- the
empty one collapses and the window slides down. So ``move_window`` clamps the
requested index to the last workspace that exists; restoring windows in
ascending desktop order then rebuilds the original layout whenever the
workspaces in between are occupied (e.g. by the terminals you reopened), and
otherwise packs them down while keeping windows that shared a desktop together
and in their original order.
"""

import os
import subprocess


def _xdotool(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["xdotool", *args], capture_output=True, text=True, timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def available() -> bool:
    return bool(os.environ.get("DISPLAY")) and _xdotool("version") is not None


def desktop_count() -> int | None:
    out = _xdotool("get_num_desktops")
    return int(out) if out and out.isdigit() else None


def terminal_desktop() -> int | None:
    """The desktop of the terminal this command runs in, else the current one."""
    window_id = os.environ.get("WINDOWID", "")
    out = _xdotool("get_desktop_for_window", window_id) if window_id else None
    if out is None or not out.lstrip("-").isdigit() or int(out) < 0:
        out = _xdotool("get_desktop")
    return int(out) if out and out.isdigit() else None


def browser_windows(pid: int) -> list[dict]:
    """Top-level windows of the browser process: id, desktop and geometry.

    Chrome creates helper windows that report desktop -1; only windows placed
    on a real desktop are returned.
    """
    out = _xdotool("search", "--pid", str(pid))
    windows = []
    for wid in (out or "").split():
        desktop = _xdotool("get_desktop_for_window", wid)
        if desktop is None or not desktop.isdigit():
            continue
        geometry = _xdotool("getwindowgeometry", "--shell", wid) or ""
        fields = dict(
            line.split("=", 1) for line in geometry.splitlines() if "=" in line
        )
        try:
            windows.append({
                "window": wid,
                "name": _xdotool("getwindowname", wid) or "",
                "desktop": int(desktop),
                "left": int(fields.get("X", 0)),
                "top": int(fields.get("Y", 0)),
                "width": int(fields.get("WIDTH", 0)),
                "height": int(fields.get("HEIGHT", 0)),
            })
        except ValueError:
            continue
    return windows


def match_windows(x_windows: list[dict], cdp_windows: list[dict]) -> dict[int, dict]:
    """Pair CDP window ids with X windows.

    CDP and X11 describe the same window in different id spaces. The X window's
    title is its active tab's title plus the browser name, so a CDP window that
    carries its active tab's ``title`` is paired by that first -- geometry alone
    is ambiguous whenever two windows share bounds (two maximized windows, or a
    window manager that stacks new windows exactly over the last). Remaining
    windows are paired by nearest bounds; frame decorations shift them by a few
    pixels. Returns {cdp windowId: x window}.
    """
    matched: dict[int, dict] = {}
    used: set[str] = set()
    for cdp in cdp_windows:
        title = cdp.get("title")
        if not title:
            continue
        hits = [
            xw for xw in x_windows
            if xw["window"] not in used and xw.get("name", "").startswith(title)
            and xw.get("name", "")[len(title):] in (" - Google Chrome", " - Chromium", "")
        ]
        if len(hits) == 1:
            matched[cdp["windowId"]] = hits[0]
            used.add(hits[0]["window"])

    pairs = []
    for cdp in cdp_windows:
        if cdp["windowId"] in matched:
            continue
        bounds = cdp.get("bounds") or {}
        for xw in x_windows:
            distance = (
                abs(bounds.get("left", 0) - xw["left"])
                + abs(bounds.get("top", 0) - xw["top"])
                + abs(bounds.get("width", 0) - xw["width"])
                + abs(bounds.get("height", 0) - xw["height"])
            )
            pairs.append((distance, cdp["windowId"], xw["window"], xw))
    pairs.sort(key=lambda item: item[0])
    for _, cdp_id, wid, xw in pairs:
        if cdp_id in matched or wid in used:
            continue
        matched[cdp_id] = xw
        used.add(wid)
    return matched


def move_window(window: str, desktop: int) -> int | None:
    """Move a window to ``desktop``, clamped to the last workspace that exists.

    Returns the desktop it ended up on.
    """
    count = desktop_count()
    if count is None:
        return None
    target = max(0, min(desktop, count - 1))
    _xdotool("set_desktop_for_window", window, str(target))
    landed = _xdotool("get_desktop_for_window", window)
    return int(landed) if landed and landed.isdigit() else None


# -- X displays --------------------------------------------------------------
#
# A browser can run on a virtual display (an Xvfb an automation keeps off the
# user's screen). Restoring it onto whatever display the restoring terminal has
# would put it on the user's real desktop, so such a display is recorded and
# restored exactly. The user's own desktop is NOT recorded: its number can
# change across a reboot (GDM may hand out :0 or :1), and a browser that was on
# the user's desktop should follow it.

_VIRTUAL_SERVERS = ("Xvfb", "Xvnc", "Xephyr", "Xdummy")


def process_display(pid: int) -> str | None:
    """The DISPLAY a browser process runs on.

    Chrome rewrites its argv in place, which clobbers /proc/<pid>/environ for
    the main process; its helpers are started with the same environment and
    keep it intact, so they are read first.
    """
    try:
        children = subprocess.run(
            ["ps", "-o", "pid=", "--ppid", str(pid)],
            capture_output=True, text=True, timeout=5,
        ).stdout.split()
    except (OSError, subprocess.TimeoutExpired):
        children = []
    for candidate in [*children, str(pid)]:
        try:
            with open(f"/proc/{candidate}/environ", "rb") as f:
                items = f.read().split(b"\0")
        except OSError:
            continue
        for item in items:
            if item.startswith(b"DISPLAY="):
                return item[8:].decode(errors="replace")
    return None


def virtual_display_server(display: str) -> list[str] | None:
    """The command line of the virtual X server serving ``display``, if any."""
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            with open(f"/proc/{entry}/cmdline", "rb") as f:
                argv = [a.decode(errors="replace") for a in f.read().split(b"\0") if a]
        except OSError:
            continue
        if argv and os.path.basename(argv[0]) in _VIRTUAL_SERVERS and display in argv[1:]:
            return argv
    return None


def display_running(display: str) -> bool:
    """Whether a local X server answers on ``display`` (e.g. ":95")."""
    import socket

    number = display.split(":", 1)[-1].split(".", 1)[0]
    if not number.isdigit():
        return False
    sock = socket.socket(socket.AF_UNIX)
    try:
        sock.settimeout(1)
        sock.connect(f"/tmp/.X11-unix/X{number}")
        return True
    except OSError:
        return False
    finally:
        sock.close()


def start_display(argv: list[str], display: str, timeout: float = 10.0) -> bool:
    """Start a virtual X server from its recorded command line; wait for it."""
    import time

    subprocess.Popen(
        argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True,
    )
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if display_running(display):
            return True
        time.sleep(0.1)
    return False
