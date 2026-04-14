# Multi-Client CDP Behavior

## Question

Can multiple CDP WebSocket clients connect to the same Chrome page target simultaneously? If so, how do they interact -- do events fan out to all clients, are DOM mutations cross-visible, and what happens when one client navigates while the other has pending work?

These questions are critical for session mode design: if chrome-agent holds a persistent WebSocket connection, we need to know whether a second invocation (or a human using DevTools) would conflict with it.

## Experiment

**Script:** `./01-multi-client-behavior.py`

The script connects two independent CDP clients (A and B) to the same page target's WebSocket URL, then runs six tests:

1. **Dual connection** -- Can both clients connect and send commands?
2. **Event fan-out** -- Both clients enable `Page.lifecycleEvent`; client A navigates. Do both receive the lifecycle events?
3. **Cross-client mutation visibility** -- Client A sets `document.title`; client B reads it. Does B see the change?
4. **Independent domain enablement** -- Both clients enable the DOM domain and call `DOM.getDocument`. Do they get independent node IDs?
5. **Navigation conflict** -- Client B starts a slow `Runtime.evaluate` (1-second promise); client A navigates mid-flight. What happens to B's pending promise?
6. **Post-stress functionality** -- After all of the above, are both clients still operational?

### How to run

Requires a Chrome instance with `--remote-debugging-port=9222`:

```
uv run python 01-multi-client-behavior.py
```

## Results

All six tests passed:

| Test | Result |
|------|--------|
| Dual connection | Both clients connected and operational |
| Event fan-out | Both clients received identical lifecycle events |
| Cross-client mutation | B sees title set by A immediately |
| Independent domains | Both get independent node IDs from `DOM.getDocument` |
| Navigation conflict | B's pending promise fails cleanly with a context-destroyed error |
| Post-stress check | Both clients fully operational after all tests |

Key observations:

- **Chrome multiplexes CDP WebSocket connections at the protocol level.** Multiple clients to the same target are first-class. Each client gets its own message ID namespace and domain subscription state.
- **Events fan out to all subscribed clients.** If both clients call `Page.enable` and `Page.setLifecycleEventsEnabled`, both receive the same lifecycle events. The event lists were identical.
- **DOM mutations are immediately cross-visible.** The clients share the same page -- mutations via `Runtime.evaluate` in one client are visible to the other with no delay. This is expected since both are operating on the same V8 context.
- **Navigation by one client destroys the other's execution context, but cleanly.** Client B's pending promise received a context-destroyed error rather than hanging. Both clients remained connected and functional afterward. This means session mode doesn't need special protection against concurrent access -- Chrome handles it gracefully.

## Conclusion

Chrome fully supports multiple simultaneous CDP clients on the same page target. Events fan out, mutations are cross-visible, and navigation conflicts produce clean errors rather than hangs or disconnections. This means:

- A persistent session connection will not block DevTools or other tools from attaching.
- No mutex or locking mechanism is needed in session mode -- Chrome's CDP implementation is inherently multi-client safe.
- The design can assume shared-state semantics: if something changes the page, all clients see it.

This informed the decision to keep session mode simple -- a single persistent connection with no coordination layer for concurrent access.
