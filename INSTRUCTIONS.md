# chrome-agent: Agent Instructions

These instructions teach an AI coding agent how to use `chrome-agent` to observe and interact with Chrome browsers. Include this in your project's `CLAUDE.md` or agent instructions file.

## Mental Model

`chrome-agent` is a CLI that connects to a Chrome browser via the Chrome DevTools Protocol (CDP). Each invocation connects, does one thing, and disconnects. No persistent state between calls.

There are two modes of operation:

### Drive mode

You launch the browser and are the sole controller. Use this when you need to browse, test, or inspect a website directly.

```bash
chrome-agent launch                     # Start a browser
chrome-agent navigate "https://..."     # Go somewhere
chrome-agent text                       # Read the page
chrome-agent click "#submit"            # Interact
```

You own the full lifecycle. All commands are safe to use freely.

### Attach mode

Something else is driving the browser -- typically automation code you wrote and are running. You connect to observe what your code is doing, diagnose why it's failing, and figure out what to change.

The feedback loop: **write code -> run it -> observe the browser -> diagnose -> modify code -> repeat.**

```bash
# Your automation is running...
chrome-agent url                        # Where is the browser now?
chrome-agent screenshot                 # What does the page look like?
chrome-agent element "#submit"          # Why can't the code click this?
# Now you know the button is hidden -- go fix the code
```

**Read freely, write carefully.** Observation commands (url, text, element, find, eval, screenshot, snapshot) are always safe. Interaction commands (click, fill, navigate) can conflict with the running automation -- only use them to unstick a stuck browser or to test something manually, not while the automation is actively working.

### When to intervene vs observe

- The automation hit a button it can't click? **Observe** with `element` to understand why (hidden? disabled? wrong selector?), then go fix the code.
- The automation is completely stuck and you need to manually advance? **Intervene** with `click` or `navigate`, then go fix the code so it handles this case.
- The automation is actively running and progressing normally? **Don't interact.** Use read-only commands only.

## Before You Start

### Check if a browser is already running

```bash
chrome-agent status
```

This tells you whether anything is listening on the CDP port, and if so, what page it's on. Always check before launching a new browser -- only one process can bind port 9222.

### Launch a browser (drive mode)

```bash
chrome-agent launch
```

This opens a headed Chromium browser with CDP on port 9222. The browser window is automatically placed on the terminal's virtual desktop (Linux with xdotool) so it doesn't pop up on the user's active workspace.

The launch process stays alive until you kill it (Ctrl+C or `kill`). When it exits, the browser closes.

### Connect to an existing browser (attach mode)

If automation code launched a browser with `--remote-debugging-port=9222` in its Chromium args, you can use all `chrome-agent` commands against it without launching anything.

## Command Reference

Commands are listed by how frequently they're used in practice, not alphabetically.

### Most used -- quick status and inspection

| Command | Description |
|---------|-------------|
| `chrome-agent url` | Print current URL and page title |
| `chrome-agent eval "<js>"` | Execute JavaScript and print result |
| `chrome-agent text` | Print visible text content |
| `chrome-agent element "<selector>"` | Detailed element info (visibility, dimensions, attributes) |
| `chrome-agent find "<selector>"` | Count and list all matching elements |
| `chrome-agent screenshot [path]` | Save screenshot (default: /tmp/cdp-screenshot.png) |
| `chrome-agent status` | Check if a browser is running on the CDP port |

### Navigation

| Command | Description |
|---------|-------------|
| `chrome-agent navigate "<url>"` | Go to a URL |
| `chrome-agent back` | Browser back |
| `chrome-agent forward` | Browser forward |
| `chrome-agent reload` | Reload current page |

### Interaction

| Command | Description |
|---------|-------------|
| `chrome-agent click "<selector>"` | Click an element (JS fallback for hidden elements) |
| `chrome-agent fill "<selector>" "<value>"` | Fill a form field |
| `chrome-agent type "<selector>" "<text>"` | Type text character by character |
| `chrome-agent press "<key>"` | Press a key (Enter, Escape, Tab, etc.) |
| `chrome-agent select "<selector>" "<value>"` | Select a dropdown option |
| `chrome-agent check "<selector>"` | Check a checkbox |
| `chrome-agent uncheck "<selector>"` | Uncheck a checkbox |
| `chrome-agent hover "<selector>"` | Hover over an element |
| `chrome-agent scroll "<selector\|up\|down>"` | Scroll to element or direction |
| `chrome-agent clickxy <x> <y>` | Click at page coordinates |

### Page inspection

| Command | Description |
|---------|-------------|
| `chrome-agent snapshot` | Print ARIA accessibility tree |
| `chrome-agent html [selector]` | Print page HTML or element's outerHTML |
| `chrome-agent value "<selector>"` | Get input element's current value |
| `chrome-agent cookies` | List all cookies |
| `chrome-agent tabs` | List all open tabs |
| `chrome-agent wait "<selector\|ms\|load>"` | Wait for selector, milliseconds, or load state |

### Browser management

| Command | Description |
|---------|-------------|
| `chrome-agent launch` | Launch a browser with CDP |
| `chrome-agent close` | Close current page |
| `chrome-agent viewport <width> <height>` | Resize viewport |

### Global options

`--port PORT` can be used before any command to connect to a different CDP port (default: 9222).

```bash
chrome-agent --port 9223 url
```

## Recipes

### Login to a site

```bash
chrome-agent navigate "https://example.com/login"
chrome-agent fill "#username" "myuser"
chrome-agent fill "#password" "mypass"
chrome-agent click "#login-button"
chrome-agent url    # Verify we landed on the right page
```

### Find the right selector for an element

```bash
chrome-agent snapshot                   # ARIA tree -- find the element's role and name
chrome-agent find "button"              # How many buttons? Which one do you need?
chrome-agent element "#submit"          # Detailed info about a specific element
chrome-agent eval "document.querySelector('#submit')?.textContent"
```

### Debug why a click isn't working

```bash
chrome-agent element "#the-button"      # Check: visible? in viewport? disabled?
chrome-agent screenshot                 # Visual state -- is something overlaying it?
chrome-agent eval "document.querySelector('#the-button')?.getBoundingClientRect()"
```

If the element exists but `Visible: False` or `Display: none`, it's hidden. If `In viewport: False`, you may need to scroll first. If `Disabled: True`, the button can't be clicked.

### Check page state after automation runs

```bash
chrome-agent url                        # Where did the automation end up?
chrome-agent text                       # What's on the page?
chrome-agent find ".error"              # Any error messages?
chrome-agent screenshot                 # Visual snapshot
```

## Failure Modes and Recovery

### "No browser running on port 9222"

Nothing is listening. Either launch a browser (`chrome-agent launch`) or make sure your automation started with `--remote-debugging-port=9222`.

### "Browser is running but has no open pages"

The browser process exists but all tabs are closed. Navigate to open a page, or restart the browser.

### Stale browser processes

If a previous browser died without cleaning up, port 9222 may be held by a zombie process. Check with `chrome-agent status`. If it reports a browser but commands fail, kill stale processes:

```bash
pkill -f "chrome-agent launch"
pkill -f "chromium.*9222"
chrome-agent status    # Should report "No browser running"
```

### "Target page, context or browser has been closed"

The browser navigated away or closed while you were running a command. Just retry -- the next invocation gets a fresh connection.

## Integration with Long-Running Automations

When your automation produces a log file, you can use Claude Code's Monitor tool to watch for events while using `chrome-agent` for on-demand inspection:

1. Start your automation in the background, logging to a file
2. Set up a Monitor to tail the log with a grep filter for important events (errors, milestones)
3. When a Monitor event indicates something interesting, inspect with `chrome-agent`
4. If stuck, intervene with `chrome-agent`, then fix the automation code

Key principle for Monitor filters: **start narrow** (errors and completion milestones only). Broaden only if you're not getting enough signal. Overly broad filters produce so much output that Monitor auto-stops.
