# chrome-agent

[![PyPI version](https://img.shields.io/pypi/v/chrome-agent)](https://pypi.org/project/chrome-agent/)
[![PyPI downloads](https://img.shields.io/pepy/dt/chrome-agent)](https://pepy.tech/projects/chrome-agent)
[![Python versions](https://img.shields.io/pypi/pyversions/chrome-agent)](https://pypi.org/project/chrome-agent/)
[![License](https://img.shields.io/pypi/l/chrome-agent)](https://github.com/captivus/chrome-agent/blob/main/LICENSE)

A CLI tool that gives AI coding agents the ability to observe and interact with Chrome browsers via the [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/).

Multiple agents and humans can share the same browser simultaneously, each with isolated event subscriptions. One agent drives while another observes network traffic. A human browses while an agent watches for errors. Four agents run a coordinated test suite against a single browser. Each participant sees only the events they subscribed to -- no interference.

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

Requires Google Chrome or Chromium installed on the system. Single runtime dependency (`websockets`). No Playwright, no browser downloads.

The browser is found by checking the platform's well-known install paths first, then `$PATH`. For anything else -- Chrome for Testing, a user-local install, a second channel you want to pin -- name it explicitly:

```bash
chrome-agent launch --binary /opt/chrome-for-testing/chrome
CHROME_AGENT_BINARY=/opt/chrome-for-testing/chrome chrome-agent launch
```

An override is authoritative: if the path is not executable the launch fails and names it, rather than silently falling back to a different browser than the one you asked for.

## Quick Start

```bash
# Launch a browser -- auto-allocates a port and names the instance
chrome-agent launch
# {"name": "myproject-01", "port": 9222, "pid": 58469, "browser_version": "Chrome/147"}

# Check what's running
chrome-agent status
# myproject-01  port 9222
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
```

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
chrome-agent launch [--headless] [--fingerprint PATH] [--port PORT] [--binary PATH] [--no-window-border]
chrome-agent status [<instance>]
chrome-agent attach <instance> [+Event ...] [--target SPEC] [--url SUBSTRING]
chrome-agent stop <instance> [--target SPEC] [--url SUBSTRING]
chrome-agent help [<instance>] [Domain | Domain.method]
chrome-agent cleanup
chrome-agent --version

chrome-agent eval [<instance>] <expr | --file PATH | -> [--json]
chrome-agent screenshot [<instance>] [-o FILE] [--full-page] [--selector CSS] [--format png|jpeg] [--quality N]
chrome-agent wait [<instance>] <Domain.event ...> [--timeout SECS] [--contains SUBSTRING]
chrome-agent navigate [<instance>] <URL> [--wait load|domcontentloaded|none] [--timeout SECS]
```

| Command | Description |
|---------|-------------|
| `launch` | Find Chrome, launch with CDP enabled. Auto-allocates a port and names the instance from the current directory. |
| `status` | List running instances with their page targets (IDs, URLs, titles). |
| `attach` | Persistent event observation with isolated subscriptions. Use `--target N` or `--url substring` for multi-tab browsers. |
| `stop` | Gracefully shut down a browser instance (`Browser.close`) or close a specific tab (`Target.closeTarget`). Use `--target` or `--url` to close a single tab without affecting the browser. |
| `help` | Query the browser's protocol schema. Lists domains, commands, events, parameters. |
| `cleanup` | Remove stale instances (dead browsers) and their session directories. |
| `--version` | Print the installed chrome-agent version (`-V` alias) and exit. |
| `eval` | Run JavaScript and print the resulting value. Source comes from an argument, `--file`, or stdin (`-`), which sidesteps JSON-inside-shell quoting. Promises are awaited; a page exception exits 1. |
| `screenshot` | Capture the page to a file -- base64 decoding included. `--full-page` captures beyond the viewport, `--selector` captures one element. |
| `wait` | Block until a CDP event fires, then print it. Exits 1 on timeout. Replaces fixed `sleep`s in scripted flows. |
| `navigate` | Navigate, wait for the document to load, and report the main document's HTTP status -- which raw `Page.navigate` never returns. |

Instances are tracked in a registry at `/tmp/chrome-agent/registry.json`. A headed browser's instance is **automatically removed from the registry when its window is closed** (its session directory is cleaned up too), so `status` reflects what is actually running. Liveness is determined by **process identity plus port attribution**, not a bare PID-existence check: the recorded PID counts only if it is a live process of the launching user whose start time matches what was recorded at launch (so a recycled or namespace-local PID never masquerades as the browser), and a listening CDP port counts only if a process claiming that port with this instance's profile directory can be found -- so browsers started via wrapper/snap launchers (which fork the real browser into another process) are still reported correctly, while a port since claimed by a *different* browser is not mistaken for this one. A **transient connection drop does not retire a live instance**: a host suspend/resume severs the supervisor's CDP connection while Chrome keeps running, so the supervisor reconnects and keeps supervising; retirement happens only once the CDP port stops listening. `cleanup` removes any entries that remain (headless instances, or browsers that were killed abruptly).

Two consequences worth knowing. **Launching from inside a PID-namespaced sandbox** (a container, bubblewrap, some agent-CLI sandboxes) records the sandbox's local PID in the shared registry; the identity check recognizes such an entry as stale once its browser is gone, instead of treating the aliased host PID as a live browser forever. **`stop` verifies its target before acting**: it never sends `Browser.close` to a port that is serving a different browser (it terminates the instance's own verified process instead, or just cleans up the stale entry), and its SIGTERM fallback only ever fires at a PID verified to be the instance's own browser process.

## Convenience Verbs

Three operations dominate agent use and are awkward as raw CDP calls, so each has a verb. They are wrappers, not a layer: the raw form still reaches every method, and nothing is validated against a bundled schema.

```bash
# JavaScript without the JSON-inside-shell quoting fight
chrome-agent eval 'document.title'
chrome-agent eval --file scrape.js          # multi-line JS, no escaping
echo 'document.readyState' | chrome-agent eval -
```

`eval` prints the **value** -- a string as itself, anything else as JSON -- because `Runtime.evaluate`'s envelope (`result.result.value`) is almost never what the caller wants. Promises are awaited. `--json` returns the full response. A thrown page exception goes to stderr and exits 1, so an error can never be mistaken for a result.

```bash
# Screenshots land on disk, already decoded
chrome-agent screenshot -o page.png
chrome-agent screenshot -o full.png --full-page
chrome-agent screenshot -o button.png --selector '#submit'
```

```bash
# Wait for an event instead of guessing with sleep
chrome-agent wait Page.loadEventFired --timeout 15
chrome-agent wait Network.responseReceived --contains example.com
```

```bash
# Navigate with a load barrier and a real status code
chrome-agent navigate https://example.com
# {"url":"https://example.com/","status":200,...,"loaded":true,"elapsedMs":93}
```

`Page.navigate` returns at commit time and its result carries no status, so a 404 or a bot-block page is indistinguishable from content until you inspect the DOM. `navigate` closes both gaps: it waits for `load` (or `domcontentloaded`, or nothing) and reports `status`. A navigation Chrome refuses outright -- DNS failure, bad scheme -- exits 1 rather than returning a result that looks fine.

`wait` opens its own isolated session, so it matches only events that fire **after** it subscribes -- start it in the background before the action that triggers the event. To catch events that may fire first, background `attach` to a file and use [`scripts/cdp-wait.py`](scripts/cdp-wait.py) instead.

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

## For AI Agents

See [AGENTS.md](AGENTS.md) for concise agent instructions (the standard for AI agent tool documentation). It covers the mental model (address an instance, send any CDP command), the sense ⇄ act loop, the two channels, the command reference, and gotchas.

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

See [docs/collaboration-guide.md](docs/collaboration-guide.md) for:
- Human-agent collaboration patterns (you browse, agent watches)
- Agent-driven workflows (agent drives, you supervise)
- Multi-agent setups with isolated event subscriptions
- The observation gap (what CDP sees vs what it misses)
- Full interaction observation via the binding bridge

For real-time observation using Claude Code's Monitor tool, see [AGENTS.md](AGENTS.md#reacting-to-events-as-they-happen-monitor) for the practical usage path (subscribing, discovering events via `help`, the gotchas), and [docs/monitor-integration.md](docs/monitor-integration.md) for the architecture and usage patterns in depth.

Monitor is specific to Claude Code. Agents on other harnesses can still be event-driven rather than falling back to fixed sleeps -- background `attach` to a file once, then block on [`scripts/cdp-wait.py`](scripts/cdp-wait.py), which returns the instant a matching event lands and also catches events that fired before the wait began. See [docs/event-driven-without-monitor.md](docs/event-driven-without-monitor.md).

## Requirements

- Python >= 3.11
- Google Chrome or Chromium (system-installed)
- Linux with xdotool (optional, for virtual desktop pinning)

## Releasing (maintainer)

Releases are cut from the project root with `release X.Y.Z` (or `release` for an interactive version prompt). The tool bumps `pyproject.toml`, commits, tags, pushes -- which triggers the PyPI publish workflow via GitHub Actions Trusted Publishing. Release notes auto-generate from commit messages between tags, so commits should read well as changelog entries.

## License

MIT
