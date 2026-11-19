"""Tests for instance ownership: an agent's browser ends with its session.

Owner detection is tested against real processes -- a throwaway process
stands in for the agent session, and a script named ``claude`` for the agent
CLI -- and the lifetime end to end: a real browser launched with an owner is
stopped by its supervisor once that owner exits, and one released with
``keep`` is not. The PID-namespace case runs a real bubblewrap sandbox when
``bwrap`` is available.
"""

import asyncio
import json
import os
import shutil
import subprocess
import sys
import textwrap
import time

import pytest

from chrome_agent import owner as owner_mod
from chrome_agent.instance_status import InstanceStatus, format_status_json, format_status_text
from chrome_agent.launcher import launch_browser
from chrome_agent.registry import _port_is_listening, lookup, registration_status, set_owner, stop
from chrome_agent.supervisor import OWNER_CHECK_INTERVAL

linux_only = pytest.mark.skipif(not sys.platform.startswith("linux"), reason="reads /proc")


def _throwaway_owner() -> subprocess.Popen:
    return subprocess.Popen(["sleep", "600"])


def _end(process: subprocess.Popen) -> None:
    process.terminate()
    process.wait(timeout=10)


@linux_only
def test_explicit_owner_pid_is_recorded(monkeypatch):
    process = _throwaway_owner()
    try:
        monkeypatch.setenv(owner_mod.OWNER_ENV, str(process.pid))
        record = owner_mod.find_owner()
        assert record["pid"] == process.pid
        assert record["kind"] == "process"
        assert record["start"] and record["pidns"].startswith("pid:[")
        assert owner_mod.owner_alive(record) is True
        assert owner_mod.is_agent_session()
    finally:
        _end(process)
    assert owner_mod.owner_alive(record) is False


@linux_only
def test_recycled_pid_is_not_the_owner():
    process = _throwaway_owner()
    try:
        record = owner_mod._record(process.pid, "process")
        assert owner_mod.owner_alive({**record, "start": "1"}) is False
    finally:
        _end(process)


@linux_only
def test_exited_but_unreaped_owner_is_gone():
    process = subprocess.Popen(["sh", "-c", "exit 0"])
    record = owner_mod._record(process.pid, "process")
    deadline = time.monotonic() + 5
    while not owner_mod._exited(process.pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert owner_mod.owner_alive(record) is False  # a zombie still answers kill(0)
    process.wait()


@linux_only
def test_the_nearest_agent_cli_ancestor_owns_the_launch(tmp_path):
    """A process named ``claude`` above the launching command is its owner --
    the comm is what identifies it (Claude Code's executable is a versioned
    file name)."""
    fake = tmp_path / "claude"
    fake.write_text(textwrap.dedent(f"""\
        #!/bin/sh
        exec {sys.executable} -c 'import json, os; from chrome_agent.owner import find_owner; print(json.dumps(find_owner())); print(os.getppid())' &
        wait
    """))
    fake.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if k != owner_mod.OWNER_ENV}
    out = subprocess.run([str(fake)], capture_output=True, text=True, env=env, timeout=30).stdout.split("\n")
    record, parent = json.loads(out[0]), int(out[1])
    assert record["kind"] == "claude-code"
    assert record["pid"] == parent


@linux_only
def test_no_owner_from_a_plain_terminal(tmp_path):
    """With no agent ancestor and no agent environment there is no owner and
    no agent session -- the user's own launches are untouched."""
    script = (
        "import json; from chrome_agent.owner import find_owner, is_agent_session;"
        "print(json.dumps([find_owner(), is_agent_session()]))"
    )
    env = {k: v for k, v in os.environ.items()
           if k not in owner_mod.AGENT_ENV and k != owner_mod.OWNER_ENV}
    # setsid + a detached grandchild: its parent is the init/subreaper, not
    # whatever agent runs this test suite.
    out = tmp_path / "out.json"
    subprocess.run(
        ["setsid", "sh", "-c", f"( {sys.executable} -c '{script}' > {out} & )"],
        env=env, timeout=30,
    )
    deadline = time.monotonic() + 15
    while (not out.exists() or not out.read_text().strip()) and time.monotonic() < deadline:
        time.sleep(0.1)
    assert json.loads(out.read_text()) == [None, False]


@linux_only
@pytest.mark.skipif(shutil.which("bwrap") is None, reason="needs bubblewrap")
def test_owner_inside_a_pid_namespaced_sandbox(tmp_path):
    """Inside a sandbox with its own PID namespace (as Codex runs commands)
    no agent CLI is visible; the sandbox itself is recorded as the owner, and
    the host can still tell whether it runs."""
    out = tmp_path / "owner.json"
    script = f"import json; from chrome_agent.owner import find_owner; open('{out}','w').write(json.dumps(find_owner()))"
    env = {k: v for k, v in os.environ.items()
           if k not in owner_mod.AGENT_ENV and k != owner_mod.OWNER_ENV}
    env["CODEX_THREAD_ID"] = "test-thread"
    sandbox = subprocess.Popen(
        ["bwrap", "--dev-bind", "/", "/", "--unshare-pid", "--proc", "/proc", "--die-with-parent",
         "sh", "-c", f"{sys.executable} -c \"{script}\"; sleep 30"],
        env=env,
    )
    try:
        deadline = time.monotonic() + 15
        while (not out.exists() or not out.read_text()) and time.monotonic() < deadline:
            time.sleep(0.1)
        record = json.loads(out.read_text())
        assert record["kind"] == "codex-sandbox"
        assert record["pid"] == 1
        assert record["pidns"] != owner_mod._pid_namespace()
        assert owner_mod.owner_alive(record) is True
    finally:
        sandbox.terminate()
        sandbox.wait(timeout=10)
    deadline = time.monotonic() + 10
    while owner_mod.owner_alive(record) is not False and time.monotonic() < deadline:
        time.sleep(0.2)
    assert owner_mod.owner_alive(record) is False


def _wait(predicate, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.25)
    return predicate()


@linux_only
def test_browser_is_stopped_when_its_owner_exits_and_kept_one_is_not(tmp_path):
    """End to end: the supervisor stops an owned browser once its owner has
    exited; a browser released with keep() outlives the same owner."""
    registry = str(tmp_path / "registry.json")
    process = _throwaway_owner()
    record = owner_mod._record(process.pid, "process")

    def launch(name):
        return asyncio.run(launch_browser(
            headless=True, registry_path=registry, instance_name=name,
            working_dir=str(tmp_path), owner=record,
        ))

    owned, kept = launch("own-test-01"), launch("own-test-02")
    try:
        assert lookup(instance_name="own-test-01", registry_path=registry).owner == record
        assert set_owner(instance_name="own-test-02", owner=None, registry_path=registry) == record

        time.sleep(OWNER_CHECK_INTERVAL + 1)
        assert _port_is_listening(owned.port), "nothing is stopped while the owner runs"

        _end(process)
        assert _wait(lambda: not _port_is_listening(owned.port), OWNER_CHECK_INTERVAL * 4), \
            "the owned browser must be stopped after its owner exits"
        assert _wait(lambda: registration_status("own-test-01", registry_path=registry) != "present", 10)
        assert _port_is_listening(kept.port), "a kept browser outlives the owner"
    finally:
        _end(process) if process.poll() is None else None
        for name in ("own-test-01", "own-test-02"):
            try:
                stop(instance_name=name, registry_path=registry)
            except Exception:
                pass


def test_status_shows_owner_kept_and_orphans():
    owner = {"kind": "claude-code", "pid": 4242, "start": "1", "pidns": "pid:[1]", "session": "abc"}
    statuses = [
        InstanceStatus(name="mine-01", port=9222, alive=True, owner=owner, owner_alive=True, yours=True,
                       placement={"kind": "virtual", "display": ":100", "server": "Xvfb", "managed": True}),
        InstanceStatus(name="theirs-01", port=9223, alive=True, owner=owner, owner_alive=True,
                       placement={"kind": "virtual", "display": ":100", "server": "Xvfb"}),
        InstanceStatus(name="user-01", port=9224, alive=True, placement={"kind": "desktop", "display": ":1"}),
        InstanceStatus(name="lost-01", port=9225, alive=True, owner=owner, owner_alive=False,
                       placement={"kind": "headless"}),
        InstanceStatus(name="far-01", port=9226, alive=True, owner=owner, owner_alive=None,
                       placement={"kind": "headless"}),
    ]
    text = format_status_text(statuses)
    assert "mine-01  port 9222  [Xvfb :100]  owner claude-code pid 4242 (yours)" in text
    assert "theirs-01  port 9223  [Xvfb :100]  owner claude-code pid 4242\n" in text
    assert "user-01  port 9224  [desktop :1]  kept" in text
    assert "lost-01  port 9225  [headless]  ORPHAN: owner claude-code pid 4242 has exited" in text
    assert "far-01  port 9226  [headless]  owner claude-code pid 4242 (cannot check from here)" in text
    assert "1 orphaned instance(s)" in text and "chrome-agent stop --orphans" in text

    data = {e["name"]: e for e in json.loads(format_status_json(statuses))}
    assert data["mine-01"]["owner"] == {"kind": "claude-code", "pid": 4242, "session": "abc",
                                        "alive": True, "yours": True}
    assert data["user-01"]["owner"] is None
    assert data["lost-01"]["owner"]["alive"] is False


def test_stop_orphans_stops_only_orphans(monkeypatch, capsys):
    from chrome_agent import cli

    owner = {"kind": "codex", "pid": 7}
    statuses = [
        InstanceStatus(name="lost-01", port=9225, alive=True, owner=owner, owner_alive=False),
        InstanceStatus(name="live-01", port=9226, alive=True, owner=owner, owner_alive=True),
        InstanceStatus(name="far-01", port=9227, alive=True, owner=owner, owner_alive=None),
        InstanceStatus(name="user-01", port=9228, alive=True),
    ]
    stopped = []
    monkeypatch.setattr("chrome_agent.instance_status.get_instance_status", lambda **k: statuses)
    monkeypatch.setattr("chrome_agent.registry.stop", lambda *, instance_name: stopped.append(instance_name) or f"Stopped {instance_name}")
    cli._run_stop(args=["--orphans"], target_spec=None, target_by=None)
    assert stopped == ["lost-01"]
    assert "lost-01 (owner codex pid 7 has exited)" in capsys.readouterr().out
