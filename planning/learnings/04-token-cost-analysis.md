# Token Cost Analysis

## Question

What is the actual token cost of agents composing CDP commands versus using pre-built convenience commands? An earlier claim of "no meaningful cost difference" needs scrutiny -- are agents taking shortcuts that mask the real cost?

## Experiment

Two experiments compared token costs for the same task (fill form, click submit, verify result, scroll to far button, click, verify) using different approaches:

**Scripts:**
- `./04-token-cost-cdp-domain-e.py` -- agent instructed to use proper CDP domain commands (DOM.getDocument, DOM.querySelector, DOM.getBoxModel, DOM.focus, Input.insertText, etc.), with `Runtime.evaluate` permitted only for reading back values
- `./04-token-cost-cdp-domain-f.py` -- same constraint, second independent run to verify consistency

Both scripts perform identical 10-step workflows:
1. Navigate to test page
2. Take "before" screenshot
3. Fill `#name-input`
4. Fill `#email-input`
5. Click checkbox `#check1`
6. Click submit `#submit-btn`
7. Verify `#result` text
8. Scroll to and click `#far-btn`
9. Verify `#result` text
10. Take "after" screenshot

### Approaches compared

| Approach | Description | Token Cost |
|---|---|---|
| Runtime.evaluate shortcut | Agent uses `Runtime.evaluate` for everything -- querySelector, focus, select, read values | ~17K tokens |
| Proper CDP domain commands | Agent uses DOM.getDocument, DOM.querySelector, DOM.getBoxModel, DOM.focus, Input.insertText, etc. | ~22K tokens |
| CLI convenience commands | Agent calls pre-built `click`, `fill`, `screenshot` commands | ~16K tokens |

### What the "proper CDP" approach looks like

Token cost experiments E and F both use the proper CDP approach. Key differences from the Runtime.evaluate shortcut:

- **Element lookup:** `DOM.getDocument` + `DOM.querySelector` instead of `Runtime.evaluate("document.querySelector(...)")`
- **Coordinates:** `DOM.getBoxModel` instead of `Runtime.evaluate("el.getBoundingClientRect()")`
- **Focus:** `DOM.focus` with `nodeId` instead of `Runtime.evaluate("el.focus()")`
- **Select all:** `Input.dispatchKeyEvent` with Ctrl+A instead of `Runtime.evaluate("el.select()")`
- **Scroll:** `DOM.scrollIntoViewIfNeeded` with `nodeId` (same in both approaches)
- **Text insertion:** `Input.insertText` (same in both approaches)
- **Click:** `Input.dispatchMouseEvent` sequence (same in both approaches)

The proper approach requires more CDP round-trips (getDocument, querySelector, getBoxModel are three calls where Runtime.evaluate is one) but uses the protocol as designed.

## Observations

### The Runtime.evaluate shortcut

When agents are given CDP tasks without constraints, they naturally gravitate toward `Runtime.evaluate` for everything. This is rational: `Runtime.evaluate` is a single CDP command that can execute arbitrary JavaScript, so it collapses multi-step CDP sequences into one call. querySelector, focus, getBoundingClientRect, select -- all become one-line JS expressions.

This produces the lowest token cost (~17K) because the agent writes fewer CDP calls and the responses are simpler (just the JavaScript return value rather than structured CDP response objects).

### The real cost of proper CDP

When constrained to use proper CDP domain commands, the token cost rises to ~22K -- a 42% premium over the Runtime.evaluate shortcut. This is because:

1. **More CDP round-trips:** Finding and interacting with an element requires DOM.getDocument + DOM.querySelector + DOM.getBoxModel (3 calls) instead of one Runtime.evaluate
2. **Richer response payloads:** DOM.getBoxModel returns a structured model object; Runtime.evaluate returns just a number
3. **More agent reasoning:** The agent must understand which CDP domain handles which concern (DOM for tree queries, Input for events, Page for navigation)

### Convenience commands vs raw CDP

CLI convenience commands (~16K tokens) are marginally cheaper than even the Runtime.evaluate shortcut (~17K). This is expected -- a pre-built `click #submit-btn` command compresses both the intent and the implementation into a single call.

However, the cost difference between convenience commands and raw CDP (either approach) is small in absolute terms. The question is not "which is cheapest?" but "does the cost justify maintaining convenience commands?"

### The earlier claim was wrong

The earlier finding of "no meaningful cost difference" between raw CDP and convenience commands was based on agents using the Runtime.evaluate shortcut. When agents use Runtime.evaluate for everything, they approximate the token efficiency of convenience commands. This made it appear that raw CDP was cheap.

The actual cost comparison is:

- Convenience commands: ~16K tokens (baseline)
- Runtime.evaluate shortcut: ~17K tokens (+6%)
- Proper CDP domain commands: ~22K tokens (+38%)

The 38% premium for proper CDP is real. But agents naturally choose the cheapest viable approach (Runtime.evaluate), so in practice the premium is closer to 6%.

## Conclusion

The token cost picture has three layers:

1. **Convenience commands are cheapest** (~16K) -- they compress intent into single calls
2. **Runtime.evaluate shortcut is nearly as cheap** (~17K) -- agents naturally discover this approach
3. **Proper CDP domain commands cost more** (~22K) -- using the protocol as designed has a 38% premium

The practical implication: agents will use Runtime.evaluate as their primary tool when given freedom to choose. This is not a problem -- Runtime.evaluate is a legitimate CDP command, and the browser executes the JavaScript the same way regardless of how it was invoked. The "proper" CDP approach is more explicit and self-documenting, but the shortcut is functionally equivalent.

The convenience commands save ~1K tokens per interaction sequence. For a tool designed for agent use, this marginal savings does not justify the maintenance burden of a convenience command layer -- especially when agents can compose equivalent operations from CDP primitives.

**Design decision:** The token cost data supports removing convenience commands. The savings are marginal (~6% vs the approach agents naturally choose), and the convenience layer adds code to maintain without adding capability.

## Cross-references

- Agent composition experiments (`03-agent-cdp-composition.md`) show the agents that produced these token costs
- Interaction primitives (`01-interaction-primitives-from-cdp.md`) document the CDP commands agents compose
