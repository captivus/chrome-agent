"""Tests for CLI-01: One-Shot Commands.

Tests the chrome-agent CLI using subprocess invocations.
Runs against a real browser on port 9333 (session fixture).
"""

import json
import subprocess
import sys

import pytest

CDP_PORT = 9333


def _run_cli(*args: str, timeout: int = 15) -> subprocess.CompletedProcess:
    """Run chrome-agent CLI and return the result."""
    return subprocess.run(
        [sys.executable, "-m", "chrome_agent", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# CDP one-shot
# ---------------------------------------------------------------------------


def test_cdp_one_shot(browser_session):
    """CDP method one-shot: send a command, get JSON response."""
    result = _run_cli(
        "--port", str(CDP_PORT),
        "Runtime.evaluate",
        '{"expression": "1+1", "returnByValue": true}',
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["result"]["value"] == 2


# ---------------------------------------------------------------------------
# Status command
# ---------------------------------------------------------------------------


def test_status_running(browser_session):
    """Status reports browser running with version."""
    result = _run_cli("status", "--port", str(CDP_PORT))
    assert result.returncode == 0
    assert "Browser running" in result.stdout


def test_status_not_running():
    """Status reports no browser on empty port."""
    result = _run_cli("status", "--port", "9444")
    assert result.returncode == 0
    assert "No browser running" in result.stdout


# ---------------------------------------------------------------------------
# Unknown command
# ---------------------------------------------------------------------------


def test_unknown_command():
    """Unknown command produces error."""
    result = _run_cli("foobar")
    assert result.returncode == 1
    assert "Unknown command" in result.stderr


# ---------------------------------------------------------------------------
# Malformed JSON
# ---------------------------------------------------------------------------


def test_malformed_json(browser_session):
    """Malformed JSON params produce error."""
    result = _run_cli(
        "--port", str(CDP_PORT),
        "Page.navigate",
        "{bad}",
    )
    assert result.returncode == 1
    assert "json" in result.stderr.lower() or "error" in result.stderr.lower()


# ---------------------------------------------------------------------------
# No browser for CDP method
# ---------------------------------------------------------------------------


def test_cdp_no_browser():
    """CDP method with no browser produces error."""
    result = _run_cli(
        "--port", "9444",
        "Runtime.evaluate",
        '{"expression": "1"}',
    )
    assert result.returncode == 1
    assert "error" in result.stderr.lower() or "no browser" in result.stderr.lower()


# ---------------------------------------------------------------------------
# No arguments / help
# ---------------------------------------------------------------------------


def test_no_arguments():
    """No arguments shows help/usage."""
    result = _run_cli()
    assert result.returncode == 0
    assert len(result.stdout) > 0


# ---------------------------------------------------------------------------
# Cleanup command
# ---------------------------------------------------------------------------


def test_cleanup():
    """Cleanup command runs without error."""
    result = _run_cli("cleanup")
    assert result.returncode == 0
    assert "cleaned up" in result.stdout.lower()
