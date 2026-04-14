"""Circular dependency detection for chrome-agent feature graph.

Reads planning/04-dependency-graph.json and reports all cycles.
Uses depth-first search with node coloring.
"""
import json
from pathlib import Path


def main():
    path = Path(__file__).parent.parent / "04-dependency-graph.json"
    with open(path) as f:
        data = json.load(f)

    # Build adjacency: feature -> list of its dependencies
    graph = {}
    for feature in data["features"]:
        fid = feature["id"]
        deps = feature.get("depends_on", [])
        if deps and isinstance(deps[0], str):
            graph[fid] = deps
        elif deps and isinstance(deps[0], dict):
            graph[fid] = [d["feature"] for d in deps]
        else:
            graph[fid] = []

    print(f"Features: {len(graph)}")
    print(f"Dependencies: {sum(len(v) for v in graph.values())}")

    # DFS cycle detection with coloring
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node: WHITE for node in graph}
    path = []
    cycles = []

    def dfs(node):
        color[node] = GRAY
        path.append(node)
        for dep in graph.get(node, []):
            if dep not in color:
                continue
            if color[dep] == GRAY:
                cycle_start = path.index(dep)
                cycles.append(path[cycle_start:] + [dep])
            elif color[dep] == WHITE:
                dfs(dep)
        path.pop()
        color[node] = BLACK

    for node in graph:
        if color[node] == WHITE:
            dfs(node)

    if not cycles:
        print("\nNO CIRCULAR DEPENDENCIES DETECTED")
    else:
        print(f"\nCIRCULAR DEPENDENCIES FOUND: {len(cycles)}")
        for i, cycle in enumerate(cycles, 1):
            print(f"  Cycle {i}: {' -> '.join(cycle)}")

    # Validate all features from inventory are present
    inventory_ids = {f["id"] for f in data["features"]}
    dep_refs = set()
    for feature in data["features"]:
        for dep in feature.get("depends_on", []):
            if isinstance(dep, str):
                dep_refs.add(dep)
            elif isinstance(dep, dict):
                dep_refs.add(dep["feature"])

    missing = dep_refs - inventory_ids
    if missing:
        print(f"\nWARNING: Dependencies reference unknown features: {missing}")
    else:
        print(f"\nAll dependency references resolve to known features.")

    # Root features (no dependencies)
    roots = [fid for fid, deps in graph.items() if not deps]
    print(f"Root features (no dependencies): {roots}")

    # Leaf features (nothing depends on them)
    depended_on = set()
    for deps in graph.values():
        depended_on.update(deps)
    leaves = [fid for fid in graph if fid not in depended_on]
    print(f"Leaf features (nothing depends on them): {leaves}")

    return len(cycles)


if __name__ == "__main__":
    main()
