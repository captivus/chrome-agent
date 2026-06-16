"""Tests for the window-border marker.

Covers the pure functions: per-instance color derivation and overlay-script
construction. The guard's live behavior (auto-attach to every tab, injection,
title prefixing, lifecycle) requires a real visible window and is verified by
driving a headed browser -- see research/2026-06-16-detection-audit.md and the
window-border verification in that work.
"""

import re

from chrome_agent.window_border import (
    _PALETTE,
    build_overlay_script,
    derive_color,
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
