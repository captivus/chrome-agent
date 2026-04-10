"""CLI entry point for chrome-agent.

Usage: chrome-agent [--port PORT] <command> [args...]

Single entry point with flat command dispatch. The --port flag is global
and parsed before the command name.
"""

import asyncio
import sys

from .commands import (
    cmd_back,
    cmd_check,
    cmd_click,
    cmd_clickxy,
    cmd_close,
    cmd_cookies,
    cmd_element,
    cmd_eval,
    cmd_fill,
    cmd_find,
    cmd_forward,
    cmd_hover,
    cmd_html,
    cmd_navigate,
    cmd_press,
    cmd_reload,
    cmd_screenshot,
    cmd_scroll,
    cmd_select,
    cmd_snapshot,
    cmd_tabs,
    cmd_text,
    cmd_type,
    cmd_uncheck,
    cmd_url,
    cmd_value,
    cmd_viewport,
    cmd_wait,
)
from .connection import check_cdp_port, connect, disconnect
from .errors import ChromeAgentError

# Default CDP port
DEFAULT_PORT = 9222

# Command registry: name -> (func, nargs, description)
# nargs: 0 = no args, 1 = one required arg, 2 = two required args, -1 = optional args
COMMANDS = {
    # Observe
    "url": (cmd_url, 0, "Print current URL and title"),
    "screenshot": (cmd_screenshot, -1, "Save screenshot [path]"),
    "snapshot": (cmd_snapshot, 0, "Print accessibility tree"),
    "text": (cmd_text, 0, "Print page visible text"),
    "html": (cmd_html, -1, "Print page HTML [selector]"),
    "element": (cmd_element, 1, "Inspect element <selector>"),
    "find": (cmd_find, 1, "Find elements <selector>"),
    "value": (cmd_value, 1, "Get input value <selector>"),
    "eval": (cmd_eval, 1, "Execute JavaScript <code>"),
    "cookies": (cmd_cookies, 0, "Dump cookies"),
    "tabs": (cmd_tabs, 0, "List open pages"),
    "wait": (cmd_wait, 1, "Wait for <selector|ms|load>"),
    # Navigate
    "navigate": (cmd_navigate, 1, "Go to <url>"),
    "back": (cmd_back, 0, "Browser back"),
    "forward": (cmd_forward, 0, "Browser forward"),
    "reload": (cmd_reload, 0, "Reload page"),
    # Interact
    "click": (cmd_click, 1, "Click <selector>"),
    "clickxy": (cmd_clickxy, 2, "Click at <x> <y>"),
    "fill": (cmd_fill, 2, "Fill <selector> <value>"),
    "type": (cmd_type, 2, "Type into <selector> <text>"),
    "press": (cmd_press, 1, "Press key <Enter|Escape|Tab|...>"),
    "select": (cmd_select, 2, "Select option <selector> <value>"),
    "check": (cmd_check, 1, "Check checkbox <selector>"),
    "uncheck": (cmd_uncheck, 1, "Uncheck checkbox <selector>"),
    "hover": (cmd_hover, 1, "Hover over <selector>"),
    "scroll": (cmd_scroll, 1, "Scroll <selector|up|down>"),
    # Meta
    "close": (cmd_close, 0, "Close current page"),
    "viewport": (cmd_viewport, 2, "Resize viewport <width> <height>"),
}

# Commands that don't need a CDP connection
LOCAL_COMMANDS = {"status", "launch", "help"}


def _print_help() -> None:
    """Print command reference."""
    print("chrome-agent -- CLI for AI agents to observe and interact with Chrome\n")
    print("Usage: chrome-agent [--port PORT] <command> [args...]\n")
    print("Commands:")
    print(f"  {'status':12s} Check if browser is running on CDP port")
    print(f"  {'launch':12s} Launch a browser with CDP enabled [--fingerprint PATH] [--headless] [--no-pin-desktop]")
    print(f"  {'help':12s} Print this help message")
    print()
    for name, (_, _, desc) in COMMANDS.items():
        print(f"  {name:12s} {desc}")


def _parse_global_args(argv: list[str]) -> tuple[int, list[str]]:
    """Extract --port from argv, return (port, remaining_args)."""
    port = DEFAULT_PORT
    remaining = []
    i = 0
    while i < len(argv):
        if argv[i] == "--port" and i + 1 < len(argv):
            try:
                port = int(argv[i + 1])
            except ValueError:
                print(f"ERROR: Invalid port: {argv[i + 1]}")
                sys.exit(1)
            i += 2
        else:
            remaining.append(argv[i])
            i += 1
    return port, remaining


async def _run_command(*, port: int, cmd_name: str, args: list[str]) -> None:
    """Connect to browser, run a command, disconnect."""
    func, expected_args, _ = COMMANDS[cmd_name]

    # Validate argument count
    if expected_args >= 0 and len(args) < expected_args:
        print(f"Command '{cmd_name}' requires {expected_args} argument(s)")
        sys.exit(1)

    pw, browser, page = await connect(port=port)
    try:
        # Dispatch based on argument pattern
        if cmd_name == "tabs":
            # cmd_tabs needs both page and browser
            await func(page=page, browser=browser)
        elif expected_args == 0:
            await func(page=page)
        elif expected_args == -1:
            # Optional args
            if cmd_name == "screenshot" and args:
                await func(page=page, path=args[0])
            elif cmd_name == "html" and args:
                await func(page=page, selector=args[0])
            else:
                await func(page=page)
        elif expected_args == 1:
            # Single required arg -- map to the right parameter name
            arg = args[0]
            if cmd_name in ("element", "find", "value", "click", "check",
                            "uncheck", "hover"):
                await func(page=page, selector=arg)
            elif cmd_name == "eval":
                await func(page=page, js_code=arg)
            elif cmd_name == "navigate":
                await func(page=page, url=arg)
            elif cmd_name == "wait":
                await func(page=page, target=arg)
            elif cmd_name == "press":
                await func(page=page, key=arg)
            elif cmd_name == "scroll":
                await func(page=page, target=arg)
            else:
                await func(page=page)
        elif expected_args == 2:
            # Two required args -- second arg may be multi-word (join remaining)
            arg1 = args[0]
            arg2 = " ".join(args[1:])
            if cmd_name == "clickxy":
                await func(page=page, x=float(arg1), y=float(arg2))
            elif cmd_name == "fill":
                await func(page=page, selector=arg1, value=arg2)
            elif cmd_name == "type":
                await func(page=page, selector=arg1, text=arg2)
            elif cmd_name == "select":
                await func(page=page, selector=arg1, value=arg2)
            elif cmd_name == "viewport":
                await func(page=page, width=int(arg1), height=int(arg2))
            else:
                await func(page=page)
    finally:
        await disconnect(pw=pw)


async def _run_status(*, port: int) -> None:
    """Check if a browser is running on the CDP port."""
    status = check_cdp_port(port=port)
    if status.listening:
        print(f"Browser running on port {port}")
        if status.browser_version:
            print(f"  Version: {status.browser_version}")
        if status.page_url:
            print(f"  URL:     {status.page_url}")
        if status.page_title:
            print(f"  Title:   {status.page_title}")
    else:
        print(f"No browser running on port {port}")


async def _run_launch(*, port: int, args: list[str]) -> None:
    """Launch a browser with CDP enabled."""
    # Import here to avoid circular imports and loading browser module
    # when it's not needed
    from .browser import launch_browser, load_fingerprint

    # Parse launch-specific flags
    fingerprint_path = None
    headless = False
    pin_desktop = True  # Default: pin browser to launching terminal's desktop

    i = 0
    while i < len(args):
        if args[i] == "--fingerprint" and i + 1 < len(args):
            fingerprint_path = args[i + 1]
            i += 2
        elif args[i] == "--headless":
            headless = True
            i += 1
        elif args[i] == "--no-pin-desktop":
            pin_desktop = False
            i += 1
        else:
            print(f"Unknown launch option: {args[i]}")
            sys.exit(1)

    # Load fingerprint if specified
    fingerprint = None
    if fingerprint_path:
        fingerprint = await load_fingerprint(path=fingerprint_path)

    session = await launch_browser(
        port=port,
        fingerprint=fingerprint,
        headless=headless,
        pin_to_desktop=pin_desktop,
    )

    print(f"Browser launched on CDP port {port}")
    print("Press Ctrl+C to close.")

    # Keep alive until interrupted
    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await session.browser.close()
        await session.playwright.stop()
        print("\nBrowser closed.")


def main() -> None:
    """CLI entry point."""
    port, remaining = _parse_global_args(argv=sys.argv[1:])

    if not remaining or remaining[0] in ("-h", "--help", "help"):
        _print_help()
        sys.exit(0)

    cmd_name = remaining[0]
    args = remaining[1:]

    if cmd_name == "status":
        asyncio.run(_run_status(port=port))
    elif cmd_name == "launch":
        asyncio.run(_run_launch(port=port, args=args))
    elif cmd_name in COMMANDS:
        try:
            asyncio.run(_run_command(port=port, cmd_name=cmd_name, args=args))
        except ChromeAgentError as e:
            print(f"ERROR: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: {e}")
            sys.exit(1)
    else:
        print(f"Unknown command: {cmd_name}")
        print("Run 'chrome-agent help' to see available commands")
        sys.exit(1)
