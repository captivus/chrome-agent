# CDP-01 Learnings: CDP WebSocket Client

Exploratory experiments that informed the [CDP-01 specification](../CDP-01-cdp-websocket-client.md). These two experiments answered a key architectural question: should chrome-agent use Playwright's CDPSession or a raw WebSocket client as its CDP transport?

## Summary

| # | Learning | Format | Key Takeaway |
|---|----------|--------|--------------|
| 01 | [Playwright CDPSession](01-playwright-cdp-session.md) | Script + write-up | CDPSession works in attach mode with full CDP access, but Playwright is a heavy dependency for a thin wrapper. |
| 02 | [Raw WebSocket client](02-raw-websocket-client.md) | Script + write-up | A ~40-line raw WebSocket client provides the same capabilities without Playwright, with comparable or better latency. |

## Narrative Arc

Experiment 01 confirmed that Playwright's CDPSession provides unrestricted access to all CDP domains when connected in attach mode -- screenshots, screencast, performance metrics, network events all work. This validated CDP as the right protocol layer for chrome-agent's needs.

However, the experiment also made clear that CDPSession is a thin `send()`/`on()` wrapper. Playwright's value -- browser lifecycle management, high-level page APIs, cross-browser support -- is irrelevant to chrome-agent, which always attaches to an already-running Chrome instance. Carrying Playwright as a dependency for a wrapper that could be replicated in 40 lines was hard to justify.

Experiment 02 proved the alternative: a minimal `websockets`-based client that handles command-response correlation and event dispatch directly. It matched CDPSession's functionality with no extra dependencies beyond `websockets`. The prototype's class structure (`connect`, `send`, `on`, background receive loop) became the skeleton for the production `CDPClient` specified in CDP-01.

## Scripts

The experiment scripts are co-located with their write-ups:

- `./01-playwright-cdp-session.py`
- `./02-raw-websocket-client.py`
