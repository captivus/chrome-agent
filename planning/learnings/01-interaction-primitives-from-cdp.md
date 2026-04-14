# Interaction Primitives from Raw CDP

## Question

Can we build click, fill, type, and actionability checks from raw CDP commands, replacing Playwright's interaction layer? How much code does it take, and is the result reliable?

Playwright's value proposition for interactions is a six-step pipeline: find element, wait for it, scroll into view, check actionability (visible, enabled, not obscured), get center coordinates, dispatch input events. If CDP provides native commands for all six steps, Playwright's abstraction adds a dependency without adding capability.

## Experiment

**Script:** `./01-interaction-primitives-from-cdp.py`

The experiment builds four interaction primitives -- `click()`, `fill()`, `type_text()`, and `press_key()` -- from raw CDP commands, then tests them against a form page with inputs, buttons, checkboxes, hidden elements, obscured elements, and an off-screen button 2000px below the fold.

### CDP commands used

| Step | CDP Command | Purpose |
|---|---|---|
| Find element | `Runtime.evaluate` with `document.querySelector()` | Locate element by CSS selector |
| Describe node | `DOM.describeNode` | Get `backendNodeId` from JS object reference |
| Scroll into view | `DOM.scrollIntoViewIfNeeded` | Ensure element is in viewport |
| Get coordinates | `DOM.getContentQuads` | Get the visible quad, compute center point |
| Hit test | `DOM.getNodeForLocation` | Check what element is at given viewport coordinates |
| Focus | `DOM.focus` | Focus an input element for typing |
| Click | `Input.dispatchMouseEvent` | mouseMoved, mousePressed, mouseReleased sequence |
| Type (bulk) | `Input.insertText` | Insert text at cursor position |
| Type (char) | `Input.dispatchKeyEvent` | keyDown/keyUp per character |
| Select all | `Runtime.evaluate` with `el.select()` | Select existing text before replacement |

### Tests run

1. **Click** -- fill form inputs, click submit, verify result text matches expected values
2. **Fill** -- replace existing input value, verify new value is set
3. **Type** -- character-by-character input via key events, verify final value
4. **Hidden element** -- attempt to get coordinates of `display:none` element, verify CDP rejects it
5. **Obscured element** -- hit-test an element covered by an overlay, verify `DOM.getNodeForLocation` returns a different `backendNodeId` than the target
6. **Scroll + click** -- click a button 2000px below fold, verify `DOM.scrollIntoViewIfNeeded` scrolls it into view and the click registers
7. **Checkbox** -- click a checkbox, verify `.checked` toggles from false to true

## Observations

All seven tests passed. The interaction primitives are reliable for standard web interactions:

- `DOM.scrollIntoViewIfNeeded` handles the scroll-into-view step natively -- no need to compute scroll offsets manually.
- `DOM.getContentQuads` returns the actual visible quad (four corner points), from which center coordinates are trivially computed. This is more precise than `getBoundingClientRect()` because it accounts for CSS transforms.
- `DOM.getNodeForLocation` provides native hit-testing -- the browser itself reports which element is at a given point, which is the correct way to detect obscured elements (overlays, modals, tooltips).
- `Input.insertText` is the bulk text insertion method -- it inserts at the cursor without dispatching individual key events. Combined with `DOM.focus` and `el.select()`, this produces a clean fill operation.
- Framework event dispatch (React, Vue) requires manually firing `input` and `change` events after `Input.insertText`, since insertText bypasses the normal event chain. The experiment does this with `Runtime.evaluate`.

The total code for the four interaction functions (`click`, `fill`, `type_text`, `press_key`) plus actionability checking (`find_element`, `get_element_center`, `check_actionable`) is approximately 120 lines of Python.

## Conclusion

Raw CDP provides native commands for every step in Playwright's interaction pipeline. The resulting code is compact (~120 lines), reliable, and uses the browser's own mechanisms for scrolling, coordinate calculation, and hit-testing rather than reimplementing them in JavaScript.

This eliminates the need for Playwright as an interaction abstraction. The CDP commands are the primitives -- wrapping them in a higher-level library adds a dependency without adding capability that agents need.

**Design decision:** Remove Playwright dependency. Interactions are built directly from CDP commands.

## Cross-references

- Experiment 4 (`02-waiting-from-cdp.md`) addresses the other half of Playwright's value -- auto-waiting
- Agent composition experiments (`03-agent-cdp-composition.md`) verify that agents can discover and use these same CDP commands independently
