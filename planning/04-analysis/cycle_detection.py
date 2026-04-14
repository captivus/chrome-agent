"""Circular dependency detection for chrome-agent feature graph.

Reads planning/04-dependency-graph.json and reports all cycles.
Uses depth-first search with node coloring.
"""

import json
from pathlib import Path


def load_graph():
    path = Path(__file__).parent.parent / "04-dependency-graph.json"
    with open(path) as f:
        return json.load(f)


def detect_cycles(graph):
    features = graph["features"]
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {fid: WHITE for fid in features}
    cycles = []
    path = []

    def dfs(node):
        color[node] = GRAY
        path.append(node)
        for dep in features[node].get("depends_on", []):
            dep_id = dep["feature"]
            if dep_id not in color:
                continue  # external dependency
            if color[dep_id] == GRAY:
                # Found a cycle -- extract it
                cycle_start = path.index(dep_id)
                cycle = path[cycle_start:] + [dep_id]
                cycles.append(cycle)
            elif color[dep_id] == WHITE:
                dfs(dep_id)
        path.pop()
        color[node] = BLACK

    for fid in features:
        if color[fid] == WHITE:
            dfs(fid)

    return cycles


def main():
    graph = load_graph()
    print(f"Features: {graph['metadata']['feature_count']}")
    print(f"Dependencies: {graph['metadata']['dependency_count']}")
    print(f"Phase: {graph['metadata']['phase']}")
    print()

    cycles = detect_cycles(graph)
    if cycles:
        print(f"CIRCULAR DEPENDENCIES FOUND: {len(cycles)}")
        for i, cycle in enumerate(cycles, 1):
            chain = " -> ".join(cycle)
            print(f"  Cycle {i}: {chain}")
    else:
        print("No circular dependencies detected.")


if __name__ == "__main__":
    main()
