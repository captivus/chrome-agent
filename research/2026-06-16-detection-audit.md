# chrome-agent automated-browser detection audit

**Date:** 2026-06-16
**Question:** Does (a) the proposed `window-border` JS injection and (b) the existing `fingerprint.py`
introduce signals that let a website detect the browser as automated? Establish ground truth by
driving real detection harnesses, not assertion.

**Method:** Headed Chrome (the only config used for stealth), isolated temp registry, dedicated ports
9410–9412, not touching the user's live instances. Three configs driven against
`bot.sannysoft.com` + a custom in-page probe, plus CreepJS screenshots:

- **A — vanilla:** plain `chrome-agent launch` (no fingerprint, no border)
- **B — fingerprint:** `launch --fingerprint` with a Linux desktop profile
- **C — window-border:** plain launch + the proposed border/badge/title injection (held connection)

The custom probe directly measures the vectors hypothesized as detectable.

Driver: `research/detection_audit_driver.py` (re-runnable).

## Results

Raw output: `/tmp/ca_audit_results.json`; screenshots `/tmp/ca_audit_{A,B,C}_{sannysoft,creepjs}.png`.

Custom probe (the hypothesized-detectable vectors):

| Signal | A vanilla | B fingerprint.py | C window-border |
|---|---|---|---|
| `navigator.webdriver` | `false` | `false` | `false` |
| webdriver is **own** property | `false` (native, on prototype) | **`true` (tamper signature)** | `false` (native) |
| `Navigator.prototype.platform` getter | `native` | **`SPOOFED(() => 'Linux x86_64')`** | `native` |
| `Navigator.prototype.vendor` getter | `native` | **`SPOOFED(() => 'Google Inc.')`** | `native` |
| `window.chrome` keys | `[loadTimes, csi, app]` (real shape) | **`[runtime, app]` (wrong shape — real keys lost)** | `[loadTimes, csi, app]` |
| `#__ca_marker__` div findable | `false` | `false` | **`true`** |
| `document.title` | `Antibot` | `Antibot` | **`🤖 chrome-agent-audit — Antibot`** |

bot.sannysoft.com WebDriver test:

| | A vanilla | B fingerprint.py | C window-border |
|---|---|---|---|
| WebDriver (New) | `missing (passed)` | **`present (failed)`** | `missing (passed)` |
| All other rows | passed | passed | passed |

CreepJS (sophisticated detector):

| | A vanilla | B fingerprint.py | C window-border |
|---|---|---|---|
| Fingerprint ID | `8576aa9d…46dc01` | `1d786216…72b394` (**different**) | `8576aa9d…46dc01` (**identical to A**) |
| Headless heuristic | **`0% headless`** | **`33% headless`** | `0% headless` |
| stealth | `0% stealth` | `0% stealth` | `0% stealth` |

All configs: CreepJS reports `chromium: true`, and **WebRTC leaks the real public IP `71.228.15.230`** regardless of config.

## Findings

1. **Vanilla chrome-agent is already clean on the classic automation signals.** Launching plain Chrome
   with `--remote-debugging-port` and attaching over CDP does **not** set `navigator.webdriver`, does not
   add a headless UA token, and preserves the native `window.chrome` shape and native navigator getters.
   It passes bot.sannysoft.com and scores `0% headless` on CreepJS. The CDP-attach model does not trip the
   automation flag the way `--enable-automation`/Selenium does.

2. **`fingerprint.py`'s JavaScript navigator overrides are net-negative against modern detection.** Every
   override is independently detectable, and two are measurably *worse than doing nothing*:
   - `navigator.webdriver` becomes an **own property** (native is on the prototype) — a tamper signature
     that flips sannysoft's WebDriver test from **pass (vanilla) → fail (fingerprinted)**.
   - `platform`/`vendor` getters stringify to arrow-function source instead of `[native code]` — the exact
     check FingerprintJS-class detectors run.
   - `window.chrome` is replaced by a stub `{runtime, app}`, **losing** the real `loadTimes`/`csi` keys.
   - Net effect on CreepJS: headless heuristic rises **0% → 33%** and the fingerprint ID changes (lies
     detected). The legitimately-useful parts of the feature are the *launch-flag* overrides (UA header,
     viewport, timezone, locale); the JS `addScriptToEvaluateOnNewDocument` navigator-patching is the liability.

3. **The proposed `window-border` marker has zero automation-detection footprint.** Its sannysoft results
   and CreepJS fingerprint ID are **byte-identical to vanilla**. Its only observable trace is exactly what
   was hypothesized: a findable `#__ca_marker__` div and a modified `document.title` — page-content
   artifacts, not automation signals. Generic/commercial anti-bot does not inspect these; only a site
   specifically diffing its own DOM or title would notice.

4. **WebRTC real-IP leak** (`71.228.15.230`) is present in all configs and is the largest deanonymization
   vector here — entirely separate from, and unaddressed by, `fingerprint.py`. Out of scope for window-border
   but worth a tracked issue.

### Design implications for window-border

- Build it **without** reusing `fingerprint.py`'s `defineProperty` approach (that pattern is the problem).
- Minimize even the page-DOM footprint: render the border/badge in a **closed shadow DOM** under a
  **randomized host id**, and run the injected script in an **isolated world** so no globals touch the page.
- **Suppress the in-page marker when a fingerprint profile is active** (stealth intent) — bot-defended sites
  are exactly where DOM/title diffing detectors live, and that is when an in-page footprint matters.
- The title prefix is page-observable too; gate it under the same suppression rule.

## Implementation outcome (2026-06-16)

Both changes landed and were verified by driving real browsers:

- **`fingerprint.py` reworked** — the JS navigator overrides were removed; it now spoofs UA / viewport /
  language / timezone via launch flags only. Re-verified headed: `navigator.webdriver` native (not own),
  `platform`/`vendor` getters native, `window.chrome` = real `[loadTimes, csi, app]`, and bot.sannysoft.com
  WebDriver test back to **passed**. Anti-tamper assertions added to `tests/test_fingerprint.py`.
- **`window_border.py` added** — a detached guard process auto-attaches to every tab (current + future) and
  marks it: a per-instance palette color border + badge in a closed shadow DOM under a randomized id, plus a
  title prefix. On by default (`--no-window-border` to disable); suppressed under `--headless` and
  `--fingerprint`. Verified headed: border renders, persists across navigation, appears on newly-opened
  tabs, distinct colors, no detectable footprint (sannysoft + CreepJS identical to vanilla), and the guard
  exits with the browser (no orphan).
