#!/usr/bin/env python3
"""Block until a CDP event matching a predicate appears in an attach stream.

Replicates the *timing* of Claude Code's Monitor tool for agents that have no
Monitor capability. The agent backgrounds `chrome-agent attach ... > events.jsonl`
once, then makes ONE blocking call to this script per event it cares about.
Control returns the instant the event lands -- no fixed sleeps, no poll loops
burning agent turns.

What this does and does not replicate:

  Monitor      : events interject while the agent works on something else.
                 Concurrent. The agent is interrupted.
  This script  : the agent blocks on a wait that returns when the event fires.
                 Sequential. The agent is not interrupted, but it also never
                 sleeps too long or wakes too early.

The file is polled internally at a fine granularity, but that is the point:
the polling happens inside one tool call instead of costing the agent a turn
per check.

Exit codes:
  0  matched  -- the event JSON is printed to stdout
  1  timed out
  2  usage / stream error
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

POLL_SECONDS = 0.02


def matches(line: str, methods: list[str], contains: list[str]) -> dict | None:
    """Return the parsed event if the line satisfies every predicate."""
    line = line.strip()
    if not line:
        return None
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return None

    # attach emits a {"status": "ready"} preamble and possibly {"error": ...}.
    # Neither is a CDP event, so a --method predicate must not match them -- but
    # a --contains-only wait deliberately can, which is how a caller blocks
    # until the stream is ready or spots an error line.
    if methods:
        method = event.get("method")
        if method is None or method not in methods:
            return None
    if contains and not all(needle in line for needle in contains):
        return None
    return event


def wait_for_event(
    path: str,
    methods: list[str],
    contains: list[str],
    timeout: float,
    from_offset: int,
) -> tuple[int, dict | None, int]:
    """Block until a matching event appears. Returns (exit_code, event, offset).

    Reads from `from_offset` rather than from the end of the file, so an event
    that landed BEFORE this call started is still seen. This is the difference
    between correct and subtly broken: `tail -f` alone starts at EOF and drops
    anything that already happened.
    """
    deadline = time.monotonic() + timeout

    # Wait for the stream file to exist at all (attach may still be starting).
    while not os.path.exists(path):
        if time.monotonic() >= deadline:
            return 1, None, from_offset
        time.sleep(POLL_SECONDS)

    with open(path, "r", encoding="utf-8") as stream:
        stream.seek(from_offset)
        pending = ""
        while True:
            chunk = stream.readline()
            if chunk:
                pending += chunk
                # A partial final line means the writer is mid-flush; wait for
                # the newline rather than parsing a truncated record.
                if not pending.endswith("\n"):
                    continue
                event = matches(pending, methods, contains)
                consumed_at = stream.tell()
                pending = ""
                if event is not None:
                    return 0, event, consumed_at
                continue

            if time.monotonic() >= deadline:
                return 1, None, stream.tell()
            time.sleep(POLL_SECONDS)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Block until a matching CDP event appears in an attach stream."
    )
    parser.add_argument("--file", required=True, help="JSONL file attach is writing to")
    parser.add_argument(
        "--method",
        action="append",
        default=[],
        help="CDP event method to match; repeatable, any-of",
    )
    parser.add_argument(
        "--contains",
        action="append",
        default=[],
        help="substring that must appear in the event JSON; repeatable, all-of",
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--from-offset",
        type=int,
        default=0,
        help="byte offset to resume from; use the offset printed by a prior call "
        "so consecutive waits don't re-match consumed events",
    )
    parser.add_argument(
        "--print-offset",
        action="store_true",
        help="print 'offset=<n>' on stderr so the caller can chain waits",
    )
    args = parser.parse_args()

    if not args.method and not args.contains:
        print("error: give at least one --method or --contains", file=sys.stderr)
        return 2

    code, event, offset = wait_for_event(
        path=args.file,
        methods=args.method,
        contains=args.contains,
        timeout=args.timeout,
        from_offset=args.from_offset,
    )

    if args.print_offset:
        print(f"offset={offset}", file=sys.stderr)

    if code == 0:
        print(json.dumps(event))
    else:
        print(
            f"timeout: no event matching methods={args.method or '*'} "
            f"contains={args.contains or '*'} within {args.timeout}s",
            file=sys.stderr,
        )
    return code


if __name__ == "__main__":
    sys.exit(main())
