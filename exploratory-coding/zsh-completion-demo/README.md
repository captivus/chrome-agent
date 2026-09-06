# zsh completion for chrome-agent -- demo and verification harness

## Goal

Tab completion for `chrome-agent`: the subcommands, and above all the **live
instance names**, so `chrome-agent stop ensor`<kbd>Tab</kbd> resolves against
what is actually registered rather than what you remember launching.

## Try it

From the repository root:

```
ZDOTDIR=$PWD/exploratory-coding/zsh-completion-demo/demo-zdotdir zsh -i
```

The demo shell sources your real `~/.zshrc` (compinit, `matcher-list`, carapace,
fzf-tab -- unchanged), then adds two things: a PATH shim so `chrome-agent` is the
working-tree build, and the completion itself. `exit` leaves it; nothing outside
the demo directory is touched.

Things to try inside it:

```
chrome-agent <TAB>                commands and live instances, both described
chrome-agent stop reader<TAB>     mid-word substring match on instance names
chrome-agent stop ensor<TAB><TAB> prefix fills, second Tab opens the fzf-tab menu
chrome-agent launch --<TAB>       flags for that subcommand
chrome-agent stop taleb-01 --<TAB> the four target selectors
chrome-agent taleb-01 Page.nav<TAB>          a CDP method, from the live protocol
chrome-agent taleb-01 <TAB>                 all 669 methods, described
chrome-agent attach taleb-01 +Page.load<TAB> a CDP event, + prefix preserved
```

Run `./setup.sh` once first -- it builds a real `chrome-agent` entry point for
the demo from this checkout, editable, so edits to the completion take effect
without reinstalling.

## Observed environment facts

Measured on this machine, 2026-09-06:

- **carapace does not own `chrome-agent`** -- `carapace --list` has 2690
  completers and `chrome-agent` is not among them. That matters: for commands
  carapace owns it prefix-filters its own candidates, which defeats
  `matcher-list` substring matching. Native zsh completion keeps it, which is
  why `stop reader`<kbd>Tab</kbd> reaches `ensorcell-reader-01` at all.
- **`chrome-agent status` takes ~60 ms** with 9 live instances, including its
  per-instance HTTP call to each browser's `/json`. That is the cost the
  completion pays on every Tab, and it is imperceptible.
- `~/.config/zsh/completions` is already on `$fpath` (set in
  `~/dotfiles/config/zsh/completions.zsh`) but **does not exist yet** -- so
  installing for real means creating it.

## Verification

`./capture.sh` renders the completion in a real terminal and screenshots it, per
`~/Documents/99_learning-records/2026-05-02-driving-host-gui-via-xvfb-without-stealing-focus.md`:
allocate a free Xvfb display (never `:0`/`:1`, never a hardcoded `:99`), run
ghostty with `--gtk-single-instance=false` so it cannot attach to the ghostty you
are using, drive it with `xdotool`, capture with `import`. Your session is never
touched, and teardown kills only the PIDs the script itself recorded.

Frames land in `captures/`. A rendered terminal frame is tens of KB; a ~240-byte
PNG means the window had not painted yet.

| frame | what it proves |
|---|---|
| `01-command-and-instances` | both groups offered, each candidate described |
| `02-instance-substring` | `stop ensor`<kbd>Tab</kbd> fills the common prefix |
| `03-launch-flags` | per-subcommand flags with descriptions |
| `04-target-flags` | the four mutually-exclusive target selectors |
| `05-instance-midword-substring` | `stop reader`<kbd>Tab</kbd> reaches `ensorcell-reader-0*` |
| `06-instance-menu-second-tab` | second Tab opens the fzf-tab menu, ports and tab counts shown |
| `07-one-shot-method-position` | the one-shot slot |
| `08-cdp-method-filtered` | `Page.nav`<kbd>Tab</kbd> completes to `Page.navigate` |
| `09-cdp-method-all` | all 669 methods, each described, from the live protocol |
| `10-attach-events` | `+Page.load`<kbd>Tab</kbd> completes, keeping the `+` |

## The harness bug that made this hard

Three verification runs showed an empty method menu, and the completion was not
at fault. Inside a completion widget, the demo shell resolved `chrome-agent` to
the **globally installed v0.5.8 tool** -- not the demo build -- even though the
demo directory was first on `$path` and `which -a` reported the demo build.
Logging `which chrome-agent` from inside the completion function is what caught
it. The original demo used a `uv run` wrapper *named* `chrome-agent`, which is
the aggravating factor; it now installs a real console script into `.venv` and
pins `hash chrome-agent=...`, which is also what a real install looks like --
exactly one chrome-agent on PATH.

Worth keeping in mind generally: a demo harness that shadows the tool under test
can silently test the wrong binary, and every symptom looks like a bug in the
thing you are testing.

## Why the cache exists

Not for Tab latency. The whole protocol schema fetches in ~7 ms, invisible next
to process startup, so the cache was initially ruled out on measurement. What
brought it back was instrumenting the completion in a live shell: with
`ZSH_AUTOSUGGEST_STRATEGY=(history completion)` -- which this configuration sets
-- **zsh runs the completion function on every keystroke**, not on Tab. Uncached,
that is a process spawn and an HTTP round trip per character typed. The cache is
keyed on the browser version the registry already records, so a hit contacts no
browser and a Chrome upgrade invalidates it.

## Not done yet

- **Target values**: `--url`<kbd>Tab</kbd> completing that instance's live tab
  URLs, `--target-index`<kbd>Tab</kbd> its indices. Needs the instance name from
  earlier in the line, which the completion already has.

## Installing it for real

Not done -- it changes managed dotfiles, so it is yours to approve:

```
mkdir -p ~/.config/zsh/completions
chrome-agent completions zsh > ~/.config/zsh/completions/_chrome-agent
```

That directory is already on `$fpath`, so a new shell picks it up. The generated
file is a snapshot, so it wants regenerating when chrome-agent is upgraded --
which argues for doing both in `~/dotfiles/install.sh` instead of by hand.
