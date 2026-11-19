"""Who launched a browser, and whether they are still there.

An agent's browser should not outlive the agent session that launched it: a
forgotten instance keeps a full Chrome running -- in practice for days, at up
to a whole CPU core. So a launch made from inside an agent session records
that session's process as the instance's **owner**, and the per-instance
supervisor stops the browser once the owner has exited (see supervisor.py).
A launch from the user's own terminal has no owner and runs until stopped, as
before; so does one launched with ``--keep`` or released with ``keep``.

**Which process is the owner.** The nearest ancestor of the launching command
that is an agent CLI (``claude``, ``codex``). Claude Code runs its shell
commands as direct children of the session process, and its sub-agents run
inside that same process, so a sub-agent's browser belongs to the session --
it is stopped when the session ends, not when the sub-agent returns. A
separately spawned agent process (an agent-collab worker, a nested
``claude -p``) is its own owner. ``CHROME_AGENT_OWNER_PID`` names the owner
explicitly, for harnesses this module does not recognize (and for tests).

**Sandboxes with their own PID namespace.** Codex runs each shell command in a
bubblewrap sandbox with its own PID namespace, where no ancestor outside the
sandbox is visible. Everything launched in there -- browser, supervisor, X
server -- is killed with the sandbox anyway, so the owner recorded is the
sandbox itself: its namespace and its init process. Each record carries the
PID namespace it was taken in, so a check made from another namespace (the
host's ``status``) can still find the process by its namespace-local PID.

Identity is (pid, start time, pid namespace): a recycled PID never passes for
the owner, and neither suspend/resume nor a clock change alters any of them.
"""

import os

from .utils import process_is_ours, process_start_time

# Process names (``/proc/<pid>/comm``) of the agent CLIs whose sessions own
# the browsers they launch. Claude Code's executable is a versioned file
# (``.../versions/2.1.327``), so the comm is what names it reliably.
AGENT_PROCESSES = {"claude": "claude-code", "codex": "codex"}

# Environment an agent session exports to the commands it runs. Used to tell
# an agent launch from the user's own terminal when no agent ancestor is
# visible (inside a PID-namespaced sandbox).
AGENT_ENV = (
    "CLAUDECODE",                      # Claude Code
    "CODEX_THREAD_ID",                 # Codex
    "CODEX_SANDBOX",                   # Codex (macOS seatbelt)
    "CODEX_SANDBOX_NETWORK_DISABLED",  # Codex, sandboxed without network
    "AI_AGENT",                        # a cross-tool convention Claude Code follows
)

OWNER_ENV = "CHROME_AGENT_OWNER_PID"


def _pid_namespace(pid: int | str = "self") -> str | None:
    try:
        return os.readlink(f"/proc/{pid}/ns/pid")
    except OSError:
        return None


def _parent(pid: int) -> int | None:
    try:
        with open(f"/proc/{pid}/stat") as f:
            return int(f.read().rsplit(")", 1)[1].split()[1])
    except (OSError, IndexError, ValueError):
        return None


def _comm(pid: int) -> str:
    try:
        with open(f"/proc/{pid}/comm") as f:
            return f.read().strip()
    except OSError:
        return ""


def _record(pid: int, kind: str) -> dict:
    return {
        "kind": kind,
        "pid": pid,
        "start": process_start_time(pid=pid),
        "pidns": _pid_namespace(pid),
    }


def agent_ancestor(pid: int | None = None) -> tuple[int, str] | None:
    """The nearest ancestor of ``pid`` (default: this process) that is an
    agent CLI, as (pid, kind), or None."""
    current = _parent(pid if pid is not None else os.getpid())
    seen = 0
    while current and current > 1 and seen < 64:
        kind = AGENT_PROCESSES.get(_comm(current))
        if kind:
            return current, kind
        current = _parent(current)
        seen += 1
    return None


def _in_child_namespace() -> bool:
    """Whether this process runs in a PID namespace of its own (a sandbox):
    there, PID 1 is the sandbox's init, not the system's."""
    comm = _comm(1)
    return bool(comm) and comm not in ("systemd", "init", "launchd") and _parent(1) == 0


def agent_environment() -> str | None:
    """The agent environment variable that marks this as an agent session."""
    for name in AGENT_ENV:
        if os.environ.get(name):
            return name
    return None


def find_owner() -> dict | None:
    """The owner record for a browser launched from this process, or None
    when the launch is not made by an agent (the user's own terminal).

    Order: an explicit ``CHROME_AGENT_OWNER_PID``; the nearest agent-CLI
    ancestor; and, for an agent session in a PID-namespaced sandbox where no
    such ancestor is visible, the sandbox itself.
    """
    explicit = os.environ.get(OWNER_ENV, "").strip()
    if explicit:
        try:
            pid = int(explicit)
        except ValueError:
            pid = 0
        if pid > 0 and process_is_ours(pid=pid):
            return _record(pid, os.environ.get("CHROME_AGENT_OWNER_KIND") or "process")
    found = agent_ancestor()
    if found:
        pid, kind = found
        record = _record(pid, kind)
        session = os.environ.get("CLAUDE_CODE_SESSION_ID") if kind == "claude-code" else os.environ.get("CODEX_THREAD_ID")
        if session:
            record["session"] = session
        return record
    if agent_environment() and _in_child_namespace():
        kind = "codex" if any(os.environ.get(n) for n in AGENT_ENV[1:4]) else "agent"
        record = _record(1, f"{kind}-sandbox")
        return record
    return None


def is_agent_session() -> bool:
    """Whether this command runs inside an agent session."""
    return bool(
        os.environ.get(OWNER_ENV, "").strip()
        or agent_ancestor()
        or agent_environment()
    )


def _exited(pid: int | str) -> bool:
    """Whether a process has exited but not been reaped (a zombie): its
    session is over even though its PID still answers."""
    try:
        with open(f"/proc/{pid}/stat") as f:
            return f.read().rsplit(")", 1)[1].split()[0] == "Z"
    except (OSError, IndexError):
        return False


def _ns_pid(pid: str) -> str | None:
    """The innermost namespace-local PID of a process (the last NSpid field)."""
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("NSpid:"):
                    return line.split()[-1]
    except OSError:
        pass
    return None


def owner_alive(owner: dict | None) -> bool | None:
    """Whether the owning process still runs: True, False, or None when this
    process cannot tell (the owner lives in a namespace it cannot see into).

    None must be read as "keep the browser": nothing is ever stopped on an
    ambiguous answer.
    """
    if not owner:
        return None
    pid, start, pidns = owner.get("pid"), owner.get("start"), owner.get("pidns")
    if not isinstance(pid, int):
        return None
    here = _pid_namespace()
    if pidns is None or here is None or pidns == here:
        return process_is_ours(pid=pid, expected_start=start) and not _exited(pid)
    # Recorded in another PID namespace. From an ancestor namespace (the host,
    # looking at a sandbox) every process in it is visible under its host PID,
    # so look for one in that namespace whose namespace-local PID matches.
    namespace_seen = False
    try:
        entries = os.listdir("/proc")
    except OSError:
        return None
    for entry in entries:
        if not entry.isdigit() or _pid_namespace(entry) != pidns:
            continue
        namespace_seen = True
        if _ns_pid(entry) == str(pid) and not _exited(entry):
            actual = process_start_time(pid=int(entry))
            if start is None or actual is None or actual == start:
                return True
    if namespace_seen:
        return False
    # No process of ours is in that namespace. From the host, that means the
    # sandbox is gone. From inside a different sandbox, nothing outside is
    # visible at all, so it proves nothing.
    return None if _in_child_namespace() else False


def same_owner(a: dict | None, b: dict | None) -> bool:
    return bool(a and b) and all(a.get(k) == b.get(k) for k in ("pid", "start", "pidns"))


def describe(owner: dict | None) -> str:
    """A short human label: "claude-code pid 9669"."""
    if not owner:
        return "none"
    return f"{owner.get('kind', 'process')} pid {owner.get('pid')}"
