"""Topological sort and critical path computation for chrome-agent implementation planning.

Reads planning/04-dependency-graph.json and:
1. Assigns each feature to a phase based on dependency depth
2. Computes the critical path (longest sequential chain)
3. Identifies parallel development opportunities within each phase
4. Outputs phase assignments and critical path
"""
import json
from collections import defaultdict
from pathlib import Path


def main():
    path = Path(__file__).parent.parent / "04-dependency-graph.json"
    with open(path) as f:
        data = json.load(f)

    # Build adjacency and reverse adjacency
    features = {}
    deps = {}
    for f in data["features"]:
        fid = f["id"]
        features[fid] = f
        d = f.get("depends_on", [])
        deps[fid] = d if isinstance(d, list) and (not d or isinstance(d[0], str)) else []

    # Compute phases by dependency depth (BFS-based layer assignment)
    in_degree = {fid: 0 for fid in features}
    for fid, dep_list in deps.items():
        for dep in dep_list:
            if dep in features:
                in_degree[fid] += 1  # wrong direction, let me fix

    # Actually: in_degree counts how many deps each feature has
    in_degree = {fid: len([d for d in dep_list if d in features]) for fid, dep_list in deps.items()}

    # Reverse map: feature -> features that depend on it
    dependents = defaultdict(list)
    for fid, dep_list in deps.items():
        for dep in dep_list:
            if dep in features:
                dependents[dep].append(fid)

    # BFS layer assignment
    phases = {}
    queue = [fid for fid, deg in in_degree.items() if deg == 0]
    remaining_deps = dict(in_degree)
    phase_num = 1

    while queue:
        # All features in this batch have all deps satisfied
        for fid in queue:
            phases[fid] = phase_num

        next_queue = []
        for fid in queue:
            for dependent in dependents[fid]:
                remaining_deps[dependent] -= 1
                if remaining_deps[dependent] == 0:
                    next_queue.append(dependent)

        queue = next_queue
        phase_num += 1

    # Group by phase
    phase_groups = defaultdict(list)
    for fid, phase in sorted(phases.items(), key=lambda x: (x[1], x[0])):
        phase_groups[phase].append(fid)

    # Print phases
    print("PHASE ASSIGNMENTS")
    print("=" * 60)
    for phase in sorted(phase_groups.keys()):
        fids = phase_groups[phase]
        print(f"\nPhase {phase} ({len(fids)} features):")
        for fid in fids:
            f = features[fid]
            dep_str = ", ".join(deps[fid]) if deps[fid] else "none"
            status = f.get("status", "?")
            print(f"  {fid} ({f['name']}) [iter {f.get('iteration', '?')}, {status}] deps: {dep_str}")

    # Critical path: longest path through the DAG
    # Use dynamic programming on topological order
    longest = {fid: 0 for fid in features}
    predecessor = {fid: None for fid in features}

    # Process in phase order (topological order)
    for phase in sorted(phase_groups.keys()):
        for fid in phase_groups[phase]:
            for dep in deps[fid]:
                if dep in features and longest[dep] + 1 > longest[fid]:
                    longest[fid] = longest[dep] + 1
                    predecessor[fid] = dep

    # Find the feature with the longest path
    max_feature = max(longest, key=longest.get)
    max_length = longest[max_feature]

    # Trace back the critical path
    critical_path = []
    current = max_feature
    while current is not None:
        critical_path.append(current)
        current = predecessor[current]
    critical_path.reverse()

    print(f"\nCRITICAL PATH (length {max_length + 1}):")
    print(" -> ".join(critical_path))
    print(f"Phases on critical path: {[phases[fid] for fid in critical_path]}")

    # Identify features NOT on critical path
    critical_set = set(critical_path)
    off_critical = [fid for fid in features if fid not in critical_set]
    print(f"\nOff critical path: {off_critical}")

    # Iteration 2 scope only
    print(f"\nITERATION 2 SCOPE:")
    iter2_features = [fid for fid, f in features.items()
                      if f.get("status") in ("not_started", "update_needed")]
    for fid in sorted(iter2_features, key=lambda x: phases[x]):
        print(f"  Phase {phases[fid]}: {fid} ({features[fid]['name']}) [{features[fid]['status']}]")


if __name__ == "__main__":
    main()
