"""Tests for the per-instance supervisor.

Covers the pure functions: per-instance color derivation and overlay-script
construction. The supervisor's live behavior (auto-attach to every tab,
injection, title prefixing, and deregister-on-close lifecycle) requires a real
visible window and is verified by driving a headed browser -- see
planning/03-specs/BRW-03-learnings/01-detection-audit.md and the supervisor verification.
"""

import re

import pytest

import chrome_agent.registry as registry_mod
import chrome_agent.supervisor as supervisor_mod
from chrome_agent.supervisor import (
    _PALETTE,
    _browser_gone,
    build_overlay_script,
    derive_color,
    run_supervisor,
)

_HEX = re.compile(r"^#[0-9a-f]{6}$")


def test_palette_is_distinct_valid_hex():
    """Every palette color is a valid 6-digit hex and the palette has no dupes."""
    assert len(_PALETTE) == len(set(_PALETTE)), "palette has duplicate colors"
    for color in _PALETTE:
        assert _HEX.match(color), f"not a valid hex color: {color}"


def test_derive_color_is_deterministic():
    """The same instance name always yields the same color."""
    assert derive_color("myproject-01") == derive_color("myproject-01")


def test_derive_color_comes_from_palette():
    """Derived colors are always palette members (never a deceptive near-match)."""
    for name in ("a-01", "b-02", "roark-property-management-01", "downloads-02", "x"):
        assert derive_color(name) in _PALETTE


def test_derive_color_spreads_across_palette():
    """Different names map across the palette, not all to one color."""
    colors = {derive_color(f"instance-{i:02d}") for i in range(50)}
    assert len(colors) > 1, "derive_color collapsed many names to a single color"


def test_build_overlay_script_embeds_identity():
    """The overlay script embeds the instance name, color, and host id."""
    script = build_overlay_script(name="myproj-01", color="#1976d2", host_id="_caABCDEF")
    assert "myproj-01" in script
    assert "#1976d2" in script
    assert "_caABCDEF" in script


def test_build_overlay_script_is_self_contained_iife():
    """The script is a side-effect-free IIFE (no globals) using a closed shadow DOM."""
    script = build_overlay_script(name="n-01", color="#1976d2", host_id="_caX")
    assert script.startswith("(() => {")
    assert script.rstrip().endswith("})();")
    # closed shadow DOM keeps the border markup out of the page's reach
    assert "attachShadow" in script and "closed" in script
    # idempotent title prefixing (re-applies, never double-prefixes)
    assert "indexOf(PREFIX)" in script


def test_build_overlay_script_escapes_quotes_in_name():
    """A name with quotes must not break the generated JS string literals."""
    script = build_overlay_script(name='ev"il-01', color="#1976d2", host_id="_caX")
    # json.dumps escapes the embedded quote rather than terminating the literal
    assert '"ev\\"il-01"' in script


# --- lifecycle: retire only when the browser is truly gone -------------------
#
# Regression coverage for the suspend/resume orphaning bug: a dropped CDP
# connection (severed by host suspend) must NOT retire a still-running instance.


@pytest.mark.asyncio
async def test_browser_gone_true_when_port_dead(monkeypatch):
    """A port that is not listening means the browser really closed."""
    monkeypatch.setattr(registry_mod, "_port_is_listening", lambda port: False)
    assert await _browser_gone(9222) is True


@pytest.mark.asyncio
async def test_browser_gone_false_when_port_stays_up(monkeypatch):
    """A port that stays up through the grace window means the drop was transient."""
    monkeypatch.setattr(registry_mod, "_port_is_listening", lambda port: True)
    monkeypatch.setattr(supervisor_mod, "_RETIRE_GRACE_SECONDS", 0.05)
    assert await _browser_gone(9222) is False


@pytest.mark.asyncio
async def test_supervisor_reconnects_on_transient_drop_not_retire(monkeypatch):
    """The core regression: a transient drop (browser still alive) reconnects
    and does NOT deregister; the instance is only retired once the browser is
    actually gone.

    Against the pre-fix code -- which deregistered unconditionally after the
    first dropped connection -- this fails: it would deregister after one drop
    and never reconnect.
    """
    supervise_calls = {"n": 0}

    async def fake_supervise(*, port, draw_border, source):
        # Simulate the long-lived CDP connection dropping immediately.
        supervise_calls["n"] += 1

    # First drop: browser still alive (transient -> reconnect).
    # Second drop: browser gone (-> retire and exit).
    gone_sequence = iter([False, True])

    async def fake_browser_gone(port):
        return next(gone_sequence)

    deregistered = {}

    def fake_deregister(*, instance_name, registry_path=None):
        deregistered["name"] = instance_name
        return True

    monkeypatch.setattr(supervisor_mod, "_supervise_connection", fake_supervise)
    monkeypatch.setattr(supervisor_mod, "_browser_gone", fake_browser_gone)
    monkeypatch.setattr(registry_mod, "deregister", fake_deregister)

    await run_supervisor(port=9222, name="answerai-01", draw_border=False)

    # Reconnected after the transient drop (two supervise cycles), and retired
    # only after the second drop revealed the browser was truly gone.
    assert supervise_calls["n"] == 2
    assert deregistered.get("name") == "answerai-01"
