"""CDP protocol discovery.

Queries a running browser's /json/protocol endpoint to retrieve the
complete CDP protocol schema. Provides both raw schema access and
formatted text output at three levels of detail: all domains, a
specific domain's commands and events, or a specific method's full
parameter signature.

Synchronous. Uses stdlib only (urllib + json).
"""

import json
import urllib.request


def fetch_protocol_schema(port: int = 9222) -> dict:
    """Fetch the raw protocol schema JSON from the browser.

    Returns the parsed JSON dict from /json/protocol.
    Synchronous. Uses stdlib urllib.

    Raises ConnectionError if no browser is running on the port.
    """
    try:
        req = urllib.request.Request(f"http://localhost:{port}/json/protocol")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        raise ConnectionError(
            f"No browser running on port {port}. "
            f"Start one with: chrome-agent launch"
        ) from exc


def discover_protocol(
    port: int = 9222,
    query: str | None = None,
) -> None:
    """Query the browser's protocol schema and print formatted output.

    query=None: list all domains
    query="Page": list commands and events in the Page domain
    query="Page.navigate": show full details for Page.navigate

    Synchronous. Uses stdlib urllib.

    Raises ConnectionError if no browser is running on the port.
    Raises ValueError if the domain or method is not found.
    """
    schema = fetch_protocol_schema(port=port)
    domains = schema["domains"]

    if query is None:
        _print_all_domains(domains=domains)
    elif "." not in query:
        _print_domain_detail(domains=domains, domain_name=query)
    else:
        _print_method_detail(domains=domains, query=query)


def _find_domain(domains: list[dict], name: str) -> dict | None:
    """Find a domain by name in the schema's domain list."""
    for domain in domains:
        if domain["domain"] == name:
            return domain
    return None


def _format_flags(item: dict) -> str:
    """Format experimental/deprecated flags for display."""
    flags = []
    if item.get("experimental"):
        flags.append("experimental")
    if item.get("deprecated"):
        flags.append("deprecated")
    return f" ({', '.join(flags)})" if flags else ""


def _print_all_domains(domains: list[dict]) -> None:
    """Print a summary of all CDP domains."""
    for domain in domains:
        name = domain["domain"]
        desc = domain.get("description", "")
        flags = _format_flags(item=domain)
        if desc:
            print(f"{name}{flags}: {desc}")
        else:
            print(f"{name}{flags}")


def _print_domain_detail(domains: list[dict], domain_name: str) -> None:
    """Print commands and events for a specific domain."""
    domain = _find_domain(domains=domains, name=domain_name)
    if domain is None:
        raise ValueError(f"Unknown domain: {domain_name}")

    print(f"Domain: {domain['domain']}")
    desc = domain.get("description", "")
    if desc:
        print(desc)

    commands = domain.get("commands", [])
    if commands:
        print("\nCommands:")
        for cmd in commands:
            flags = _format_flags(item=cmd)
            print(f"  {domain_name}.{cmd['name']}{flags}")
            cmd_desc = cmd.get("description", "")
            if cmd_desc:
                print(f"    {cmd_desc}")

    events = domain.get("events", [])
    if events:
        print("\nEvents:")
        for evt in events:
            flags = _format_flags(item=evt)
            print(f"  {domain_name}.{evt['name']}{flags}")
            evt_desc = evt.get("description", "")
            if evt_desc:
                print(f"    {evt_desc}")


def _print_method_detail(domains: list[dict], query: str) -> None:
    """Print full details for a specific command or event."""
    domain_name, method_name = query.split(".", 1)
    domain = _find_domain(domains=domains, name=domain_name)
    if domain is None:
        raise ValueError(f"Unknown domain: {domain_name}")

    # Search commands first, then events
    item = None
    for cmd in domain.get("commands", []):
        if cmd["name"] == method_name:
            item = cmd
            break
    if item is None:
        for evt in domain.get("events", []):
            if evt["name"] == method_name:
                item = evt
                break
    if item is None:
        raise ValueError(f"Unknown method: {query}")

    print(f"{domain_name}.{method_name}")
    desc = item.get("description", "")
    if desc:
        print(desc)
    if item.get("experimental"):
        print("(experimental)")

    parameters = item.get("parameters", [])
    if parameters:
        print("\nParameters:")
        for param in parameters:
            optional = param.get("optional", False)
            required_str = "" if optional else " (required)"
            type_str = param.get("type") or param.get("$ref") or "object"
            print(f"  {param['name']}: {type_str}{required_str}")
            param_desc = param.get("description", "")
            if param_desc:
                print(f"    {param_desc}")

    returns = item.get("returns", [])
    if returns:
        print("\nReturns:")
        for ret in returns:
            type_str = ret.get("type") or ret.get("$ref") or "object"
            print(f"  {ret['name']}: {type_str}")
            ret_desc = ret.get("description", "")
            if ret_desc:
                print(f"    {ret_desc}")
