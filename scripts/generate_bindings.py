"""Generate typed Python bindings from Chrome's CDP protocol schema.

Reads the protocol schema from a running browser's /json/protocol endpoint
and generates typed Python modules in src/chrome_agent/domains/.

Usage:
    uv run python scripts/generate_bindings.py [--port PORT]
"""

import argparse
import json
import keyword
import os
import re
import sys
import urllib.request

# Python reserved words that might appear as CDP parameter names
_RESERVED = set(keyword.kwlist) | {"type", "id", "format", "input", "range", "object", "list"}


def _snake_case(name: str) -> str:
    """Convert camelCase or PascalCase to snake_case."""
    # Insert underscore before uppercase letters that follow lowercase or before
    # sequences of uppercase followed by uppercase+lowercase
    s1 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    s2 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s1)
    return s2.lower()


def _safe_param_name(name: str) -> str:
    """Make a CDP parameter name safe for Python."""
    snake = _snake_case(name)
    if snake in _RESERVED:
        return snake + "_"
    return snake


def _python_type(param: dict) -> str:
    """Map a CDP type specification to a Python type annotation string."""
    if "$ref" in param:
        ref = param["$ref"]
        # Cross-domain references like "Network.RequestId" -- just use str
        # since we're not importing across modules for simplicity
        if "." in ref:
            return "str"
        return ref
    type_name = param.get("type", "")
    if type_name == "string":
        return "str"
    if type_name == "integer":
        return "int"
    if type_name == "number":
        return "float"
    if type_name == "boolean":
        return "bool"
    if type_name == "array":
        items = param.get("items", {})
        item_type = _python_type(items)
        return f"list[{item_type}]"
    if type_name == "object":
        return "dict"
    if type_name == "any":
        return "Any"
    if type_name == "binary":
        return "str"
    return "Any"


def _generate_domain(domain: dict) -> str:
    """Generate a complete Python module for a CDP domain."""
    domain_name = domain["domain"]
    module_name = _snake_case(domain_name)
    lines = []

    # Header
    lines.append(f'"""CDP {domain_name} domain.')
    lines.append("")
    desc = domain.get("description", "").strip()
    if desc:
        lines.append(desc)
        lines.append("")
    lines.append("Auto-generated from Chrome DevTools Protocol schema.")
    lines.append("Do not edit manually. Re-run the generator to update.")
    lines.append('"""')
    lines.append("")
    lines.append("from __future__ import annotations")
    lines.append("")
    lines.append("from typing import Any")
    lines.append("")
    lines.append("from chrome_agent.cdp_client import CDPClient")
    lines.append("")
    lines.append("")

    # Generate types (enums and dataclasses)
    for type_def in domain.get("types", []):
        type_name = type_def["id"]
        if "enum" in type_def:
            # String literal type alias
            values = ", ".join(f'"{v}"' for v in type_def["enum"])
            type_desc = type_def.get("description", "").strip()
            if type_desc:
                for desc_line in type_desc.splitlines():
                    lines.append(f"# {desc_line}")
            lines.append(f"{type_name} = str  # Literal enum: {values}")
            lines.append("")
        elif "properties" in type_def:
            type_desc = type_def.get("description", "").strip()
            if type_desc:
                for desc_line in type_desc.splitlines():
                    lines.append(f"# {desc_line}")
            lines.append(f"{type_name} = dict  # Object type")
            lines.append("")
        else:
            # Simple type alias (e.g., FrameId extends string)
            base_type = _python_type(type_def)
            lines.append(f"{type_name} = {base_type}")
            lines.append("")

    # Domain class
    lines.append(f"class {domain_name}:")
    class_desc = domain.get("description", "").strip()
    if class_desc:
        # Escape triple quotes in descriptions
        class_desc = class_desc.replace('"""', "'''")
        lines.append(f'    """{class_desc}"""')
    else:
        lines.append(f'    """CDP {domain_name} domain."""')
    lines.append("")
    lines.append("    def __init__(self, client: CDPClient):")
    lines.append("        self._client = client")

    # Command methods
    for command in domain.get("commands", []):
        lines.append("")
        lines.extend(_generate_command_method(domain_name=domain_name, command=command))

    # If no commands, add pass
    if not domain.get("commands"):
        lines.append("")
        lines.append("    pass")

    lines.append("")
    return "\n".join(lines)


def _generate_command_method(domain_name: str, command: dict) -> list[str]:
    """Generate an async method for a CDP command."""
    cmd_name = command["name"]
    method_name = _snake_case(cmd_name)
    lines = []

    params = command.get("parameters", [])
    required = [p for p in params if not p.get("optional")]
    optional = [p for p in params if p.get("optional")]

    # Build signature
    sig_parts = ["self"]
    for p in required:
        safe_name = _safe_param_name(p["name"])
        py_type = _python_type(p)
        sig_parts.append(f"{safe_name}: {py_type}")
    for p in optional:
        safe_name = _safe_param_name(p["name"])
        py_type = _python_type(p)
        sig_parts.append(f"{safe_name}: {py_type} | None = None")

    # Format signature
    if len(sig_parts) <= 3:
        sig = ", ".join(sig_parts)
        lines.append(f"    async def {method_name}({sig}) -> dict:")
    else:
        lines.append(f"    async def {method_name}(")
        for i, part in enumerate(sig_parts):
            comma = "," if i < len(sig_parts) - 1 else ","
            lines.append(f"        {part}{comma}")
        lines.append("    ) -> dict:")

    # Docstring
    desc = command.get("description", "").strip()
    if desc:
        desc = desc.replace('"""', "'''")
        if "\n" in desc:
            lines.append(f'        """{desc}')
            lines.append('        """')
        else:
            lines.append(f'        """{desc}"""')

    # Build params dict
    if not params:
        lines.append(f'        return await self._client.send(method="{domain_name}.{cmd_name}")')
    else:
        lines.append("        params: dict[str, Any] = {}")
        for p in required:
            safe_name = _safe_param_name(p["name"])
            cdp_name = p["name"]
            lines.append(f'        params["{cdp_name}"] = {safe_name}')
        for p in optional:
            safe_name = _safe_param_name(p["name"])
            cdp_name = p["name"]
            lines.append(f"        if {safe_name} is not None:")
            lines.append(f'            params["{cdp_name}"] = {safe_name}')
        lines.append(f'        return await self._client.send(method="{domain_name}.{cmd_name}", params=params)')

    return lines


def load_schema(source: str) -> dict:
    """Fetch the protocol schema from the browser's /json/protocol endpoint."""
    try:
        req = urllib.request.Request(source)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        raise ConnectionError(f"Cannot fetch protocol schema from {source}: {exc}") from exc


def generate_bindings(
    source: str,
    output_dir: str = "src/chrome_agent/domains",
) -> None:
    """Generate typed Python bindings from the CDP protocol schema."""
    schema = load_schema(source=source)
    domains = schema["domains"]

    os.makedirs(output_dir, exist_ok=True)

    domain_modules = []
    stats = {"domains": 0, "commands": 0, "types": 0, "events": 0}

    for domain in domains:
        domain_name = domain["domain"]
        module_name = _snake_case(domain_name)
        domain_modules.append((module_name, domain_name))

        module_code = _generate_domain(domain=domain)
        file_path = os.path.join(output_dir, f"{module_name}.py")
        with open(file_path, "w") as f:
            f.write(module_code)

        stats["domains"] += 1
        stats["commands"] += len(domain.get("commands", []))
        stats["types"] += len(domain.get("types", []))
        stats["events"] += len(domain.get("events", []))

    # Generate __init__.py
    init_lines = [
        '"""CDP domain bindings.',
        "",
        "Auto-generated from Chrome DevTools Protocol schema.",
        "Do not edit manually. Re-run the generator to update.",
        '"""',
        "",
    ]
    for module_name, class_name in sorted(domain_modules):
        init_lines.append(f"from .{module_name} import {class_name}")
    init_lines.append("")
    init_lines.append("__all__ = [")
    for _, class_name in sorted(domain_modules):
        init_lines.append(f'    "{class_name}",')
    init_lines.append("]")
    init_lines.append("")

    init_path = os.path.join(output_dir, "__init__.py")
    with open(init_path, "w") as f:
        f.write("\n".join(init_lines))

    print(f"Generated {stats['domains']} domains, "
          f"{stats['commands']} commands, "
          f"{stats['types']} types, "
          f"{stats['events']} events")
    print(f"Output: {output_dir}/")


def main():
    parser = argparse.ArgumentParser(description="Generate CDP typed bindings")
    parser.add_argument("--port", type=int, default=9222, help="CDP port")
    parser.add_argument("--output-dir", default="src/chrome_agent/domains",
                        help="Output directory for generated modules")
    args = parser.parse_args()

    source = f"http://localhost:{args.port}/json/protocol"
    generate_bindings(source=source, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
