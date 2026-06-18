# BRW-03 Learnings: Fingerprint Profiles

Empirical work that informed the [BRW-03 fingerprint hardening](../BRW-03-fingerprint-profiles.md#12-iteration-3-update----fingerprint-hardening) (Iteration 3) and validated the detection-safety of the [BRW-06 Window Border](../BRW-06-window-border.md). This was a measurement exercise, not a code experiment: real detection harnesses were driven against real browsers to establish ground truth before changing anything.

## Summary

| # | Learning | Format | Key Takeaway |
|---|----------|--------|--------------|
| 01 | [Detection audit](01-detection-audit.md) | Driver script + write-up | A plain CDP-attached Chrome is already clean on the classic automation signals. The prior fingerprint JS overrides were net-negative -- they flip `bot.sannysoft.com`'s WebDriver test from pass to fail and raise CreepJS's headless score. An in-page marker (the window border) adds **zero** automation-detection signal. WebRTC still leaks the real public IP regardless of profile. |

## Narrative Arc

The audit drove three configurations -- vanilla launch, `--fingerprint`, and an injected in-page marker -- against `bot.sannysoft.com`, CreepJS, and a custom probe, in headed Chrome with an isolated registry. Three findings emerged:

1. **Vanilla is already clean.** A plain `--remote-debugging-port` + CDP-attach launch does not set `navigator.webdriver`, keeps the genuine `window.chrome` shape, and passes sannysoft. The CDP-attach model does not trip the automation flag the way `--enable-automation`/Selenium does.

2. **The old fingerprint overrides were counterproductive.** Each JS navigator override (`webdriver`/`platform`/`vendor`/`window.chrome`) is independently detectable, and two were measurably *worse than nothing*: the `webdriver` override made it an own property (a tamper signature) that flipped sannysoft's WebDriver test pass -> fail, and CreepJS's headless heuristic rose 0% -> 33%. This drove removing the JS overrides from BRW-03, keeping only the launch-flag spoofs.

3. **The window border is detection-safe.** Its sannysoft results and CreepJS fingerprint ID are byte-identical to vanilla. Its only observable traces are a host element in the DOM and a modified `document.title` -- page-content artifacts, not automation signals -- which is why it is suppressed under `--fingerprint` (where DOM/title-diffing detectors live) but on by default otherwise.

A separate, unaddressed finding: WebRTC ICE leaks the real public IP via STUN in all configurations. It only matters relative to network-level anonymization (a proxy/VPN), and the `--force-webrtc-ip-handling-policy` flag was empirically shown to be a no-op without a proxy. Documented as a known limitation.

## Scripts

The driver is co-located with the write-up:

- `./01-detection-audit-driver.py` -- launches the three configurations, drives the detection harnesses + custom probe, and reports results. Re-runnable via `uv run python planning/03-specs/BRW-03-learnings/01-detection-audit-driver.py`.
