#!/usr/bin/env bash
# Render the chrome-agent zsh completion in a REAL terminal and screenshot it.
#
# Follows ~/Documents/99_learning-records/2026-05-02-driving-host-gui-via-xvfb-without-stealing-focus.md:
# allocate a free display (never :0/:1, never a hardcoded :99), run ghostty with
# --gtk-single-instance=false so it cannot attach to the user's own ghostty,
# drive with xdotool, capture with import. The user's session is never touched.
#
# Usage: ./capture.sh [outdir]
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$HERE/captures}"
mkdir -p "$OUT"
rm -f "$OUT"/*.png

# ---------------------------------------------------------------- display ----
DISP=""
XVFB_PID=""
for n in $(seq 120 179); do
  DISPLAY=":$n" xdpyinfo >/dev/null 2>&1 && continue          # live -- skip
  Xvfb ":$n" -screen 0 1600x900x24 -ac +extension RANDR -nolisten tcp \
    >/dev/null 2>"/tmp/xvfb-$n.log" &
  pid=$!
  for _ in $(seq 1 30); do DISPLAY=":$n" xdpyinfo >/dev/null 2>&1 && break; sleep 0.1; done
  # Both conditions: the display answers AND the server answering is the one we started.
  if DISPLAY=":$n" xdpyinfo >/dev/null 2>&1 && kill -0 "$pid" 2>/dev/null; then
    DISP=":$n"; XVFB_PID="$pid"; break
  fi
  kill "$pid" 2>/dev/null
done
[[ -n "$DISP" ]] || { echo "could not allocate a display" >&2; exit 1; }
echo "driving $DISP (Xvfb pid $XVFB_PID)"

GHOSTTY_PID=""
cleanup() {
  # Only ever kill PIDs recorded at launch -- never a name-derived lookup.
  [[ -n "$GHOSTTY_PID" ]] && kill "$GHOSTTY_PID" 2>/dev/null
  [[ -n "$XVFB_PID" ]] && kill "$XVFB_PID" 2>/dev/null
  return 0
}
trap cleanup EXIT

# ---------------------------------------------------------------- terminal ----
export LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe        # Xvfb has no GPU
DISPLAY="$DISP" ZDOTDIR="$HERE/demo-zdotdir" \
  ghostty --gtk-single-instance=false --window-width=200 --window-height=45 \
  -e zsh -i >/dev/null 2>&1 &
GHOSTTY_PID=$!

WID=""
for _ in $(seq 1 60); do                                       # llvmpipe cold start is slow
  WID=$(DISPLAY="$DISP" xdotool search --pid "$GHOSTTY_PID" 2>/dev/null | tail -1)
  [[ -n "$WID" ]] && break
  sleep 1
done
[[ -n "$WID" ]] || { echo "ghostty never mapped a window" >&2; exit 1; }
echo "window $WID"
DISPLAY="$DISP" xdotool windowsize "$WID" 1560 860
sleep 3

# Focus by physical click -- there is no WM, so windowactivate cannot work.
eval "$(DISPLAY="$DISP" xdotool getwindowgeometry --shell "$WID")"
DISPLAY="$DISP" xdotool mousemove $((X + WIDTH/2)) $((Y + HEIGHT/2)) click 1
sleep 2

shot() { DISPLAY="$DISP" import -window root "$OUT/$1.png"; echo "  -> $1.png $(stat -c%s "$OUT/$1.png") bytes"; }

# An interactive shell carries line-buffer and open-menu state between steps;
# reset with pauses BETWEEN the keys or they race and leave residue.
reset_line() {
  DISPLAY="$DISP" xdotool key Escape;  sleep 0.6
  DISPLAY="$DISP" xdotool key ctrl+u;  sleep 0.6
  DISPLAY="$DISP" xdotool key ctrl+c;  sleep 0.8
}

type_str() { DISPLAY="$DISP" xdotool type --delay 40 "$1"; }
tab()      { DISPLAY="$DISP" xdotool key Tab; }

sleep 8                                                        # let the demo banner settle
shot 00-prompt

# 1. bare command: subcommands + live instances, both described
reset_line; type_str "chrome-agent "; sleep 1; tab; sleep 4
shot 01-command-and-instances
DISPLAY="$DISP" xdotool key Escape; sleep 1

# 2. substring match on an instance name (the matcher-list payoff)
reset_line; type_str "chrome-agent stop ensor"; sleep 1; tab; sleep 4
shot 02-instance-substring
DISPLAY="$DISP" xdotool key Escape; sleep 1

# 3. flags for a subcommand
reset_line; type_str "chrome-agent launch --"; sleep 1; tab; sleep 4
shot 03-launch-flags
DISPLAY="$DISP" xdotool key Escape; sleep 1

# 4. target selectors on stop
reset_line; type_str "chrome-agent stop taleb-01 --"; sleep 1; tab; sleep 4
shot 04-target-flags
DISPLAY="$DISP" xdotool key Escape; sleep 1

# 5. TRUE mid-word substring on an instance name -- this is the matcher-list
#    payoff, and the thing that would NOT work if carapace owned chrome-agent.
reset_line; type_str "chrome-agent stop reader"; sleep 1; tab; sleep 4
shot 05-instance-midword-substring
DISPLAY="$DISP" xdotool key Escape; sleep 1

# 6. second Tab after the common prefix fills -- fzf-tab opens the menu
reset_line; type_str "chrome-agent stop ensor"; sleep 1; tab; sleep 3; tab; sleep 4
shot 06-instance-menu-second-tab
DISPLAY="$DISP" xdotool key Escape; sleep 1

# 7. one-shot form: after an instance name, the CDP method position
reset_line; type_str "chrome-agent taleb-01 "; sleep 1; tab; sleep 4
shot 07-one-shot-method-position
DISPLAY="$DISP" xdotool key Escape; sleep 1

# 8. CDP methods in the one-shot position, filtered by what is typed
reset_line; type_str "chrome-agent taleb-01 Page.nav"; sleep 1; tab; sleep 5
shot 08-cdp-method-filtered
DISPLAY="$DISP" xdotool key Escape; sleep 1

# 9. the whole method surface -- 669 candidates, grouped and described
reset_line; type_str "chrome-agent taleb-01 "; sleep 1; tab; sleep 6
shot 09-cdp-method-all
DISPLAY="$DISP" xdotool key Escape; sleep 1

# 10. attach events -- the + prefix must survive onto the inserted candidate
reset_line; type_str "chrome-agent attach taleb-01 +Page.load"; sleep 1; tab; sleep 5
shot 10-attach-events
DISPLAY="$DISP" xdotool key Escape; sleep 1

echo "captures in $OUT"
