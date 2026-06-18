# Feature Specification

> *This document is the complete definition of a single atomic feature -- what to build, how to validate it, what to observe during implementation, what it depends on, and (once implementation begins) its implementation history.*

## 1. Feature ID and Name

BRW-07: Instance Supervisor

## 2. User Story

As a user running agent browsers, I want the instance registry to mirror reality in real time -- when I close a browser window, its instance should automatically disappear from the registry without my running any command -- and I want liveness to be reported correctly even for Chrome installs that fork the real browser into a different process than the one I launched.

## 3. Implementation Contract

### Level 1 -- Plain English

chrome-agent has no daemon, so nothing watches a launched browser between commands. This feature adds a per-instance *supervisor*: a small detached process spawned once per headed launch that holds a single browser-level CDP connection open for the browser's lifetime. Because the connection is long-lived, the supervisor is the only thing that can observe a window/browser close *as it happens* and react to it.

The supervisor has one primary job and one optional job:

1. **Lifecycle (the BRW-07 concern).** When the browser-level CDP connection drops -- the window was closed, the browser crashed, or it was shut down -- the supervisor confirms the browser is truly gone (its CDP port has stopped listening), then retires the instance: it removes the entry from the registry and deletes the session directory. Net effect: close the window and the instance disappears from the registry in real time, with no command to run. A dropped connection is *not* taken as proof the browser closed -- a host suspend/resume (or any transient blip) can sever the WebSocket while Chrome keeps running and listening. The supervisor consults the CDP port to distinguish a real close (retire) from a transient drop (reconnect and resume).

2. **Window border (the optional BRW-06 concern).** While the browser is alive and a border is requested, the same process draws the colored border + badge + title prefix on every current and future page target. BRW-07 owns the *process and lifecycle*; BRW-06 owns the *visual overlay*. They share one process because both require a long-lived CDP connection.

Headless launches get no supervisor: there is no window to close or to mark, and their registry entries are reclaimed by the launch-time prune (the fallback path) instead.

Liveness reporting is the second half of the feature. A PID-only liveness check is unreliable, because some Chrome installs (snap, the `chromium-browser` wrapper, or Chrome's own self-relaunch) fork the real browser into a different process and the launched PID exits immediately. The fix is port-based liveness: an instance is alive if EITHER the recorded process is running OR its CDP port still accepts connections.

### Level 2 -- Logic Flow (INPUT / LOGIC / OUTPUT)

**INPUT (supervisor process):**

- `port`: integer -- CDP port of the launched browser
- `name`: string -- registered instance name
- `registry_path`: string | None -- path to the registry JSON (for test isolation)
- `draw_border`: boolean -- whether to also draw the window border (BRW-06)

**INPUT (liveness helpers):**

- `pid`: integer -- the recorded process id of the instance
- `port`: integer -- the recorded CDP port of the instance

**LOGIC:**

```
# Spawned by launch_browser for every HEADED launch (fire-and-forget, detached).
spawn_supervisor(port, name, registry_path, draw_border):
    return subprocess.Popen(
        [sys.executable, "-m", "chrome_agent.supervisor",
         str(port), name, registry_path, "1" if draw_border else "0"],
        stdout=DEVNULL, stderr=DEVNULL,
    )
    # Detached: it must survive the launching CLI exiting. Headless launches
    # spawn NO supervisor.

run_supervisor(port, name, registry_path, draw_border):
    # Compute the border host id / overlay script ONCE so reconnects reuse the
    # same randomized host id (the overlay's idempotent guard suppresses redraws).
    source = build_overlay_script(...) if draw_border else None

    while True:
        try:
            _supervise_connection(port, draw_border, source)  # blocks until drop
        except Exception:
            pass  # failed (re)connect or mid-stream error -> fall through

        if _browser_gone(port):           # CDP port stopped listening within grace
            deregister(name, registry_path)   # remove entry + delete session dir
            return                            # browser really closed -> exit
        sleep(0.5)                         # transient drop -> reconnect and resume

_supervise_connection(port, draw_border, source):
    cdp = CDPClient(get_ws_url(port, target_type="browser"))
    await cdp.connect()
    if draw_border and source is not None:
        # autoAttach (flatten) attaches to all current AND future page targets;
        # on each Target.attachedToTarget, install the overlay on that session.
        cdp.on("Target.attachedToTarget", on_attached)
        await cdp.send("Target.setAutoAttach",
                       {"autoAttach": True, "waitForDebuggerOnStart": False, "flatten": True})
    try:
        while cdp._connected:   # hold the connection open for the browser's life
            await sleep(1)
    finally:
        await cdp.close()

_browser_gone(port) -> bool:
    # Poll the CDP port for up to _RETIRE_GRACE_SECONDS (5.0s). True as soon as
    # the port stops listening (real close); False if it stays up the whole
    # window (transient drop -- Chrome is still running).
    deadline = now + 5.0
    while now < deadline:
        if not _port_is_listening(port):
            return True
        sleep(0.2)
    return False

# --- Registry side ---

deregister(instance_name, registry_path) -> bool:
    # Browser-free: does NOT contact the browser. Idempotent: a no-op if the
    # instance is already gone, so it is safe to race with stop() / cleanup().
    entry = registry.pop(instance_name, None)
    if entry is None:
        return False
    save_registry()
    if entry.user_data_dir:
        _remove_session_dir(entry.user_data_dir)   # retry while Chrome releases files
    return True

_remove_session_dir(session_dir):
    # Chrome can briefly hold profile files after close. Retry up to 20 times,
    # 0.3s apart (~6s), then leave any orphan for the launch-time sweep.
    for _ in range(20):
        if not exists(session_dir): return
        rmtree(session_dir, ignore_errors=True)
        if not exists(session_dir): return
        sleep(0.3)

# --- Port-based liveness (the keep-alive bug fix) ---

_instance_is_alive(pid, port) -> bool:
    return process_is_running(pid) or _port_is_listening(port)
    # Used by registry.lookup / enumerate_instances / cleanup.
    # instance_status.get_instance_status NO LONGER overrides with a PID-only
    # check -- it trusts the registry's alive flag.

# --- Launch-time prune (fallback safety net) ---

launch_browser(...):
    cleanup_sessions(registry_path)   # FIRST: prune truly-dead entries (pid-OR-port)
                                      # + sweep orphaned session dirs by SingletonLock PID
    ... launch chrome, register instance ...
    if not headless:
        spawn_supervisor(port, name, registry_path,
                         draw_border = window_border and fp_profile is None)
```

**OUTPUT:**

- Real-time deregistration: on a clean browser close, the instance's registry entry is removed and its session directory is deleted within seconds, with no user command.
- Correct liveness: `lookup` / `enumerate_instances` / `status` report `alive: true` for a live browser even when the recorded PID has exited but the CDP port is still listening; `alive: false` only when both the PID is dead and the port is not listening.
- The supervisor process exits once the browser is gone (or never starts, for headless).

### Level 3 -- Formal Interfaces

```python
# --- src/chrome_agent/supervisor.py ---

_RETIRE_GRACE_SECONDS = 5.0  # how long to wait for a dropped browser's CDP
                             # port to stop listening before concluding it closed


async def run_supervisor(
    *,
    port: int,
    name: str,
    registry_path: str | None = None,
    draw_border: bool = True,
) -> None:
    """Supervise a launched browser until it actually closes.

    Holds a browser-level CDP connection. While alive and draw_border is set,
    marks every page target with the window border (BRW-06). The instance is
    retired from the registry (and its session directory removed) ONLY when the
    browser is truly gone -- detected by its CDP port no longer listening.

    A dropped CDP connection is NOT taken as proof the browser closed: a host
    suspend/resume (or transient blip) severs the long-lived WebSocket while
    Chrome keeps running and listening. On a drop, consult the port via
    _browser_gone and reconnect-and-resume if still up; retire only once gone.
    """
    ...


def spawn_supervisor(
    *,
    port: int,
    name: str,
    registry_path: str,
    draw_border: bool,
) -> subprocess.Popen:
    """Spawn the detached per-instance supervisor process for a launched browser.

    Runs `python -m chrome_agent.supervisor PORT NAME REGISTRY_PATH DRAW_BORDER`
    with stdout/stderr to DEVNULL. Detached: survives the launching CLI exiting.
    """
    ...


async def _supervise_connection(
    *, port: int, draw_border: bool, source: str | None
) -> None:
    """Hold one browser-level CDP connection until it drops.

    Connects; when draw_border and source are set, installs the window border on
    every current and future page target via Target.setAutoAttach (flatten),
    then blocks until the connection drops. Returns on disconnect; raises if the
    connect itself fails.
    """
    ...


async def _browser_gone(port: int) -> bool:
    """True if the browser is truly gone, False if the CDP drop was transient.

    Polls _port_is_listening(port) for up to _RETIRE_GRACE_SECONDS.
    """
    ...


# --- src/chrome_agent/registry.py ---

def deregister(
    instance_name: str,
    registry_path: str | None = None,
) -> bool:
    """Remove an instance from the registry and delete its session directory.

    Unlike stop(), does NOT contact the browser -- used by the supervisor after
    the browser has already closed. Idempotent: a no-op if the instance is not
    (or no longer) registered, so it is safe to race with stop() / cleanup().

    Returns True if an entry was removed.
    """
    ...


def _instance_is_alive(pid: int, port: int) -> bool:
    """Whether a registered instance is still usable.

    True if EITHER the recorded process is running OR its CDP port still accepts
    connections. The port check is what handles fork-and-exit Chrome installs.
    """
    return process_is_running(pid) or _port_is_listening(port)


def _port_is_listening(port: int) -> bool:
    """Quick socket check for an active listener on a port (0.25s timeout)."""
    ...


def _remove_session_dir(session_dir: str) -> None:
    """Remove a session directory, retrying while Chrome releases its files.

    Retries up to 20 times, 0.3s apart. If files are still held after the
    window, leaves the orphan for the launch-time sweep (cleanup_sessions).
    """
    ...
```

## 4. Validation Contract

### Level 1 -- Plain English Scenarios

Browser-free deregistration:
- Given a registered instance with a session directory, calling `deregister` removes the registry entry and deletes the session directory -- without contacting the browser. Calling it a second time is a harmless no-op (idempotent), so it is safe to race with `stop` / `cleanup`.

Port-based liveness (the keep-alive bug fix):
- Given an instance whose recorded PID has exited but whose CDP port is still listening (a fork-and-exit Chrome install), liveness is reported as alive in `lookup` and `enumerate_instances`.
- Given an instance whose PID is dead AND whose port is no longer listening, liveness is reported as dead.

Cleanup respects a live port:
- Given an instance whose recorded PID is dead but whose CDP port is still listening, `cleanup` must NOT prune it.

Live deregistration-on-close (integration, verified by driving):
- Given a headed browser launched via chrome-agent, closing the window causes the registry entry and session directory to vanish within seconds, with no command run.
- Given a headless launch, no supervisor is spawned (there is no window to close or mark).
- The user's own live instances are never touched by another instance's supervisor.

### Level 2 -- Test Logic (GIVEN / WHEN / THEN)

Scenario: deregister removes entry and session dir, idempotently, without the browser
GIVEN: a registered instance "proj-01" with an existing session directory, no browser involved
WHEN: deregister("proj-01") is called
THEN: it returns True, the session directory no longer exists, and lookup("proj-01") raises InstanceNotFoundError
AND WHEN: deregister("proj-01") is called again
THEN: it returns False (a harmless no-op)

Scenario: alive when PID is dead but CDP port is listening
GIVEN: an instance registered with a dead PID and a port_override pointing at a live listening socket
WHEN: lookup and enumerate_instances are evaluated
THEN: both report alive is True
AND WHEN: the listening socket is closed (PID dead AND port not listening)
THEN: lookup reports alive is False

Scenario: cleanup keeps an instance with a live port
GIVEN: an instance registered with a dead PID and a port_override pointing at a live listening socket
WHEN: cleanup() is called
THEN: the instance name is NOT in the returned list of removed instances

### Level 3 -- Formal Test Definitions

```
test_deregister_removes_entry_and_session_dir:
    setup:
        reg_path = tmp_path / "registry.json"
        session_dir = tmp_path / "session" (created)
        register(working_dir="/home/user/proj", pid=os.getpid(),
                 browser_version="Chrome/149", user_data_dir=session_dir,
                 registry_path=reg_path)
    action / assertions:
        deregister("proj-01", registry_path=reg_path) is True
        not session_dir.exists()
        lookup("proj-01", registry_path=reg_path) raises InstanceNotFoundError
        # Idempotent: deregistering again (e.g. racing stop()) is a no-op
        deregister("proj-01", registry_path=reg_path) is False

test_alive_when_pid_dead_but_cdp_port_listening:
    setup:
        reg_path = tmp_path / "registry.json"
        listener = a bound, listening localhost socket -> port  # stands in for
                                                                # the live CDP port
        register(working_dir="/home/user/wrapped", pid=_dead_pid(),
                 browser_version="Chrome/149", user_data_dir=tmp_path / "s",
                 port_override=port, registry_path=reg_path)
    assertions (while the listener is up):
        lookup("wrapped-01", registry_path=reg_path).alive is True
        enumerate_instances(registry_path=reg_path)[0].alive is True
    then close the listener:
        # PID dead AND port no longer listening -> genuinely dead
        lookup("wrapped-01", registry_path=reg_path).alive is False

test_cleanup_keeps_instance_with_live_port:
    setup:
        reg_path = tmp_path / "registry.json"
        listener = a bound, listening localhost socket -> port
        register(working_dir="/home/user/wrapped", pid=_dead_pid(),
                 browser_version="Chrome/149", user_data_dir=tmp_path / "s",
                 port_override=port, registry_path=reg_path)
    assertions (while the listener is up):
        "wrapped-01" not in cleanup(registry_path=reg_path)
```

Helpers used by the tests: `_dead_pid()` spawns and reaps `true` to get a guaranteed-dead PID; `_free_port()` binds and releases a socket to get a port with nothing listening (a dead instance must use a free port, since pid-OR-port liveness reads a real browser on a hardcoded low port as alive).

The live deregistration-on-close behavior is integration-verified by *driving* real headed browsers (launch -> close -> entry + session dir vanish within seconds; headless spawns no supervisor; the user's live instances untouched). This is not a headless unit test -- it exercises the actual detached supervisor process against a real Chrome.

## 5. Feedback Channels

### Visual

Launch a headed instance and run `chrome-agent status` -- the instance appears with `alive: true` and its page targets. Close the browser window and re-run `status`: the instance is gone from the listing within seconds. For the keep-alive bug specifically, launch against a fork-and-exit Chrome install and confirm `status` shows the live browser as alive (not `alive: false` with no targets, the pre-fix symptom).

### Auditory

The supervisor logs through the registry on retirement: `deregister` emits "Deregistered instance %s (browser closed)". The launch-time prune emits "Cleaned up stale instance %s" / "Removing orphaned session directory ...". Watch these to confirm whether a vanished instance was retired by its supervisor (real-time close) or reclaimed by the fallback prune (supervisor was killed, or headless).

### Tactile

Drive the full lifecycle by hand: launch a headed browser, open several tabs, close the window, and observe the registry entry and the session directory on disk both disappear within seconds. Then kill the supervisor process while the browser is still alive and confirm the entry persists until the next `launch` (launch-time prune) or a manual `chrome-agent cleanup` -- and that a still-live port is never wrongly pruned. Separately, run `chrome-agent stop` on an instance and confirm the supervisor's later deregistration is a harmless no-op (no error, no double-removal).

## 6. Dependencies

| Dependency | What this feature needs from it | Rationale |
|------------|--------------------------------|-----------|
| BRW-04 Instance Registry | `deregister` (browser-free, idempotent removal + session-dir delete), `_instance_is_alive` / `_port_is_listening` liveness helpers, `cleanup` (launch-time prune fallback) | The supervisor's only job on close is to retire the registry entry; the liveness helpers are where the port-OR-pid fix lives. |
| BRW-01 Browser Launch | `launch_browser` spawns the supervisor (headed only) and runs `cleanup_sessions` first as the launch-time prune fallback | The supervisor's lifecycle is bound to a launch; the prune is the safety net for killed supervisors and headless instances. |
| CDP-01 CDP WebSocket Client | `CDPClient` + `get_ws_url` for the long-lived browser-level connection and (for the border) `Target.setAutoAttach` / event subscription | The supervisor's ability to observe a close in real time depends entirely on holding a live CDP connection. |

## 7. Scoping Decisions

| Decision | What prompted it | Rationale | Revisit when |
|----------|-----------------|-----------|--------------|
| One detached process per headed launch (fire-and-forget) | chrome-agent has no daemon; the launching CLI exits immediately | A detached `Popen` survives the caller exiting, so the supervisor can outlive the launch command and watch the browser for its whole lifetime. No central daemon to manage. | If a single multiplexing supervisor for all instances becomes cheaper than one process each. |
| Headless launches get no supervisor | There is no window to close or border to draw for a headless browser | Headless registry entries are reclaimed by the launch-time prune instead; spawning a supervisor would be pure overhead. | If headless instances ever need real-time deregistration. |
| Retire only when the CDP *port* stops listening, not on the raw connection drop | A host suspend/resume severed the long-lived WebSocket while Chrome kept running, orphaning live instances from the registry | The port is the same signal `_instance_is_alive` trusts. Waiting up to `_RETIRE_GRACE_SECONDS` (5s) for the port to drop distinguishes a real close (retire) from a transient blip (reconnect and resume). | If 5s proves too short for slow-closing browsers or too long for responsiveness. |
| Port-OR-pid liveness (not pid-only) | Some Chrome installs (snap, the `chromium-browser` wrapper, Chrome self-relaunch) fork the real browser into a different process; the launched PID exits immediately | A PID-only check reported the live browser as dead (`launch` succeeded but `status` showed `alive: false`, no targets). Checking CDP port reachability is what actually determines whether the browser is drivable. `instance_status` no longer overrides with a PID-only check. | If a port check ever produces false positives (something else binds the recorded port). |
| Border suppressed under a fingerprint profile; lifecycle still runs | The in-page border (host element + modified `document.title`) is page-observable, and fingerprinting is used exactly on bot-defended sites | BRW-07 (lifecycle) is a process concern that runs regardless; BRW-06 (border) is a visual concern that must not leak a detectable artifact on defended sites. See `BRW-03-learnings/01-detection-audit.md`. | If a non-page-observable marking mechanism is found. |
| Honest limitation: deregistration fires on a clean CDP connection drop | If the supervisor process itself is killed while the browser lives, no one is watching that close | The entry then persists until the launch-time prune (`cleanup_sessions` on the next `launch`) or a manual `chrome-agent cleanup`. The port-OR-pid liveness ensures a live-port instance is never wrongly pruned in the meantime. | If killed-supervisor orphans become common enough to warrant a watchdog. |

## 8. Learnings

| # | Topic | Type | Summary | Link |
|---|-------|------|---------|------|
| 1 | Daemonless real-time lifecycle | Design | With no daemon, a per-launch detached process holding a long-lived CDP connection is the only thing that can observe a window close as it happens. | src/chrome_agent/supervisor.py |
| 2 | Connection drop != browser closed | Bug | A host suspend/resume severs the long-lived WebSocket while Chrome keeps running, so retiring on the raw drop orphaned live instances. Confirm via the CDP port before retiring; reconnect on a transient drop. | src/chrome_agent/supervisor.py (`_browser_gone`, `run_supervisor`) |
| 3 | Fork-and-exit Chrome breaks PID liveness | Bug | snap / `chromium-browser` wrapper / Chrome self-relaunch fork the browser into a different process and the launched PID exits; a PID-only check wrongly reported the live browser dead. Port-OR-pid liveness fixes it. | src/chrome_agent/registry.py (`_instance_is_alive`) |
| 4 | Chrome holds profile files briefly after close | Bug | A single `rmtree(ignore_errors=True)` right after close can leave the session tree behind; a retry loop (~20 x 0.3s) is needed before falling back to the launch-time sweep. | src/chrome_agent/registry.py (`_remove_session_dir`) |
| 5 | Idempotent, browser-free deregistration | Design | `deregister` must not contact the browser (it's already gone) and must be a no-op when the entry is missing, so it races safely with `stop` / `cleanup`. | src/chrome_agent/registry.py (`deregister`) |

---

## 9. Implementation Status

**Status:** Complete

## 10. Test Results

### Final Test Results

| Test | Result | Notes |
|------|--------|-------|
| test_deregister_removes_entry_and_session_dir | Pass | `deregister` removes the entry and session dir without contacting the browser; second call returns False (idempotent, safe to race with `stop` / `cleanup`) |
| test_alive_when_pid_dead_but_cdp_port_listening | Pass | Liveness holds when the recorded PID is dead but the CDP port responds (fork-and-exit Chrome); reports dead once both PID and port are gone |
| test_cleanup_keeps_instance_with_live_port | Pass | `cleanup` does not prune an instance whose CDP port is still listening |
| Live deregistration-on-close | Pass (integration, by driving) | Headed launch -> close window -> registry entry + session dir vanish within seconds; headless spawns no supervisor; the user's live instances untouched. Verified by driving real browsers, not a headless unit test. |

All registry tests pass (15/15 in `tests/test_registry.py`), zero regressions.

## 11. Review Notes

### Agent Review Notes

**Daemonless real-time lifecycle is the core idea.** chrome-agent has no daemon, so between commands nothing watches a launched browser. A per-launch *detached* process holding a long-lived browser-level CDP connection is the only mechanism that can observe a window close *as it happens* and react -- removing the registry entry and session directory in real time. This is why `spawn_supervisor` uses a detached `Popen` (fire-and-forget): it must survive the launching CLI exiting.

**Connection drop is not proof of close (the keep-alive regression for live sockets).** The first cut retired the instance the moment the long-lived WebSocket dropped. A host suspend/resume (or any transient blip) severs that WebSocket while Chrome keeps running and listening, so this orphaned live instances from the registry across a suspend. The fix: on a drop, consult `_browser_gone` -- poll the CDP port for up to `_RETIRE_GRACE_SECONDS` (5s); retire only if the port stops listening, otherwise reconnect and resume supervising (re-installing the border on the live tabs). The border host id / overlay script is computed once before the loop so reconnects reuse the same randomized host id and the overlay's idempotent guard suppresses redraws.

**Fork-and-exit Chrome broke PID-only liveness (the status bug).** Some Chrome installs -- snap, the `chromium-browser` wrapper, or Chrome's own self-relaunch -- fork the real browser into a different process; the launched PID exits immediately. A PID-only liveness check then reported a perfectly live browser as dead: `launch` succeeded but `status` showed `alive: false` with no targets. The fix is `_instance_is_alive(pid, port) = process_is_running(pid) OR _port_is_listening(port)`, used in `lookup` / `enumerate_instances` / `cleanup`. Critically, `instance_status.get_instance_status` no longer overrides with a PID-only check -- it trusts the registry's alive flag. Reproduced with a fork-exit wrapper and verified fixed.

**Session-dir deletion needs a retry loop.** Chrome helper processes can briefly outlive the listening socket and keep holding profile files, so a single `rmtree(ignore_errors=True)` right after close can leave the tree behind. `_remove_session_dir` retries (~20 x 0.3s) and, if files are still held, leaves the orphan for the launch-time sweep (`cleanup_sessions`) to reclaim later.

**Two independent reclamation paths.** The supervisor is the real-time path. `launch_browser` calling `cleanup_sessions()` first is the fallback: it prunes truly-dead registry entries (pid-OR-port) and sweeps orphaned session directories by their SingletonLock PID. This covers browsers whose supervisor was killed and headless instances (which have no supervisor). `deregister` being idempotent and browser-free means it races safely with `stop` and `cleanup` -- whichever removes the entry first wins, and the others are harmless no-ops.

**BRW-07 vs BRW-06 split.** The supervisor process also draws the window border when requested (headed, not fingerprint, `window_border` enabled) via `Target.setAutoAttach` + overlay injection on every page target. They share one process because both need a long-lived CDP connection, but BRW-07 is the lifecycle/process concern and BRW-06 is the visual concern. The border is suppressed under a fingerprint profile (page-observable artifact) while the lifecycle job still runs.

### User Review Notes

[To be filled by user]
