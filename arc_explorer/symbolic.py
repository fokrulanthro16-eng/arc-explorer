"""Symbolic Hypothesis Graph Reasoning Engine & N-depth DAG Planner for ARC-AGI tasks."""

from typing import List, Dict, Tuple, Optional, Any, Set
import copy


class SymbolicOperator:
    """Base class for symbolic matrix transformation operators."""

    def __init__(self, name: str, complexity: float = 1.0):
        self.name = name
        self.complexity = complexity

    def apply(self, grid: List[List[int]]) -> List[List[int]]:
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "complexity": self.complexity}


class IdentityOperator(SymbolicOperator):
    """Identity transformation (no change)."""

    def __init__(self):
        super().__init__("Identity", complexity=0.1)

    def apply(self, grid: List[List[int]]) -> List[List[int]]:
        return [list(r) for r in grid]


class BoundingBoxCropOperator(SymbolicOperator):
    """Subgrid crop around non-zero connected component bounding box."""

    def __init__(self):
        super().__init__("BoundingBoxCrop", complexity=0.8)

    def apply(self, grid: List[List[int]]) -> List[List[int]]:
        if not grid or not grid[0]:
            return grid
        h, w = len(grid), len(grid[0])
        non_zero = [(r, c) for r in range(h) for c in range(w) if grid[r][c] != 0]
        if not non_zero:
            return grid
        r_min = min(r for r, c in non_zero)
        r_max = max(r for r, c in non_zero)
        c_min = min(c for r, c in non_zero)
        c_max = max(c for r, c in non_zero)
        return [[grid[r][c] for c in range(c_min, c_max + 1)] for r in range(r_min, r_max + 1)]


class BlockScaleOperator(SymbolicOperator):
    """2x2 block scaling expansion."""

    def __init__(self, scale_factor: int = 2):
        super().__init__(f"BlockScale{scale_factor}x", complexity=1.0)
        self.scale_factor = scale_factor

    def apply(self, grid: List[List[int]]) -> List[List[int]]:
        if not grid or not grid[0]:
            return grid
        h, w = len(grid), len(grid[0])
        k = self.scale_factor
        out = [[0] * (w * k) for _ in range(h * k)]
        for r in range(h):
            for c in range(w):
                color = grid[r][c]
                for dr in range(k):
                    for dc in range(k):
                        out[r * k + dr][c * k + dc] = color
        return out


class TileReplicationOperator(SymbolicOperator):
    """Matrix tile repeat (2x2 repeat)."""

    def __init__(self, repeat_r: int = 2, repeat_c: int = 2):
        super().__init__(f"TileRepeat{repeat_r}x{repeat_c}", complexity=1.0)
        self.repeat_r = repeat_r
        self.repeat_c = repeat_c

    def apply(self, grid: List[List[int]]) -> List[List[int]]:
        if not grid or not grid[0]:
            return grid
        h, w = len(grid), len(grid[0])
        out = [[0] * (w * self.repeat_c) for _ in range(h * self.repeat_r)]
        for r in range(h * self.repeat_r):
            for c in range(w * self.repeat_c):
                out[r][c] = grid[r % h][c % w]
        return out


class ColorMapOperator(SymbolicOperator):
    """Color substitution mapping c -> f(c)."""

    def __init__(self, mapping: Dict[int, int]):
        super().__init__(f"ColorMap{mapping}", complexity=1.2)
        self.mapping = mapping

    def apply(self, grid: List[List[int]]) -> List[List[int]]:
        return [[self.mapping.get(cell, cell) for cell in row] for row in grid]


class HorizontalReflectionOperator(SymbolicOperator):
    """Horizontal mirror reflection across vertical axis."""

    def __init__(self):
        super().__init__("HorizontalReflection", complexity=1.0)

    def apply(self, grid: List[List[int]]) -> List[List[int]]:
        return [list(reversed(row)) for row in grid]


class VerticalReflectionOperator(SymbolicOperator):
    """Vertical flip across horizontal axis."""

    def __init__(self):
        super().__init__("VerticalReflection", complexity=1.0)

    def apply(self, grid: List[List[int]]) -> List[List[int]]:
        return [list(row) for row in reversed(grid)]


class Rotation180Operator(SymbolicOperator):
    """180-degree matrix rotation."""

    def __init__(self):
        super().__init__("Rotation180", complexity=1.1)

    def apply(self, grid: List[List[int]]) -> List[List[int]]:
        return [list(reversed(row)) for row in reversed(grid)]


class SpatialTranslateOperator(SymbolicOperator):
    """Translates non-background objects by (dr, dc)."""

    def __init__(self, dr: int, dc: int):
        super().__init__(f"SpatialTranslate({dr},{dc})", complexity=1.1)
        self.dr = dr
        self.dc = dc

    def apply(self, grid: List[List[int]]) -> List[List[int]]:
        if not grid or not grid[0]:
            return grid
        h, w = len(grid), len(grid[0])
        out = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                if grid[r][c] != 0:
                    nr, nc = r + self.dr, c + self.dc
                    if 0 <= nr < h and 0 <= nc < w:
                        out[nr][nc] = grid[r][c]
        return out


class RegionInfillOperator(SymbolicOperator):
    """Fills enclosed single-cell holes with background surrounding color."""

    def __init__(self, fill_color: int = 2):
        super().__init__(f"RegionInfill({fill_color})", complexity=1.2)
        self.fill_color = fill_color

    def apply(self, grid: List[List[int]]) -> List[List[int]]:
        if not grid or not grid[0]:
            return grid
        h, w = len(grid), len(grid[0])
        out = [list(row) for row in grid]
        for r in range(1, h - 1):
            for c in range(1, w - 1):
                if grid[r][c] == 0:
                    adj = [grid[r - 1][c], grid[r + 1][c], grid[r][c - 1], grid[r][c + 1]]
                    if all(color != 0 for color in adj):
                        out[r][c] = self.fill_color
        return out


class LineExtendOperator(SymbolicOperator):
    """Extends non-zero endpoints horizontally/diagonally."""

    def __init__(self):
        super().__init__("LineExtend", complexity=1.2)

    def apply(self, grid: List[List[int]]) -> List[List[int]]:
        if not grid or not grid[0]:
            return grid
        h, w = len(grid), len(grid[0])
        out = [list(row) for row in grid]
        for r in range(h):
            row_colors = [c for c in grid[r] if c != 0]
            if len(row_colors) == 1:
                color = row_colors[0]
                out[r] = [color] * w
        return out


class SymbolicHypothesis:
    """Represents a candidate rule pipeline of symbolic operators."""

    def __init__(self, operators: List[SymbolicOperator], hyp_id: str = ""):
        self.operators = operators
        self.name = " -> ".join(op.name for op in operators)
        self.hyp_id = hyp_id or f"sym_hyp_{hash(self.name) & 0xffffffff:08x}"
        self.complexity = sum(op.complexity for op in operators)
        self.score: float = 0.0
        self.is_rejected: bool = False
        self.trace_logs: List[Dict[str, Any]] = []

    def execute(self, grid: List[List[int]]) -> List[List[int]]:
        current = [list(row) for row in grid]
        for op in self.operators:
            current = op.apply(current)
        return current

    def evaluate_training_pairs(self, train_pairs: List[Any]) -> float:
        """Evaluates hypothesis consistency across all training pairs."""
        if not train_pairs:
            self.score = 0.0
            self.is_rejected = True
            return 0.0

        matches = 0
        self.trace_logs.clear()

        for idx, pair in enumerate(train_pairs):
            input_grid = pair.input_grid
            expected_output = pair.output_grid
            predicted_output = self.execute(input_grid)

            is_exact = predicted_output == expected_output
            if is_exact:
                matches += 1

            self.trace_logs.append({
                "pair_index": idx,
                "input_shape": (len(input_grid), len(input_grid[0])),
                "expected_shape": (len(expected_output), len(expected_output[0])),
                "predicted_shape": (len(predicted_output), len(predicted_output[0])),
                "exact_match": is_exact,
            })

        consistency_ratio = matches / len(train_pairs)
        # Hypothesis must pass ALL training pairs to be accepted
        if consistency_ratio < 1.0:
            self.is_rejected = True
            self.score = 0.0
        else:
            self.is_rejected = False
            # Simplicity prior: higher complexity slightly penalizes score for tie-breaking
            self.score = 1.0 - (0.01 * self.complexity)

        return self.score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.hyp_id,
            "name": self.name,
            "complexity": round(self.complexity, 3),
            "score": round(self.score, 4),
            "is_rejected": self.is_rejected,
            "operators": [op.to_dict() for op in self.operators],
        }


class SymbolicDAGPlanner:
    """N-depth Acyclic Directed Graph (DAG) search planner for multi-stage symbolic reasoning."""

    def __init__(self, max_depth: int = 4):
        self.max_depth = max_depth

    def search_dag_hypotheses(
        self, train_pairs: List[Any], candidate_operators: List[SymbolicOperator]
    ) -> List[SymbolicHypothesis]:
        """Explores N-depth acyclic operator paths, avoiding state cycles."""
        hypotheses: List[SymbolicHypothesis] = []
        visited_paths: Set[Tuple[str, ...]] = set()

        # Seed queue with 1-op paths
        queue: List[List[SymbolicOperator]] = [[op] for op in candidate_operators]

        while queue:
            path = queue.pop(0)
            path_signature = tuple(op.name for op in path)
            if path_signature in visited_paths:
                continue
            visited_paths.add(path_signature)

            hyp = SymbolicHypothesis(path)
            hyp.evaluate_training_pairs(train_pairs)
            hypotheses.append(hyp)

            # If path achieved 100% exact match consistency on train pairs, don't expand further
            if not hyp.is_rejected and hyp.score > 0.0:
                continue

            # Expand path if below max_depth
            if len(path) < self.max_depth:
                for next_op in candidate_operators:
                    # Cycle prevention 1: Do not repeat exact same operator consecutively unless non-idempotent
                    if path[-1].name == next_op.name and not isinstance(next_op, BoundingBoxCropOperator):
                        continue

                    # Cycle prevention 2: Check if next_op creates a grid state cycle on pair 0
                    if train_pairs:
                        in_g0 = train_pairs[0].input_grid
                        grid_states = [in_g0]
                        curr = [list(r) for r in in_g0]
                        for op in path:
                            curr = op.apply(curr)
                            grid_states.append(curr)

                        next_curr = next_op.apply(curr)
                        # If next state is identical to any prior state in path, prune cycle
                        if any(next_curr == prev for prev in grid_states):
                            continue

                    queue.append(path + [next_op])

        return hypotheses


class SymbolicHypothesisGraph:
    """Symbolic Hypothesis Graph for generating, scoring, and executing general ARC rules via N-depth DAG search."""

    def __init__(self):
        self.hypotheses: List[SymbolicHypothesis] = []
        self.solved_trace: Optional[Dict[str, Any]] = None

    def _generate_candidate_operators(self, train_pairs: List[Any]) -> List[SymbolicOperator]:
        candidates: List[SymbolicOperator] = [
            IdentityOperator(),
            BoundingBoxCropOperator(),
            BlockScaleOperator(2),
            TileReplicationOperator(2, 2),
            HorizontalReflectionOperator(),
            VerticalReflectionOperator(),
            Rotation180Operator(),
            LineExtendOperator(),
        ]

        # Extract color mappings from train pairs
        color_maps: Dict[int, int] = {}
        for pair in train_pairs:
            in_g, out_g = pair.input_grid, pair.output_grid
            if len(in_g) == len(out_g) and len(in_g[0]) == len(out_g[0]):
                for r in range(len(in_g)):
                    for c in range(len(in_g[0])):
                        if in_g[r][c] != out_g[r][c]:
                            color_maps[in_g[r][c]] = out_g[r][c]

            in_colors = set(c for r in in_g for c in r if c != 0)
            out_colors = set(c for r in out_g for c in r if c != 0)
            diff_in = in_colors - out_colors
            diff_out = out_colors - in_colors
            if len(diff_in) == 1 and len(diff_out) == 1:
                color_maps[list(diff_in)[0]] = list(diff_out)[0]

        if color_maps:
            candidates.append(ColorMapOperator(color_maps))


        # Spatial translation candidates
        for pair in train_pairs:
            in_g, out_g = pair.input_grid, pair.output_grid
            if len(in_g) == len(out_g) and len(in_g[0]) == len(out_g[0]):
                in_nz = [(r, c) for r in range(len(in_g)) for c in range(len(in_g[0])) if in_g[r][c] != 0]
                out_nz = [(r, c) for r in range(len(out_g)) for c in range(len(out_g[0])) if out_g[r][c] != 0]
                if in_nz and out_nz:
                    dr = out_nz[0][0] - in_nz[0][0]
                    dc = out_nz[0][1] - in_nz[0][1]
                    if dr != 0 or dc != 0:
                        candidates.append(SpatialTranslateOperator(dr, dc))

        # Region infill candidates
        for fill in [2, 3, 8]:
            candidates.append(RegionInfillOperator(fill))

        return candidates

    def build_and_evaluate(self, train_pairs: List[Any], max_depth: int = 4) -> SymbolicHypothesis:
        """Builds symbolic hypothesis graph, performs N-depth DAG search, and returns optimal consistent hypothesis."""
        ops = self._generate_candidate_operators(train_pairs)
        planner = SymbolicDAGPlanner(max_depth=max_depth)
        self.hypotheses = planner.search_dag_hypotheses(train_pairs, ops)

        valid_hyps = [h for h in self.hypotheses if not h.is_rejected]
        if valid_hyps:
            valid_hyps.sort(key=lambda h: h.score, reverse=True)
            best_hyp = valid_hyps[0]
        else:
            best_hyp = SymbolicHypothesis([IdentityOperator()])
            best_hyp.evaluate_training_pairs(train_pairs)

        self.solved_trace = {
            "best_hypothesis": best_hyp.to_dict(),
            "total_hypotheses_evaluated": len(self.hypotheses),
            "valid_hypotheses_count": len(valid_hyps),
            "train_pairs_count": len(train_pairs),
            "dag_depth": len(best_hyp.operators),
        }
        return best_hyp
