"""Tests for session snapshots: encryption, archive, store, save/restore."""

import asyncio
import base64
import io
import json
import os
import socket

import pytest

from chrome_agent import snapcrypto, snapshot
from chrome_agent.desktop import match_windows
from chrome_agent.registry import allocate_port, register


@pytest.fixture
def key(monkeypatch):
    raw = os.urandom(32)
    monkeypatch.setenv(snapcrypto.KEY_ENV, base64.b64encode(raw).decode())
    return raw


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    return tmp_path / "xdg" / "chrome-agent" / "snapshots"


# -- encryption --------------------------------------------------------------

def test_encrypt_roundtrip_multichunk(key, monkeypatch):
    monkeypatch.setattr(snapcrypto, "_CHUNK", 1000)
    data = os.urandom(10_500)
    sealed = snapcrypto.encrypt_bytes(data, key)
    assert data not in sealed
    assert snapcrypto.decrypt_bytes(sealed, key) == data


def test_wrong_key_is_refused(key):
    sealed = snapcrypto.encrypt_bytes(b"secret", key)
    with pytest.raises(snapcrypto.SnapshotKeyError):
        snapcrypto.decrypt_bytes(sealed, os.urandom(32))


def test_tampering_is_detected(key):
    sealed = bytearray(snapcrypto.encrypt_bytes(b"secret cookie", key))
    sealed[-3] ^= 1
    with pytest.raises(snapcrypto.SnapshotKeyError):
        snapcrypto.decrypt_bytes(bytes(sealed), key)


def test_dropping_trailing_chunks_is_detected(key, monkeypatch):
    """Chunks carry a final flag: cutting at a chunk boundary still fails."""
    monkeypatch.setattr(snapcrypto, "_CHUNK", 100)
    sealed = snapcrypto.encrypt_bytes(os.urandom(450), key)
    header = len(snapcrypto._MAGIC) + snapcrypto._PREFIX_LEN
    first_chunk_end = header + 4 + int.from_bytes(sealed[header:header + 4], "big")
    with pytest.raises(snapcrypto.SnapshotKeyError):
        snapcrypto.decrypt_bytes(sealed[:first_chunk_end], key)


def test_env_key_must_be_32_bytes(monkeypatch):
    monkeypatch.setenv(snapcrypto.KEY_ENV, base64.b64encode(b"short").decode())
    with pytest.raises(snapcrypto.SnapshotKeyError):
        snapcrypto.get_key(create=False)


# -- profile archive ---------------------------------------------------------

def test_archive_excludes_caches_and_non_regular_files(tmp_path, key):
    profile = tmp_path / "profile"
    (profile / "Default" / "Cache").mkdir(parents=True)
    (profile / "Default" / "Cache" / "data_0").write_bytes(b"x" * 100)
    (profile / "Default" / "Local Storage").mkdir()
    (profile / "Default" / "Local Storage" / "000003.log").write_bytes(b"token=abc")
    (profile / "Default" / "Cookies").write_bytes(b"SQLite format 3\0cookies")
    (profile / "OptGuideOnDeviceModel").mkdir()
    (profile / "OptGuideOnDeviceModel" / "weights.bin").write_bytes(b"w" * 100)
    os.symlink("host-123", profile / "SingletonLock")
    sock = socket.socket(socket.AF_UNIX)
    sock.bind(str(profile / "SingletonSocket"))
    os.mkfifo(profile / "a-fifo")  # reading this would block forever

    archive = tmp_path / "profile.tar.enc"
    result = snapshot.write_profile_archive(str(profile), str(archive), key)
    sock.close()
    assert result["files"] == 2
    assert b"token=abc" not in archive.read_bytes()

    dest = tmp_path / "restored"
    snapshot.extract_profile_archive(str(archive), str(dest), key)
    assert (dest / "Default" / "Local Storage" / "000003.log").read_bytes() == b"token=abc"
    assert (dest / "Default" / "Cookies").exists()
    assert not (dest / "Default" / "Cache").exists()
    assert not (dest / "OptGuideOnDeviceModel").exists()


def test_mark_clean_exit(tmp_path):
    (tmp_path / "Default").mkdir()
    prefs = tmp_path / "Default" / "Preferences"
    prefs.write_text(json.dumps({"profile": {"exit_type": "Crashed", "name": "x"}}))
    snapshot._mark_clean_exit(str(tmp_path))
    data = json.loads(prefs.read_text())
    assert data["profile"] == {"exit_type": "Normal", "exited_cleanly": True, "name": "x"}


# -- store -------------------------------------------------------------------

def _fake_version(store, name, stamp, **info):
    path = store / name / stamp
    path.mkdir(parents=True)
    (path / "info.json").write_text(json.dumps({
        "name": name, "instance": name, "stamp": stamp,
        "saved_at": "2026-09-01T00:00:00+00:00", **info,
    }))
    return path


def test_resolve_refs_latest_and_exact(store):
    _fake_version(store, "site-01", "20260901T000000Z")
    _fake_version(store, "site-01", "20260902T000000Z")
    _fake_version(store, "other-01", "20260901T000000Z")
    (store / "site-01" / ".tmp-20260903T000000Z").mkdir()  # in-progress save

    assert [v.ref for v in snapshot.resolve_refs("site-01")] == ["site-01@20260902T000000Z"]
    assert [v.ref for v in snapshot.resolve_refs("site-01@20260901T000000Z")] == [
        "site-01@20260901T000000Z"
    ]
    assert {v.name for v in snapshot.resolve_refs("*-01")} == {"site-01", "other-01"}
    with pytest.raises(snapshot.SnapshotError):
        snapshot.resolve_refs("nope")


def test_remove_last_version_removes_name_dir(store):
    _fake_version(store, "site-01", "20260901T000000Z")
    (version,) = snapshot.list_versions()
    snapshot.remove_version(version)
    assert not (store / "site-01").exists()


def test_parse_age():
    assert snapshot.parse_age("30d").days == 30
    assert snapshot.parse_age("12h").total_seconds() == 12 * 3600
    with pytest.raises(snapshot.SnapshotError):
        snapshot.parse_age("soon")


def test_reserved_ports_follow_latest_batch(store, tmp_path, monkeypatch):
    import chrome_agent.registry as registry

    reg = tmp_path / "registry.json"
    monkeypatch.setattr(registry, "REGISTRY_PATH", str(reg))
    _fake_version(store, "a-01", "20260901T000000Z", port=9240)
    _fake_version(store, "b-01", "20260901T000000Z", port=9241)
    snapshot.write_batch(snapshot.list_versions())
    assert snapshot.reserved_ports() == {9240, 9241}

    # Once an instance is registered again, its registry entry holds the port.
    reg.write_text(json.dumps({"a-01": {"port": 9240, "pid": 1}}))
    assert snapshot.reserved_ports() == {9241}


def test_allocate_port_skips_reserved():
    port = allocate_port(registry={}, reserved={9222, 9223})
    assert port not in (9222, 9223)


def test_register_with_name_override_and_launch_record(tmp_path):
    reg = str(tmp_path / "registry.json")
    info = register(
        working_dir="/somewhere/else", pid=os.getpid(), browser_version="Chrome/1",
        user_data_dir="/tmp/x", port_override=9299, registry_path=reg,
        name_override="original-01", launch={"headless": True},
    )
    assert info.name == "original-01"
    entry = json.loads(open(reg).read())["original-01"]
    assert entry["working_dir"] == "/somewhere/else"
    assert entry["launch"] == {"headless": True}


# -- helpers -----------------------------------------------------------------

def test_cookie_param_drops_read_only_fields():
    cookie = {
        "name": "sid", "value": "v", "domain": ".x.com", "path": "/", "expires": -1,
        "size": 5, "httpOnly": True, "secure": True, "session": True,
        "sameSite": "Lax", "priority": "Medium", "sourceScheme": "Secure", "sourcePort": 443,
    }
    param = snapshot._cookie_param(cookie)
    assert "size" not in param and "session" not in param and "expires" not in param
    assert param["name"] == "sid" and param["httpOnly"] is True

    persistent = dict(cookie, session=False, expires=1893456000.5)
    assert snapshot._cookie_param(persistent)["expires"] == 1893456000.5


def test_strip_marker():
    assert snapshot._strip_marker("\U0001F916 site-01 — Inbox", "site-01") == "Inbox"
    assert snapshot._strip_marker("\U0001F916 site-01 —", "site-01") == ""
    assert snapshot._strip_marker("Plain", "site-01") == "Plain"


def test_effective_profile_dir_last_one_wins():
    tokens = ["chrome", "--user-data-dir=/tmp/chrome-agent/s", "--user-data-dir=/tmp/mine"]
    assert snapshot._effective_profile_dir(tokens, "/tmp/chrome-agent/s") == "/tmp/mine"
    assert snapshot._effective_profile_dir(["chrome"], "/reg") == "/reg"


def test_rewrite_target():
    argv = ["attach", "x-01", "--target", "1A2B3C4D", "+Page.loadEventFired"]
    assert snapshot._rewrite_target(argv, "--target", "1A2B3C4D", "NEWID") == [
        "attach", "x-01", "--target-id", "NEWID", "+Page.loadEventFired",
    ]


def test_match_windows_prefers_title_over_identical_geometry():
    bounds = {"left": 0, "top": 0, "width": 800, "height": 600}
    x_windows = [
        {"window": "1", "name": "Mail - Google Chrome", "desktop": 2, **bounds},
        {"window": "2", "name": "Docs - Google Chrome", "desktop": 5, **bounds},
    ]
    cdp = [
        {"windowId": 10, "bounds": bounds, "title": "Docs"},
        {"windowId": 11, "bounds": bounds, "title": "Mail"},
    ]
    matched = match_windows(x_windows, cdp)
    assert matched[10]["desktop"] == 5
    assert matched[11]["desktop"] == 2


# -- live save and restore ---------------------------------------------------

@pytest.mark.asyncio
async def test_save_stop_restore_roundtrip(tmp_path, monkeypatch, key, store):
    """A headless browser's cookies (incl. session cookies), localStorage,
    tabs, name and port survive save --stop and restore."""
    import chrome_agent.registry as registry
    from chrome_agent.cdp_client import CDPClient, get_ws_url
    from chrome_agent.launcher import launch_browser

    monkeypatch.setattr(registry, "REGISTRY_PATH", str(tmp_path / "registry.json"))
    workdir = tmp_path / "roundtrip"
    workdir.mkdir()
    page = tmp_path / "page.html"
    page.write_text("<title>Roundtrip</title>")

    info = await launch_browser(
        port_override=9334, headless=True, pin_to_desktop=False, working_dir=str(workdir),
    )
    assert info.name == "roundtrip-01"
    async with CDPClient(ws_url=get_ws_url(port=9334, target_type="browser")) as cdp:
        await cdp.send(method="Storage.setCookies", params={"cookies": [
            {"name": "sid", "value": "session-only", "domain": "example.test", "path": "/"},
        ]})
        await cdp.send(method="Target.createTarget", params={"url": f"file://{page}"})
    await asyncio.sleep(1)

    plan = await asyncio.to_thread(snapshot.plan_save, "roundtrip-01")
    version = await asyncio.to_thread(snapshot.save_instance, plan, stop=True)
    assert version.info["mode"] == "stopped"
    assert "roundtrip-01" not in json.loads((tmp_path / "registry.json").read_text())

    report = await asyncio.to_thread(snapshot.restore_version, version)
    try:
        assert report["name"] == "roundtrip-01"
        assert report["port"] == 9334
        async with CDPClient(ws_url=get_ws_url(port=9334, target_type="browser")) as cdp:
            cookies = (await cdp.send(method="Storage.getCookies"))["cookies"]
            targets = (await cdp.send(method="Target.getTargets"))["targetInfos"]
        assert {"sid": "session-only"}.items() <= {c["name"]: c["value"] for c in cookies}.items()
        assert any(t["url"] == f"file://{page}" for t in targets)
    finally:
        await asyncio.to_thread(registry.stop, instance_name="roundtrip-01")


def test_display_helpers_on_a_display_that_does_not_exist():
    from chrome_agent import desktop

    assert desktop.display_running(":65000") is False
    assert desktop.virtual_display_server(":65000") is None
    assert desktop.display_running("not-a-display") is False


def test_virtual_display_blocks_restore_until_started(store, key):
    version = snapshot.Version(name="v-01", stamp="20260901T000000Z", path="/nonexistent", info={})
    state = {
        "instance": "v-01", "port": 65001,
        "launch": {"virtual_display": {"display": ":65000", "server": ["Xvfb", ":65000"]}},
    }
    problem = snapshot.check_restorable(version, state, any_port=False)
    assert "virtual display :65000" in problem and "--start-display" in problem
    assert snapshot.check_restorable(version, state, any_port=False, start_display=True) is None
