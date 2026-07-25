#!/usr/bin/env bash
# Proves the Monitor-replication technique against a live browser.
# Launches its own throwaway instance and tears it down on exit.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WAIT="$HERE/cdp-wait.py"
WORK="$(mktemp -d)"
STREAM="$WORK/events.jsonl"
INST=""
ATTACH_PID=""

cleanup() {
  [[ -n "$ATTACH_PID" ]] && kill "$ATTACH_PID" 2>/dev/null
  [[ -n "$INST" ]] && chrome-agent stop "$INST" >/dev/null 2>&1
  rm -rf "$WORK"
}
trap cleanup EXIT

now() { date +%s.%N; }
elapsed() { echo "scale=3; $2 - $1" | bc; }
pass() { echo "  PASS  $1"; }
fail() { echo "  FAIL  $1"; FAILED=1; }
FAILED=0

echo "=== setup ==="
LAUNCH="$(chrome-agent launch --headless 2>&1)"
INST="$(echo "$LAUNCH" | python3 -c 'import sys,json; print(json.load(sys.stdin)["name"])')"
echo "instance: $INST"

# The whole technique rests on this one line: ONE backgrounded command,
# started once, that streams events to a file for the rest of the session.
# NOTE the redirect ORDER: `> file 2>&1` merges stderr into the file.
# The reverse, `2>&1 > file`, sends stderr to the old stdout (the terminal) and
# silently loses attach's startup errors -- the same silent-failure trap that
# bites `2>&1` under Monitor.
chrome-agent attach "$INST" \
  +Page.frameNavigated +Page.loadEventFired +Runtime.consoleAPICalled \
  > "$STREAM" 2>&1 &
ATTACH_PID=$!

# Block until attach reports ready -- itself an instance of the technique.
python3 "$WAIT" --file "$STREAM" --contains '"status": "ready"' --timeout 10 >/dev/null 2>&1 \
  || { echo "attach never became ready"; exit 1; }
echo "attach streaming to $STREAM (pid $ATTACH_PID)"

echo
echo "=== 1. wake-on-event: does the wait return when the event fires? ==="
python3 "$WAIT" --file "$STREAM" --method Page.loadEventFired --timeout 20 > "$WORK/r1.json" &
W1=$!
sleep 0.5                                   # ensure the waiter is genuinely blocked
T0=$(now)
chrome-agent "$INST" Page.navigate '{"url":"data:text/html,<h1>alpha</h1>"}' >/dev/null 2>&1
wait $W1; RC1=$?
T1=$(now)
LAT=$(elapsed "$T0" "$T1")
echo "  navigate -> wait returned in ${LAT}s (rc=$RC1)"
if [[ $RC1 -eq 0 ]] && (( $(echo "$LAT < 0.5" | bc) )); then
  pass "returned on the event, not on a schedule"
else
  fail "expected rc=0 and sub-500ms wake"
fi

echo
echo "=== 2. race safety: event fires BEFORE the wait starts ==="
chrome-agent "$INST" Page.navigate '{"url":"data:text/html,<h1>MARKER-BRAVO</h1>"}' >/dev/null 2>&1
sleep 1.5                                   # event has definitively already landed
T0=$(now)
python3 "$WAIT" --file "$STREAM" --method Page.frameNavigated \
  --contains "MARKER-BRAVO" --timeout 5 > "$WORK/r2.json" 2>/dev/null
RC2=$?
T1=$(now)
echo "  late wait returned in $(elapsed "$T0" "$T1")s (rc=$RC2)"
if [[ $RC2 -eq 0 ]]; then
  pass "caught an event that had already happened (tail -f would have missed it)"
else
  fail "missed an already-landed event"
fi

echo
echo "=== 3. bounded failure: event that never comes ==="
T0=$(now)
python3 "$WAIT" --file "$STREAM" --method Nonexistent.neverFires --timeout 3 >/dev/null 2>&1
RC3=$?
T1=$(now)
TMO=$(elapsed "$T0" "$T1")
echo "  returned in ${TMO}s (rc=$RC3)"
if [[ $RC3 -eq 1 ]] && (( $(echo "$TMO >= 2.9 && $TMO < 4.5" | bc) )); then
  pass "exits non-zero at the deadline instead of hanging"
else
  fail "expected rc=1 at ~3s"
fi

echo
echo "=== 4. content predicate: wait for a SPECIFIC page, not any page ==="
python3 "$WAIT" --file "$STREAM" --method Page.frameNavigated \
  --contains "MARKER-DELTA" --timeout 20 > "$WORK/r4.json" &
W4=$!
sleep 0.4
chrome-agent "$INST" Page.navigate '{"url":"data:text/html,<h1>decoy-charlie</h1>"}' >/dev/null 2>&1
sleep 0.6
if kill -0 $W4 2>/dev/null; then
  STILL_BLOCKED=yes
else
  STILL_BLOCKED=no
fi
chrome-agent "$INST" Page.navigate '{"url":"data:text/html,<h1>MARKER-DELTA</h1>"}' >/dev/null 2>&1
wait $W4; RC4=$?
echo "  ignored decoy while blocked: $STILL_BLOCKED ; matched target rc=$RC4"
if [[ "$STILL_BLOCKED" == "yes" && $RC4 -eq 0 ]] && grep -q "MARKER-DELTA" "$WORK/r4.json"; then
  pass "discriminates on content, not just method"
else
  fail "predicate did not discriminate correctly"
fi

echo
echo "=== 5. chaining: consecutive waits must not re-match consumed events ==="
OFF=$(python3 "$WAIT" --file "$STREAM" --method Page.frameNavigated --timeout 5 \
        --from-offset 0 --print-offset 2>&1 >/dev/null | sed -n 's/^offset=//p')
echo "  first wait consumed up to byte $OFF"
python3 "$WAIT" --file "$STREAM" --method Page.frameNavigated --timeout 3 \
  --from-offset "$OFF" > "$WORK/r5a.json" 2>/dev/null
RC5=$?
FIRST_URL=$(python3 -c "import json;print(json.load(open('$WORK/r5a.json'))['params']['frame']['url'][:40])" 2>/dev/null)
echo "  resumed wait returned rc=$RC5 url=$FIRST_URL"
if [[ $RC5 -eq 0 && "$FIRST_URL" != *alpha* ]]; then
  pass "resumed past consumed events instead of re-matching the first"
else
  fail "offset chaining did not advance"
fi

echo
echo "=== 6. the comparison that matters: fixed sleep vs event wait ==="
python3 "$WAIT" --file "$STREAM" --method Page.loadEventFired --timeout 20 >/dev/null &
W6=$!
sleep 0.3
T0=$(now)
chrome-agent "$INST" Page.navigate '{"url":"data:text/html,<h1>echo</h1>"}' >/dev/null 2>&1
wait $W6
T1=$(now)
REAL=$(elapsed "$T0" "$T1")
echo "  actual time until the page was ready:      ${REAL}s"
echo "  a conservative 'sleep 5' would have cost:  5.000s"
WASTE=$(echo "scale=3; 5 - $REAL" | bc)
echo "  wasted wall-clock per wait:                ${WASTE}s"
pass "wakes on the event instead of guessing a duration"

echo
if [[ $FAILED -eq 0 ]]; then echo "ALL CRITERIA PASSED"; else echo "SOME CRITERIA FAILED"; fi
exit $FAILED
