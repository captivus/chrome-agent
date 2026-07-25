# Event-driven page observation without a Monitor tool

Guidance for agents whose harness has **no Monitor capability** — no way for the
harness to push notifications into the conversation. Everything here assumes
only two things: the agent can **background a shell command**, and it can
**read a file**.

Verified end-to-end against Chrome 150 / chrome-agent 0.5.5 on 2026-07-25.
Run `scripts/cdp-wait-prove.sh` to reproduce; it launches its own throwaway
instance and tears it down on exit.

---

## What can and cannot be replicated

Be precise about this, because the difference is architectural, not cosmetic.

| | Monitor | This technique |
| :-- | :-- | :-- |
| Who initiates | the harness pushes | the agent asks |
| Agent state while waiting | **working on something else** | **blocked on one call** |
| When control returns | events interject mid-turn | the moment the event fires |
| Cost per event checked | zero agent turns | one tool call, which returns on the event |

**What you cannot replicate: interruption.** Without harness support, nothing
can inject a message into the agent's context mid-turn. An agent that is
thinking cannot be tapped on the shoulder. That is a property of the harness,
not of the browser, and no amount of shell cleverness produces it.

**What you can replicate, exactly: the timing.** The agent never sleeps too
long, never wakes too early, and never burns turns polling. In practice this is
most of Monitor's value — the measured difference against a conservative fixed
sleep is ~4.9 seconds of wasted wall-clock *per wait*.

The honest one-line summary: **you trade concurrency for precision, and keep
the precision.**

---

## The architecture

Two moving parts. Start the stream once; block on it many times.

```bash
# ONCE per session -- one backgrounded command, streaming events to a file.
chrome-agent attach mysite-01 \
  +Page.frameNavigated +Page.loadEventFired +Runtime.exceptionThrown \
  > /tmp/events.jsonl 2>&1 &
```

```bash
# MANY times -- each call returns the instant a matching event lands.
python3 scripts/cdp-wait.py --file /tmp/events.jsonl --method Page.loadEventFired --timeout 20
```

The file is the buffer. `attach` appends to it continuously; the waiter reads
forward through it. Because the history is on disk, a wait started *after* an
event has already fired still sees it — which is the single most important
property here, and the one naive approaches get wrong.

### The act → wait → act loop

```bash
# act
chrome-agent mysite-01 Input.dispatchMouseEvent '{"type":"mousePressed",...}'
chrome-agent mysite-01 Input.dispatchMouseEvent '{"type":"mouseReleased",...}'

# wait for the consequence -- returns in milliseconds, not on a guess
python3 scripts/cdp-wait.py --file /tmp/events.jsonl \
  --method Page.frameNavigated --contains "/order/" --timeout 15

# act on what actually happened
chrome-agent mysite-01 Runtime.evaluate '{"expression":"...","returnByValue":true}'
```

This is the sense ⇄ act loop with the sense step *event-timed* rather than
sleep-timed.

---

## Pitfalls, all of them load-bearing

**1. `tail -f` alone is broken, and fails intermittently.** It starts reading at
EOF, so any event that fired between your action and the start of your wait is
silently dropped. You get a hang, then a timeout, on a page that worked fine.
The fix is to read from a byte offset (default: the beginning), which is what
`cdp-wait.py` does. Measured: an event that fired 1.5 s before the wait started
was still matched, in 21 ms.

**2. Redirect order matters — `> file 2>&1`, never `2>&1 > file`.** The reverse
sends stderr to the *old* stdout and loses `attach`'s startup errors entirely.
A wrong instance name then produces an empty stream and a wait that times out
for reasons nothing in your logs explains. (This bug was written, and caught, in
the course of building this — it is not hypothetical.)

**3. Chain your waits with offsets, or you re-match history.** A second wait
started from offset 0 returns the *first* matching event again, instantly, and
your loop appears to succeed while doing nothing. Use `--print-offset` and pass
the result to the next call's `--from-offset`.

**4. Always subscribe to failure events.** `+Runtime.exceptionThrown`
`+Network.loadingFailed`. A wait for a success event on a page that threw will
sit there until timeout with no indication of why. Silence is not success.

**5. Every pipeline stage must flush per line** if you filter downstream —
`jq --unbuffered`, `grep --line-buffered`, `awk` + `fflush()`. `head` cannot
flush at all. A buffered stage turns a millisecond wake into a stall.

**6. Discover events, don't guess them.** `chrome-agent help <inst> <Domain>`
prints an explicit `Events:` block read live from the running browser — on
Chrome 150 that is 57 domains and 237 events. Enumerate the domain rather than
assuming CDP can't see what you need.

---

## If your harness *does* notify on background-command completion

Some harnesses (Claude Code's `Bash` with `run_in_background` among them) send
the agent a notification when a backgrounded command exits. Where that exists
you can get closer to true asynchrony for a **single** event: background a
waiter that exits when the event fires, keep working, and let the completion
notification be your signal.

```bash
python3 scripts/cdp-wait.py --file /tmp/events.jsonl --method Page.loadEventFired --timeout 60 &
```

That yields one asynchronous notification per backgrounded waiter — not a
continuous stream, but genuinely non-blocking. Whether any given non-Claude-Code
harness does this has **not** been verified here; check before relying on it.

---

## Files

- `scripts/cdp-wait.py` — the waiter. stdlib only, no dependencies.
- `scripts/cdp-wait-prove.sh` — the proof harness. Launches its own instance,
  runs six criteria, cleans up on exit.

## Measured results (2026-07-25, Chrome 150.0.7871.128, chrome-agent 0.5.5)

| Criterion | Result |
| :-- | :-- |
| Wake-on-event | 82 ms from `Page.navigate` to wait returning |
| Race safety (event 1.5 s early) | caught in 21 ms |
| Bounded failure | rc=1 at 3.03 s against a 3 s deadline |
| Content predicate | ignored decoy navigation, matched target |
| Offset chaining | resumed at byte 570, returned the next event |
| vs. `sleep 5` | real wait 0.073 s — 4.93 s wasted per occurrence |
