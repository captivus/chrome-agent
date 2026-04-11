# chrome-agent

A CLI tool that gives AI coding agents the ability to observe and interact with Chrome browsers.

Built as a replacement for browser MCP tools. Faster, lower token overhead, and supports something MCP tools can't do: multiple agents sharing the same browser instance.

## Why this exists

AI coding agents need to see and interact with browsers -- to test their code, debug automation, inspect page state. The standard approach (browser MCP tools) uses a persistent server with protocol negotiation and verbose response formatting. `chrome-agent` takes a different approach: each command is a standalone CLI call that connects to Chrome via the DevTools Protocol, does one thing, and disconnects. No server, no session state, no bloat.

This also enables a workflow that MCP tools can't support: one process drives the browser (your automation code) while a separate agent observes the same browser to diagnose issues and improve the code.

## Installation

```bash
uv tool install chrome-agent
playwright install chromium
```

Or add to a project:

```bash
uv add chrome-agent
uv run playwright install chromium
```

## Two ways to use it

### Drive mode -- you control the browser

Launch a browser and interact with it directly. This is the MCP replacement use case.

```bash
chrome-agent launch &
chrome-agent navigate "https://example.com"
chrome-agent text                        # Read page content
chrome-agent element "h1"                # Inspect an element
chrome-agent fill "#search" "query"      # Fill a form field
chrome-agent click "#submit"             # Click a button
chrome-agent screenshot /tmp/page.png    # Capture the screen
```

### Attach mode -- observe a running browser

Your automation code launches a browser with `--remote-debugging-port=9222`. You connect to observe what the code is doing, diagnose failures, and figure out what to change.

```bash
chrome-agent status                      # Is the browser running?
chrome-agent url                         # Where is it?
chrome-agent element "#submit-btn"       # Why can't the code click this?
chrome-agent eval "document.querySelectorAll('.error').length"
chrome-agent screenshot                  # What does it look like?
```

The feedback loop: **write code -> run it -> observe the browser -> diagnose -> modify code -> repeat.**

## Commands

```
chrome-agent [--port PORT] <command> [args...]
```

### Check browser status

```
status                Check if a browser is running on the CDP port
launch                Launch a browser with CDP enabled
                      [--fingerprint PATH] [--headless] [--no-pin-desktop]
help                  Print command reference
```

### Observe (read-only, always safe)

```
url                   Print current URL and page title
screenshot [path]     Save a screenshot (default: /tmp/cdp-screenshot.png)
snapshot              Print the ARIA accessibility tree
text                  Print visible text content
html [selector]       Print page HTML or a specific element's HTML
element <selector>    Detailed element inspection (visibility, dimensions,
                      attributes, position, disabled state)
find <selector>       Count and list all matching elements
value <selector>      Get an input element's current value
eval <code>           Execute JavaScript and print the result
cookies               List all cookies
tabs                  List all open tabs/pages
wait <target>         Wait for a selector, milliseconds, or load state
```

### Navigate

```
navigate <url>        Go to a URL
back                  Browser back
forward               Browser forward
reload                Reload the page
```

### Interact

```
click <selector>      Click an element (JS fallback for hidden elements)
fill <selector> <val> Fill a form field (clears first)
type <selector> <txt> Type text character by character
press <key>           Press a keyboard key (Enter, Escape, Tab, etc.)
select <sel> <value>  Select a dropdown option
check <selector>      Check a checkbox
uncheck <selector>    Uncheck a checkbox
hover <selector>      Hover over an element
scroll <target>       Scroll to element, or scroll up/down
clickxy <x> <y>       Click at page coordinates
close                 Close the current page
viewport <w> <h>      Resize the viewport
```

## For AI agents

The primary user of this tool is an AI coding agent, not a human. See [INSTRUCTIONS.md](INSTRUCTIONS.md) for comprehensive agent instructions covering:

- Drive mode vs attach mode mental model
- Safety rules for shared browser access
- The development feedback loop
- When to observe vs intervene
- Command recipes for common tasks
- Failure modes and recovery

Include the contents of `INSTRUCTIONS.md` in your project's `CLAUDE.md` or agent instructions file.

## Browser fingerprinting (optional)

For sites that detect automated browsers, launch with a fingerprint profile:

```bash
chrome-agent launch --fingerprint path/to/fingerprint.json
```

The fingerprint JSON overrides the browser's user agent, viewport, locale, timezone, and platform to match a real desktop browser:

```json
{
    "userAgent": "Mozilla/5.0 (X11; Linux x86_64) ...",
    "platform": "Linux x86_64",
    "vendor": "Google Inc.",
    "language": "en-US",
    "timezone": "America/Chicago",
    "viewport": {"width": 1920, "height": 1080}
}
```

Without `--fingerprint`, the browser launches with default Chromium settings.

## Requirements

- Python >= 3.11
- Playwright >= 1.50.0
- Chromium (installed via `playwright install chromium`)
- Linux with xdotool (optional, for virtual desktop pinning)

## License

MIT
