"""Final validation for the dependency graph.

Checks:
1. Every feature from the inventory appears in the graph
2. No circular dependencies
3. Metadata counts match actual data
4. All referenced dependencies exist
"""

import json
from pathlib import Path


def load_graph():
    path = Path(__file__).parent.parent / "04-dependency-graph.json"
    with open(path) as f:
        return json.load(f)


def validate(graph):
    features = graph["features"]
    metadata = graph["metadata"]
    errors = []

    # Check feature count
    actual_count = len(features)
    declared_count = metadata["feature_count"]
    if actual_count != declared_count:
        errors.append(f"Feature count mismatch: metadata says {declared_count}, actual is {actual_count}")

    # Check dependency count
    actual_deps = sum(len(f.get("depends_on", [])) for f in features.values())
    declared_deps = metadata["dependency_count"]
    if actual_deps != declared_deps:
        errors.append(f"Dependency count mismatch: metadata says {declared_deps}, actual is {actual_deps}")

    # Check all referenced dependencies exist
    for fid, feature in features.items():
        for dep in feature.get("depends_on", []):
            dep_id = dep["feature"]
            if dep_id not in features:
                errors.append(f"{fid} depends on {dep_id} which is not in the feature list")

    # Check expected features (from inventory)
    expected = ["CDP-01", "CDP-02", "CDP-03", "GEN-01", "BRW-01", "BRW-02", "BRW-03", "CLI-01"]
    for fid in expected:
        if fid not in features:
            errors.append(f"Expected feature {fid} not found in graph")
    for fid in features:
        if fid not in expected:
            errors.append(f"Unexpected feature {fid} in graph (not in expected list)")

    # Cycle detection (reuse from cycle_detection.py)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {fid: WHITE for fid in features}
    has_cycle = False
    path = []

    def dfs(node):
        nonlocal has_cycle
        color[node] = GRAY
        path.append(node)
        for dep in features[node].get("depends_on", []):
            dep_id = dep["feature"]
            if dep_id not in color:
                continue
            if color[dep_id] == GRAY:
                has_cycle = True
                cycle_start = path.index(dep_id)
                cycle = path[cycle_start:] + [dep_id]
                errors.append(f"Circular dependency: {' -> '.join(cycle)}")
            elif color[dep_id] == WHITE:
                dfs(dep_id)
        path.pop()
        color[node] = BLACK

    for fid in features:
        if color[fid] == WHITE:
            dfs(fid)

    return errors


def main():
    graph = load_graph()
    print("Running final validation...")
    print(f"  Features: {len(graph['features'])}")
    print(f"  Dependencies: {sum(len(f.get('depends_on', [])) for f in graph['features'].values())}")
    print()

    errors = validate(graph)
    if errors:
        print(f"VALIDATION FAILED -- {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
    else:
        print("VALIDATION PASSED")
        print("  - All features present")
        print("  - No circular dependencies")
        print("  - Metadata counts match")
        print("  - All dependency references valid")

    # Show the natural layers
    features = graph["features"]
    roots = [fid for fid, f in features.items() if not f.get("depends_on")]
    print(f"\n  Root features (no dependencies): {', '.join(roots)}")

    layer1 = [fid for fid, f in features.items()
              if f.get("depends_on")
              and all(d["feature"] in roots for d in f["depends_on"])]
    print(f"  Layer 1 (depend only on roots): {', '.join(layer1)}")

    remaining = [fid for fid in features if fid not in roots and fid not in layer1]
    print(f"  Remaining: {', '.join(remaining)}")


if __name__ == "__main__":
    main()
