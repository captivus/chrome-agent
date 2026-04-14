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
