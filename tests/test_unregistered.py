"""Finding and stopping browsers that are missing from the registry.

Stand-in processes play the browsers and supervisors: what identifies them is
their command line (``--user-data-dir=<root>/session-*``, and
``chrome_agent.supervisor PORT NAME REGISTRY DRAW_BORDER [PROFILE]``), which a
sleeping Python process can carry as well as Chrome.
"""

import json
import subprocess
import sys
import time

import pytest

from chrome_agent.unregistered import find_unregistered, stop_unregistered

SLEEP = "import time; time.sleep(120)"


@pytest.fixture
def procs():
    started = []

    def spawn(*args):
        p = subprocess.Popen([sys.executable, "-c", SLEEP, *args])
        started.append(p)
        time.sleep(0.2)
        return p

    yield spawn
    for p in started:
        p.kill()
        p.wait()


@pytest.fixture
def root(tmp_path):
    (tmp_path / "root").mkdir()
    return tmp_path / "root"


def _profile(root, name):
    d = root / f"session-{name}"
    d.mkdir()
    return str(d)


def _find(root, registry):
    return find_unregistered([str(registry)], session_root=str(root), min_age=0)


def test_finds_only_unregistered_browsers(procs, root, tmp_path):
    lost, kept = _profile(root, "lost"), _profile(root, "kept")
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"kept-01": {"port": 9601, "pid": 1, "user_data_dir": kept}}))
    b_lost = procs(f"--remote-debugging-port=9600", f"--user-data-dir={lost}")
    procs(f"--remote-debugging-port=9601", f"--user-data-dir={kept}")
    procs("--type=renderer", f"--user-data-dir={lost}")  # a helper, not the browser
    procs(f"--user-data-dir={tmp_path}/elsewhere")  # not a chrome-agent profile

    found = _find(root, registry)
    assert [(b.pid, b.port, b.user_data_dir) for b in found] == [(b_lost.pid, 9600, lost)]


def test_young_browsers_are_left_out(procs, root, tmp_path):
    """A launch registers its browser a moment after Chrome starts."""
    procs("--remote-debugging-port=9600", f"--user-data-dir={_profile(root, 'new')}")
    registry = tmp_path / "registry.json"
    assert find_unregistered([str(registry)], session_root=str(root), min_age=60) == []


def test_supervisors_are_attributed(procs, root, tmp_path):
    lost = _profile(root, "lost")
    registry = tmp_path / "registry.json"
    other = _profile(root, "other")
    registry.write_text(json.dumps({"live-01": {"port": 9600, "pid": 1, "user_data_dir": other}}))
    procs("--remote-debugging-port=9600", f"--user-data-dir={lost}")
    new_style = procs("chrome_agent.supervisor", "9600", "lost-01", str(registry), "1", lost)
    legacy_stale = procs("chrome_agent.supervisor", "9600", "gone-01", str(registry), "1")
    procs("chrome_agent.supervisor", "9600", "live-01", str(registry), "1")  # the registered one's
    procs("chrome_agent.supervisor", "9600", "x-01", str(registry), "1", other)

    (browser,) = _find(root, registry)
    assert sorted(s["pid"] for s in browser.supervisors) == sorted([new_style.pid, legacy_stale.pid])


def test_stop_ends_supervisors_then_browser_and_removes_profile(procs, root, tmp_path):
    lost = _profile(root, "lost")
    registry = tmp_path / "registry.json"
    browser_p = procs("--remote-debugging-port=9600", f"--user-data-dir={lost}")
    sup_p = procs("chrome_agent.supervisor", "9600", "lost-01", str(registry), "1", lost)

    (browser,) = _find(root, registry)
    message = stop_unregistered(browser, session_root=str(root))
    assert message.startswith("Stopped")
    assert browser_p.wait(timeout=5) is not None and sup_p.wait(timeout=5) is not None
    assert not (root / "session-lost").exists()


def test_stop_refuses_a_pid_that_is_no_longer_that_browser(procs, root, tmp_path):
    """Verified by start time immediately before signalling: a recycled pid is left alone."""
    lost = _profile(root, "lost")
    browser_p = procs("--remote-debugging-port=9600", f"--user-data-dir={lost}")
    (browser,) = _find(root, tmp_path / "registry.json")
    browser.pid_start = "0"  # as if the pid now belonged to a later process
    assert "left alone" in stop_unregistered(browser, session_root=str(root))
    assert browser_p.poll() is None
    assert (root / "session-lost").exists()


# ---------------------------------------------------------------------------
# CLI: status reports, cleanup --unregistered stops
# ---------------------------------------------------------------------------


def test_status_unregistered_json(monkeypatch, capsys, procs, root, tmp_path):
    import chrome_agent.unregistered as unreg
    from chrome_agent import cli

    lost = _profile(root, "lost")
    b = procs("--remote-debugging-port=9600", f"--user-data-dir={lost}")
    found = _find(root, tmp_path / "registry.json")
    monkeypatch.setattr(unreg, "find_unregistered", lambda *a, **k: found)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    cli._run_status(["--unregistered"])
    data = json.loads(capsys.readouterr().out)
    assert [(d["pid"], d["port"], d["user_data_dir"]) for d in data] == [(b.pid, 9600, lost)]


def test_status_notes_unregistered_on_stderr(monkeypatch, capsys):
    import chrome_agent.instance_status as status_mod
    import chrome_agent.unregistered as unreg
    from chrome_agent import cli
    from chrome_agent.unregistered import UnregisteredBrowser

    monkeypatch.setattr(status_mod, "get_instance_status", lambda **k: [])
    monkeypatch.setattr(unreg, "find_unregistered", lambda *a, **k: [UnregisteredBrowser(
        pid=1, pid_start=None, user_data_dir="/tmp/chrome-agent/session-x", port=9600,
        started=None, profile_exists=False)])
    cli._run_status([])
    out = capsys.readouterr()
    assert "1 chrome-agent browser(s) are running but not in the registry" in out.err
    assert "not in the registry" not in out.out


def test_cleanup_unregistered_stops_what_it_finds(monkeypatch, capsys, procs, root, tmp_path):
    import chrome_agent.unregistered as unreg
    from chrome_agent import cli

    lost = _profile(root, "lost")
    b = procs("--remote-debugging-port=9600", f"--user-data-dir={lost}")
    found = _find(root, tmp_path / "registry.json")
    monkeypatch.setattr(unreg, "find_unregistered", lambda *a, **k: found)
    monkeypatch.setattr(unreg, "SESSION_ROOT", str(root))
    real_stop = unreg.stop_unregistered
    monkeypatch.setattr(unreg, "stop_unregistered", lambda br: real_stop(br, session_root=str(root)))
    cli._run_cleanup(["--unregistered"])
    assert "Stopped browser" in capsys.readouterr().out
    assert b.wait(timeout=5) is not None


def test_cleanup_rejects_unknown_options():
    from chrome_agent import cli

    with pytest.raises(SystemExit):
        cli._run_cleanup(["--everything"])
