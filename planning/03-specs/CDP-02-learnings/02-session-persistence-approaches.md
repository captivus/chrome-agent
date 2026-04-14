# Session Persistence Approaches

## Question

What is the best architecture for keeping a CDP WebSocket connection open across multiple CLI invocations? Two candidates were explored:

1. **UNIX socket daemon** -- A long-running process holds the WebSocket open and exposes a UNIX socket. Each CLI invocation connects to the socket, sends a JSON command, gets the response, and disconnects.
2. **Stdin/stdout REPL** -- A subprocess holds the WebSocket open and reads commands from stdin. The parent process (the AI agent or shell) keeps the subprocess alive and pipes commands in, reading JSON responses from stdout.

The key metric is per-command latency compared to the baseline (fresh WebSocket connection per invocation).

## Experiments

### UNIX socket daemon

**Scripts:** `./02-session-daemon.py` (daemon), `./02-session-client.py` (thin client), `./02-session-daemon-test.py` (benchmark harness)

The daemon discovers the page target, opens a WebSocket, and listens on a UNIX socket (`/tmp/chrome-agent.sock`). Each client connection sends a JSON line with `method` and `params`, receives the CDP response as a JSON line. The daemon also supports event subscriptions and a `__shutdown__` command.

The benchmark harness starts the daemon, runs 5 commands through it, then runs the same 5 commands via fresh WebSocket connections (new connection per command), and prints a comparison table.

### Stdin/stdout REPL

**Scripts:** `./02-session-repl.py` (REPL process), `./02-session-repl-test.py` (benchmark harness)

The REPL process opens a WebSocket, enables common domains (Page, DOM, Runtime), emits a `{"status": "ready"}` line, then reads commands from stdin as `Domain.method {json_params}` lines. Responses are JSON lines on stdout. Event subscriptions use `+EventName` syntax.

The benchmark harness spawns the REPL as a subprocess, sends 5 commands via stdin pipe, then runs the same 5 commands via fresh WebSocket connections for comparison.

### How to run

Both require a Chrome instance with `--remote-debugging-port=9222`:

```
uv run python 02-session-daemon-test.py
uv run python 02-session-repl-test.py
```

## Results

### Daemon approach: 1.3x speedup

The daemon eliminated per-invocation WebSocket setup (connect + TLS handshake). However, it still required per-command UNIX socket connect/disconnect. The UNIX socket round-trip added its own overhead, partially eating into the savings from the persistent WebSocket.

### REPL approach: 2.1x speedup

The REPL eliminated all connection overhead -- both the WebSocket setup and the per-command socket connect. Commands travel over an already-open stdin/stdout pipe. The only cost per command is JSON serialization, a pipe write, the CDP round-trip, and a pipe read.

### Per-invocation CLI overhead: ~350ms

Both benchmarks revealed that the baseline cost of a fresh WebSocket connection per CLI invocation is approximately 350ms. This includes:

- HTTP request to `localhost:9222/json` to discover the page target (~10-20ms)
- WebSocket connect + TLS handshake (~50-80ms)
- Enabling CDP domains (Page, DOM, Runtime) (~30-50ms)
- The rest is Python startup, import time, and WebSocket library overhead

For a single command, 350ms is acceptable. For multi-step workflows (screenshot, evaluate, navigate, screenshot again), paying 350ms per step adds up quickly -- a 10-step workflow wastes 3.5 seconds on connection overhead alone. This makes session mode essential for practical multi-step use cases.

## Comparison

| Approach | Speedup | Architecture | Complexity |
|----------|---------|-------------|------------|
| Daemon (UNIX socket) | 1.3x | Separate long-running process, socket IPC | Higher -- process lifecycle management, socket cleanup, port conflicts |
| REPL (stdin/stdout) | 2.1x | Subprocess of the caller, pipe IPC | Lower -- parent controls lifecycle, no socket files, no port conflicts |
| Baseline (fresh conn) | 1.0x | New WebSocket per invocation | Simplest but slowest |

## Conclusion

The REPL approach was chosen for session mode based on three factors:

1. **Performance** -- 2.1x speedup vs 1.3x for the daemon. The REPL avoids per-command UNIX socket connection overhead entirely.
2. **Simplicity** -- No daemon lifecycle management. The parent process spawns the REPL subprocess and owns its lifecycle. No socket files to clean up, no stale daemon detection, no port conflicts.
3. **Natural fit for AI agent callers** -- AI agents (the primary consumer of session mode) already manage subprocesses naturally. A stdin/stdout protocol is simpler to integrate than a UNIX socket client.

The 350ms per-invocation overhead measurement confirmed that session mode is not a nice-to-have but essential infrastructure for multi-step workflows.
