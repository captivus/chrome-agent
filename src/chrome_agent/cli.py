"""CLI entry point for chrome-agent.

Routes to operational commands (launch, status, attach, help, cleanup)
and one-shot CDP method calls (<instance> Domain.method '{"params": ...}').

Iteration 2: instance name routing, target specifiers, attach mode.

Usage: chrome-agent <command> [args...]
"""

import asyncio
import json
import sys


# Operational commands -- checked first during routing
OPERATIONAL_COMMANDS = {"launch", "status", "attach", "help", "cleanup", "stop"}


def _extract_flags(argv: list[str]) -> tuple[list[str], str | None, str | None]:
    """Extract --target and --url flags from argv before routing.

    Returns (remaining_args, target_spec, url_spec).
    Flags can appear anywhere in argv.
    """
    remaining = []
    target_spec = None
    url_spec = None
    i = 0
    while i < len(argv):
        if argv[i] == "--target" and i + 1 < len(argv):
            target_spec = argv[i + 1]
            i += 2
        elif argv[i] == "--url" and i + 1 < len(argv):
            url_spec = argv[i + 1]
            i += 2
        else:
            remaining.append(argv[i])
            i += 1

    if target_spec and url_spec:
        print("Error: cannot specify both --target and --url", file=sys.stderr)
        sys.exit(1)

    return remaining, target_spec, url_spec


def _print_static_usage() -> None:
    """Print static usage when no browser is available for protocol listing."""
    print("chrome-agent -- CLI for AI agents to control Chrome via CDP\n")
    print("Usage: chrome-agent <command> [args...]\n")
    print("Operational commands:")
    print("  launch [--port PORT] [--fingerprint PATH] [--headless]   Launch Chrome with CDP")
    print("  status [<instance>]                                      List instances and targets")
    print("  attach <instance> [+Event ...] [--target SPEC] [--url SUB]  Attach for events")
    print("  help [<instance>] [Domain | Domain.method]               Protocol discovery")
    print("  stop <instance>                                            Stop a browser gracefully")
    print("  cleanup                                                   Remove stale instances")
    print()
    print("CDP one-shot commands:")
    print("  <instance> Domain.method '{\"param\": \"value\"}'         Send a single CDP command")
    print("  Domain.method '{\"param\": \"value\"}'                    (auto-selects instance)")
    print()
    print("Examples:")
    print("  chrome-agent launch --headless")
    print("  chrome-agent status")
    print("  chrome-agent attach mysite-01 +Page.loadEventFired")
    print("  chrome-agent mysite-01 Page.navigate '{\"url\": \"https://example.com\"}'")
    print("  chrome-agent help Page.navigate")


async def _run_launch(args: list[str]) -> None:
    """Launch a browser with CDP enabled."""
    from .launcher import launch_browser

    fingerprint_path = None
    headless = False
    port_override = None
    i = 0
    while i < len(args):
        if args[i] == "--fingerprint" and i + 1 < len(args):
            fingerprint_path = args[i + 1]
            i += 2
        elif args[i] == "--headless":
            headless = True
            i += 1
        elif args[i] == "--port" and i + 1 < len(args):
            try:
                port_override = int(args[i + 1])
            except ValueError:
                print(f"Error: invalid port: {args[i + 1]}", file=sys.stderr)
                sys.exit(1)
            i += 2
        else:
            print(f"Error: unknown launch option: {args[i]}", file=sys.stderr)
            sys.exit(1)

    try:
        result = await launch_browser(
            port_override=port_override,
            fingerprint=fingerprint_path,
            headless=headless,
        )
    except (RuntimeError, TimeoutError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if sys.stdout.isatty():
        print(f"Browser launched: {result.name}")
        print(f"  Port:    {result.port}")
        print(f"  PID:     {result.pid}")
        print(f"  Version: {result.browser_version}")
    else:
        print(json.dumps({
            "name": result.name,
            "port": result.port,
            "pid": result.pid,
            "browser_version": result.browser_version,
        }))


def _run_status(args: list[str]) -> None:
    """List running browser instances and their targets."""
    from .instance_status import (
        format_status_json,
        format_status_text,
        get_instance_status,
    )
    from .registry import InstanceNotFoundError

    instance_name = args[0] if args else None

    try:
        statuses = get_instance_status(instance_name=instance_name)
    except InstanceNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if not statuses and instance_name is None:
        print("No instances registered. Launch one with: chrome-agent launch")
        return

    if sys.stdout.isatty():
        print(format_status_text(statuses))
    else:
        print(format_status_json(statuses))


async def _run_attach(args: list[str], target_spec: str | None, url_spec: str | None) -> None:
    """Attach to a browser instance for event observation."""
    from .attach import run_attach

    if not args:
        print("Error: attach requires an instance name", file=sys.stderr)
        print("Usage: chrome-agent attach <instance> [+Event ...]", file=sys.stderr)
        sys.exit(1)

    instance_name = args[0]
    subscriptions = [arg[1:] for arg in args[1:] if arg.startswith("+")]

    target_by = None
    spec = None
    if target_spec is not None:
        spec = target_spec
        # Determine if it's an index (numeric) or ID prefix
        target_by = "index" if target_spec.isdigit() else "id"
    elif url_spec is not None:
        spec = url_spec
        target_by = "url"

    try:
        await run_attach(
            instance_name=instance_name,
            subscriptions=subscriptions,
            target_spec=spec,
            target_by=target_by,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def _run_help(args: list[str]) -> None:
    """Protocol discovery / help.

    Disambiguation: if the first arg exists in the registry, treat it
    as an instance name. Otherwise treat it as a domain query.
    """
    from .protocol import discover_protocol

    if not args:
        try:
            discover_protocol()
        except ConnectionError:
            _print_static_usage()
        return

    # Try to disambiguate: is args[0] an instance name or a domain query?
    instance_name = None
    query = None

    try:
        from .registry import lookup
        lookup(instance_name=args[0])
        # It's a registered instance name
        instance_name = args[0]
        query = args[1] if len(args) > 1 else None
    except Exception:
        # Not in registry -- treat as domain query
        query = args[0]

    try:
        discover_protocol(instance_name=instance_name, query=query)
    except ConnectionError:
        if instance_name:
            print(f"Error: browser for instance '{instance_name}' is not responding", file=sys.stderr)
        else:
            _print_static_usage()
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def _run_stop(args: list[str], target_spec: str | None, url_spec: str | None) -> None:
    """Stop a browser instance or close a specific tab."""
    from .registry import InstanceNotFoundError, stop

    if not args:
        print("Error: stop requires an instance name", file=sys.stderr)
        print("Usage: chrome-agent stop <instance> [--target SPEC | --url SUBSTRING]", file=sys.stderr)
        sys.exit(1)

    instance_name = args[0]

    # If a target specifier was provided, resolve it to a target ID
    resolved_target_id = None
    if target_spec is not None or url_spec is not None:
        from .attach import resolve_target
        from .cdp_client import CDPClient, get_ws_url
        from .registry import lookup

        info = lookup(instance_name=instance_name)

        async def _get_targets():
            browser_ws = get_ws_url(port=info.port, target_type="browser")
            async with CDPClient(ws_url=browser_ws) as cdp:
                result = await cdp.send(method="Target.getTargets")
                return sorted(
                    (t for t in result.get("targetInfos", []) if t.get("type") == "page"),
                    key=lambda t: t.get("targetId", ""),
                )

        import asyncio
        page_targets = asyncio.run(_get_targets())

        target_by = None
        spec = None
        if target_spec is not None:
            spec = target_spec
            target_by = "index" if target_spec.isdigit() else "id"
        elif url_spec is not None:
            spec = url_spec
            target_by = "url"

        try:
            resolved_target_id = resolve_target(
                page_targets=page_targets,
                target_spec=spec,
                target_by=target_by,
            )
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)

    try:
        result = stop(instance_name=instance_name, target_id=resolved_target_id)
        print(result)
    except InstanceNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def _run_cleanup() -> None:
    """Clean up stale instances and session directories."""
    from .launcher import cleanup_sessions

    removed = cleanup_sessions()
    if removed:
        print(f"Cleaned up {len(removed)} stale instance(s): {', '.join(removed)}")
    else:
        print("No stale instances found")


async def _run_cdp_one_shot(
    instance_name: str | None,
    method: str,
    params_str: str | None,
    target_spec: str | None,
    url_spec: str | None,
) -> None:
    """Send a single CDP command via browser-level WS + Target.attachToTarget."""
    from .cdp_client import CDPClient, get_ws_url
    from .errors import CDPError

    # Resolve instance
    if instance_name is not None:
        from .registry import lookup
        info = lookup(instance_name=instance_name)
        port = info.port
    else:
        # Default instance resolution: auto-select single live instance
        from .registry import enumerate_instances
        instances = enumerate_instances()
        live = [i for i in instances if i.alive]
        if len(live) == 0:
            print("Error: no instances registered. Launch one with: chrome-agent launch", file=sys.stderr)
            sys.exit(1)
        elif len(live) > 1:
            names = ", ".join(i.name for i in live)
            print(f"Error: multiple instances running. Specify one: {names}", file=sys.stderr)
            sys.exit(1)
        port = live[0].port

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

    # Connect to browser-level WebSocket
    try:
        browser_ws_url = get_ws_url(port=port, target_type="browser")
    except (ConnectionError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        async with CDPClient(ws_url=browser_ws_url) as cdp:
            # Resolve target
            targets_result = await cdp.send(method="Target.getTargets")
            page_targets = sorted(
                (t for t in targets_result.get("targetInfos", [])
                 if t.get("type") == "page"),
                key=lambda t: t.get("targetId", ""),
            )

            if not page_targets:
                print("Error: no page targets in browser", file=sys.stderr)
                sys.exit(1)

            from .attach import resolve_target
            target_by = None
            spec = None
            if target_spec is not None:
                spec = target_spec
                target_by = "index" if target_spec.isdigit() else "id"
            elif url_spec is not None:
                spec = url_spec
                target_by = "url"

            target_id = resolve_target(
                page_targets=page_targets,
                target_spec=spec,
                target_by=target_by,
            )

            # Create isolated session
            session_result = await cdp.send(
                method="Target.attachToTarget",
                params={"targetId": target_id, "flatten": True},
            )
            session_id = session_result["sessionId"]

            try:
                result = await cdp.send(
                    method=method,
                    params=params,
                    session_id=session_id,
                )
                print(json.dumps(result, indent=2))
            finally:
                try:
                    await cdp.send(
                        method="Target.detachFromTarget",
                        params={"sessionId": session_id},
                    )
                except Exception:
                    pass

    except CDPError as exc:
        print(f"CDP error {exc.code}: {exc.message}", file=sys.stderr)
        sys.exit(1)
    except ConnectionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """CLI entry point."""
    # Phase 0: Extract --target and --url flags before routing
    args, target_spec, url_spec = _extract_flags(sys.argv[1:])

    if not args or args[0] in ("-h", "--help"):
        _print_static_usage()
        sys.exit(0)

    command = args[0]
    rest = args[1:]

    # Route operational commands first
    if command in OPERATIONAL_COMMANDS:
        if command == "launch":
            asyncio.run(_run_launch(args=rest))
        elif command == "status":
            _run_status(args=rest)
        elif command == "attach":
            asyncio.run(_run_attach(args=rest, target_spec=target_spec, url_spec=url_spec))
        elif command == "help":
            _run_help(args=rest)
        elif command == "stop":
            _run_stop(args=rest, target_spec=target_spec, url_spec=url_spec)
        elif command == "cleanup":
            _run_cleanup()
        return

    # Check if command contains a dot -- bare CDP method (auto-select instance)
    if "." in command:
        method = command
        params_str = rest[0] if rest else None
        asyncio.run(_run_cdp_one_shot(
            instance_name=None,
            method=method,
            params_str=params_str,
            target_spec=target_spec,
            url_spec=url_spec,
        ))
        return

    # Otherwise: first arg is instance name, second should be a CDP method
    instance_name = command
    if not rest or "." not in rest[0]:
        print(f"Error: expected Domain.method after instance name '{instance_name}'", file=sys.stderr)
        print("Usage: chrome-agent <instance> Domain.method '{\"params\"}'", file=sys.stderr)
        sys.exit(1)

    method = rest[0]
    params_str = rest[1] if len(rest) > 1 else None
    asyncio.run(_run_cdp_one_shot(
        instance_name=instance_name,
        method=method,
        params_str=params_str,
        target_spec=target_spec,
        url_spec=url_spec,
    ))
