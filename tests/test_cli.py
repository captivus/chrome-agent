"""Tests for CLI-01: One-Shot Commands (iteration 2).

Tests the CLI routing, instance name resolution, and command forms.
Uses subprocess invocations for integration tests.
"""

import json
import re
import subprocess
import sys

import pytest


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    """Run chrome-agent CLI as a subprocess."""
    return subprocess.run(
        [sys.executable, "-m", "chrome_agent", *args],
        capture_output=True,
        text=True,
        timeout=15,
    )


# ---------------------------------------------------------------------------
# Basic routing
# ---------------------------------------------------------------------------


def test_no_arguments():
    """No arguments shows usage text."""
    result = _run_cli()
    assert result.returncode == 0
    assert "chrome-agent" in result.stdout.lower()


def test_help_flag():
    """--help shows usage text."""
    result = _run_cli("--help")
    assert result.returncode == 0
    assert "chrome-agent" in result.stdout.lower()


def test_version_flag():
    """--version prints 'chrome-agent <version>' and exits 0."""
    result = _run_cli("--version")
    assert result.returncode == 0
    assert result.stdout.lower().startswith("chrome-agent")
    assert re.search(r"\d+\.\d+", result.stdout), f"no version number in: {result.stdout!r}"


def test_version_short_flag():
    """-V is an alias for --version."""
    result = _run_cli("-V")
    assert result.returncode == 0
    assert re.search(r"\d+\.\d+", result.stdout), f"no version number in: {result.stdout!r}"


def test_unknown_command():
    """Unknown non-dot command gives helpful error."""
    result = _run_cli("foobar")
    assert result.returncode == 1
    assert "error" in result.stderr.lower()


def test_cleanup():
    """Cleanup command runs without error."""
    result = _run_cli("cleanup")
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# Status command
# ---------------------------------------------------------------------------


def test_status():
    """Status command runs without error."""
    result = _run_cli("status")
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# Help command
# ---------------------------------------------------------------------------


def test_help_no_args():
    """Help with no args shows domains or usage."""
    result = _run_cli("help")
    assert result.returncode == 0
    assert len(result.stdout) > 0


def test_help_domain_query():
    """help <Domain> (no instance named) shows real domain detail, never the usage banner.

    The dispatch bug: `help Page` silently degraded to the static usage banner
    whenever no single instance auto-resolved (zero, or two-plus, live browsers).
    With a browser reachable, the output must be the Page domain itself -- not the
    operational-usage text. With none reachable, it must be a clean actionable
    error (exit 1, no traceback), not the banner. Asserting only returncode == 0
    (the prior test) passed on the bug, since the banner also exits 0.
    """
    result = _run_cli("help", "Page")
    if result.returncode == 0:
        assert "Domain: Page" in result.stdout, f"expected Page domain detail, got:\n{result.stdout!r}"
        assert "Operational commands:" not in result.stdout, "degraded to the usage banner"
    else:
        assert result.returncode == 1
        assert "Traceback" not in (result.stdout + result.stderr)
        assert "browser" in result.stderr.lower()


def test_help_method_query():
    """help <Domain.method> (no instance named) shows method detail, never the usage banner."""
    result = _run_cli("help", "Page.navigate")
    if result.returncode == 0:
        assert "Page.navigate" in result.stdout
        assert "Parameters:" in result.stdout
        assert "Operational commands:" not in result.stdout, "degraded to the usage banner"
    else:
        assert result.returncode == 1
        assert "Traceback" not in (result.stdout + result.stderr)
        assert "browser" in result.stderr.lower()


def test_help_query_no_browser_clean_error(monkeypatch, capsys):
    """help <Domain> with no live browser emits a clean actionable error, not the usage banner.

    The silent-swallow half of the dispatch bug: _run_help caught ConnectionError
    on the no-instance path and printed the generic usage banner. A user who asked
    for `help Page` should instead get a clear "no running browser ... launch"
    error on stderr, exit 1, no traceback. Run in-process (not subprocess) so the
    empty-registry state is deterministic regardless of what browsers are running.
    """
    from chrome_agent import cli

    monkeypatch.setattr("chrome_agent.registry.enumerate_instances", lambda *a, **k: [])
    with pytest.raises(SystemExit) as exc_info:
        cli._run_help(args=["Page"])
    assert exc_info.value.code == 1
    out = capsys.readouterr()
    assert "Operational commands:" not in out.out, "degraded to the usage banner"
    assert "Traceback" not in (out.out + out.err)
    assert "browser" in out.err.lower()
    assert "launch" in out.err.lower()


# ---------------------------------------------------------------------------
# Flag extraction
# ---------------------------------------------------------------------------


def test_target_url_mutual_exclusivity():
    """--target and --url together produces error."""
    result = _run_cli("--target", "ABC", "--url", "test.com", "mysite", "Page.navigate", '{"url": "x"}')
    assert result.returncode == 1
    assert "cannot specify both" in result.stderr.lower()


# ---------------------------------------------------------------------------
# Malformed input
# ---------------------------------------------------------------------------


def test_malformed_json():
    """Malformed JSON params produces clear error."""
    result = _run_cli("someinstance", "Page.navigate", "{bad json}")
    assert result.returncode == 1
    assert "error" in result.stderr.lower()


def test_unknown_instance_one_shot_clean_error():
    """An unknown instance name in a one-shot emits a clean Error:, not a traceback.

    Regression: _run_cdp_one_shot resolved the instance with lookup() but did not
    catch InstanceNotFoundError (unlike status/stop/help), so an unknown instance
    name crashed with an uncaught Python traceback instead of the clean
    `Error: Instance '<name>' not found. Available: ...` message every other
    command path emits.

    The discriminating signal is the ABSENCE of a traceback: the broken code
    already exits 1 *and* the available-instances list already appears inside the
    traceback, so asserting only on exit code or on "not found" would pass on the
    bug. The traceback check is what makes this test able to fail on the defect.
    """
    result = _run_cli(
        "definitely-not-a-real-instance-xyz",
        "Runtime.evaluate",
        '{"expression": "1+1", "returnByValue": true}',
    )
    combined = result.stdout + result.stderr
    assert result.returncode == 1
    assert "Traceback" not in combined, f"uncaught traceback leaked:\n{combined}"
    assert result.stderr.startswith("Error:"), (
        f"expected clean 'Error:' prefix, got:\n{result.stderr!r}"
    )
    assert "not found" in result.stderr.lower()


def test_unknown_instance_stop_target_clean_error():
    """stop <unknown> --target N emits a clean Error:, not a traceback.

    Same error class as the one-shot path: _run_stop's target-resolution branch
    also called lookup() unguarded, so `stop <unknown> --target N` crashed with an
    uncaught traceback. Swept and fixed alongside the one-shot path so the whole
    error class -- not just the first reported instance -- is closed.
    """
    result = _run_cli("stop", "definitely-not-a-real-instance-xyz", "--target", "1")
    combined = result.stdout + result.stderr
    assert result.returncode == 1
    assert "Traceback" not in combined, f"uncaught traceback leaked:\n{combined}"
    assert result.stderr.startswith("Error:"), (
        f"expected clean 'Error:' prefix, got:\n{result.stderr!r}"
    )
    assert "not found" in result.stderr.lower()


def test_stop_target_dead_instance_clean_error(monkeypatch, capsys):
    """stop <registered-but-unreachable> --target N emits a clean Error:, not a traceback.

    The last member of the clean-error class: _run_stop's --target/--url branch
    fetched page targets via get_ws_url() inside asyncio.run(_get_targets()) with no
    guard -- so a registered instance whose browser had died (a stale registry entry,
    which the README notes happens for headless / abruptly-killed instances) leaked a
    ConnectionError traceback, even though the identical get_ws_url() call in the
    one-shot path was already guarded. Run in-process so the registered-but-dead state
    is deterministic without touching the real registry.
    """
    from chrome_agent import cli, registry
    from chrome_agent.registry import InstanceInfo

    # A registered instance whose browser is not listening (closed port).
    monkeypatch.setattr(
        registry,
        "lookup",
        lambda instance_name, registry_path=None: InstanceInfo(
            name=instance_name, port=59999, pid=1, browser_version="x", alive=False
        ),
    )
    with pytest.raises(SystemExit) as exc_info:
        cli._run_stop(args=["deadinst"], target_spec="1", url_spec=None)
    assert exc_info.value.code == 1
    out = capsys.readouterr()
    assert "Traceback" not in (out.out + out.err), f"uncaught traceback leaked:\n{out.err}"
    assert out.err.startswith("Error:"), f"expected clean 'Error:' prefix, got:\n{out.err!r}"


def test_one_shot_ambiguous_target_clean_error(browser_session, monkeypatch, capsys):
    """A one-shot against a multi-tab browser (no --target) emits a clean error, not a traceback.

    Broader member of the same error class as the instance-not-found fix:
    _run_cdp_one_shot caught CDPError and ConnectionError but not the
    AmbiguousTargetError that resolve_target raises when multiple page targets exist
    and no --target is given, so the one-shot crashed with an uncaught traceback
    instead of the formatted "Multiple page targets found. Specify one: ..." message
    the error type already carries.
    """
    import asyncio

    from chrome_agent import cli
    from chrome_agent.cdp_client import CDPClient, get_ws_url
    from chrome_agent.registry import InstanceInfo

    port = browser_session.port

    async def _create_tabs():
        ws = get_ws_url(port=port, target_type="browser")
        async with CDPClient(ws_url=ws) as cdp:
            ids = []
            for _ in range(2):
                r = await cdp.send(method="Target.createTarget", params={"url": "about:blank"})
                ids.append(r["targetId"])
            return ids

    async def _close_tabs(ids):
        ws = get_ws_url(port=port, target_type="browser")
        async with CDPClient(ws_url=ws) as cdp:
            for tid in ids:
                try:
                    await cdp.send(method="Target.closeTarget", params={"targetId": tid})
                except Exception:
                    pass

    # Resolve the CLI's instance lookup to the fixture browser, whatever name is passed.
    monkeypatch.setattr(
        "chrome_agent.registry.lookup",
        lambda instance_name, registry_path=None: InstanceInfo(
            name=instance_name, port=port, pid=browser_session.pid,
            browser_version="test", alive=True,
        ),
    )

    tab_ids = asyncio.run(_create_tabs())
    try:
        with pytest.raises(SystemExit) as exc_info:
            asyncio.run(cli._run_cdp_one_shot(
                instance_name="anyname",
                method="Page.captureScreenshot",
                params_str='{"format": "png"}',
                target_spec=None,
                url_spec=None,
            ))
        assert exc_info.value.code == 1
        out = capsys.readouterr()
        combined = out.out + out.err
        assert "Traceback" not in combined, f"uncaught traceback leaked:\n{combined}"
        assert "Specify one" in out.err or "Multiple page targets" in out.err, (
            f"expected the ambiguous-target listing, got:\n{out.err!r}"
        )
    finally:
        asyncio.run(_close_tabs(tab_ids))


def test_launch_chrome_not_found_clean_error(monkeypatch, capsys):
    """launch with no Chrome binary emits a clean error, not a traceback (same error class).

    _run_launch caught (RuntimeError, TimeoutError) but not BrowserNotFoundError, so a
    machine without Chrome installed crashed with an uncaught traceback instead of the
    "Chrome/Chromium not found. Searched: ..." message.
    """
    import asyncio

    from chrome_agent import cli

    monkeypatch.setattr("chrome_agent.launcher.find_chrome_binary", lambda: None)
    with pytest.raises(SystemExit) as exc_info:
        asyncio.run(cli._run_launch(args=[]))
    assert exc_info.value.code == 1
    out = capsys.readouterr()
    assert "Traceback" not in (out.out + out.err)
    assert "not found" in out.err.lower()


# ---------------------------------------------------------------------------
# Bare CDP method (backward compat)
# ---------------------------------------------------------------------------


def test_bare_cdp_method():
    """Bare CDP method (no instance name) routes correctly."""
    result = _run_cli("Runtime.evaluate", '{"expression": "1+1", "returnByValue": true}')
    # Either succeeds (auto-selects sole instance) or fails with clear error
    assert result.returncode in (0, 1)
    if result.returncode == 0:
        data = json.loads(result.stdout)
        assert "result" in data


# ---------------------------------------------------------------------------
# Dotted instance name routing (regression: instance names with dots such as
# "aroundchicago.tech-01" were being misrouted as bare CDP methods because the
# old dispatch used `if "." in command`. Fix uses registry lookup + a stricter
# Domain.method heuristic.)
# ---------------------------------------------------------------------------


def test_dotted_instance_name_routes_as_instance(monkeypatch):
    """An instance name containing dots must route as an instance, not a method.

    Regression: the old dispatch used `if "." in command` to detect bare CDP
    methods, which misrouted directory-derived instance names like
    "aroundchicago.tech-01" as methods.
    """
    from chrome_agent import cli
    from chrome_agent.registry import InstanceInfo

    # Fake registry: one dotted-name instance
    fake_instances = [
        InstanceInfo(name="aroundchicago.tech-01", port=9999,
                     pid=1, browser_version="Chrome/test", alive=True),
    ]
    monkeypatch.setattr(
        "chrome_agent.registry.enumerate_instances",
        lambda *a, **kw: fake_instances,
    )

    # Capture what _run_cdp_one_shot receives
    captured = {}

    async def fake_one_shot(instance_name, method, params_str, target_spec, url_spec):
        captured["instance_name"] = instance_name
        captured["method"] = method
        captured["params_str"] = params_str

    monkeypatch.setattr(cli, "_run_cdp_one_shot", fake_one_shot)

    # Invoke main() with the problematic argv
    monkeypatch.setattr(sys, "argv", [
        "chrome-agent",
        "aroundchicago.tech-01",
        "Runtime.evaluate",
        '{"expression":"1+1","returnByValue":true}',
    ])
    cli.main()

    assert captured["instance_name"] == "aroundchicago.tech-01"
    assert captured["method"] == "Runtime.evaluate"


def test_unregistered_dotted_first_arg_routes_as_method(monkeypatch):
    """If the first arg isn't registered but matches Domain.method shape, route as bare method."""
    from chrome_agent import cli

    # Empty registry
    monkeypatch.setattr(
        "chrome_agent.registry.enumerate_instances",
        lambda *a, **kw: [],
    )

    captured = {}

    async def fake_one_shot(instance_name, method, params_str, target_spec, url_spec):
        captured["instance_name"] = instance_name
        captured["method"] = method

    monkeypatch.setattr(cli, "_run_cdp_one_shot", fake_one_shot)

    monkeypatch.setattr(sys, "argv", [
        "chrome-agent",
        "Runtime.evaluate",
        '{"expression":"1+1","returnByValue":true}',
    ])
    cli.main()

    # Auto-select path: instance_name is None, method is the dotted first arg
    assert captured["instance_name"] is None
    assert captured["method"] == "Runtime.evaluate"
