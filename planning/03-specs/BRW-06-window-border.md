# Feature Specification

> *This document is the complete definition of a single atomic feature -- what to build, how to validate it, what to observe during implementation, what it depends on, and (once implementation begins) its implementation history.*

## 1. Feature ID and Name

BRW-06: Window Border

## 2. User Story

As a user whose machine is being driven by an AI agent, I want an agent-launched Chrome window to be visually distinct from my own other Chrome windows, so that I can tell at a glance which window the agent is driving and never mistake it for one of my own.

## 3. Implementation Contract

### Level 1 -- Plain English

This feature marks an agent-launched, headed browser window so it is unmistakable among the user's other Chrome windows. While the browser is alive, every tab -- the one open at launch and any opened later -- is marked in two ways:

1. **In-page marker:** a colored border around the viewport plus a corner badge showing the instance name (e.g. `🤖 myproject-01`).
2. **Title prefix:** the page's own `document.title` is prefixed so the window reads as `🤖 <instance> — <the page's own title>` in the taskbar and Alt-Tab switcher. The page's own title is preserved -- the prefix is prepended, not substituted.

The border color is **stable per instance**: a given instance name always maps to the same color, drawn from a fixed, curated 14-color palette. The same machinery -- a single long-lived, detached supervisor process per instance (BRW-07) -- both holds the CDP connection that re-runs the marker on every new document and performs instance lifecycle (deregister-on-close). BRW-06 is the *visual* concern; BRW-07 is the *process / lifecycle* concern; they share one process.

The marker is drawn for **headed launches by default**. It is **suppressed** when (a) `--headless` (there is no visible window to mark), (b) `--no-window-border` (the user opted out), or (c) a `--fingerprint` profile is active (the in-page marker is page-observable, and stealth contexts are exactly where DOM/title-diffing detectors live -- see the detection audit in Learnings).

The injected code is engineered to leave the smallest possible page footprint: a side-effect-free IIFE that draws into a **closed** shadow DOM under a **randomized** host id, in an **isolated world**, leaking no globals; the border is click-through (`pointer-events:none`) so it never intercepts the agent's interactions.

### Level 2 -- Logic Flow (INPUT / LOGIC / OUTPUT)

**INPUT:**

- `name`: string -- the instance name (e.g. `myproject-01`); drives both the badge text and the derived color.
- `port`: integer -- CDP port of the running browser (the supervisor connects browser-level).
- `draw_border`: bool -- whether to draw the marker at all (the launcher passes `window_border and fp_profile is None`, and never spawns a supervisor for headless launches).
- `host_id`: string -- a randomized host element id (`_ca` + `secrets.token_hex(8)`), computed once per supervisor so reconnects reuse it and the overlay's idempotent guard suppresses redraws.

**LOGIC:**

```
derive_color(name):
    # Stable per-instance color from a fixed curated palette.
    digest = int(md5(name).hexdigest(), 16)
    return _PALETTE[digest % len(_PALETTE)]   # 14 vivid, well-separated colors


build_overlay_script(name, color, host_id):
    # Returns a side-effect-free IIFE string. The script:
    #   - computes PREFIX = "🤖 " + name + " — "
    #   - fixTitle(): if document.title does not already start with PREFIX,
    #       prepend it (idempotent -- never double-prefixes)
    #   - draw(): if no element with host_id exists, create a fixed,
    #       click-through (pointer-events:none) host <div>; attach a CLOSED
    #       shadow root holding the colored border + corner badge; append to
    #       documentElement. Returns true if drawn/already-present.
    #   - ensureDraw(): draw now, else MutationObserver until the DOM is ready
    #   - watchTitle(): fixTitle now, then MutationObserver on <title>/<head>
    #       to re-apply on SPA/title changes, and on documentElement to re-draw
    #       if the page wipes the host element
    # name/color/host_id are embedded via json.dumps (quote-safe).


# Injection onto one page session (handled by the supervisor, BRW-07):
_setup_session(cdp, session_id, source):
    cdp.send("Page.enable", session_id)
    # Future documents: re-run on every navigation, in an ISOLATED WORLD.
    cdp.send("Page.addScriptToEvaluateOnNewDocument",
             {"source": source, "worldName": ISOLATED_WORLD}, session_id)
    # The already-open document: a one-time injection.
    cdp.send("Runtime.evaluate", {"expression": source}, session_id)


# Cover all current + future tabs (handled by the supervisor, BRW-07):
_supervise_connection(port, draw_border, source):
    cdp = connect browser-level WebSocket on port
    if draw_border and source:
        cdp.on("Target.attachedToTarget", on_attached)   # one per page target
        cdp.send("Target.setAutoAttach",
                 {"autoAttach": True, "waitForDebuggerOnStart": False, "flatten": True})
    block until the connection drops
```

**OUTPUT:**

- `derive_color(name)` -> a `#rrggbb` string from the fixed palette (deterministic).
- `build_overlay_script(...)` -> a JavaScript IIFE string, ready to inject.
- Observable effect while the browser is alive: every page target shows the colored border + corner badge, and its window/tab title is prefixed with `🤖 <instance> — `. The marker re-draws if the page wipes it and re-applies the title prefix on SPA navigations.
- No return value from the injection path; the work is the side effect inside each page.

### Level 3 -- Formal Interfaces

```python
# Module-level constants (src/chrome_agent/supervisor.py)

ISOLATED_WORLD = "__chrome_agent_marker__"

# Curated palette of vivid, well-separated colors, each dark enough for white
# badge text. A fixed palette (vs. a continuous hue) avoids deceptively-similar
# colors for different instances.
_PALETTE: tuple[str, ...]  # 14 entries, e.g. "#d11149", "#1976d2", ...


def derive_color(name: str) -> str:
    """Derive a stable, distinct palette color from an instance name.

    Deterministic (same name -> same color); chosen from a fixed
    well-separated palette so different instances are visually distinct
    from each other, not just from un-marked Chrome.
    """
    ...


def build_overlay_script(*, name: str, color: str, host_id: str) -> str:
    """Build the IIFE injected into each page to draw the marker.

    Draws a fixed, click-through colored border + corner badge inside a
    closed shadow DOM, and keeps ``document.title`` prefixed (re-applied
    idempotently on SPA/title changes). Re-draws if the page wipes it.
    Leaks no globals.
    """
    ...
```

The injection and lifecycle entry points live in the same module and are owned by BRW-07 (Instance Supervisor); BRW-06's contribution is the visual machinery (`_PALETTE`, `derive_color`, `build_overlay_script`) plus the suppression policy applied at launch:

```python
# src/chrome_agent/launcher.py -- launch_browser(...)
#   window_border: bool = True   # parameter; --no-window-border sets it False
#
# Supervisor is spawned for headed launches only, with:
#   draw_border = window_border and fp_profile is None
# i.e. suppressed under --headless (no supervisor), --no-window-border, or
# an active --fingerprint profile.
```

## 4. Validation Contract

The contract splits cleanly into two tiers. The **pure functions** (`derive_color`, `build_overlay_script`) are deterministic and fully unit-testable. The **live behavior** (marker renders on all tabs including newly-opened, persists across navigation, distinct colors, suppression rules) needs a *real visible window* -- it cannot be verified by a headless unit test -- and so was validated by driving a headed browser and screenshotting (see Feedback Channels and Test Results).

### Level 1 -- Plain English Scenarios

Color is stable and distinct:
- Given an instance name, `derive_color` returns the same color every time it is called for that name.
- Given a derived color, it is always a member of the curated palette -- never an arbitrary near-match of another instance's color.
- Given many different names, the derived colors spread across the palette rather than collapsing to one.

Overlay script is correct and safe:
- Given a name, color, and host id, the generated script embeds all three, is a self-contained IIFE, and uses a closed shadow DOM.
- Given a name containing quotes, the generated script's JS string literals are not broken (the name is escaped via `json.dumps`).
- The title prefixing is idempotent -- the script checks `indexOf(PREFIX)` before prepending, so re-running it never double-prefixes.

Live behavior (verified by driving a headed browser):
- Given a headed launch, the colored border + badge render on the current tab and on every newly-opened tab.
- Given a marked window, navigating to a new page keeps the marker and the title prefix.
- Given two instances with different names, their borders are visually distinct colors.
- Given `--headless`, `--no-window-border`, or `--fingerprint`, no marker is drawn.

### Level 2 -- Test Logic (GIVEN / WHEN / THEN)

Scenario: Palette is distinct and valid
GIVEN: the curated `_PALETTE`
WHEN: each entry is inspected
THEN: every entry is a valid 6-digit hex color and there are no duplicates

Scenario: Color derivation is deterministic
GIVEN: an instance name "myproject-01"
WHEN: `derive_color` is called twice
THEN: both calls return the same color

Scenario: Derived color is a palette member
GIVEN: a set of representative instance names
WHEN: `derive_color` is called for each
THEN: every returned color is in `_PALETTE`

Scenario: Colors spread across the palette
GIVEN: 50 distinct instance names
WHEN: `derive_color` is called for each
THEN: more than one distinct color results (no collapse to a single color)

Scenario: Overlay script embeds identity
GIVEN: name "myproj-01", color "#1976d2", host id "_caABCDEF"
WHEN: `build_overlay_script` is called
THEN: the returned script contains the name, the color, and the host id

Scenario: Overlay script is a self-contained, safe IIFE
GIVEN: a name, color, and host id
WHEN: `build_overlay_script` is called
THEN: the script starts with "(() => {" and ends with "})();", references `attachShadow` with mode "closed", and uses `indexOf(PREFIX)` for idempotent title prefixing

Scenario: Overlay script escapes quotes in the name
GIVEN: a name containing a double quote (`ev"il-01`)
WHEN: `build_overlay_script` is called
THEN: the embedded literal is the escaped `"ev\"il-01"` -- the quote does not terminate the JS string

Scenario: Marker renders on all tabs and persists (live)
GIVEN: a headed browser launched with the marker enabled
WHEN: a tab is open at launch, a new tab is opened, and an existing tab navigates to a new URL
THEN: every tab shows the border + badge and a prefixed title; the marker survives navigation and appears on the newly-opened tab

Scenario: Suppression (live)
GIVEN: a launch with `--headless`, `--no-window-border`, or `--fingerprint`
WHEN: the browser is inspected
THEN: no host element, no border/badge, and no title prefix are present

### Level 3 -- Formal Test Definitions

```
test_palette_is_distinct_valid_hex:
    given: _PALETTE
    assert: len(_PALETTE) == len(set(_PALETTE))         # no duplicates
            all(re.match(r"^#[0-9a-f]{6}$", c) for c in _PALETTE)

test_derive_color_is_deterministic:
    assert: derive_color("myproject-01") == derive_color("myproject-01")

test_derive_color_comes_from_palette:
    for name in ("a-01", "b-02", "roark-property-management-01", "downloads-02", "x"):
        assert derive_color(name) in _PALETTE

test_derive_color_spreads_across_palette:
    colors = {derive_color(f"instance-{i:02d}") for i in range(50)}
    assert: len(colors) > 1

test_build_overlay_script_embeds_identity:
    script = build_overlay_script(name="myproj-01", color="#1976d2", host_id="_caABCDEF")
    assert: "myproj-01" in script and "#1976d2" in script and "_caABCDEF" in script

test_build_overlay_script_is_self_contained_iife:
    script = build_overlay_script(name="n-01", color="#1976d2", host_id="_caX")
    assert: script.startswith("(() => {")
            script.rstrip().endswith("})();")
            "attachShadow" in script and "closed" in script   # closed shadow DOM
            "indexOf(PREFIX)" in script                        # idempotent title prefix

test_build_overlay_script_escapes_quotes_in_name:
    script = build_overlay_script(name='ev"il-01', color="#1976d2", host_id="_caX")
    assert: '"ev\\"il-01"' in script   # json.dumps escapes, not terminates the literal

# Live behavior -- NOT a headless unit test; requires a real visible window.
# Verified by driving a headed browser and screenshotting (config C in the
# detection audit): border renders on current + newly-opened tabs, persists
# across navigation, distinct colors per instance, and is suppressed under
# --headless / --no-window-border / --fingerprint. The guard also exits with
# the browser (no orphan). See BRW-03-learnings/01-detection-audit.md.
```

## 5. Feedback Channels

### Visual

This is a visual feature, so the visual channel is primary and authoritative. Launch a headed browser, drive it to a page, and **screenshot the real visible window**: confirm the colored border frames the viewport, the corner badge reads `🤖 <instance>`, and the window/tab title shows the `🤖 <instance> — <page title>` prefix in the taskbar / Alt-Tab. Launch a second instance with a different name and screenshot both to confirm the colors are visibly distinct. Re-screenshot after navigating and after opening a new tab to confirm the marker persists and propagates. A unit test cannot stand in for this -- the marker only exists in a rendered window.

### Auditory

Inspect the marker's footprint and the page's self-report. Use `Runtime.evaluate` to query whether the randomized host element exists, read back `document.title`, and -- for the detection question -- drive `bot.sannysoft.com` and CreepJS and read their reported results. The audit's ground truth is that the marker's sannysoft results and CreepJS fingerprint ID are byte-identical to a vanilla launch; its only observable traces are the host `<div>` and the modified `document.title` (page-content artifacts, not automation signals).

### Tactile

Drive the marked browser as an agent would: open a session, navigate across multiple pages, open new tabs, and click through page content. Confirm (a) the border is click-through -- it never intercepts clicks (`pointer-events:none`), (b) the marker re-draws if a page wipes the DOM, and (c) the title prefix re-applies on SPA navigations without double-prefixing. Then close the window and confirm the supervisor exits (no orphan) and the instance is retired from the registry.

## 6. Dependencies

| Dependency | What this feature needs from it | Rationale |
|------------|--------------------------------|-----------|
| BRW-07 (Instance Supervisor) | The long-lived, detached per-instance process that holds the browser-level CDP connection, auto-attaches to every page target, and injects the overlay on each | The marker must re-run on every new document, which only happens while the registering connection is alive; BRW-06 is the visual payload that BRW-07's process carries. They share one process. |
| BRW-04 (Instance Registry) | The instance name | The name drives both the badge text and the derived color (name -> color mapping). |
| CDP-01 (CDP WebSocket Client) | `CDPClient` for browser-level connection and CDP commands | Injection uses `Page.addScriptToEvaluateOnNewDocument`, `Runtime.evaluate`, and `Target.setAutoAttach` over a CDP WebSocket. |

## 7. Scoping Decisions

| Decision | What prompted it | Rationale | Revisit when |
|----------|-----------------|-----------|--------------|
| Zero added automation-detection signal; suppress under `--fingerprint` | An empirical detection audit verified the marker's bot.sannysoft.com results and CreepJS fingerprint ID are **byte-identical** to a vanilla launch -- its only observable traces are the host `<div>` and the modified `document.title`, which are *page-content* artifacts, not automation signals | Because those traces *are* page-observable, the marker is suppressed under `--fingerprint`: bot-defended sites -- exactly where fingerprinting is used -- are where DOM/title-diffing detectors live. Generic/commercial anti-bot does not inspect for them. See the detection audit in Learnings. | A site is found that diffs its own DOM/title to detect the marker even in non-fingerprint contexts, or the audit's conclusions need re-validation against newer detectors. |
| Fixed 14-color curated palette, not a continuous hue | An earlier continuous-hue approach (hue derived from the name) produced near-identical reds for different names -- two instances could look like a match when they were not | A fixed, well-separated palette makes two instances either an obvious match or obviously different, never a deceptive near-match. Each color is also dark enough for white badge text. | More than ~14 simultaneously-distinguishable instances are routinely in use and the palette starts colliding visibly. |
| Closed shadow DOM, randomized host id, isolated world, side-effect-free IIFE | The audit's design implication: minimize even the page-DOM footprint and never reuse `fingerprint.py`'s `defineProperty` pattern (that pattern is itself a detection liability) | A closed shadow root keeps the markup out of the page's reach; a randomized host id avoids a fixed selector to match on; an isolated world means no globals touch the page. The marker reads as ordinary page content, nothing more. | A future need to expose the marker to the page (none anticipated). |
| Click-through border (`pointer-events:none`) | The agent drives the same page the marker overlays | The marker must never intercept the agent's clicks or the page's own interactions; a full-viewport overlay that captured events would break automation. | Never -- this is a hard constraint. |
| Idempotent title prefix; preserve the page's own title | SPA navigations and the page's own title-setting would otherwise either lose the page title or stack duplicate prefixes | `fixTitle` checks `indexOf(PREFIX)` before prepending and a MutationObserver re-applies it on title changes, so the title always reads `🤖 <instance> — <page title>` exactly once. | Never -- preserving the page's title is a requirement. |
| Marker drawn for headed launches only; on by default | A headless browser has no visible window to mark; the marker's purpose is human-visible disambiguation | Headless launches get no supervisor at all, so no marker. Headed launches draw it unless `--no-window-border` or `--fingerprint`. | If a headless-but-visible (e.g. remote VNC) workflow ever needs a marker. |

## 8. Learnings

| # | Topic | Type | Summary | Link |
|---|-------|------|---------|------|
| 1 | Detection audit (2026-06-16) | Empirical verification | Driving real harnesses (bot.sannysoft.com, CreepJS) across vanilla / fingerprint / window-border configs established that the marker adds **zero** automation-detection signal -- sannysoft results and CreepJS fingerprint ID byte-identical to vanilla. Its only traces are the host `<div>` and modified `document.title` (page-content, not automation). This drove the suppress-under-`--fingerprint` rule and the closed-shadow-DOM / randomized-host-id / isolated-world design. The audit also found that `fingerprint.py`'s old JS navigator overrides were net-negative (a tamper signature that *failed* sannysoft), prompting their removal. | BRW-03-learnings/01-detection-audit.md |
| 2 | Continuous hue -> fixed palette | Design correction | A continuous hue derived from the name produced near-identical reds for different instances. Replaced with a fixed curated palette indexed by md5(name), so instances are obviously same-or-different, never a deceptive near-match. | src/chrome_agent/supervisor.py (`_PALETTE`, `derive_color`) |
| 3 | Page-observable marker must be suppressed in stealth contexts | Design constraint | The in-page border/badge/title are findable in the DOM; bot-defended sites are where DOM/title-diffing detectors live, so the marker is gated off under `--fingerprint`. The lifecycle job (deregister-on-close) still runs. | src/chrome_agent/launcher.py (`draw_border = window_border and fp_profile is None`) |

---

## 9. Implementation Status

**Status:** Complete

## 10. Test Results

The pure-function surface is covered by unit tests in `tests/test_supervisor.py`; the live, window-dependent behavior was verified by driving a real headed browser (config C in the detection audit) and screenshotting, because it cannot be exercised by a headless unit test.

### Final Test Results

| Test | Result | Notes |
|------|--------|-------|
| test_palette_is_distinct_valid_hex | Pass | Every `_PALETTE` color is a valid 6-digit hex; no duplicates |
| test_derive_color_is_deterministic | Pass | Same name -> same color across calls |
| test_derive_color_comes_from_palette | Pass | Derived colors are always palette members (no deceptive near-match) |
| test_derive_color_spreads_across_palette | Pass | 50 distinct names map to more than one color (no collapse) |
| test_build_overlay_script_embeds_identity | Pass | Script embeds the name, color, and host id |
| test_build_overlay_script_is_self_contained_iife | Pass | IIFE shape; uses a closed shadow DOM; idempotent title prefixing (`indexOf(PREFIX)`) |
| test_build_overlay_script_escapes_quotes_in_name | Pass | A quoted name is `json.dumps`-escaped, not literal-terminating |
| Live: border renders on current + newly-opened tabs | Pass (driven, headed) | Verified by screenshot; covers `Target.setAutoAttach` auto-attach to all tabs |
| Live: marker + title prefix persist across navigation | Pass (driven, headed) | Re-screenshot after navigation |
| Live: distinct colors per instance | Pass (driven, headed) | Two instances, two visibly different palette colors |
| Live: suppressed under --headless / --no-window-border / --fingerprint | Pass (driven, headed) | No host element, no border/badge, no title prefix |
| Live: no detectable footprint (sannysoft + CreepJS) | Pass (driven, headed) | sannysoft results and CreepJS fingerprint ID byte-identical to vanilla (audit config C) |
| Live: guard exits with the browser (no orphan) | Pass (driven, headed) | Supervisor process exits on close; instance retired from registry |

## 11. Review Notes

### Agent Review Notes

**The detection audit drove the entire design.** Rather than asserting the marker was safe, the implementation was preceded by an empirical audit that drove real detection harnesses (bot.sannysoft.com, CreepJS) across three configs. The audit established ground truth: a vanilla CDP-attach launch is *already* clean on the classic automation signals, and the proposed marker adds nothing detectable on top -- its sannysoft results and CreepJS fingerprint ID are byte-identical to vanilla. The only observable traces are the host `<div>` and the modified `document.title`, which are page-content artifacts. This is what licensed shipping the marker on-by-default for headed launches, and what dictated the suppress-under-`--fingerprint` rule (bot-defended sites are where DOM/title diffing happens). See `BRW-03-learnings/01-detection-audit.md`.

**Do not reuse the fingerprint `defineProperty` pattern.** The same audit found that `fingerprint.py`'s JavaScript navigator overrides were net-negative -- `navigator.webdriver` became an *own* property (a tamper signature that flipped sannysoft's WebDriver test from pass to fail), and `platform`/`vendor` getters stringified to arrow-function source. The marker deliberately avoids any `defineProperty` navigator patching: it only appends a host element and prefixes the title, both inside the most-contained primitives available (closed shadow DOM, randomized host id, isolated world).

**Continuous hue was a real mistake, caught and corrected.** The first color scheme derived a hue from the name continuously, which produced near-identical reds for different instances -- defeating the feature's whole purpose (telling instances apart at a glance). The fix was a fixed, curated 14-color palette indexed by `md5(name)`: instances are now either an obvious match or obviously different, never a deceptive near-match.

**Visual feature, visual verification.** The unit tests cover only the deterministic, pure functions (color derivation, script construction). Everything that makes this feature *work* -- the border rendering, the badge, the title prefix, propagation to new tabs, persistence across navigation, suppression, and the no-orphan lifecycle -- exists only in a rendered window and was verified by driving a real headed browser and reading screenshots plus the live DOM/title. A headless unit test would have proven nothing about the user-visible outcome.

**Shared process with BRW-07.** The marker and the deregister-on-close lifecycle both depend on holding a long-lived browser-level CDP connection (the marker re-runs only while the registering connection is alive). Rather than two processes, BRW-06's visual payload rides on BRW-07's single detached supervisor. The host id and overlay script are computed once per supervisor so a reconnect after a transient CDP drop reuses the same randomized id and the overlay's idempotent guard suppresses a redraw.

### User Review Notes

[To be filled by user]
