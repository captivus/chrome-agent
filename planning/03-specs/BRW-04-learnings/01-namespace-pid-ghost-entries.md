# Namespace-PID ghost entries: incident, mechanism, fix, validation

**Date:** 2026-07-22
**Trigger:** `status` showed two `pickleball-league` instances with no targets; `cleanup` found nothing stale; `stop` failed with `Browser.close failed ... No browser listening` followed by `Error: [Errno 1] Operation not permitted`.

## Incident

A Codex CLI session working in `~/projects/pickleball-league` ran `chrome-agent launch` from inside its bubblewrap sandbox (`bwrap --unshare-user --unshare-pid ... --bind /tmp /tmp`, confirmed from `/proc/<pid>/cmdline` of the live sandbox). Two properties combined:

- `--bind /tmp /tmp` shares the host `/tmp`, so registry entries and session dirs land in the real `/tmp/chrome-agent/`.
- `--unshare-pid` gives the sandbox a private PID namespace, so `subprocess.Popen(...).pid` records the PID **as seen inside the sandbox**. The registry held PIDs 4, 51, 178 (two entries even shared PID 4, from two separate sandbox launches).

On the host those PIDs were root-owned kernel threads (`kworker`, `cpuhp/12`, `irq/9-acpi`, all started at boot). `os.kill(pid, 0)` raises `PermissionError`, and `process_is_running()` deliberately returned True on `PermissionError` — so once the sandbox died (taking its browsers with it, `--die-with-parent`), the entries became **immortal ghosts**: alive in `status`, invisible to `cleanup`, and `stop` fell through to its SIGTERM fallback and fired `os.kill(pid, 15)` at a kernel thread. Only root-ownership stopped that signal; a namespace PID aliasing to a user-owned process would have been killed.

## Second finding: port collisions are real

The production registry also held **two entries claiming port 9223** (`chrome-agent-01` and `motomon-02`), both browser processes alive. Only one (`chrome-agent-01`) won the bind; the other runs CDP-less. Pre-fix, `stop motomon-02` would have sent `Browser.close` to port 9223 — killing `chrome-agent-01`'s browser. A separate collision existed on 9224 (a non-chrome-agent Chrome using a `.triage-profile` also claims that port), proving attribution must collect *all* claimants, not pick "the" owner.

## Third finding: the session-dir sweep had the same PID flaw plus a cross-registry blast radius

`cleanup_sessions()`'s orphan sweep read Chrome's `SingletonLock` PID (namespace-local for sandboxed launches — Chrome writes the PID as it sees itself) through the same `process_is_running()`. Worse, the sweep walks the **global** `_SESSION_ROOT` but consulted only the registry it was invoked with — so any invocation with an isolated registry path (tests, tools) treated default-registry instances' dirs as untracked and deleted them under live browsers. Live browsers whose dirs are deleted recreate them lazily **without** a `SingletonLock`, making the recreated dirs prey for the sweep's "no lock → remove" rule on every subsequent pass; several production instances' dirs were observed cycling through delete/recreate this way.

## Fix (registry.py, launcher.py, utils.py)

1. **Process identity, not existence** — `utils.process_is_ours(pid, expected_start)`: chrome-agent launches Chrome as the invoking user, so `PermissionError` means *not ours*; and a start-time token (`/proc/<pid>/stat` field 22, `ps -o lstart=` fallback, recorded at launch as `pid_start` in the registry) detects recycled PIDs. Legacy entries without a token degrade to the signalability check.
2. **Port attribution** — `registry._cdp_port_claimants(port)` scans `/proc/*/cmdline` for `--remote-debugging-port=<port>` and returns the **set** of claiming `--user-data-dir`s. Chrome rewrites its argv into a single space-joined string (one trailing NUL), so the parser tokenizes on whitespace+NUL — a decoy subprocess with well-formed argv passes a naive NUL-split parser that fails on every real Chrome (caught by the real-browser integration test).
3. **Liveness ladder** (`_instance_is_alive`): PID identity → port dead = dead → our dir among the port's claimants = alive, claimed only by others = dead → unattributable listener = alive (conservative; never destroy on ambiguity).
4. **`stop` verifies its target immediately before each destructive act**: never `Browser.close` a port whose claimants don't include this instance's profile dir (terminates the instance's own verified PID instead, or just cleans the stale entry); SIGTERM fallback fires only at a PID verified ours.
5. **Sweep guards**: dirs tracked by the invoked registry **or the default registry** are never swept; orphan lock PIDs go through `process_is_ours`.

## Validation

- 21 regression tests (`tests/test_pid_identity.py`), each scenario verified failing on pre-fix semantics: ghost liveness/cleanup/stop-no-signal, recycled-PID detection, collision attribution, multi-claimant ports, bind-race stop-by-PID, sweep guards, real-Chrome attribution.
- Full suite 149 passed (128 pre-existing + 21 new), including real-browser integration tests.
- Ghost scenario script (real headless launch → kill → PID rewritten to a kernel-thread PID against an isolated registry): pre-fix reproduced all three symptoms including the SIGTERM at PID 4; post-fix reads dead, cleanup reaps entry + session dir, no signal fired.
- Production: the launch-time prune reaped both real pickleball ghosts (entries + session dirs); all nine genuinely-live instances (verified against `ps`/`ss` ground truth) stayed alive and untouched through `status`/`cleanup`; own-instance launch/stop lifecycle clean.
- A true bwrap reproduction was attempted but this host's `kernel.apparmor_restrict_unprivileged_userns=1` denies unprivileged user namespaces to unconfined processes; the causal step (namespace-local PID recording) rests on the production evidence above.

## Residual limitations (accepted, documented)

- A ghost whose dead port is later bound by a process carrying no `--remote-debugging-port` flag reads alive (unattributable-listener conservatism) — same as pre-fix, no destruction either way.
- `/proc` attribution is Linux-only; elsewhere the ladder degrades to pre-fix port-listening behavior.
- A sandbox that also unshares the network yields an entry whose browser is unreachable from the host; it reads dead once the sandbox exits (port never visible), which is the desired outcome.
- `status` display for a bind-race loser shows the winner's tabs (targets are queried by port); the entry itself is correctly alive via PID identity.

## Instrument note

Shell `grep` on `/proc/*/cmdline` requires `--text` (`-a`): without it, GNU grep's binary heuristic silently reports no match on these NUL-containing files even when the pattern is present — a scan that "finds nothing" this way is an instrument failure, not evidence of absence. (The shipped Python attribution reads the bytes directly and is unaffected.)
