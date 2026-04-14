# CDP-02 Session Mode -- Learnings

Experiments conducted during specification of the CDP-02 (Session Mode) feature. These validated assumptions about Chrome's CDP multi-client behavior and compared architectures for persistent session connections.

| # | Learning | Key Takeaway |
|---|----------|-------------|
| [01](01-multi-client-behavior.md) | Multi-client CDP behavior | Chrome fully supports multiple simultaneous CDP clients on the same page target. Events fan out, mutations are cross-visible, navigation conflicts produce clean errors. No locking needed. |
| [02](02-session-persistence-approaches.md) | Session persistence approaches | REPL (stdin/stdout) achieves 2.1x speedup over fresh connections vs 1.3x for a UNIX socket daemon. REPL chosen for performance and simplicity. Per-invocation overhead of ~350ms makes session mode essential for multi-step workflows. |

## Experiment scripts

Scripts are co-located with their write-ups:

- `./01-multi-client-behavior.py` -- Connects two CDP clients to the same page target, tests event fan-out, mutation visibility, and navigation conflicts
- `./02-session-daemon.py` -- UNIX socket daemon that holds a persistent CDP WebSocket
- `./02-session-client.py` -- Thin client for the daemon
- `./02-session-daemon-test.py` -- Benchmark harness comparing daemon vs fresh connections
- `./02-session-repl.py` -- Stdin/stdout REPL that holds a persistent CDP WebSocket
- `./02-session-repl-test.py` -- Benchmark harness comparing REPL vs fresh connections
