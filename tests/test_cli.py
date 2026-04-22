"""Tests for CLI-01: One-Shot Commands (iteration 2).

Tests the CLI routing, instance name resolution, and command forms.
Uses subprocess invocations for integration tests.
"""

import json
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
    """Help with domain name shows domain info."""
    result = _run_cli("help", "Page")
    # May fail if no browser is accessible, which is OK
    assert result.returncode == 0


def test_help_method_query():
    """Help with Domain.method shows method details."""
    result = _run_cli("help", "Page.navigate")
    assert result.returncode == 0


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
