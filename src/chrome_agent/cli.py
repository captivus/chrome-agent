"""CLI entry point for chrome-agent.

Routes to operational commands (launch, status, session, help, cleanup)
and one-shot CDP method calls (Domain.method '{"params": ...}').

Usage: chrome-agent [--port PORT] <command> [args...]
"""

import asyncio
import json
import sys

DEFAULT_PORT = 9222


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
                print(f"Error: invalid port: {argv[i + 1]}", file=sys.stderr)
                sys.exit(1)
            i += 2
        else:
            remaining.append(argv[i])
            i += 1
    return port, remaining


def _print_static_usage() -> None:
    """Print static usage when no browser is available for protocol listing."""
    print("chrome-agent -- CLI for AI agents to control Chrome via CDP\n")
    print("Usage: chrome-agent [--port PORT] <command> [args...]\n")
    print("Operational commands:")
    print("  launch [--fingerprint PATH] [--headless]   Launch Chrome with CDP")
    print("  status                                     Check browser status")
    print("  session                                    Start persistent CDP session")
    print("  help [Domain | Domain.method]              Protocol discovery")
    print("  cleanup                                    Remove stale session dirs")
    print()
    print("CDP one-shot commands:")
    print("  Domain.method '{\"param\": \"value\"}'        Send a single CDP command")
    print()
    print("Examples:")
    print("  chrome-agent launch --headless")
    print("  chrome-agent status")
    print("  chrome-agent Page.navigate '{\"url\": \"https://example.com\"}'")
    print("  chrome-agent help Page")
    print("  chrome-agent help Page.navigate")


async def _run_launch(port: int, args: list[str]) -> None:
    """Launch a browser with CDP enabled."""
    from .launcher import launch_browser

    fingerprint_path = None
    headless = False
    i = 0
    while i < len(args):
        if args[i] == "--fingerprint" and i + 1 < len(args):
            fingerprint_path = args[i + 1]
            i += 2
        elif args[i] == "--headless":
            headless = True
            i += 1
        else:
            print(f"Error: unknown launch option: {args[i]}", file=sys.stderr)
            sys.exit(1)

    try:
        result = await launch_browser(
            port=port,
            fingerprint=fingerprint_path,
            headless=headless,
        )
    except (RuntimeError, TimeoutError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Browser launched on port {port}")
    print(f"  PID:     {result.pid}")
    print(f"  Version: {result.browser_version}")
    print(f"  Data:    {result.user_data_dir}")


def _run_status(port: int) -> None:
    """Check browser status."""
    from .connection import check_cdp_port

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


async def _run_session(port: int) -> None:
    """Start a persistent CDP session."""
    from .session import run_session

    exit_code = await run_session(port=port)
    sys.exit(exit_code)


def _run_help(port: int, query: str | None) -> None:
    """Protocol discovery / help."""
    from .protocol import discover_protocol

    if query is None:
        try:
            discover_protocol(port=port, query=None)
        except ConnectionError:
            _print_static_usage()
    else:
        try:
            discover_protocol(port=port, query=query)
        except ConnectionError:
            print(
                f"Error: no browser running on port {port}. "
                f"Start one with: chrome-agent launch",
                file=sys.stderr,
            )
            sys.exit(1)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)


def _run_cleanup() -> None:
    """Clean up stale session directories."""
    from .launcher import cleanup_sessions

    cleanup_sessions()
    print("Stale session directories cleaned up")


async def _run_cdp_one_shot(port: int, method: str, params_str: str | None) -> None:
    """Send a single CDP command and print the response."""
    from .cdp_client import CDPClient, get_ws_url
    from .errors import CDPError

    # Parse params
    params = None
    if params_str is not None:
        try:
            params = json.loads(params_str)
        except json.JSONDecodeError as exc:
            print(f"Error: invalid JSON parameters: {exc}", file=sys.stderr)
            sys.exit(1)
        if not isinstance(params, dict):
            print("Error: parameters must be a JSON object", file=sys.stderr)
            sys.exit(1)

    # Connect and send
    try:
        ws_url = get_ws_url(port=port, target_type="page")
    except (ConnectionError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        async with CDPClient(ws_url=ws_url) as cdp:
            result = await cdp.send(method=method, params=params)
            print(json.dumps(result, indent=2))
    except CDPError as exc:
        print(f"CDP error {exc.code}: {exc.message}", file=sys.stderr)
        sys.exit(1)
    except ConnectionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """CLI entry point."""
    port, remaining = _parse_global_args(argv=sys.argv[1:])

    if not remaining or remaining[0] in ("-h", "--help"):
        _print_static_usage()
        sys.exit(0)

    command = remaining[0]
    args = remaining[1:]

    if command == "launch":
        asyncio.run(_run_launch(port=port, args=args))
    elif command == "status":
        _run_status(port=port)
    elif command == "session":
        asyncio.run(_run_session(port=port))
    elif command == "help":
        query = args[0] if args else None
        _run_help(port=port, query=query)
    elif command == "cleanup":
        _run_cleanup()
    elif "." in command:
        params_str = args[0] if args else None
        asyncio.run(_run_cdp_one_shot(port=port, method=command, params_str=params_str))
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print("Run 'chrome-agent help' for usage", file=sys.stderr)
        sys.exit(1)
