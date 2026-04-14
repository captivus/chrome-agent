"""Topological sort and critical path computation for chrome-agent implementation planning.

Reads planning/04-dependency-graph.json and:
1. Assigns each feature to a phase based on dependency depth
2. Verifies no intra-phase dependencies
3. Computes the critical path (longest sequential chain)
"""

import json
from pathlib import Path


def load_graph():
    path = Path(__file__).parent.parent / "04-dependency-graph.json"
    with open(path) as f:
        return json.load(f)


def compute_phases(features):
    """Assign each feature to a phase based on dependency depth."""
    phases = {}

    def get_phase(fid):
        if fid in phases:
            return phases[fid]
        deps = features[fid].get("depends_on", [])
        if not deps:
            phases[fid] = 1
            return 1
        max_dep_phase = max(get_phase(d["feature"]) for d in deps)
        phases[fid] = max_dep_phase + 1
        return phases[fid]

    for fid in features:
        get_phase(fid)

    return phases


def verify_no_intra_phase_deps(features, phases):
    """Check that no features within the same phase depend on each other."""
    errors = []
    for fid, feature in features.items():
        for dep in feature.get("depends_on", []):
            dep_id = dep["feature"]
            if dep_id in phases and phases[fid] == phases[dep_id]:
                errors.append(f"{fid} and {dep_id} are both in phase {phases[fid]} but {fid} depends on {dep_id}")
    return errors


def compute_critical_path(features, phases):
    """Find the longest sequential chain through the phase structure."""
    # Build reverse lookup: for each feature, what depends on it
    dependents = {fid: [] for fid in features}
    for fid, feature in features.items():
        for dep in feature.get("depends_on", []):
            dep_id = dep["feature"]
            if dep_id in dependents:
                dependents[dep_id].append(fid)

    # Find longest path from each root
    memo = {}

    def longest_path(fid):
        if fid in memo:
            return memo[fid]
        deps_of = dependents[fid]
        if not deps_of:
            memo[fid] = [fid]
            return [fid]
        best = max((longest_path(d) for d in deps_of), key=len)
        memo[fid] = [fid] + best
        return memo[fid]

    # Start from all roots (no dependencies)
    roots = [fid for fid, f in features.items() if not f.get("depends_on")]
    all_paths = [longest_path(r) for r in roots]
    critical = max(all_paths, key=len)
    return critical


def main():
    graph = load_graph()
    features = graph["features"]

    # Compute phases
    phases = compute_phases(features)

    # Verify
    errors = verify_no_intra_phase_deps(features, phases)
    if errors:
        print("INTRA-PHASE DEPENDENCY ERRORS:")
        for e in errors:
            print(f"  - {e}")
        return

    # Group by phase
    phase_groups = {}
    for fid, phase in phases.items():
        phase_groups.setdefault(phase, []).append(fid)

    # Print phases
    print("PHASE ASSIGNMENTS")
    print("=" * 60)
    for phase_num in sorted(phase_groups):
        features_in_phase = phase_groups[phase_num]
        names = [f"{fid} ({features[fid]['name']})" for fid in features_in_phase]
        print(f"\n  Phase {phase_num} ({len(features_in_phase)} features):")
        for name in names:
            print(f"    - {name}")

    # Critical path
    critical = compute_critical_path(features, phases)
    print(f"\nCRITICAL PATH ({len(critical)} features, {max(phases.values())} phases):")
    print(f"  {' -> '.join(critical)}")

    # Output as JSON for the implementation plan
    output = {
        "phases": {str(p): sorted(fids) for p, fids in sorted(phase_groups.items())},
        "critical_path": critical,
        "feature_phases": phases,
    }
    print(f"\nJSON output:")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
