# chrome-agent

[![PyPI version](https://img.shields.io/pypi/v/chrome-agent)](https://pypi.org/project/chrome-agent/)
[![PyPI downloads](https://img.shields.io/pepy/dt/chrome-agent)](https://pepy.tech/projects/chrome-agent)
[![Python versions](https://img.shields.io/pypi/pyversions/chrome-agent)](https://pypi.org/project/chrome-agent/)
[![License](https://img.shields.io/pypi/l/chrome-agent)](https://github.com/captivus/chrome-agent/blob/main/LICENSE)

A CLI tool that gives AI coding agents the ability to observe and interact with Chrome browsers via the [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/).

Multiple agents and humans can share the same browser simultaneously, each with isolated event subscriptions. One agent drives while another observes network traffic. A human browses while an agent watches for errors. Four agents run a coordinated test suite against a single browser. Each participant sees only the events they subscribed to -- no interference.

**I teach a live course on this:** [Building AI Agents for the Web](https://agentsfortheweb.com/?c=now-a-course-readme). Next free live lesson, Tuesday, November 24: [Find the hidden API behind any web app](https://agentsfortheweb.com/live/?c=now-a-course-readme).

<h3 align="center">Used by engineers at</h3>

<p align="center">
  <img src="https://raw.githubusercontent.com/captivus/chrome-agent/main/docs/logos/microsoft.svg" alt="Microsoft" height="28">
  &nbsp;&nbsp;&nbsp;
  <img src="https://raw.githubusercontent.com/captivus/chrome-agent/main/docs/logos/johns-hopkins-university.svg" alt="Johns Hopkins University" height="30">
  &nbsp;&nbsp;&nbsp;
  <img src="https://raw.githubusercontent.com/captivus/chrome-agent/main/docs/logos/bosch.svg" alt="Bosch" height="28">
  &nbsp;&nbsp;&nbsp;
  <img src="https://raw.githubusercontent.com/captivus/chrome-agent/main/docs/logos/texas-instruments.svg" alt="Texas Instruments" height="30">
  &nbsp;&nbsp;&nbsp;
  <img src="https://raw.githubusercontent.com/captivus/chrome-agent/main/docs/logos/deutsche-telekom.svg" alt="Deutsche Telekom" height="28">
  <br><br>
  <img src="https://raw.githubusercontent.com/captivus/chrome-agent/main/docs/logos/texas-am-university.svg" alt="Texas A&amp;M University" height="30">
  &nbsp;&nbsp;&nbsp;
  <img src="https://raw.githubusercontent.com/captivus/chrome-agent/main/docs/logos/red-hat.svg" alt="Red Hat" height="28">
  &nbsp;&nbsp;&nbsp;
  <img src="https://raw.githubusercontent.com/captivus/chrome-agent/main/docs/logos/sysco.svg" alt="Sysco" height="28">
  &nbsp;&nbsp;&nbsp;
  <img src="https://raw.githubusercontent.com/captivus/chrome-agent/main/docs/logos/databricks.svg" alt="Databricks" height="28">
  &nbsp;&nbsp;&nbsp;
  <img src="https://raw.githubusercontent.com/captivus/chrome-agent/main/docs/logos/grainger.svg" alt="Grainger" height="28">
  <br><br>
  <img src="https://raw.githubusercontent.com/captivus/chrome-agent/main/docs/logos/posthog.svg" alt="PostHog" height="28">
  &nbsp;&nbsp;&nbsp;
  <img src="https://raw.githubusercontent.com/captivus/chrome-agent/main/docs/logos/nextiva.svg" alt="Nextiva" height="28">
  &nbsp;&nbsp;&nbsp;
  <img src="https://raw.githubusercontent.com/captivus/chrome-agent/main/docs/logos/jusbrasil.svg" alt="Jusbrasil" height="28">
  &nbsp;&nbsp;&nbsp;
  <img src="https://raw.githubusercontent.com/captivus/chrome-agent/main/docs/logos/parcellab.svg" alt="parcelLab" height="28">
  &nbsp;&nbsp;&nbsp;
  <img src="https://raw.githubusercontent.com/captivus/chrome-agent/main/docs/logos/zuru-tech.svg" alt="ZURU Tech" height="28">
</p>

## Why this exists

AI coding agents need to see and interact with browsers -- to test their code, debug automation, inspect page state. The standard approach (browser MCP tools) uses a persistent server with protocol negotiation and verbose response formatting. `chrome-agent` takes a different approach: direct access to Chrome's DevTools Protocol with no abstraction layer.

This means full CDP protocol access -- every command, every event, every domain Chrome exposes. Not a curated subset of capabilities, but the complete protocol. Agents compose interactions from CDP primitives the same way DevTools does.

## Tracks the running browser, not its own version

Because there is no abstraction layer, chrome-agent tracks your browser rather than its own release. The CLI sends the method name and parameters you give it straight to Chrome and streams back the events you subscribe to -- nothing is validated against a bundled schema. So **any command, event, or domain your installed Chrome supports just works**, including protocol surface added *after* the version of chrome-agent you installed. There is no curated subset to fall behind.

For example, the `CrashReportContext` and `WebMCP` domains (added to CDP in later Chrome releases) are both absent from an older chrome-agent's typed bindings, yet a method on one returns a normal result through the CLI, with no change to chrome-agent:

```bash
chrome-agent myproject-01 CrashReportContext.getEntries
# {"entries": []}
```

The one point-in-time artifact is the typed Python classes (see [Python API](#python-api)) -- an optional convenience layer that snapshots the schema at generation time. They never gate access: `CDPClient.send(method=..., params=...)` reaches any method regardless. And `help` reads the protocol schema live from the running browser, so its documentation is always as current as your Chrome.

## Installation

```bash
uv tool install chrome-agent
```

Or add to a project:

```bash
uv add chrome-agent
```

Requires Google Chrome or Chromium installed on the system. Runtime dependencies are `websockets`, plus `cryptography` and `keyring` for encrypting saved sessions. No Playwright, no browser downloads.

## Quick Start

```bash
# Launch a browser -- auto-allocates a port and names the instance. From your
# terminal it opens on your desktop; from an AI agent, on a virtual display
# (see "Agent browsers" below)
chrome-agent launch
# {"name": "myproject-01", "port": 9222, "pid": 58469, "browser_version": "Chrome/147", "display": {"kind": "desktop", "display": ":1"}, "owner": null}

# Check what's running
chrome-agent status
# myproject-01  port 9222  [desktop :1]  kept
#   [1] 956FD3C2  https://example.com  "Example Domain"

# Read the page title
chrome-agent myproject-01 Runtime.evaluate '{"expression": "document.title", "returnByValue": true}'

# Navigate
chrome-agent myproject-01 Page.navigate '{"url": "https://example.com"}'

# Take a screenshot (returns base64 PNG in JSON)
chrome-agent myproject-01 Page.captureScreenshot '{"format": "png"}'

# Discover available commands
chrome-agent help myproject-01 Page
chrome-agent help myproject-01 Page.navigate

# Stop the browser when done
chrome-agent stop myproject-01

# Or stop a whole related set at once (quote the pattern -- see Instance Patterns)
chrome-agent stop 'myproject-*'
```

## Instance Patterns

Anywhere an instance name is accepted, a glob works instead -- `*`, `?`, `[abc]`, matched case-sensitively against the registered names.

```bash
chrome-agent stop 'myproject-*'      # stops every match, printing the names first
chrome-agent status 'myproject-*'    # lists every match
chrome-agent 'myproject-0[2]' Page.navigate '{"url": "https://example.com"}'
```

`stop` and `status` act on every match. The single-browser commands -- `attach`, `help` and one-shot CDP calls -- resolve a pattern that matches exactly one instance and otherwise error with the candidates listed, rather than picking one. A pattern matching nothing is an error, not a silent no-op.

**Quote the pattern.** Your shell expands an unquoted glob before chrome-agent sees it, and zsh aborts the command outright when nothing in the working directory matches (`zsh: no matches found: myproject-*`).

A literal name is never treated as a pattern, so `chrome-agent stop myproject-01` cannot sweep up `myproject-02`. Because `stop --target` closes one tab, combining it with a pattern that matches several instances is refused.

## Tab Completion

zsh only, for now. Two ways to install it; pick one.

**Sourced from `.zshrc`** -- one line, works anywhere, costs one subprocess
(~60 ms) at shell startup. It must come *after* `compinit`:

```bash
source <(chrome-agent completions zsh)
```

**Installed as a file** -- no startup cost, but the directory has to be on
`$fpath` *before* `compinit` runs, which is the step that is easy to miss:

```bash
mkdir -p ~/.config/zsh/completions
chrome-agent completions zsh > ~/.config/zsh/completions/_chrome-agent
```

```bash
fpath=(~/.config/zsh/completions $fpath)
autoload -Uz compinit && compinit
```

That second block goes in `.zshrc`, in that order. If the directory is not on
`$fpath`, the file is simply never read and Tab does nothing -- there is no
error to tell you so.

Either way, open a new shell and check it took:

```bash
chrome-agent <TAB>
```

You should get the subcommands and your running instances, each with a
description. If nothing happens, `echo $_comps[chrome-agent]` should print
`_chrome-agent`; an empty result means the completion was never registered.

The generated file is a snapshot of the completion logic, so regenerate it after
upgrading chrome-agent (the *candidates* it offers are always read live; the
function itself is not). Sourcing from `.zshrc` avoids that entirely.

Completes the subcommands, their flags, the **live instance names**, and **CDP
method and event names**:

```
chrome-agent stop reader<TAB>              -> ensorcell-reader-01, described by port and tab count
chrome-agent taleb-01 Page.nav<TAB>        -> Page.navigate
chrome-agent attach taleb-01 +Page.load<TAB> -> +Page.loadEventFired
```

Instance names are read from the registry as you type, so they are what is
actually registered rather than a list baked in at install time. Methods and
events come from the running browser's own `/json/protocol` -- the protocol
*this* Chrome implements, not a snapshot shipped with chrome-agent -- cached on
disk under the browser version, so a Chrome upgrade invalidates it. Without a
running browser you simply get no candidates.

The protocol cache lives under `$XDG_CACHE_HOME/chrome-agent` (default
`~/.cache/chrome-agent`), one file per browser version; deleting it is safe and
costs one 7 ms refetch.

## Two Channels

chrome-agent uses a two-channel pattern for browser interaction:

### One-shot mode (commands)

Send a single CDP command. Connects, sends, prints JSON response, disconnects.

```bash
chrome-agent <instance> Domain.method '{"param": "value"}'
```

Good for spot checks, screenshots, quick queries. ~50-80ms per call. If only one instance is running, the instance name can be omitted.

### Attach mode (events)

Persistent connection with isolated event subscriptions. Streams events to stdout as JSON lines.

```bash
chrome-agent attach <instance> +Page.loadEventFired +Network.requestWillBeSent
```

Run it in the background while sending one-shot commands:

```bash
# Background: observe events
chrome-agent attach myproject-01 +Page.loadEventFired +Network.requestWillBeSent > /tmp/events.jsonl &

# Foreground: send commands -- events appear in the attach stream
chrome-agent myproject-01 Page.navigate '{"url": "https://example.com"}'
```

Subscribe to exactly the events you need. Each attach session is isolated -- subscribing to Network events in one session does not affect other sessions.

An attach session **exits on its own once it has outlived its purpose** -- when its instance is retired from the registry, or its browser is gone or no longer reachable -- so a backgrounded observer never lingers indefinitely after the thing it was watching is gone. It also shuts down cleanly (detaching its CDP session) on `SIGTERM`/`SIGINT`, even while idle with no events arriving. A transient registry read or CDP-port blip is ridden out rather than acted on.

## Operational Commands

```
chrome-agent launch [--display virtual|desktop] [--keep] [--headless] [--fingerprint PATH] [--port PORT] [--no-window-border]
chrome-agent status [<instance|glob>]
chrome-agent attach <instance|glob> [+Event ...] [--target SPEC | --target-id ID | --target-index N | --url SUBSTRING]
chrome-agent stop <instance|glob> [--target SPEC | --target-id ID | --target-index N | --url SUBSTRING]
chrome-agent stop --orphans
chrome-agent keep <instance|glob>
chrome-agent move <instance> --to desktop|virtual
chrome-agent help [<instance|glob>] [Domain | Domain.method]
chrome-agent cleanup
chrome-agent save <instance|glob>... | --all [--stop] [--as NAME] [--overwrite | --keep-both]
chrome-agent restore [<name[@stamp]>...] | --all [--here] [--any-port] [--desktop saved|terminal] [--display virtual|desktop] [--no-reattach] [--replace-profile] [--start-display]
chrome-agent restore <name[@stamp]> --as NEW-NAME [...]
chrome-agent snapshots [list [<glob>] | show <name[@stamp]> | rm <ref>... [--older-than AGE] [--yes] | export-key | import-key [--replace]]
chrome-agent completions <zsh | instances | snapshots | methods | events> [<instance>]
chrome-agent --version
```

| Command | Description |
|---------|-------------|
| `launch` | Find Chrome, launch with CDP enabled. Auto-allocates a port and names the instance from the current directory. From an AI agent's session the browser goes on a managed virtual display and is tied to that session; from your terminal it opens on your desktop and runs until stopped. `--display virtual\|desktop` and `--keep` override -- see [Agent browsers](#agent-browsers-off-your-screen-and-gone-with-the-agent). |
| `status` | List running instances with their page targets (IDs, URLs, titles), in the order the tabs sit on screen, window by window, numbered `[1]`, `[2]`, ... left to right -- the numbers `--target N` and `--target-index N` select. If the order cannot be read, `status` says so and numbers tabs by target id instead. Accepts a glob to list a matching subset. Each header says where the browser is -- `[desktop :1]` on your screen, `[Xvfb :100]` on a virtual X display (Xvfb, Xvnc, Xephyr), `[headless]` with no window -- and who it belongs to: `owner claude-code pid 9669` for an agent session's browser (`(yours)` when you are that session), `kept` for one with no owner, `ORPHAN` when its owner has exited. The JSON form carries `display` and `owner` fields for every live instance. |
| `attach` | Persistent event observation with isolated subscriptions. Use `--target` (fewer than 8 digits is a tab number, anything else a target-id prefix), `--url substring`, or the explicit `--target-id` / `--target-index` for multi-tab browsers. Tab `N` is the Nth tab on screen, as `status` numbers them. |
| `stop` | Gracefully shut down a browser instance (`Browser.close`) or close a specific tab (`Target.closeTarget`). Accepts a glob, stopping every matching instance. Use `--target` or `--url` to close a single tab without affecting the browser; because this closes a tab, prefer `--target-id`: an id never changes, while a tab's number shifts whenever tabs are opened, closed or dragged. |
| `help` | Query the browser's protocol schema. Lists domains, commands, events, parameters. |
| `stop --orphans` | Stop every browser whose owning agent session has exited. Normally each one's supervisor does this by itself within seconds; this is the sweep for when it could not. |
| `keep` | Release an instance from its agent session, so it runs until stopped (like `launch --keep`). |
| `move` | Move a running browser between your desktop and a managed virtual display, keeping its name, port, tabs and logins (a `save --stop` and `restore` in one step). |
| `cleanup` | Remove stale instances (dead browsers) and their session directories; re-arm the keeper of any managed virtual display that lost its own. |
| `save` | Snapshot running instances -- profile, tabs, cookies, launch flags, desktop, observers -- so they can be restored later. See [Saving and Restoring Sessions](#saving-and-restoring-sessions). |
| `restore` | Bring snapshots back as running instances under their original names and ports (or one under a new name, with `--as`). |
| `snapshots` | List, inspect (`show`) and delete (`rm`) saved snapshots; back up the encryption key. |
| `completions` | `zsh` prints a shell completion; `instances`, `methods` and `events` print `name:description` lines for the registered instances and for the running browser's CDP protocol (what the completion reads as you type). |
| `--version` | Print the installed chrome-agent version (`-V` alias) and exit. |

Instances are tracked in a registry at `/tmp/chrome-agent/registry.json`. A headed browser's instance is **automatically removed from the registry when its window is closed** (its session directory is cleaned up too), so `status` reflects what is actually running. Liveness is determined by **process identity plus port attribution**, not a bare PID-existence check: the recorded PID counts only if it is a live process of the launching user whose start time matches what was recorded at launch (so a recycled or namespace-local PID never masquerades as the browser), and a listening CDP port counts only if a process claiming that port with this instance's profile directory can be found -- so browsers started via wrapper/snap launchers (which fork the real browser into another process) are still reported correctly, while a port since claimed by a *different* browser is not mistaken for this one. A **transient connection drop does not retire a live instance**: a host suspend/resume severs the supervisor's CDP connection while Chrome keeps running, so the supervisor reconnects and keeps supervising; retirement happens only once the CDP port stops listening. `cleanup` removes any entries that remain (headless instances, or browsers that were killed abruptly).

Two consequences worth knowing. **Launching from inside a PID-namespaced sandbox** (a container, bubblewrap, some agent-CLI sandboxes) records the sandbox's local PID in the shared registry; the identity check recognizes such an entry as stale once its browser is gone, instead of treating the aliased host PID as a live browser forever. **`stop` verifies its target before acting**: it never sends `Browser.close` to a port that is serving a different browser (it terminates the instance's own verified process instead, or just cleans up the stale entry), and its SIGTERM fallback only ever fires at a PID verified to be the instance's own browser process.

## Agent browsers: off your screen, and gone with the agent

Two things go wrong when AI agents launch browsers on a workstation. A headed window opening on your desktop takes your focus in the middle of whatever you were doing. And a browser an agent forgot to stop keeps running after the agent is gone -- for days, at up to a full CPU core each. chrome-agent handles both by default for agents, and leaves your own launches alone.

**Who counts as an agent.** A launch is an agent's when it comes from inside an agent session: chrome-agent looks for an agent CLI (`claude`, `codex`) among the launching command's parent processes, and for the environment those CLIs export (`CLAUDECODE`, `CODEX_THREAD_ID`, `AI_AGENT`, ...). Both Claude Code and Codex are recognized with no setup. `chrome-agent launch` typed in your own terminal has neither, so it behaves as it always has. Detection was chosen over a variable each agent launcher must remember to set (the failure being guarded against is exactly a forgotten step) and over a virtual default for everyone (your own `launch` should open where you can see it). For another harness, `CHROME_AGENT_OWNER_PID=<its pid>` marks its launches as an agent's, owned by that process; `CHROME_AGENT_DISPLAY=virtual|desktop` sets the default display for anyone.

**Off your screen: a managed virtual display.** An agent's browser opens on a virtual X display (Xvfb) that chrome-agent starts itself on the first free display from `:100`, shares between every agent browser while it is up, and removes once the last browser on it is gone. It is an ordinary headed Chrome, so sites see nothing unusual (unlike `--headless`); screenshots, input and CDP work the same. A small keeper process per display checks every 2 seconds whether any process still runs on that display -- which catches a browser however it ended: `stop`, a closed window, a crash, a kill -- and stops the Xvfb after two idle checks (never within 30 seconds of a launch claiming it, so a browser still starting is safe). (Xvfb's own `-terminate` is no help: it exits on any connection closing, even a bare probe.) An agent that already runs on a virtual display (`DISPLAY=:95` with an Xvfb behind it) keeps using it. If Xvfb is not installed, an agent launch fails and says how to install it rather than falling back to your screen. Linux only; elsewhere the default stays the desktop.

**Onto your screen when you need it.** `launch --display desktop` opens on your desktop -- e.g. so you can sign in to a site yourself. `chrome-agent move <instance> --to desktop` brings a running browser onto your screen and `--to virtual` takes it off again, keeping its name, port, tabs, logins and cookies: a browser cannot change X display while it runs, so this is `save --stop` and `restore` in one step, through a snapshot that is deleted once the browser is back (it needs the snapshot key, see below).

**Gone with the agent: owners.** An agent's launch records the agent session's process as the instance's **owner** -- pid, start time and PID namespace, so a recycled PID never passes for it. The per-instance supervisor checks the owner every 5 seconds and stops the browser after two checks find it gone, so an agent browser outlives its session by about 10 seconds. A browser launched with `--keep`, released with `chrome-agent keep`, launched from your terminal, or brought back by `restore` has no owner and runs until stopped. Nothing ever stops a browser on an uncertain answer, and there is no age-based sweep: a browser is stopped because the session it belongs to ended, never because it has been running a long time.

- **Sub-agents.** Claude Code runs sub-agents inside the session's own process, so their browsers belong to the session and last until it ends. An agent that runs as its own process (an agent-collab worker, a nested `claude -p`) owns its browsers itself, and they end with it; it can hand one on with `keep`.
- **PID-namespaced sandboxes.** Codex runs each command in a bubblewrap sandbox with its own PID namespace, where no process outside it is visible. Everything started in there -- browser, supervisor, a virtual display of its own -- dies with the sandbox regardless, so the owner recorded is the sandbox itself; `status` on the host finds it by namespace. A check made from inside a different sandbox cannot see the owner and reports it as unknown, never as gone.
- **Suspend and resume.** Process identity survives a suspend, and the supervisor already rides out the CDP drop a resume causes, so a sleeping laptop stops nothing.
- **When the supervisor itself was killed**, no one stops the browser: `status` shows it as `ORPHAN`, and `chrome-agent stop --orphans` stops every such browser.

## Saving and Restoring Sessions

A launched browser's profile lives under `/tmp/chrome-agent/` and is deleted when the browser closes -- and most Linux systems empty `/tmp` at boot anyway. So logins, cookies and open tabs do not survive a restart unless you save them:

```bash
chrome-agent save --all --stop     # before a reboot: close every instance cleanly and save it
chrome-agent restore --all         # after: bring them all back
```

A snapshot holds everything needed to bring an instance back as it was:

- **The profile** -- cookies, localStorage, IndexedDB, saved logins -- minus caches and components Chrome re-downloads on its own (a real profile is typically 5-20 MB saved).
- **Every cookie the browser holds in memory**, including session cookies that are never written to disk; they are set again on restore before any tab loads.
- **Windows and tabs**, with each window's size, position and active tab.
- **Tab order**, window by window, as the tabs sit on screen. CDP has no command for tab order (`Target.getTargets` lists pages in an order of its own), so `save`, `status` and selecting a tab by number load a tiny bundled extension over CDP for a moment (about a tenth of a second), read the order from Chrome's extension API, and uninstall it; an extension loaded this way does not survive a restart, so it never ends up in a saved profile. Where Chrome refuses (extensions disabled by policy or flag), tabs fall back to target-id order -- for numbering too, so `status` and `--target N` still agree.
- **Name, port and working directory**, so an agent or script that addresses `mysite-01` (or its port) carries on unchanged. A fresh `launch` avoids the ports the last `save --all` will restore onto.
- **Launch settings** -- headless, extra Chrome flags, fingerprint flags and TZ, window border, and a custom `--user-data-dir` if one was given.
- **The virtual desktop** of each window (Linux/X11), or -- for a browser kept off-screen on a virtual X display (Xvfb, Xvnc, Xephyr) -- that display and the command that started its server.
- **`attach` observers** subscribed to the instance. One that wrote to a file (including a shell loop that re-attaches) is restarted on restore; one whose output was piped to a reader that is gone is printed as the command to run.

```bash
chrome-agent save mysite-01                  # live: the browser keeps running
chrome-agent save mysite-01 --stop           # close it cleanly first -- fully consistent
chrome-agent save 'mysite-*'                 # every matching instance
chrome-agent restore mysite-01               # the latest version
chrome-agent restore mysite-01@20260927T153000Z
chrome-agent restore                         # everything launched from the current directory
chrome-agent restore mysite-04 --as mysite-01  # bring it back under a new name
chrome-agent snapshots                       # list: name@stamp, saved, tabs, size, port, origin dir
chrome-agent snapshots show mysite-01        # tabs, observers, launch flags, desktop
chrome-agent snapshots rm mysite-01          # every version (asks first; --yes when scripted)
chrome-agent snapshots rm --older-than 30d
```

**Versions.** Each save is a timestamped version. When one already exists, an interactive `save` shows when it was saved and its tabs and asks whether to overwrite it; answering no keeps both. Non-interactively, both are kept unless `--overwrite` is given. Nothing is ever deleted automatically -- not by a restore, not by age -- so saving and discarding credentials stays a deliberate act.

**Consistency.** `--stop` closes the browser cleanly before copying, so every database is complete on disk; use it before a reboot. A live save copies the files while Chrome runs without taking any lock (Chrome holds most of its SQLite databases exclusively, and a reader's lock on the rest could make Chrome's own writes fail), re-reading any file that changes mid-copy. Cookies are captured from the running browser either way, so they do not depend on what Chrome has flushed to disk.

**Encryption.** Snapshots are credential bundles, so every snapshot file except a small plaintext summary (no URLs, no cookies) is encrypted with AES-256-GCM under a key kept in the OS keyring (GNOME Keyring / KWallet, macOS Keychain, Windows Credential Locker). The keyring unlocks at login, so restores need no prompt; a snapshot that ends up in a backup or a synced folder is unreadable without the key. **If the keyring is lost, the snapshots are unrecoverable** -- back the key up with `chrome-agent snapshots export-key`, and load it on another machine with `chrome-agent snapshots import-key < keyfile`. On a host with no keyring service, set `CHROME_AGENT_SNAPSHOT_KEY` to a base64 32-byte key. Snapshots live in `~/.local/share/chrome-agent/snapshots/` (mode 0700).

**Renaming.** `save --as NAME` names the *snapshot*, not the session: the snapshot still records the instance name it was saved from, and a plain `restore` brings that name back. To bring a session back under a different instance name, use `restore <snapshot> --as NEW-NAME`. Everything else -- tabs, logins, port, windows -- comes back as saved, and `attach` observers that named the old instance are restarted against the new one. The snapshot is left unchanged (restoring it without `--as` still gives the old name); the next `save` of the renamed browser is filed under the new name. `--as` restores exactly one snapshot, so it cannot be combined with `--all` or a glob matching several.

**Restoring safely.** `restore` refuses when the instance is already running (it was restored already, or the original never closed), when the saved port is taken by something else (`--any-port` picks a new one), or when a custom profile directory already exists (`--replace-profile` moves it aside rather than deleting it). It warns when the installed Chrome is older than the one that saved the snapshot, since an older Chrome may refuse a newer profile. Sites that bind a login to a device or IP, or expire it server-side, may still ask you to sign in again.

**Virtual displays.** A browser running on a virtual X display is restored onto that same display, never onto the screen of whoever runs `restore`. A virtual display usually does not survive a reboot, so `restore` refuses while it is down and names the command that starts it; `--start-display` runs that recorded command (e.g. `Xvfb :90 -screen 0 1920x1200x24 -nolisten tcp`) first. A session saved from a display chrome-agent managed is not tied to its number: it comes back on whichever managed display is up, started if need be. A browser on your own desktop is not tied to a display number either -- that can change across a reboot -- and follows the display `restore` runs on. `--display virtual` or `--display desktop` overrides all of this for one restore. A restored session has no owner (see [Agent browsers](#agent-browsers-off-your-screen-and-gone-with-the-agent)): it runs until stopped, whoever restores it.

**Virtual desktops.** A single restore puts the browser on the current terminal's desktop, alongside the project you just reopened. `restore --all` puts each window back on the desktop it was saved from (`--desktop` overrides either default). With dynamic workspaces (GNOME's default) a window can only go as far as the last workspace that exists -- the window manager deletes empty workspaces in the middle -- so `restore --all` works through the snapshots in desktop order: the original layout comes back where the workspaces in between are occupied, and otherwise windows are packed down, keeping the ones that shared a desktop together and in order.

## Interacting with Elements

Agents interact with page elements using a three-step pattern: **locate, act, verify.**

```bash
# Locate -- find element coordinates via JavaScript
chrome-agent myproject-01 Runtime.evaluate '{"expression": "(() => { const r = document.querySelector(\"#submit\").getBoundingClientRect(); return {x: r.x+r.width/2, y: r.y+r.height/2}; })()", "returnByValue": true}'

# Act -- dispatch real input events at those coordinates
chrome-agent myproject-01 Input.dispatchMouseEvent '{"type": "mousePressed", "x": 400, "y": 300, "button": "left", "clickCount": 1}'
chrome-agent myproject-01 Input.dispatchMouseEvent '{"type": "mouseReleased", "x": 400, "y": 300, "button": "left", "clickCount": 1}'

# Verify -- confirm the action worked
chrome-agent myproject-01 Runtime.evaluate '{"expression": "document.title", "returnByValue": true}'
```

Chrome processes dispatched input events identically to physical input. A human watching the browser sees the cursor move, buttons depress, text highlight, and pages load in real time.

## Python API

```python
from chrome_agent.cdp_client import CDPClient, get_ws_url
from chrome_agent.domains.page import Page
from chrome_agent.domains.runtime import Runtime

async with CDPClient(ws_url=get_ws_url(port=9222)) as cdp:
    page = Page(client=cdp)
    runtime = Runtime(client=cdp)

    await page.navigate(url="https://example.com")
    result = await runtime.evaluate(expression="document.title", return_by_value=True)
    print(result["result"]["value"])
```

54 typed domain classes with snake_case methods, generated from Chrome's protocol schema. They are an optional convenience layer -- a point-in-time snapshot, not a gate. For any method newer than the snapshot, call `CDPClient.send(method=..., params=...)` directly (see [Tracks the running browser, not its own version](#tracks-the-running-browser-not-its-own-version)).

## Window Border

So you can tell an agent-driven window apart from your own Chrome windows, every launched browser is marked by default: a colored border + corner badge around each tab (a stable, per-instance color derived from the instance name), and a title prefix so the window reads as `🤖 <instance> — <the page's own title>` in the taskbar / Alt-Tab. The marker is drawn in a closed shadow DOM and adds no automation-detection signal (verified against bot.sannysoft.com and CreepJS).

```bash
chrome-agent launch                     # marked (default)
chrome-agent launch --no-window-border  # no marker
```

The marker is suppressed automatically when running `--headless` (no visible window) or with `--fingerprint` (the in-page marker is page-observable, and stealth is the point on the sites where fingerprinting is used).

## Browser Fingerprinting

For sites that detect automated browsers, launch with a fingerprint profile:

```bash
chrome-agent launch --fingerprint profile.json
```

```json
{
    "userAgent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 ...",
    "platform": "Linux x86_64",
    "vendor": "Google Inc.",
    "language": "en-US",
    "timezone": "America/Chicago",
    "viewport": {"width": 1920, "height": 1080}
}
```

Spoofs the user agent (HTTP header and JavaScript), viewport, language, and timezone via Chrome launch flags -- persistent across navigations, with no JavaScript injection.

It deliberately does **not** patch `navigator.webdriver`, `navigator.platform`, `navigator.vendor`, or `window.chrome`. An empirical detection audit found those JS overrides are each independently detectable and make the browser *more* detectable, not less: they flip bot.sannysoft.com's WebDriver test from pass to fail (the override makes `navigator.webdriver` an own property) and raise CreepJS's headless score. A plain CDP-attached Chrome already reports the native `navigator.webdriver === false` and keeps the genuine `window.chrome` shape, so the cleanest profile is one that leaves the JS environment untouched. A profile's `platform`/`vendor` should match the host OS (they are retained in the schema but not spoofed). Note that WebRTC can still leak the real IP regardless of profile.

Headless mode has one giveaway that has nothing to do with fingerprinting: Chrome puts `HeadlessChrome/` in the User-Agent (`...HeadlessChrome/151.0.0.0 Safari/537.36`), and some sites block on that string alone. A profile's `userAgent` replaces it. For a lighter fix, derive the ordinary UA from a running headless instance and relaunch with only that flag:

```bash
UA=$(chrome-agent <instance> Browser.getVersion | sed -n '/"userAgent"/{s/.*"userAgent": "\([^"]*\)".*/\1/;s/HeadlessChrome/Chrome/;p;}')
chrome-agent stop <instance>
chrome-agent launch --headless -- "--user-agent=$UA"
```

Derived this way, the version and platform always match the installed Chrome; a hardcoded UA drifts out of step on the next update, and a UA claiming a different version than the browser is its own signal.

## For AI Agents

See [AGENTS.md](https://github.com/captivus/chrome-agent/blob/main/AGENTS.md) for concise agent instructions (the standard for AI agent tool documentation). It covers the mental model (address an instance, send any CDP command), the sense ⇄ act loop, the two channels, the command reference, and gotchas.

**The guide ships with the package**, so an agent can reach it from any install without a checkout:

```bash
chrome-agent guide          # print the guide
chrome-agent guide --path   # print its path, to read with your own file tools
```

`--path` is usually what you want: reading the file directly beats paging 20+ KB through stdout. The command is listed in `chrome-agent --help`, which is how an agent meeting this tool for the first time finds it.

The bundled copy is captured when the release is built, so it always matches the version installed. To make it load automatically -- most agent harnesses read an `AGENTS.md` from the *project* root, not from site-packages -- link it into your project:

```bash
ln -s "$(chrome-agent guide --path)" AGENTS-chrome-agent.md
```

**`AGENTS.md` is a tailorable example, not gospel.** Its *mechanics* are exact, but the operating judgment in it is general -- adapt it to your own sites, tasks, and constraints. A good pattern is to keep a private, project-specific layer on top -- site-specific field notes, extraction playbooks, hard-won gotchas -- that *references* this public manual and extends it, rather than forking a separate set of instructions. Grow yours the same way.

## Collaboration

Multiple participants -- humans, AI agents, or both -- can share a browser simultaneously. Each participant creates an independent CDP session with isolated event subscriptions. One agent enabling Network observation does not flood another agent's event stream.

See [docs/collaboration-guide.md](https://github.com/captivus/chrome-agent/blob/main/docs/collaboration-guide.md) for:
- Human-agent collaboration patterns (you browse, agent watches)
- Agent-driven workflows (agent drives, you supervise)
- Multi-agent setups with isolated event subscriptions
- The observation gap (what CDP sees vs what it misses)
- Full interaction observation via the binding bridge

For real-time observation using Claude Code's Monitor tool, see [AGENTS.md](AGENTS.md#reacting-to-events-as-they-happen-monitor) for the practical usage path (subscribing, discovering events via `help`, the gotchas), and [docs/monitor-integration.md](https://github.com/captivus/chrome-agent/blob/main/docs/monitor-integration.md) for the architecture and usage patterns in depth.

Monitor is specific to Claude Code. Agents on other harnesses can still be event-driven rather than falling back to fixed sleeps -- background `attach` to a file once, then block on [`scripts/cdp-wait.py`](https://github.com/captivus/chrome-agent/blob/main/scripts/cdp-wait.py), which returns the instant a matching event lands and also catches events that fired before the wait began. See [docs/event-driven-without-monitor.md](https://github.com/captivus/chrome-agent/blob/main/docs/event-driven-without-monitor.md).

## Requirements

- Python >= 3.11
- Google Chrome or Chromium (system-installed)
- Linux with xdotool (optional, for virtual desktop pinning)
- Xvfb on Linux, for agent launches (`sudo apt install xvfb`); without it an agent must launch with `--display desktop` or `--headless`

## Releasing (maintainer)

Releases are cut from the project root with `release X.Y.Z` (or `release` for an interactive version prompt). The tool bumps `pyproject.toml`, commits, tags, pushes -- which triggers the PyPI publish workflow via GitHub Actions Trusted Publishing. Release notes auto-generate from commit messages between tags, so commits should read well as changelog entries.

## License

MIT
