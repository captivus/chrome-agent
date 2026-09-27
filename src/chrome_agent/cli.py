"""CLI entry point for chrome-agent.

Routes to operational commands (launch, status, attach, help, cleanup)
and one-shot CDP method calls (<instance> Domain.method '{"params": ...}').

Iteration 2: instance name routing, target specifiers, attach mode.

Usage: chrome-agent <command> [args...]
"""

import asyncio
import json
import os
import sys


# Operational commands -- checked first during routing
OPERATIONAL_COMMANDS = {
    "launch", "status", "attach", "help", "cleanup", "stop", "guide", "completions",
    "save", "restore", "snapshots",
}


# Target-selection flags and the resolution each one forces. Bare --target maps
# to None: "decide by shape", handled in one place by attach.resolve_target
# rather than guessed separately at each call site.
TARGET_FLAGS = {
    "--target": None,
    "--target-id": "id",
    "--target-index": "index",
    "--url": "url",
}


def _extract_flags(argv: list[str]) -> tuple[list[str], str | None, str | None]:
    """Extract the target-selection flags from argv before routing.

    Returns (remaining_args, target_spec, target_by), where target_by is "id",
    "index" or "url" for an explicit flag and None for bare --target (resolved
    by shape when the targets are known). Flags can appear anywhere in argv.
    """
    remaining = []
    seen: list[tuple[str, str]] = []
    i = 0
    while i < len(argv):
        if argv[i] in TARGET_FLAGS and i + 1 < len(argv):
            seen.append((argv[i], argv[i + 1]))
            i += 2
        else:
            remaining.append(argv[i])
            i += 1

    if len(seen) > 1:
        names = ", ".join(flag for flag, _ in seen)
        print(f"Error: specify only one target selector (got {names})", file=sys.stderr)
        sys.exit(1)

    if not seen:
        return remaining, None, None

    flag, spec = seen[0]
    return remaining, spec, TARGET_FLAGS[flag]


def _print_guide(args: list[str]) -> None:
    """Print the bundled agent guide (AGENTS.md), or just its path.

    The guide ships inside the package, so it is available from any install
    without a checkout. `--path` prints the file location instead of its
    contents, which is usually what an agent wants: reading the file with its
    own tools beats paging 20+ KB through stdout.
    """
    from importlib.resources import files

    guide = files("chrome_agent").joinpath("AGENTS.md")
    if "--path" in args:
        print(guide)
    else:
        print(guide.read_text(encoding="utf-8"), end="")


def _run_completions(args: list[str]) -> None:
    """Print shell completions, or the live data the completion draws on.

    `zsh` prints the completion function (ship it to a directory on $fpath as
    _chrome-agent, or source it after compinit). `instances` prints one
    `name:description` line per registered instance -- the format zsh's
    _describe consumes -- and is what the completion calls on every Tab, so the
    names offered are the ones actually registered rather than a snapshot.
    """
    if not args:
        print("Error: completions requires a shell or data name", file=sys.stderr)
        print("Usage: chrome-agent completions <zsh | instances>", file=sys.stderr)
        sys.exit(1)

    what = args[0]

    if what == "zsh":
        from importlib.resources import files

        script = files("chrome_agent").joinpath("completions.zsh")
        print(script.read_text(encoding="utf-8"), end="")
        return

    if what in ("methods", "events"):
        _print_protocol_completions(
            kind="commands" if what == "methods" else "events",
            instance_name=args[1] if len(args) > 1 else None,
        )
        return

    if what == "instances":
        from .instance_status import get_instance_status

        for status in get_instance_status():
            if not status.alive:
                description = f"port {status.port} -- DEAD"
            else:
                count = len(status.targets)
                description = f"port {status.port} -- {count} tab{'' if count == 1 else 's'}"
            print(f"{status.name}:{description}")
        return

    if what == "snapshots":
        from .snapshot import list_versions

        latest = {}
        for version in list_versions():
            latest[version.name] = version
        for name, version in latest.items():
            info = version.info
            print(f"{name}:{info.get('tabs', 0)} tabs, port {info.get('port')}, saved {info.get('saved_at', '')[:16].replace('T', ' ')} UTC")
        return

    print(f"Error: unknown completions target: {what}", file=sys.stderr)
    print(
        "Usage: chrome-agent completions <zsh | instances | snapshots | methods | events> [<instance>]",
        file=sys.stderr,
    )
    sys.exit(1)


def _print_protocol_completions(*, kind: str, instance_name: str | None) -> None:
    """Print `Domain.member:description` lines for the live protocol.

    Read from the running browser rather than a bundled list, so the candidates
    match the protocol *this* Chrome implements -- including surface newer than
    any snapshot shipped with chrome-agent. Any live instance answers, since the
    schema is identical across instances of the same browser.

    The result is cached on disk, keyed by the browser version the registry
    already records -- so a hit needs no browser contact at all, and a Chrome
    upgrade invalidates it by changing the key. The fetch itself is only ~7 ms
    and would not justify a cache for Tab alone; what does is that zsh runs
    completion on every *keystroke* when autosuggestions use the completion
    strategy, so an uncached lookup means a process spawn and an HTTP round
    trip per character typed.

    Prints nothing and exits 0 when no browser is reachable -- at Tab time the
    right answer is no candidates, not an error in the middle of a command line.
    """
    from .protocol import fetch_protocol_schema

    resolved = _resolve_instance_for_protocol(instance_name=instance_name)
    if resolved is None:
        return
    port, browser_version = resolved

    cache = _protocol_cache_path(browser_version=browser_version, kind=kind)
    if cache is not None and cache.exists():
        try:
            sys.stdout.write(cache.read_text(encoding="utf-8"))
            return
        except OSError:
            pass  # unreadable cache is not a reason to fail; re-fetch below

    try:
        schema = fetch_protocol_schema(port=port)
    except (ConnectionError, RuntimeError, OSError):
        return

    lines = []
    for domain in schema.get("domains", []):
        name = domain.get("domain", "")
        for member in domain.get(kind, []):
            # _describe splits each line on its FIRST colon, so colons inside a
            # description are harmless; newlines are not -- a CDP description
            # can run to several lines, and each would read as its own bogus
            # candidate. Join rather than truncate to the first line: CDP wraps
            # its prose at arbitrary points, so a first-line cut ends mid
            # sentence and reads as a bug in the menu.
            description = " ".join((member.get("description") or "").split())
            lines.append(f"{name}.{member.get('name', '')}:{description}")

    text = "".join(f"{line}\n" for line in lines)
    sys.stdout.write(text)

    if cache is not None:
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            # Write via a temp file in the same directory and rename, so a
            # completion racing this one never reads a half-written cache.
            temp = cache.with_name(f"{cache.name}.{os.getpid()}.tmp")
            temp.write_text(text, encoding="utf-8")
            os.replace(temp, cache)
        except OSError:
            pass  # a cache we cannot write is not an error worth surfacing


def _resolve_instance_for_protocol(
    *, instance_name: str | None
) -> tuple[int, str] | None:
    """Resolve to (port, browser_version), or None when nothing can answer.

    Any live instance will do when none is named: the protocol schema is a
    property of the browser build, not of the instance.
    """
    from .registry import enumerate_instances, lookup

    try:
        if instance_name is not None:
            info = lookup(instance_name=instance_name)
            return (info.port, info.browser_version) if info.alive else None
        for info in enumerate_instances():
            if info.alive:
                return info.port, info.browser_version
    except Exception:
        return None
    return None


def _protocol_cache_path(*, browser_version: str, kind: str):
    """Where the protocol completions for this browser build are cached.

    None when the registry has no version to key on -- better to re-fetch every
    time than to serve one browser's protocol under another's name.
    """
    import re
    from pathlib import Path

    if not browser_version:
        return None
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(
        os.path.expanduser("~"), ".cache"
    )
    safe = re.sub(r"[^A-Za-z0-9._-]", "-", browser_version)
    return Path(base) / "chrome-agent" / f"protocol-{safe}-{kind}.txt"


def _print_static_usage() -> None:
    """Print static usage when no browser is available for protocol listing."""
    print("chrome-agent -- CLI for AI agents to control Chrome via CDP\n")
    print("Usage: chrome-agent <command> [args...]\n")
    print("Operational commands:")
    print("  launch [--port PORT] [--fingerprint PATH] [--headless] [--no-window-border] [-- CHROME_ARGS]  Launch Chrome")
    print("  status [<instance>]                                    List instances and targets")
    print("  attach <instance> [+Event ...] [TARGET]                Attach for events")
    print("  help [<instance>] [Domain | Domain.method]             Protocol discovery")
    print("  stop <instance> [TARGET]                               Stop a browser, or close one tab")
    print("  cleanup                                                Remove stale instances")
    print("  save <instance>... | --all [--stop] [--as NAME]        Snapshot sessions (profile, tabs, cookies)")
    print("  restore [<name[@stamp]>...] [--all] [--any-port]       Bring saved sessions back")
    print("  snapshots [list|show|rm|export-key|import-key]         Manage saved snapshots")
    print("  guide [--path]                                         Print this tool's agent guide")
    print("  completions <zsh|instances|methods|events> [<instance>]  Shell completion and its data")
    print()
    print("  --version, -V                                          Show version and exit")
    print()
    print("Instance patterns (quote them -- the shell expands an unquoted glob first):")
    print("  '<glob>'               Any instance argument may be a glob (*, ?, [abc])")
    print("                         status and stop act on every match;")
    print("                         attach, help and one-shots require it to match exactly one")
    print()
    print("Target selectors (TARGET -- pick one; usable on attach, stop and one-shots):")
    print("  --target SPEC          Tab index if SPEC is fewer than 8 digits, else a target-id prefix")
    print("  --target-id ID         Always a target-id prefix (the `id` or `full_id` from status)")
    print("  --target-index N       Always the 1-based index from status")
    print("  --url SUBSTRING        The tab whose URL contains SUBSTRING")
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
    print("  chrome-agent stop 'mysite-*'")


async def _run_launch(args: list[str]) -> None:
    """Launch a browser with CDP enabled."""
    from .launcher import BrowserNotFoundError, launch_browser

    fingerprint_path = None
    headless = False
    port_override = None
    window_border = True
    extra_args = []
    i = 0
    while i < len(args):
        if args[i] == "--":
            # Everything after -- is passed through to Chrome
            extra_args = args[i + 1:]
            break
        elif args[i] == "--fingerprint" and i + 1 < len(args):
            fingerprint_path = args[i + 1]
            i += 2
        elif args[i] == "--headless":
            headless = True
            i += 1
        elif args[i] == "--no-window-border":
            window_border = False
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
            extra_args=extra_args,
            window_border=window_border,
        )
    except (BrowserNotFoundError, RuntimeError, TimeoutError) as exc:
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


async def _run_attach(args: list[str], target_spec: str | None, target_by: str | None) -> None:
    """Attach to a browser instance for event observation."""
    from .attach import run_attach

    if not args:
        print("Error: attach requires an instance name", file=sys.stderr)
        print("Usage: chrome-agent attach <instance> [+Event ...]", file=sys.stderr)
        sys.exit(1)

    from .registry import (
        AmbiguousInstanceError,
        InstanceNotFoundError,
        resolve_instance_name,
    )

    try:
        instance_name = resolve_instance_name(name_or_pattern=args[0])
    except (AmbiguousInstanceError, InstanceNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    subscriptions = [arg[1:] for arg in args[1:] if arg.startswith("+")]

    try:
        await run_attach(
            instance_name=instance_name,
            subscriptions=subscriptions,
            target_spec=target_spec,
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

    from .registry import AmbiguousInstanceError, resolve_instance_name

    try:
        # Resolves a literal name or a single-match glob; a pattern matching
        # several instances is an error rather than a silent pick, even though
        # the protocol schema is identical across them.
        instance_name = resolve_instance_name(name_or_pattern=args[0])
        query = args[1] if len(args) > 1 else None
    except AmbiguousInstanceError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception:
        # Not in registry -- treat as domain query
        query = args[0]

    try:
        discover_protocol(instance_name=instance_name, query=query)
    except ConnectionError:
        # A query was given (a Domain/method to look up), but no browser could
        # answer it. Emit a clear, actionable error instead of silently falling
        # through to the generic usage banner.
        if instance_name:
            print(f"Error: browser for instance '{instance_name}' is not responding", file=sys.stderr)
        else:
            print(
                "Error: no running browser to query for protocol help. "
                "Start one with: chrome-agent launch",
                file=sys.stderr,
            )
        sys.exit(1)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def _run_stop(args: list[str], target_spec: str | None, target_by: str | None) -> None:
    """Stop one or more browser instances, or close a specific tab.

    The instance argument may be a glob pattern, in which case every matching
    instance is stopped -- the matched names are printed first, so a broad
    pattern leaves a record of what it swept up. A target selector closes one
    tab, which is only meaningful against a single browser, so it is refused
    when the pattern matches several.
    """
    from .registry import InstanceNotFoundError, resolve_instance_names, stop

    if not args:
        print("Error: stop requires an instance name", file=sys.stderr)
        print("Usage: chrome-agent stop <instance> [--target SPEC | --target-id ID | --target-index N | --url SUBSTRING]", file=sys.stderr)
        sys.exit(1)

    try:
        matched = resolve_instance_names(name_or_pattern=args[0])
    except InstanceNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if len(matched) > 1:
        if target_spec is not None:
            names = ", ".join(matched)
            print(
                f"Error: a target selector closes one tab, but pattern "
                f"'{args[0]}' matches {len(matched)} instances: {names}",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"Pattern '{args[0]}' matched {len(matched)} instances:")
        print(f"  {', '.join(matched)}")
        failures = 0
        for name in matched:
            try:
                print(stop(instance_name=name))
            except Exception as exc:
                print(f"Error stopping {name}: {exc}", file=sys.stderr)
                failures += 1
        if failures:
            sys.exit(1)
        return

    instance_name = matched[0]

    # If a target specifier was provided, resolve it to a target ID
    resolved_target_id = None
    if target_spec is not None:
        from .attach import resolve_target
        from .cdp_client import CDPClient, get_ws_url
        from .registry import lookup

        try:
            info = lookup(instance_name=instance_name)
        except InstanceNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)

        async def _get_targets():
            browser_ws = get_ws_url(port=info.port, target_type="browser")
            async with CDPClient(ws_url=browser_ws) as cdp:
                result = await cdp.send(method="Target.getTargets")
                return sorted(
                    (t for t in result.get("targetInfos", []) if t.get("type") == "page"),
                    key=lambda t: t.get("targetId", ""),
                )

        import asyncio
        try:
            page_targets = asyncio.run(_get_targets())
        except (ConnectionError, RuntimeError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)

        try:
            resolved_target_id = resolve_target(
                page_targets=page_targets,
                target_spec=target_spec,
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


# ---------------------------------------------------------------------------
# Session snapshots: save / restore / snapshots
# ---------------------------------------------------------------------------

def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def _human_age(version) -> str:
    from .snapshot import version_age

    seconds = int(version_age(version).total_seconds())
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86400}d ago"


def _local_time(iso: str) -> str:
    from datetime import datetime

    return datetime.fromisoformat(iso).astimezone().strftime("%Y-%m-%d %H:%M")


def _print_tabs(state: dict, indent: str = "  ") -> None:
    windows = state.get("windows", [])
    for w, window in enumerate(windows):
        if len(windows) > 1:
            print(f"{indent}window {w + 1}:")
        for tab in window["tabs"]:
            mark = "*" if tab.get("active") else " "
            title = tab.get("title") or ""
            print(f"{indent}{mark} {title[:50]:50}  {tab['url'][:90]}")


def _confirm(prompt: str) -> bool:
    try:
        return input(f"{prompt} [y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


def _run_save(args: list[str]) -> None:
    """Save running instances as snapshots."""
    from .registry import InstanceNotFoundError, enumerate_instances, resolve_instance_names
    from .snapcrypto import SnapshotKeyError
    from .snapshot import (
        SnapshotError,
        latest_version,
        plan_save,
        read_state,
        save_instance,
        write_batch,
    )

    save_all = stop = False
    decision = None
    snapshot_name = None
    patterns = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--all":
            save_all = True
        elif arg == "--stop":
            stop = True
        elif arg in ("--overwrite", "--keep-both"):
            if decision and decision != arg:
                print("Error: --overwrite and --keep-both are mutually exclusive", file=sys.stderr)
                sys.exit(1)
            decision = arg
        elif arg == "--as" and i + 1 < len(args):
            snapshot_name = args[i + 1]
            i += 1
        elif arg.startswith("-"):
            print(f"Error: unknown save option: {arg}", file=sys.stderr)
            sys.exit(1)
        else:
            patterns.append(arg)
        i += 1

    if save_all == bool(patterns):
        print("Error: name the instance(s) to save, or pass --all", file=sys.stderr)
        print("Usage: chrome-agent save <instance|glob>... [--stop] [--as NAME] [--overwrite|--keep-both]", file=sys.stderr)
        print("       chrome-agent save --all [--stop] [--overwrite|--keep-both]", file=sys.stderr)
        sys.exit(1)

    if save_all:
        names = [i.name for i in enumerate_instances() if i.alive]
        if not names:
            print("No running instances to save.")
            return
    else:
        names = []
        for pattern in patterns:
            try:
                names += [n for n in resolve_instance_names(name_or_pattern=pattern) if n not in names]
            except InstanceNotFoundError as exc:
                print(f"Error: {exc}", file=sys.stderr)
                sys.exit(1)
    if snapshot_name and len(names) > 1:
        print("Error: --as names a single snapshot, but several instances were selected", file=sys.stderr)
        sys.exit(1)

    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    saved, failures = [], 0
    for name in names:
        target_name = snapshot_name or name
        try:
            plan = plan_save(name)
            existing = latest_version(target_name)
            replace = None
            if existing is not None:
                if decision == "--overwrite":
                    replace = existing
                elif decision is None and interactive:
                    print(f"\n{target_name} already has a snapshot, saved {_local_time(existing.info['saved_at'])} "
                          f"({_human_age(existing)}, {existing.info.get('mode')}):")
                    try:
                        _print_tabs(read_state(existing), indent="    ")
                    except (SnapshotKeyError, OSError) as exc:
                        print(f"    (tabs unreadable: {exc})")
                    if _confirm(f"Overwrite it? (No keeps both, as timestamped versions)"):
                        replace = existing
            version = save_instance(plan, stop=stop, snapshot_name=snapshot_name, replace=replace)
        except (SnapshotError, SnapshotKeyError, InstanceNotFoundError, ConnectionError, RuntimeError) as exc:
            print(f"Error saving {name}: {exc}", file=sys.stderr)
            failures += 1
            continue
        saved.append(version)
        info = version.info
        what = "replaced previous" if replace else ("kept previous too" if existing else "new")
        if sys.stdout.isatty():
            print(f"Saved {name} -> {version.ref}  ({info['tabs']} tabs, {info['cookies']} cookies, "
                  f"{_human_size(info['size_bytes'])}, {info['mode']}{', browser stopped' if stop else ''}; {what})")
        else:
            print(json.dumps({"instance": name, "snapshot": version.ref, "replaced": bool(replace),
                              **{k: info[k] for k in ("tabs", "cookies", "size_bytes", "mode", "port")}}))

    if save_all and saved:
        write_batch(saved)
        if sys.stdout.isatty():
            print(f"\nSaved {len(saved)} of {len(names)} instance(s). Restore them all with: chrome-agent restore --all")
    if failures:
        sys.exit(1)


def _run_restore(args: list[str]) -> None:
    """Restore snapshots as running instances."""
    from .snapcrypto import SnapshotKeyError
    from .snapshot import (
        SnapshotError,
        batch_versions,
        latest_batch,
        list_versions,
        resolve_refs,
        restore_version,
    )

    restore_all = here = any_port = replace_profile = start_display = False
    reattach = True
    desktop_mode = None
    refs = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--all":
            restore_all = True
        elif arg == "--here":
            here = True
        elif arg == "--any-port":
            any_port = True
        elif arg == "--no-reattach":
            reattach = False
        elif arg == "--replace-profile":
            replace_profile = True
        elif arg == "--start-display":
            start_display = True
        elif arg == "--desktop" and i + 1 < len(args) and args[i + 1] in ("saved", "terminal"):
            desktop_mode = args[i + 1]
            i += 1
        elif arg.startswith("-"):
            print(f"Error: unknown restore option: {arg}", file=sys.stderr)
            sys.exit(1)
        else:
            refs.append(arg)
        i += 1

    cwd = os.getcwd()
    try:
        if restore_all:
            if refs:
                print("Error: --all restores the last `save --all` batch; do not also name snapshots", file=sys.stderr)
                sys.exit(1)
            batch = latest_batch()
            if batch is None:
                print("Error: no `save --all` batch found. Restore by name: chrome-agent restore <name>", file=sys.stderr)
                sys.exit(1)
            versions = batch_versions(batch)
            desktop_mode = desktop_mode or "saved"
        elif refs:
            versions = []
            for ref in refs:
                versions += [v for v in resolve_refs(ref) if v not in versions]
            desktop_mode = desktop_mode or "terminal"
        else:
            here = True
            latest = {}
            for v in list_versions():
                latest[v.name] = v
            versions = list(latest.values())
            desktop_mode = desktop_mode or "terminal"
        if here:
            versions = [v for v in versions if v.info.get("origin_dir") == cwd]
    except SnapshotError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if not versions:
        print(f"Error: no snapshots {'in that batch ' if restore_all else ''}were launched from {cwd}"
              if here else "Error: nothing to restore", file=sys.stderr)
        print("See what is saved with: chrome-agent snapshots", file=sys.stderr)
        sys.exit(1)

    # Ascending desktop order, so dynamic workspaces fill in as they would
    # have been (see desktop.py); windows with no recorded desktop go last.
    versions.sort(key=lambda v: (v.info.get("desktop") is None, v.info.get("desktop") or 0, v.name))

    failures = 0
    for version in versions:
        try:
            report = restore_version(
                version, any_port=any_port, desktop_mode=desktop_mode, reattach=reattach,
                replace_profile=replace_profile, start_display=start_display,
            )
        except (SnapshotError, SnapshotKeyError, RuntimeError, TimeoutError, ConnectionError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            failures += 1
            continue
        if sys.stdout.isatty():
            on = f", on virtual display {report['display']}" if report.get("display") else ""
            print(f"Restored {report['snapshot']} as {report['name']} on port {report['port']} "
                  f"({report['tabs']} tabs, {report['windows']} window(s), {report['cookies']} cookies{on})")
            for warning in report["warnings"]:
                print(f"  warning: {warning}")
            for sub in report["subscriptions"]:
                print(f"  observer {sub['status']}: {sub['command']}")
        else:
            print(json.dumps(report))
    if failures:
        sys.exit(1)


def _run_snapshots(args: list[str]) -> None:
    """List, inspect and delete snapshots; back up the encryption key."""
    from .snapcrypto import SnapshotKeyError, export_key, import_key
    from .snapshot import (
        SnapshotError,
        list_versions,
        parse_age,
        read_state,
        remove_version,
        resolve_refs,
        snapshot_root,
        version_age,
    )

    sub = args[0] if args else "list"
    rest = args[1:]
    if sub not in ("list", "show", "rm", "export-key", "import-key"):
        sub, rest = "list", args  # `snapshots <glob>` lists

    try:
        if sub == "list":
            versions = list_versions(pattern=rest[0] if rest else None)
            if not sys.stdout.isatty():
                print(json.dumps([{"snapshot": v.ref, **v.info} for v in versions]))
                return
            if not versions:
                print("No snapshots saved. Save one with: chrome-agent save <instance>")
                return
            latest = {}
            for v in versions:
                latest[v.name] = v.stamp
            home = os.path.expanduser("~")
            for v in versions:
                info = v.info
                origin = (info.get("origin_dir") or "?").replace(home, "~", 1)
                mark = " " if latest[v.name] == v.stamp else "-"
                print(f"{mark} {v.ref:52} {_local_time(info['saved_at'])} ({_human_age(v):>7})  "
                      f"{info.get('tabs', 0):>3} tabs  {_human_size(info.get('size_bytes', 0)):>9}  "
                      f"port {info.get('port')}  {info.get('mode', '')}  {origin}")
            total = sum(v.info.get("size_bytes", 0) for v in versions)
            print(f"\n{len(versions)} snapshot version(s), {_human_size(total)} in {snapshot_root()}")
            if any(latest[v.name] != v.stamp for v in versions):
                print("('-' marks an older version; restoring by name uses the latest)")
            return

        if sub == "show":
            if not rest:
                print("Usage: chrome-agent snapshots show <name[@stamp]>", file=sys.stderr)
                sys.exit(1)
            for version in resolve_refs(rest[0]):
                state = read_state(version)
                info = version.info
                print(f"{version.ref}")
                print(f"  saved     {_local_time(info['saved_at'])} ({_human_age(version)}), {info.get('mode')}")
                print(f"  instance  {state['instance']} on port {state['port']}, {state.get('browser_version')}")
                print(f"  origin    {state.get('origin_dir')}")
                if state.get("profile_override"):
                    print(f"  profile   {state['profile_override']} (custom --user-data-dir)")
                launch = state.get("launch", {})
                flags = " ".join(launch.get("chrome_args", [])) or "(none)"
                print(f"  launch    {'headless' if launch.get('headless') else 'headed'}, "
                      f"border {'on' if launch.get('window_border') else 'off'}, flags: {flags}")
                virtual = launch.get("virtual_display")
                if virtual:
                    print(f"  display   {virtual['display']} (virtual: {' '.join(virtual['server'])})")
                desks = sorted(set(state.get("desktops", {}).values()))
                if desks:
                    print(f"  desktop   {', '.join(str(d + 1) for d in desks)} (1-based)")
                print(f"  size      {_human_size(info.get('size_bytes', 0))} "
                      f"({info.get('profile_files')} profile files, {len(state.get('cookies', []))} cookies)")
                print("  tabs (* = active):")
                _print_tabs(state, indent="    ")
                subs = state.get("subscriptions", [])
                if subs:
                    print("  observers:")
                    for s in subs:
                        if s.get("wrapper"):
                            how = f"writes {s['stdout']}" if s.get("stdout") else "output was piped"
                            print(f"    (in a shell, {how}) {' '.join(s['wrapper']['argv'])[:200]}")
                        else:
                            out = f" >> {s['stdout']}" if s.get("stdout") else "  (output was piped)"
                            print(f"    chrome-agent {' '.join(s['argv'])}{out}")
            return

        if sub == "rm":
            yes = "--yes" in rest or "-y" in rest
            older = None
            refs = []
            j = 0
            while j < len(rest):
                if rest[j] in ("--yes", "-y"):
                    pass
                elif rest[j] == "--older-than" and j + 1 < len(rest):
                    older = parse_age(rest[j + 1])
                    j += 1
                else:
                    refs.append(rest[j])
                j += 1
            if not refs and older is None:
                print("Usage: chrome-agent snapshots rm <name|name@stamp|glob>... [--older-than AGE] [--yes]", file=sys.stderr)
                sys.exit(1)
            if refs:
                victims = []
                for ref in refs:
                    name, _, stamp = ref.partition("@")
                    matches = [v for v in list_versions(pattern=name) if not stamp or v.stamp == stamp]
                    if not matches:
                        raise SnapshotError(f"No snapshot matches '{ref}'")
                    victims += [v for v in matches if v not in victims]
            else:
                victims = list_versions()
            if older is not None:
                victims = [v for v in victims if version_age(v) > older]
            if not victims:
                print("Nothing to delete.")
                return
            print(f"{'Deleting' if yes else 'Will delete'} {len(victims)} snapshot version(s):")
            for v in victims:
                print(f"  {v.ref}  ({_local_time(v.info['saved_at'])}, {v.info.get('tabs')} tabs, "
                      f"{_human_size(v.info.get('size_bytes', 0))})")
            if not yes:
                if not (sys.stdin.isatty() and sys.stdout.isatty()):
                    print("Error: deleting snapshots needs --yes when not run interactively", file=sys.stderr)
                    sys.exit(1)
                if not _confirm("Delete these?"):
                    print("Nothing deleted.")
                    return
            for v in victims:
                remove_version(v)
            print(f"Deleted {len(victims)} snapshot version(s).")
            return

        if sub == "export-key":
            print(export_key())
            return

        if sub == "import-key":
            text = sys.stdin.read()
            import_key(text, replace="--replace" in rest)
            print("Snapshot key stored in the OS keyring.")
            return
    except (SnapshotError, SnapshotKeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


async def _run_cdp_one_shot(
    instance_name: str | None,
    method: str,
    params_str: str | None,
    target_spec: str | None,
    target_by: str | None,
) -> None:
    """Send a single CDP command via browser-level WS + Target.attachToTarget."""
    from .attach import AmbiguousTargetError, TargetNotFoundError
    from .cdp_client import CDPClient, get_ws_url
    from .errors import CDPError

    # Resolve instance
    if instance_name is not None:
        from .registry import (
            AmbiguousInstanceError,
            InstanceNotFoundError,
            lookup,
            resolve_instance_name,
        )
        try:
            resolved = resolve_instance_name(name_or_pattern=instance_name)
            info = lookup(instance_name=resolved)
        except (AmbiguousInstanceError, InstanceNotFoundError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
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
            target_id = resolve_target(
                page_targets=page_targets,
                target_spec=target_spec,
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

    except (AmbiguousTargetError, TargetNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except CDPError as exc:
        print(f"CDP error {exc.code}: {exc.message}", file=sys.stderr)
        sys.exit(1)
    except ConnectionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """CLI entry point."""
    # Phase 0: Extract the target-selection flags before routing
    args, target_spec, target_by = _extract_flags(sys.argv[1:])

    if args and args[0] in ("--version", "-V"):
        from . import __version__
        print(f"chrome-agent {__version__}")
        sys.exit(0)

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
            asyncio.run(_run_attach(args=rest, target_spec=target_spec, target_by=target_by))
        elif command == "help":
            _run_help(args=rest)
        elif command == "stop":
            _run_stop(args=rest, target_spec=target_spec, target_by=target_by)
        elif command == "cleanup":
            _run_cleanup()
        elif command == "guide":
            _print_guide(args=rest)
        elif command == "completions":
            _run_completions(args=rest)
        elif command == "save":
            _run_save(args=rest)
        elif command == "restore":
            _run_restore(args=rest)
        elif command == "snapshots":
            _run_snapshots(args=rest)
        return

    # Disambiguate "instance name" vs "bare Domain.method":
    #   - Registered instance names (e.g. from a directory basename like
    #     "aroundchicago.tech-01") may contain dots, so a naive "." check
    #     misroutes them as CDP methods.
    #   - Resolve by checking the registry first. If the first arg matches a
    #     known instance, route as instance. Otherwise, apply the
    #     Domain.method heuristic (PascalCase domain + dot + camelCase method).
    #   - A glob pattern is always an instance argument: method names are not
    #     globbable, so a wildcard is unambiguous intent to select instances.
    from .registry import enumerate_instances, is_pattern

    known_instances = {i.name for i in enumerate_instances()}
    is_known_instance = command in known_instances or is_pattern(command)
    looks_like_method = (
        "." in command
        and command.count(".") == 1
        and command.split(".")[0].isidentifier()
        and command.split(".")[0][:1].isupper()
    )

    if not is_known_instance and looks_like_method:
        method = command
        params_str = rest[0] if rest else None
        asyncio.run(_run_cdp_one_shot(
            instance_name=None,
            method=method,
            params_str=params_str,
            target_spec=target_spec,
            target_by=target_by,
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
        target_by=target_by,
    ))
