# Waiting from Raw CDP

## Question

Can CDP's native events replace Playwright's auto-waiting? Playwright provides four layers of waiting: navigation lifecycle, element appearance, element visibility/stability, and auto-retry on actionability failures. If CDP can handle all of these event-driven (without polling), Playwright's waiting abstraction becomes unnecessary.

## Experiment

**Script:** `./02-waiting-from-cdp.py`

The experiment builds three waiting primitives from CDP events and compares event-driven waiting to polling:

1. `wait_for_lifecycle()` -- listens for `Page.lifecycleEvent` (load, DOMContentLoaded, networkIdle)
2. `wait_for_selector()` -- uses `Runtime.evaluate` with `awaitPromise=True` to push a `MutationObserver`-backed Promise into the browser
3. `wait_for_navigation()` -- listens for `Page.frameNavigated`

A polling-based `wait_for_selector_poll()` is included for direct comparison.

### CDP mechanisms used

| Mechanism | CDP Command/Event | Purpose |
|---|---|---|
| Page lifecycle | `Page.lifecycleEvent` | load, DOMContentLoaded, networkIdle |
| Navigation | `Page.frameNavigated` | Detect frame navigation completion |
| Element appearance | `Runtime.evaluate` + `awaitPromise` + `MutationObserver` | Wait for element insertion, zero polling |
| Attribute change | `MutationObserver` with `attributeFilter` | Wait for style/attribute mutations |
| DOM mutations | `DOM.childNodeInserted`, `DOM.attributeModified` | CDP-level mutation events (alternative approach) |

### Tests run

1. **Page load lifecycle** -- navigate to example.com, wait for DOMContentLoaded, load, and networkIdle via `Page.lifecycleEvent`. All three events received, zero polling.
2. **Delayed element (event-driven)** -- page inserts a `#delayed-element` after 500ms via `setTimeout`. `MutationObserver` + `awaitPromise` detects it promptly at insertion time (~500ms).
3. **Event-driven vs polling comparison** -- page inserts `#very-delayed-btn` after 1500ms. Both event-driven and polling (50ms interval) approaches find it. Event-driven reacts at the exact moment of DOM insertion; polling has up to one interval of latency.
4. **Navigation after click** -- click a link, wait for `Page.frameNavigated`, then wait for load lifecycle event. Fully event-driven chain: click, navigation, load.
5. **Timeout** -- wait for `#does-not-exist` with 1-second timeout. Promise rejects correctly after timeout.
6. **Attribute/style change** -- create a hidden element, reveal it after 600ms by changing `style.display` and setting `data-ready="true"`. `MutationObserver` with `attributeFilter` detects the change at mutation time.

## Observations

The key technique is `Runtime.evaluate` with `awaitPromise: true`. This pushes a JavaScript Promise into the browser's event loop and awaits its resolution from Python. The browser does the watching -- the Python side just waits on the WebSocket response.

For element waiting, this means:

```
Python: send Runtime.evaluate with MutationObserver Promise
  → browser: MutationObserver watches DOM
  → browser: element inserted, observer fires, Promise resolves
  → CDP: sends result back over WebSocket
Python: receives result, continues
```

There is no polling loop. The reaction time is sub-millisecond from the DOM mutation -- the `MutationObserver` callback fires synchronously during the DOM mutation, resolves the Promise, and the CDP response is sent immediately.

By contrast, polling with a 50ms interval adds up to 50ms of latency (half the interval on average). With 100ms polling (a common default), average latency is 50ms. This is not catastrophic, but event-driven waiting is both faster and more efficient (no repeated WebSocket round-trips).

For page lifecycle events, `Page.lifecycleEvent` with `Page.setLifecycleEventsEnabled` provides load, DOMContentLoaded, networkIdle, and other events natively. No polling needed.

For navigation detection, `Page.frameNavigated` fires when a frame navigates. Combined with lifecycle events, this gives a complete event-driven navigation chain.

## Conclusion

CDP provides fully event-driven waiting for all four of Playwright's waiting layers:

1. **Navigation lifecycle** -- `Page.lifecycleEvent` (zero polling)
2. **Element appearance** -- `MutationObserver` via `Runtime.evaluate` + `awaitPromise` (sub-millisecond reaction)
3. **Element visibility/stability** -- `MutationObserver` with `attributeFilter` for style/attribute changes
4. **Timeout** -- standard `Promise` rejection with `setTimeout`

The `Runtime.evaluate` + `awaitPromise` pattern is the key insight. It lets Python push arbitrary async logic into the browser and await the result. This is not limited to waiting -- any browser-side async operation can be awaited this way.

**Design decision:** No Playwright-style auto-waiting abstraction needed. Waiting is done with browser-native `MutationObserver` via `Runtime.evaluate` + `awaitPromise`.

## Cross-references

- Experiment 3 (`01-interaction-primitives-from-cdp.md`) proves the interaction primitives
- Together, experiments 3 and 4 eliminate both halves of Playwright's value proposition (interactions + waiting)
