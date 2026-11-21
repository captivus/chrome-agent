"""One browser, one label, one supervisor.

Regression tests for the runaway of 2026-11-21: two chrome-agent instances
ended up supervising the same browser (concurrent launches chose the same
port; the losing Chrome fell back to [::1] while its launch registered the
winner's port as its own). Both supervisors labelled the same tabs, each
re-prefixed the other's change through its title observer, and the title grew
without end while the browser and renderer burned a CPU core.

The overlay tests run the real script in the session's (headless) browser.
"""

import asyncio
import json
import threading

import pytest

import chrome_agent.registry as registry_mod
import chrome_agent.supervisor as supervisor_mod
from chrome_agent.cdp_client import CDPClient, get_ws_url
from chrome_agent.launcher import launch_browser
from chrome_agent.registry import _save_registry, port_listener_profile
from chrome_agent.supervisor import (
    NotOurBrowser,
    _supervise_connection,
    build_overlay_script,
    owner_has_gone,
    run_supervisor,
)

CDP_PORT = 9333
LABEL = "\U0001f916 "


async def _eval(cdp: CDPClient, expression: str):
    result = await cdp.send(
        method="Runtime.evaluate",
        params={"expression": expression, "returnByValue": True, "awaitPromise": True},
    )
    return result["result"].get("value")


async def _fresh_page(cdp: CDPClient, title: str) -> None:
    await cdp.send(method="Page.enable")
    await cdp.send(method="Page.navigate", params={"url": f"data:text/html,<title>{title}</title><p>x"})
    for _ in range(50):
        if await _eval(cdp, "document.readyState") == "complete":
            return
        await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_two_labellers_settle_on_one_label(browser_session):
    """Two supervisors' overlays on one tab: one label, no loop, no growth.

    Before the fix this title grew without bound ("🤖 b — 🤖 a — 🤖 b — ...").
    """
    async with CDPClient(ws_url=get_ws_url(port=CDP_PORT, target_type="page")) as cdp:
        await _fresh_page(cdp, "Hello")
        # Count every title change the page goes through from here on.
        await _eval(cdp, """(() => { window.__titleChanges = 0;
            new MutationObserver(() => window.__titleChanges++).observe(
              document.querySelector('title'), {childList: true, characterData: true, subtree: true}); })()""")
        for name in ("inst-a", "inst-b"):
            await _eval(cdp, build_overlay_script(name=name, color="#123456", host_id=f"_ca{name[-1]}"))
        await asyncio.sleep(0.5)
        assert await _eval(cdp, "document.title") == f"{LABEL}inst-a — Hello"

        # The page changes its own title (an SPA): labelled once, by whoever
        # sees it first, and then left alone.
        await _eval(cdp, "document.title = 'World'")
        await asyncio.sleep(0.5)
        title = await _eval(cdp, "document.title")
        assert title.count(LABEL) == 1 and title.endswith(" — World")
        assert await _eval(cdp, "window.__titleChanges") <= 4


@pytest.mark.asyncio
async def test_label_gives_up_against_a_page_that_strips_it(browser_session):
    """A page that removes the label whenever it appears cannot pin a CPU."""
    async with CDPClient(ws_url=get_ws_url(port=CDP_PORT, target_type="page")) as cdp:
        await _fresh_page(cdp, "Stubborn")
        await _eval(cdp, """(() => { window.__strips = 0;
            new MutationObserver(() => { var t = document.title;
              if (t.indexOf('\\uD83E\\uDD16 ') === 0) { window.__strips++; document.title = t.replace(/^\\uD83E\\uDD16 .*? \\u2014 /, ''); } }
            ).observe(document.querySelector('title'), {childList: true, characterData: true, subtree: true}); })()""")
        await _eval(cdp, build_overlay_script(name="inst-c", color="#123456", host_id="_cac"))
        await asyncio.sleep(1.0)
        first = await _eval(cdp, "window.__strips")
        await asyncio.sleep(1.0)
        assert first <= 25  # the cap is 20 writes a second
        assert await _eval(cdp, "window.__strips") == first  # and then it stopped


def test_port_listener_profile_names_the_serving_browser(browser_session):
    assert port_listener_profile(CDP_PORT) == browser_session.user_data_dir


def test_port_listener_profile_unknown_without_listener():
    assert port_listener_profile(9) is None


@pytest.mark.asyncio
async def test_launch_refuses_a_port_another_browser_serves(browser_session, tmp_path):
    """A launch whose port answers for another browser must not register it."""
    reg = str(tmp_path / "registry.json")
    with pytest.raises(RuntimeError, match="served by a different browser"):
        await launch_browser(
            port_override=CDP_PORT, headless=True, pin_to_desktop=False, registry_path=reg,
        )
    assert not (tmp_path / "registry.json").exists() or json.loads((tmp_path / "registry.json").read_text()) == {}
    # The other browser is untouched.
    assert port_listener_profile(CDP_PORT) == browser_session.user_data_dir


@pytest.mark.asyncio
async def test_supervisor_will_not_connect_to_another_browser(monkeypatch):
    monkeypatch.setattr(registry_mod, "port_listener_profile", lambda port: "/tmp/chrome-agent/session-other")

    def no_connect(**_):
        raise AssertionError("connected to a browser that is not ours")

    monkeypatch.setattr(supervisor_mod, "get_ws_url", no_connect)
    with pytest.raises(NotOurBrowser):
        await _supervise_connection(
            port=9222, draw_border=True, source="0", name="x-01",
            user_data_dir="/tmp/chrome-agent/session-mine",
        )


def _write_registry(path, name, user_data_dir, owner=None):
    path.write_text(json.dumps({name: {
        "port": 9222, "pid": 1, "user_data_dir": user_data_dir, "owner": owner,
    }}))


@pytest.mark.asyncio
async def test_stale_supervisor_does_not_retire_the_names_new_owner(monkeypatch, tmp_path):
    """Our browser is gone and the name now belongs to a newer browser:
    exit without deregistering it."""
    reg = tmp_path / "registry.json"
    _write_registry(reg, "x-01", "/tmp/chrome-agent/session-newer")

    async def fake_supervise(**_):
        raise NotOurBrowser("/tmp/chrome-agent/session-newer")

    async def gone(port, user_data_dir=None):
        return True

    monkeypatch.setattr(supervisor_mod, "_supervise_connection", fake_supervise)
    monkeypatch.setattr(supervisor_mod, "_browser_gone", gone)
    await run_supervisor(
        port=9222, name="x-01", registry_path=str(reg), draw_border=False,
        user_data_dir="/tmp/chrome-agent/session-mine",
    )
    assert "x-01" in json.loads(reg.read_text())


@pytest.mark.asyncio
async def test_browser_gone_when_only_another_browser_claims_the_port(monkeypatch):
    monkeypatch.setattr(registry_mod, "_port_is_listening", lambda port: True)
    monkeypatch.setattr(registry_mod, "_cdp_port_claimants", lambda port: {"/tmp/chrome-agent/session-other"})
    monkeypatch.setattr(supervisor_mod, "_RETIRE_GRACE_SECONDS", 0.5)
    assert await supervisor_mod._browser_gone(9222, "/tmp/chrome-agent/session-mine") is True
    assert await supervisor_mod._browser_gone(9222, "/tmp/chrome-agent/session-other") is False


def test_owner_check_ignores_an_entry_that_is_not_ours(monkeypatch, tmp_path):
    reg = tmp_path / "registry.json"
    _write_registry(reg, "x-01", "/tmp/chrome-agent/session-newer", owner={"kind": "process", "pid": 1})
    monkeypatch.setattr("chrome_agent.owner.owner_alive", lambda owner: False)
    assert owner_has_gone("x-01", str(reg), "/tmp/chrome-agent/session-newer") is True
    assert owner_has_gone("x-01", str(reg), "/tmp/chrome-agent/session-mine") is False


def test_concurrent_registry_saves_do_not_collide(tmp_path):
    path = str(tmp_path / "registry.json")
    errors = []

    def save(i):
        try:
            for j in range(50):
                _save_registry({f"n{i}": j}, path)
        except Exception as exc:  # pragma: no cover - the failure being tested
            errors.append(exc)

    threads = [threading.Thread(target=save, args=(i,)) for i in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert errors == []
    assert list(tmp_path.iterdir()) == [tmp_path / "registry.json"]


# ---------------------------------------------------------------------------
# A browser whose registry entry was lost is still stopped with its owner
# ---------------------------------------------------------------------------

MINE = "/tmp/chrome-agent/session-mine"
OWNER = {"kind": "process", "pid": 4242}


def _owner_dead(monkeypatch, dead=True):
    monkeypatch.setattr("chrome_agent.owner.owner_alive", lambda owner: not dead)


def test_check_owner_follows_its_entry_and_remembers(monkeypatch, tmp_path):
    from chrome_agent.supervisor import check_owner

    _owner_dead(monkeypatch)
    reg = tmp_path / "registry.json"
    _write_registry(reg, "x-01", MINE, owner=OWNER)
    memory = {"owner": None}
    assert check_owner("x-01", str(reg), MINE, memory) == (True, True)
    assert memory["owner"] == OWNER
    # The entry is lost: the remembered owner still decides.
    reg.write_text("{}")
    assert check_owner("x-01", str(reg), MINE, memory) == (True, False)
    # The name now belongs to another browser: still our remembered owner.
    _write_registry(reg, "x-01", "/tmp/chrome-agent/session-newer")
    assert check_owner("x-01", str(reg), MINE, memory) == (True, False)


def test_check_owner_respects_keep(monkeypatch, tmp_path):
    """`keep` clears the owner; losing the entry afterwards must not bring it back."""
    from chrome_agent.supervisor import check_owner

    _owner_dead(monkeypatch)
    reg = tmp_path / "registry.json"
    _write_registry(reg, "x-01", MINE, owner=None)
    memory = {"owner": OWNER}  # seeded at launch
    assert check_owner("x-01", str(reg), MINE, memory) == (False, True)
    reg.write_text("{}")
    assert check_owner("x-01", str(reg), MINE, memory) == (False, False)


def test_check_owner_legacy_supervisor_never_falls_back(monkeypatch, tmp_path):
    from chrome_agent.supervisor import check_owner

    _owner_dead(monkeypatch)
    reg = tmp_path / "registry.json"
    reg.write_text("{}")
    assert check_owner("x-01", str(reg), None, {"owner": OWNER}) == (False, False)


class _FakeCDP:
    def __init__(self, ws_url):
        self._connected = False
        self.sent = []

    async def connect(self):
        self._connected = True

    async def send(self, method, params=None, session_id=None):
        self.sent.append(method)
        if method == "Browser.close":
            self._connected = False
        return {}

    def on(self, event, callback):
        pass

    async def close(self):
        self._connected = False


@pytest.mark.asyncio
@pytest.mark.parametrize("entry_ours", [False, True])
async def test_owner_gone_stops_the_browser_with_or_without_entry(monkeypatch, entry_ours):
    made = []

    def fake_cdp(ws_url):
        made.append(_FakeCDP(ws_url))
        return made[-1]

    stopped = []
    monkeypatch.setattr(supervisor_mod, "CDPClient", fake_cdp)
    monkeypatch.setattr(supervisor_mod, "get_ws_url", lambda **_: "ws://x")
    monkeypatch.setattr(registry_mod, "port_listener_profile", lambda port: MINE)
    monkeypatch.setattr(supervisor_mod, "OWNER_CHECK_INTERVAL", 0.0)
    monkeypatch.setattr(supervisor_mod, "check_owner", lambda *a: (True, entry_ours))
    monkeypatch.setattr(supervisor_mod, "_record_owner_stop", lambda *a: None)
    monkeypatch.setattr(registry_mod, "stop", lambda **kw: stopped.append(kw["instance_name"]))

    await asyncio.wait_for(_supervise_connection(
        port=9222, draw_border=False, source=None, name="x-01", user_data_dir=MINE,
    ), timeout=10)
    if entry_ours:
        assert stopped == ["x-01"] and "Browser.close" not in made[0].sent
    else:
        assert stopped == [] and made[0].sent == ["Browser.close"]


def test_spawn_passes_profile_and_owner(monkeypatch):
    calls = []
    monkeypatch.setattr(supervisor_mod.subprocess, "Popen", lambda argv, **kw: calls.append(argv))
    supervisor_mod.spawn_supervisor(
        port=9222, name="x-01", registry_path="/r.json", draw_border=True,
        user_data_dir=MINE, owner=OWNER,
    )
    assert calls[0][-2:] == [MINE, json.dumps(OWNER, separators=(",", ":"))]
