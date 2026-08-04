"""Failure Clustering Module for ARC Explorer."""

from typing import Dict, List, Any
import math
from arc_explorer.object_perception import ObjectPerceptionEngine
from arc_explorer.symmetry_engine import detect_mirror_symmetry, detect_rotational_symmetry, detect_periodic_lattice


def cluster_failed_task(train_pairs: List[Any], failure_reason: str = "") -> str:
    """Clusters an unsolved ARC task into a domain failure category based on grid delta properties."""
    if not train_pairs:
        return "unknown / unclassified"

    # Analyze input/output grid properties across train pairs
    shape_diffs = []
    color_only_diffs = []
    object_count_diffs = []
    symmetry_matches = []
    periodic_matches = []
    enclosure_diffs = []

    for pair in train_pairs:
        in_g = pair.input_grid
        out_g = pair.output_grid
        if not in_g or not out_g or not in_g[0] or not out_g[0]:
            continue

        h_in, w_in = len(in_g), len(in_g[0])
        h_out, w_out = len(out_g), len(out_g[0])

        if (h_in, w_in) != (h_out, w_out):
            shape_diffs.append((h_in, w_in, h_out, w_out))
        else:
            # Same shape: check if only colors changed
            diff_cells = sum(1 for r in range(h_in) for c in range(w_in) if in_g[r][c] != out_g[r][c])
            if diff_cells > 0:
                color_only_diffs.append(diff_cells)

        # Detect objects
        in_objs = ObjectPerceptionEngine.detect_objects(in_g)
        out_objs = ObjectPerceptionEngine.detect_objects(out_g)
        if len(in_objs) != len(out_objs):
            object_count_diffs.append((len(in_objs), len(out_objs)))

        # Check symmetry properties of output
        sym_m = detect_mirror_symmetry(out_g)
        sym_r = detect_rotational_symmetry(out_g)
        if sym_m["horizontal"] or sym_m["vertical"] or sym_r[180]:
            symmetry_matches.append(True)

        # Check periodic lattice properties of output
        lattice = detect_periodic_lattice(out_g)
        if lattice is not None:
            periodic_matches.append(True)

    # Heuristic Clustering Hierarchy based on grid delta signatures

    # 1. Resizing or Tiling
    if len(shape_diffs) == len(train_pairs) and len(shape_diffs) > 0:
        return "resizing or tiling"

    # 2. Symmetry
    if len(symmetry_matches) == len(train_pairs) and len(symmetry_matches) > 0:
        return "symmetry"

    # 3. Periodic Pattern
    if len(periodic_matches) == len(train_pairs) and len(periodic_matches) > 0:
        return "periodic pattern"

    # 4. Object Counting
    if len(object_count_diffs) == len(train_pairs) and len(object_count_diffs) > 0:
        return "object counting"

    # 5. Connected-Component Manipulation
    if object_count_diffs:
        return "connected-component manipulation"

    # 6. Color Transformation
    if len(color_only_diffs) == len(train_pairs) and len(color_only_diffs) > 0:
        return "color transformation"

    # 7. Spatial Relation
    if "spatial" in failure_reason.lower() or "position" in failure_reason.lower():
        return "spatial relation"

    # 8. Gravity or Motion
    if "gravity" in failure_reason.lower() or "move" in failure_reason.lower():
        return "gravity or motion"

    # 9. Enclosure or Flood Fill
    if "infill" in failure_reason.lower() or "enclosed" in failure_reason.lower():
        return "enclosure or flood fill"

    return "unknown / unclassified"


def categorize_failed_tasks(unsolved_results: List[Any]) -> Dict[str, List[str]]:
    """Categorizes a list of unsolved TaskEvalResult objects into failure category clusters."""
    categories: Dict[str, List[str]] = {
        "color transformation": [],
        "object counting": [],
        "connected-component manipulation": [],
        "spatial relation": [],
        "symmetry": [],
        "periodic pattern": [],
        "gravity or motion": [],
        "enclosure or flood fill": [],
        "resizing or tiling": [],
        "unknown / unclassified": [],
    }

    for res in unsolved_results:
        task_id = getattr(res, "task_id", str(res))
        task = getattr(res, "task", None)
        train_pairs = getattr(task, "train_pairs", []) if task else []
        reason = getattr(res, "failure_reason", "")

        cat = cluster_failed_task(train_pairs, reason)
        if cat not in categories:
            cat = "unknown / unclassified"
        categories[cat].append(task_id)

    return categories
