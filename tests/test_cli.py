"""Tests for CLI-01: One-Shot Commands (iteration 2).

Tests the CLI routing, instance name resolution, and command forms.
Uses subprocess invocations for integration tests.
"""

import json
import re
import shutil
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
    assert "only one target selector" in result.stderr.lower()
    assert "--target, --url" in result.stderr


def test_explicit_target_selectors_are_mutually_exclusive():
    """The explicit selectors join the same exclusivity rule as --target/--url."""
    result = _run_cli(
        "--target-id", "ABC", "--target-index", "1", "mysite", "Page.navigate", '{"url": "x"}'
    )
    assert result.returncode == 1
    assert "only one target selector" in result.stderr.lower()


def test_extract_flags_maps_each_selector_to_its_resolution():
    """Each flag carries its own resolution; bare --target defers to shape."""
    from chrome_agent.cli import _extract_flags

    assert _extract_flags(["mysite", "--target", "2"]) == (["mysite"], "2", None)
    assert _extract_flags(["mysite", "--target-id", "2"]) == (["mysite"], "2", "id")
    assert _extract_flags(["mysite", "--target-index", "2"]) == (["mysite"], "2", "index")
    assert _extract_flags(["mysite", "--url", "x.com"]) == (["mysite"], "x.com", "url")
    assert _extract_flags(["mysite", "Page.navigate"]) == (["mysite", "Page.navigate"], None, None)


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
        cli._run_stop(args=["deadinst"], target_spec="1", target_by=None)
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

    # Resolve the CLI's instance lookup to the fixture browser, whatever name is
    # passed -- including the pattern resolution the one-shot now runs first, so
    # this test stays about ambiguous TABS rather than ambiguous instances.
    monkeypatch.setattr(
        "chrome_agent.registry.resolve_instance_name",
        lambda name_or_pattern, registry_path=None: name_or_pattern,
    )
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
                target_by=None,
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

    async def fake_one_shot(instance_name, method, params_str, target_spec, target_by):
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

    async def fake_one_shot(instance_name, method, params_str, target_spec, target_by):
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


# ---------------------------------------------------------------------------
# Instance patterns -- fan-out where it is unambiguous, refusal where it isn't
# ---------------------------------------------------------------------------


def _seed_registry(tmp_path, monkeypatch, *names: str) -> str:
    """Point the registry at a temp file holding the given instance names."""
    import json as _json

    reg_path = str(tmp_path / "registry.json")
    with open(reg_path, "w") as f:
        _json.dump({
            name: {
                "port": 9222 + index,
                "pid": 999000 + index,
                "browser_version": "Chrome/151",
                "user_data_dir": str(tmp_path / name),
                "pid_start": "0",
            }
            for index, name in enumerate(names)
        }, f)
    monkeypatch.setattr("chrome_agent.registry.REGISTRY_PATH", reg_path)
    return reg_path


def test_stop_pattern_stops_every_match(tmp_path, monkeypatch, capsys):
    """`stop '<glob>'` stops each matching instance and leaves the rest alone."""
    from chrome_agent import cli, registry

    _seed_registry(tmp_path, monkeypatch, "mysite-01", "mysite-02", "other-01")

    stopped = []
    monkeypatch.setattr(
        registry,
        "stop",
        lambda instance_name, **kwargs: stopped.append(instance_name) or f"Stopped {instance_name}",
    )

    cli._run_stop(args=["mysite-*"], target_spec=None, target_by=None)

    assert stopped == ["mysite-01", "mysite-02"]
    out = capsys.readouterr().out
    assert "matched 2 instances" in out
    assert "mysite-01, mysite-02" in out
    assert "other-01" not in out


def test_stop_pattern_prints_matches_before_acting(tmp_path, monkeypatch, capsys):
    """The match summary is printed before the first stop, so a broad pattern
    leaves a record of what it swept up even if a later stop fails."""
    from chrome_agent import cli, registry

    _seed_registry(tmp_path, monkeypatch, "mysite-01", "mysite-02")

    def _boom(instance_name, **kwargs):
        raise RuntimeError("browser gone")

    monkeypatch.setattr(registry, "stop", _boom)

    with pytest.raises(SystemExit) as exc_info:
        cli._run_stop(args=["mysite-*"], target_spec=None, target_by=None)

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "mysite-01, mysite-02" in captured.out
    assert "Error stopping mysite-01" in captured.err
    assert "Error stopping mysite-02" in captured.err


def test_stop_pattern_with_target_selector_is_refused(tmp_path, monkeypatch, capsys):
    """Closing one tab across several browsers is meaningless, so it errors."""
    from chrome_agent import cli, registry

    _seed_registry(tmp_path, monkeypatch, "mysite-01", "mysite-02")
    monkeypatch.setattr(registry, "stop", lambda **kwargs: pytest.fail("must not stop"))

    with pytest.raises(SystemExit) as exc_info:
        cli._run_stop(args=["mysite-*"], target_spec="1", target_by="index")

    assert exc_info.value.code == 1
    assert "target selector closes one tab" in capsys.readouterr().err


def test_stop_pattern_no_match_exits_nonzero(tmp_path, monkeypatch, capsys):
    """A glob that matches nothing is an error, not a silent no-op."""
    from chrome_agent import cli, registry

    _seed_registry(tmp_path, monkeypatch, "mysite-01")
    monkeypatch.setattr(registry, "stop", lambda **kwargs: pytest.fail("must not stop"))

    with pytest.raises(SystemExit) as exc_info:
        cli._run_stop(args=["nosuch-*"], target_spec=None, target_by=None)

    assert exc_info.value.code == 1
    assert "matched no instances" in capsys.readouterr().err


def test_status_pattern_lists_only_matches(tmp_path, monkeypatch, capsys):
    """`status '<glob>'` filters the listing to the matching instances."""
    from chrome_agent import cli

    _seed_registry(tmp_path, monkeypatch, "mysite-01", "mysite-02", "other-01")
    monkeypatch.setattr(
        "chrome_agent.registry._instance_is_alive",
        lambda *a, **k: False,
    )

    cli._run_status(args=["mysite-*"])

    listed = [entry["name"] for entry in json.loads(capsys.readouterr().out)]
    assert listed == ["mysite-01", "mysite-02"]


def test_one_shot_pattern_matching_several_errors_with_candidates(tmp_path, monkeypatch, capsys):
    """A one-shot acts on one browser, so a multi-match names the candidates."""
    import asyncio

    from chrome_agent import cli

    _seed_registry(tmp_path, monkeypatch, "mysite-01", "mysite-02")

    with pytest.raises(SystemExit) as exc_info:
        asyncio.run(cli._run_cdp_one_shot(
            instance_name="mysite-*",
            method="Page.navigate",
            params_str='{"url": "https://example.com"}',
            target_spec=None,
            target_by=None,
        ))

    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert "matches 2 instances" in err
    assert "mysite-01, mysite-02" in err


def test_pattern_first_arg_routes_as_instance_not_method(tmp_path, monkeypatch):
    """A glob is always an instance argument -- method names are not globbable."""
    from chrome_agent import cli

    _seed_registry(tmp_path, monkeypatch, "mysite-01")

    captured = {}

    async def fake_one_shot(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(cli, "_run_cdp_one_shot", fake_one_shot)
    monkeypatch.setattr(sys, "argv", [
        "chrome-agent", "Runtime.eval*", "Page.navigate", '{"url": "https://example.com"}',
    ])

    cli.main()

    assert captured["instance_name"] == "Runtime.eval*"
    assert captured["method"] == "Page.navigate"


# ---------------------------------------------------------------------------
# Shell completions
# ---------------------------------------------------------------------------


def test_completions_zsh_prints_a_loadable_completion():
    """`completions zsh` prints the packaged completion, compdef header first."""
    result = _run_cli("completions", "zsh")

    assert result.returncode == 0
    assert result.stdout.startswith("#compdef chrome-agent")
    assert "_chrome-agent() {" in result.stdout
    assert "compdef _chrome-agent chrome-agent" in result.stdout


def test_completions_zsh_is_valid_zsh():
    """The shipped completion parses as zsh -- a syntax error would ship broken.

    Guards the file that every user's shell sources; a typo in it is invisible
    to the Python tests that never execute it.
    """
    zsh = shutil.which("zsh")
    if zsh is None:
        pytest.skip("zsh not installed")

    script = _run_cli("completions", "zsh").stdout
    check = subprocess.run([zsh, "-n"], input=script, capture_output=True, text=True, timeout=15)

    assert check.returncode == 0, f"zsh -n rejected the completion:\n{check.stderr}"


def test_completions_instances_emits_describe_format(tmp_path, monkeypatch, capsys):
    """`completions instances` prints one `name:description` line per instance.

    That colon-separated shape is what zsh's _describe consumes, so the
    completion menu shows a description beside each instance name.
    """
    from chrome_agent import cli

    _seed_registry(tmp_path, monkeypatch, "mysite-01", "other-01")
    monkeypatch.setattr("chrome_agent.registry._instance_is_alive", lambda *a, **k: False)

    cli._run_completions(args=["instances"])

    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 2
    for line in lines:
        name, _, description = line.partition(":")
        assert name in ("mysite-01", "other-01")
        assert description.startswith("port ")
        assert "DEAD" in description


def test_completions_instances_counts_tabs(tmp_path, monkeypatch, capsys):
    """A live instance is described by its port and tab count, singular or plural."""
    from chrome_agent import cli
    from chrome_agent.instance_status import PageTarget

    _seed_registry(tmp_path, monkeypatch, "mysite-01", "other-01")
    monkeypatch.setattr("chrome_agent.registry._instance_is_alive", lambda *a, **k: True)

    def _targets(*, port):
        count = 1 if port == 9222 else 3
        return [
            PageTarget(target_id="T" * 32, short_id="TTTTTTTT", index=i, url="", title="")
            for i in range(1, count + 1)
        ]

    monkeypatch.setattr("chrome_agent.instance_status.query_targets", _targets)

    cli._run_completions(args=["instances"])

    out = capsys.readouterr().out
    assert "mysite-01:port 9222 -- 1 tab\n" in out
    assert "other-01:port 9223 -- 3 tabs\n" in out


def test_completions_requires_a_target(capsys):
    """Bare `completions`, and an unknown target, both error with the usage."""
    from chrome_agent import cli

    with pytest.raises(SystemExit) as exc_info:
        cli._run_completions(args=[])
    assert exc_info.value.code == 1
    assert "completions <zsh | instances>" in capsys.readouterr().err

    with pytest.raises(SystemExit) as exc_info:
        cli._run_completions(args=["bash"])
    assert exc_info.value.code == 1
    assert "unknown completions target: bash" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Protocol completions (CDP methods and events)
# ---------------------------------------------------------------------------


SCHEMA_FIXTURE = {
    "domains": [
        {
            "domain": "Page",
            "commands": [
                {"name": "navigate", "description": "Navigates current page to the given URL."},
                {"name": "reload", "description": "Reloads given page:\nwith a colon and a newline."},
                {"name": "bringToFront"},
            ],
            "events": [
                {"name": "loadEventFired", "description": "Fired when the page loads."},
            ],
        },
    ],
}


def _fake_instance(monkeypatch, *, alive=True, version="Chrome/151.0.0.1"):
    from chrome_agent.registry import InstanceInfo

    info = InstanceInfo(
        name="mysite-01", port=9222, pid=999, browser_version=version,
        user_data_dir="", alive=alive,
    )
    monkeypatch.setattr("chrome_agent.registry.lookup", lambda **kw: info)
    monkeypatch.setattr("chrome_agent.registry.enumerate_instances", lambda **kw: [info])
    return info


def test_completions_methods_reads_the_live_protocol(tmp_path, monkeypatch, capsys):
    """Methods come from the running browser, one Domain.method per line."""
    from chrome_agent import cli

    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    _fake_instance(monkeypatch)
    monkeypatch.setattr("chrome_agent.protocol.fetch_protocol_schema", lambda port: SCHEMA_FIXTURE)

    cli._run_completions(args=["methods", "mysite-01"])

    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "Page.navigate:Navigates current page to the given URL."
    # A multi-line CDP description must collapse to one line -- each extra line
    # would otherwise read as its own bogus candidate -- by joining rather than
    # truncating, since CDP wraps its prose at arbitrary points and a first-line
    # cut ends mid sentence.
    assert lines[1] == "Page.reload:Reloads given page: with a colon and a newline."
    # A method with no description still gets its (empty) description field.
    assert lines[2] == "Page.bringToFront:"


def test_completions_events_reads_the_event_list(tmp_path, monkeypatch, capsys):
    """Events come from the same schema, from the events key rather than commands."""
    from chrome_agent import cli

    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    _fake_instance(monkeypatch)
    monkeypatch.setattr("chrome_agent.protocol.fetch_protocol_schema", lambda port: SCHEMA_FIXTURE)

    cli._run_completions(args=["events", "mysite-01"])

    assert capsys.readouterr().out == "Page.loadEventFired:Fired when the page loads.\n"


def test_completions_methods_cache_avoids_a_second_fetch(tmp_path, monkeypatch, capsys):
    """The second call is served from disk without contacting the browser.

    zsh runs completion on every keystroke when autosuggestions use the
    completion strategy, so an uncached lookup is an HTTP round trip per
    character typed.
    """
    from chrome_agent import cli

    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    _fake_instance(monkeypatch)

    calls = []

    def _fetch(port):
        calls.append(port)
        return SCHEMA_FIXTURE

    monkeypatch.setattr("chrome_agent.protocol.fetch_protocol_schema", _fetch)

    cli._run_completions(args=["methods", "mysite-01"])
    first = capsys.readouterr().out
    cli._run_completions(args=["methods", "mysite-01"])
    second = capsys.readouterr().out

    assert calls == [9222], "the cached call still fetched from the browser"
    assert second == first, "the cache served different bytes than the fetch"
    cached = tmp_path / "chrome-agent" / "protocol-Chrome-151.0.0.1-commands.txt"
    assert cached.exists()


def test_completions_methods_cache_key_follows_the_browser_version(tmp_path, monkeypatch, capsys):
    """A Chrome upgrade changes the key, so the stale protocol is never served."""
    from chrome_agent import cli

    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    monkeypatch.setattr("chrome_agent.protocol.fetch_protocol_schema", lambda port: SCHEMA_FIXTURE)

    _fake_instance(monkeypatch, version="Chrome/151.0.0.1")
    cli._run_completions(args=["methods", "mysite-01"])
    capsys.readouterr()

    _fake_instance(monkeypatch, version="Chrome/152.0.0.1")
    cli._run_completions(args=["methods", "mysite-01"])
    capsys.readouterr()

    names = sorted(p.name for p in (tmp_path / "chrome-agent").iterdir())
    assert names == [
        "protocol-Chrome-151.0.0.1-commands.txt",
        "protocol-Chrome-152.0.0.1-commands.txt",
    ]


def test_completions_methods_silent_when_no_browser(tmp_path, monkeypatch, capsys):
    """No live instance means no candidates -- not an error mid-command-line."""
    from chrome_agent import cli

    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    monkeypatch.setattr("chrome_agent.registry.enumerate_instances", lambda **kw: [])

    cli._run_completions(args=["methods"])

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_completions_methods_silent_when_the_named_instance_is_dead(tmp_path, monkeypatch, capsys):
    """A dead instance cannot answer, and saying so at Tab time would be noise."""
    from chrome_agent import cli

    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    _fake_instance(monkeypatch, alive=False)

    cli._run_completions(args=["methods", "mysite-01"])

    assert capsys.readouterr().out == ""


def test_protocol_cache_is_skipped_without_a_version(monkeypatch):
    """No recorded browser version means no cache key -- re-fetch rather than
    serve one browser's protocol under another's name."""
    from chrome_agent import cli

    assert cli._protocol_cache_path(browser_version="", kind="commands") is None
