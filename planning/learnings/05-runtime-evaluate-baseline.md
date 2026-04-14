# Runtime.evaluate Baseline

## Question

What does the Runtime.evaluate shortcut approach look like as a concrete, end-to-end implementation? The token cost analysis (04) compares three approaches by token count, but the Runtime.evaluate shortcut -- the approach agents naturally gravitate to -- needed a clean reference implementation to ground the comparison.

## Experiment

**Script:** `./05-runtime-evaluate-baseline.py`

The script performs a 7-step form interaction workflow using only `Runtime.evaluate` for all DOM operations:

1. Take "before" screenshot
2. Fill `#name-input` with "CDP Test User"
3. Fill `#email-input` with "cdp@test.com"
4. Click checkbox `#check1`
5. Click `#submit-btn`
6. Verify `#result` text matches expected value
7. Take "after" screenshot

Every interaction (focus, value setting, event dispatch, click, text readback) is accomplished through `Runtime.evaluate` with inline JavaScript. No DOM domain commands, no Input domain commands -- just JavaScript execution through a single CDP method.

The script also includes a minimal `CDPClient` class (~40 lines) that predates the production implementation in CDP-01. This was the working prototype that validated the raw WebSocket approach.

## Observations

- **Every DOM operation collapses to one CDP call.** Finding an element, focusing it, setting its value, and dispatching events is a single `Runtime.evaluate` with an IIFE that does all four steps. Compare this to the proper CDP approach which requires `DOM.getDocument` + `DOM.querySelector` + `DOM.focus` + `Input.insertText` (four round-trips).

- **Event dispatch must be explicit.** Setting `el.value` via JavaScript does not fire `input` or `change` events. The script manually dispatches both events after setting the value. This is the same discovery documented in the interaction primitives experiment (01) -- frameworks like React require these events to update their state.

- **Screenshot and page control still use CDP domains.** `Page.captureScreenshot`, `Page.enable`, and `Runtime.enable` are used directly -- these have no JavaScript equivalent.

- **The CDPClient prototype is functionally identical to the production implementation.** The ~40-line class in this script (connect, send with ID correlation, event subscription, recv loop) became the skeleton for the CDP-01 specification.

## Conclusion

The Runtime.evaluate shortcut is a legitimate and effective approach for browser automation via CDP. It produces compact scripts (171 lines including the CDP client), requires fewer round-trips than proper CDP domain commands, and is the approach agents independently discover when given freedom to choose (as documented in the token cost analysis).

This script served as both a validation of the Runtime.evaluate approach and a reference implementation for comparing token costs across approaches.

## Cross-references

- Token cost analysis (`04-token-cost-analysis.md`) -- uses this approach as the baseline for cost comparison
- Interaction primitives (`01-interaction-primitives-from-cdp.md`) -- documents the same event dispatch requirement (input + change events)
- Raw WebSocket client (`../03-specs/CDP-01-learnings/02-raw-websocket-client.md`) -- the CDPClient prototype in this script is the precursor to the production class
