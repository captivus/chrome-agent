# Learnings Index

Experiments that informed chrome-agent's design decisions around CDP, Playwright removal, and convenience command removal.

## Summary Table

| # | Learning | Key Finding | Design Decision |
|---|---|---|---|
| [01](01-interaction-primitives-from-cdp.md) | Interaction primitives from CDP | click, fill, type, actionability checks built from ~120 lines of raw CDP | Remove Playwright dependency |
| [02](02-waiting-from-cdp.md) | Waiting from CDP | MutationObserver + Runtime.evaluate awaitPromise gives sub-millisecond event-driven waiting | No auto-waiting abstraction needed |
| [03](03-agent-cdp-composition.md) | Agent CDP composition | Four agents composed CDP from PDL docs alone -- form fill, network capture, accessibility, screencast | Remove convenience commands |
| [04](04-token-cost-analysis.md) | Token cost analysis | Proper CDP costs 38% more than convenience commands, but agents naturally use Runtime.evaluate shortcut (~6% premium) | Token cost does not justify convenience layer |
| [05](05-runtime-evaluate-baseline.md) | Runtime.evaluate baseline | End-to-end form interaction using only Runtime.evaluate -- the approach agents naturally gravitate to | Reference implementation for token cost comparison |

## Experiment Scripts

Scripts are co-located with their write-ups:

| Script | Description |
|---|---|
| `./01-interaction-primitives-from-cdp.py` | Interaction primitives (click, fill, type) from raw CDP |
| `./02-waiting-from-cdp.py` | Event-driven waiting via MutationObserver + awaitPromise |
| `./03-agent-composition-form.py` | Agent composing form fill from PDL docs |
| `./03-agent-composition-network.py` | Agent composing network capture from PDL docs |
| `./03-agent-composition-ax-perf.py` | Agent composing accessibility/performance from PDL docs |
| `./03-agent-composition-screencast.py` | Agent composing screencast/emulation from PDL docs |
| `./04-token-cost-runtime-eval-a.py` | Token cost: Runtime.evaluate shortcut (run 1) |
| `./04-token-cost-runtime-eval-b.py` | Token cost: Runtime.evaluate shortcut (run 2) |
| `./04-token-cost-cdp-domain-e.py` | Token cost: proper CDP domain commands (run 1) |
| `./04-token-cost-cdp-domain-f.py` | Token cost: proper CDP domain commands (run 2) |
| `./05-runtime-evaluate-baseline.py` | Runtime.evaluate baseline: end-to-end form interaction reference |

## Design Decisions Supported

These experiments collectively support three design decisions:

1. **Remove Playwright** -- Experiments 01 and 02 prove that raw CDP provides native equivalents for both interaction primitives and auto-waiting, the two halves of Playwright's value proposition.

2. **Remove convenience commands** -- Experiment 03 proves agents can compose CDP from protocol docs alone. Experiment 04 shows the token cost savings of convenience commands is marginal (~6% vs the approach agents naturally choose).

3. **chrome-agent provides transport + observation, not abstraction** -- The tool's role is to connect agents to a browser via CDP and provide observation capabilities (screenshot, text, accessibility tree). Agents compose interactions from CDP primitives.
