"""Symbolic Hypothesis Graph Reasoning Engine, N-depth DAG Planner & Parameter Synthesis Engine for ARC-AGI tasks."""

from typing import List, Dict, Tuple, Optional, Any, Set
import copy
from arc_explorer.object_perception import ObjectPerceptionEngine, ObjectCompositionEngine, ConnectedObject
from arc_explorer.spatial_relation import (
    align_to_anchor,
    place_relative,
    place_left_of,
    place_right_of,
    place_above,
    place_below,
    stack_objects,
    sort_objects_by_area,
    sort_objects_by_centroid,
    compute_relative_displacement,
)
from arc_explorer.symmetry_engine import (
    detect_mirror_symmetry,
    apply_mirror_symmetry,
    detect_rotational_symmetry,
    reflect_4fold_symmetry,
    detect_periodic_lattice,
    tessellate_lattice,
    complete_missing_region_via_symmetry,
)







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
    """Block scaling expansion by factor scale_factor."""

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
    """Matrix tile repeat (repeat_r x repeat_c)."""

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


class RotationOperator(SymbolicOperator):
    """Matrix rotation for angle in [90, 180, 270] degrees."""

    def __init__(self, angle: int = 90):
        super().__init__(f"Rotation{angle}", complexity=1.0 if angle == 180 else 1.1)
        self.angle = angle

    def apply(self, grid: List[List[int]]) -> List[List[int]]:
        if not grid or not grid[0]:
            return grid
        if self.angle == 90:
            # 90 deg clockwise
            return [list(row) for row in zip(*reversed(grid))]
        elif self.angle == 180:
            # 180 deg rotation
            return [list(reversed(row)) for row in reversed(grid)]
        elif self.angle == 270:
            # 270 deg clockwise (90 deg counter-clockwise)
            return [list(row) for row in reversed(list(zip(*grid)))]
        return [list(r) for r in grid]


class Rotation180Operator(RotationOperator):
    """Backward-compatible 180-degree matrix rotation."""

    def __init__(self):
        super().__init__(180)
        self.name = "Rotation180"


class ReflectionOperator(SymbolicOperator):
    """Axis reflection operator for axis in ['horizontal', 'vertical', 'main_diagonal', 'anti_diagonal']."""

    def __init__(self, axis: str = "horizontal"):
        super().__init__(f"Reflection({axis})", complexity=1.0)
        self.axis = axis

    def apply(self, grid: List[List[int]]) -> List[List[int]]:
        if not grid or not grid[0]:
            return grid
        if self.axis == "horizontal":
            return [list(reversed(row)) for row in grid]
        elif self.axis == "vertical":
            return [list(row) for row in reversed(grid)]
        elif self.axis == "main_diagonal":
            return [list(row) for row in zip(*grid)]
        elif self.axis == "anti_diagonal":
            return [list(reversed(r)) for r in reversed(list(zip(*grid)))]
        return [list(r) for r in grid]



class HorizontalReflectionOperator(ReflectionOperator):
    """Backward-compatible horizontal mirror reflection."""

    def __init__(self):
        super().__init__("horizontal")
        self.name = "HorizontalReflection"


class VerticalReflectionOperator(ReflectionOperator):
    """Backward-compatible vertical flip."""

    def __init__(self):
        super().__init__("vertical")
        self.name = "VerticalReflection"


class ObjectMaskOperator(SymbolicOperator):
    """Applies object mask replacement for target_color -> fill_color."""

    def __init__(self, target_color: int, fill_color: int):
        super().__init__(f"ObjectMask({target_color}->{fill_color})", complexity=1.1)
        self.target_color = target_color
        self.fill_color = fill_color

    def apply(self, grid: List[List[int]]) -> List[List[int]]:
        return [[self.fill_color if cell == self.target_color else cell for cell in row] for row in grid]


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


class RaycastLineExtensionOperator(SymbolicOperator):
    """Generalized ray-casting operator that detects coloured line/ray seeds
    and extends them horizontally, vertically, or diagonally until a grid
    boundary or blocking object is reached.

    Supports both forward (unidirectional) and bidirectional extension.
    All parameters (ray_color, directions, stop condition) are inferred
    dynamically from training pairs — nothing is hard-coded.
    """

    # The 8 cardinal and diagonal unit vectors.
    ALL_DIRECTIONS = [
        (-1, 0), (1, 0), (0, -1), (0, 1),
        (-1, -1), (-1, 1), (1, -1), (1, 1),
    ]

    def __init__(
        self,
        ray_color: int,
        directions: List[Tuple[int, int]],
        bidirectional: bool = False,
        stop_colors: Optional[Set[int]] = None,
        background: int = 0,
    ):
        dir_labels = {
            (-1, 0): "N", (1, 0): "S", (0, -1): "W", (0, 1): "E",
            (-1, -1): "NW", (-1, 1): "NE", (1, -1): "SW", (1, 1): "SE",
        }
        dir_tag = "+".join(dir_labels.get(d, str(d)) for d in directions)
        bidir_tag = "bidir" if bidirectional else "unidir"
        super().__init__(
            f"RaycastLineExtension(c={ray_color},{dir_tag},{bidir_tag})",
            complexity=1.3,
        )
        self.ray_color = ray_color
        self.directions = list(directions)
        self.bidirectional = bidirectional
        self.stop_colors: Set[int] = stop_colors if stop_colors is not None else set()
        self.background = background

    # ── grid transformation ──────────────────────────────────────────

    def apply(self, grid: List[List[int]]) -> List[List[int]]:
        if not grid or not grid[0]:
            return grid
        h, w = len(grid), len(grid[0])
        out = [list(row) for row in grid]

        # Collect original seed positions (cells already carrying ray_color)
        seeds: Set[Tuple[int, int]] = set()
        for r in range(h):
            for c in range(w):
                if grid[r][c] == self.ray_color:
                    seeds.add((r, c))

        if not seeds:
            return out

        # Build effective direction list (add opposites when bidirectional)
        effective_dirs = list(self.directions)
        if self.bidirectional:
            for dr, dc in self.directions:
                opp = (-dr, -dc)
                if opp not in effective_dirs:
                    effective_dirs.append(opp)

        for sr, sc in seeds:
            for dr, dc in effective_dirs:
                # Only extend from endpoint seeds in this direction —
                # skip interior seeds whose neighbour is also a seed.
                if (sr + dr, sc + dc) in seeds:
                    continue

                cr, cc = sr + dr, sc + dc
                while 0 <= cr < h and 0 <= cc < w:
                    cell = out[cr][cc]
                    if cell == self.background:
                        out[cr][cc] = self.ray_color
                    elif cell == self.ray_color:
                        pass  # already painted — continue through
                    else:
                        break  # blocked by any other colour
                    cr += dr
                    cc += dc

        return out

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "ray_color": self.ray_color,
            "directions": self.directions,
            "bidirectional": self.bidirectional,
            "stop_colors": sorted(self.stop_colors),
        })
        return base

    # ── parameter inference from training pairs ──────────────────────

    @staticmethod
    def infer_from_pairs(
        train_pairs: List[Any], background: int = 0
    ) -> List["RaycastLineExtensionOperator"]:
        """Analyses all training pairs to infer ray colour, extension
        directions, bidirectionality, and stop colours.  Returns a
        (possibly empty) list of candidate operators."""
        from collections import Counter

        ALL_DIRS = RaycastLineExtensionOperator.ALL_DIRECTIONS

        direction_votes: Counter = Counter()
        color_votes: Counter = Counter()
        stop_colors_found: Set[int] = set()
        opposite_evidence = 0

        for pair in train_pairs:
            in_g, out_g = pair.input_grid, pair.output_grid
            if not in_g or not in_g[0]:
                continue
            if len(in_g) != len(out_g) or len(in_g[0]) != len(out_g[0]):
                continue
            h, w = len(in_g), len(in_g[0])

            # Seeds: non-background cells in the input grid
            seeds_by_color: Dict[int, Set[Tuple[int, int]]] = {}
            for r in range(h):
                for c in range(w):
                    if in_g[r][c] != background:
                        seeds_by_color.setdefault(in_g[r][c], set()).add((r, c))

            pair_dirs_per_color: Dict[int, Set[Tuple[int, int]]] = {}

            for color, seed_set in seeds_by_color.items():
                for sr, sc in seed_set:
                    for dr, dc in ALL_DIRS:
                        # Only trace from endpoint seeds
                        if (sr + dr, sc + dc) in seed_set:
                            continue

                        # Walk forward and count newly-painted cells
                        extended = 0
                        cr, cc = sr + dr, sc + dc
                        while 0 <= cr < h and 0 <= cc < w:
                            if in_g[cr][cc] == background and out_g[cr][cc] == color:
                                extended += 1
                            elif out_g[cr][cc] == color:
                                pass  # seed or already-painted
                            else:
                                break
                            cr, cc = cr + dr, cc + dc

                        if extended > 0:
                            direction_votes[(dr, dc)] += extended
                            color_votes[color] += extended
                            pair_dirs_per_color.setdefault(color, set()).add((dr, dc))

                            # Check stop colour (the cell that halted the walk)
                            if 0 <= cr < h and 0 <= cc < w:
                                blocker = out_g[cr][cc]
                                if blocker != background and blocker != color:
                                    stop_colors_found.add(blocker)

            # Detect bidirectionality within this pair
            for color, dirs in pair_dirs_per_color.items():
                for dr, dc in dirs:
                    if (-dr, -dc) in dirs:
                        opposite_evidence += 1

        if not color_votes:
            return []

        ray_color = color_votes.most_common(1)[0][0]
        active_dirs = [d for d in ALL_DIRS if direction_votes[d] > 0]
        bidirectional = opposite_evidence > 0

        if bidirectional:
            # Deduplicate opposite pairs — keep canonical direction only
            canonical: List[Tuple[int, int]] = []
            seen: Set[Tuple[int, int]] = set()
            for d in active_dirs:
                if d not in seen:
                    canonical.append(d)
                    seen.add(d)
                    seen.add((-d[0], -d[1]))
            active_dirs = canonical

        if not active_dirs:
            return []

        return [
            RaycastLineExtensionOperator(
                ray_color=ray_color,
                directions=active_dirs,
                bidirectional=bidirectional,
                stop_colors=stop_colors_found,
                background=background,
            )
        ]


class GravityDropOperator(SymbolicOperator):
    """Simulates gravity: coloured cells fall/slide in a cardinal direction
    until they rest against the grid boundary or a fixed obstacle.

    Handles per-colour selectivity (some colours can be fixed while
    others fall) and preserves relative order of falling cells.
    All parameters are inferred dynamically from training pairs.
    """

    CARDINAL_DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    def __init__(
        self,
        direction: Tuple[int, int],
        affected_colors: Optional[Set[int]] = None,
        background: int = 0,
    ):
        dir_labels = {
            (-1, 0): "up", (1, 0): "down",
            (0, -1): "left", (0, 1): "right",
        }
        dir_name = dir_labels.get(direction, str(direction))
        colors_tag = (
            "all"
            if affected_colors is None
            else ",".join(str(c) for c in sorted(affected_colors))
        )
        super().__init__(
            f"GravityDrop({dir_name},colors={colors_tag})", complexity=1.3,
        )
        self.direction = direction
        self.affected_colors = affected_colors  # None \u2192 all non-background
        self.background = background

    # \u2500\u2500 helpers \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

    def _is_affected(self, color: int) -> bool:
        if color == self.background:
            return False
        if self.affected_colors is None:
            return True
        return color in self.affected_colors

    def _drop_line(self, line: List[int], forward: bool) -> List[int]:
        """Gravity-compact a 1-D line.

        *forward=True*  \u2192 cells fall toward higher indices (down / right).
        *forward=False* \u2192 cells fall toward lower indices  (up / left).

        Fixed (non-affected, non-background) cells act as obstacles;
        the line is split into independent segments between them and
        each segment is compacted separately.
        """
        n = len(line)
        result = list(line)

        # Identify fixed obstacle positions
        fixed_positions = sorted(
            i for i in range(n)
            if result[i] != self.background and not self._is_affected(result[i])
        )

        # Build segments between fixed positions
        segments: List[Tuple[int, int]] = []  # (start, exclusive_end)
        prev = 0
        for fp in fixed_positions:
            if prev < fp:
                segments.append((prev, fp))
            prev = fp + 1
        if prev < n:
            segments.append((prev, n))

        for start, end in segments:
            affected: List[int] = []
            for i in range(start, end):
                if self._is_affected(result[i]):
                    affected.append(result[i])
                    result[i] = self.background

            if not affected:
                continue

            if forward:
                slot = end - 1
                for cell in reversed(affected):
                    while slot >= start and result[slot] != self.background:
                        slot -= 1
                    if slot >= start:
                        result[slot] = cell
                        slot -= 1
            else:
                slot = start
                for cell in affected:
                    while slot < end and result[slot] != self.background:
                        slot += 1
                    if slot < end:
                        result[slot] = cell
                        slot += 1

        return result

    # \u2500\u2500 grid transformation \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

    def apply(self, grid: List[List[int]]) -> List[List[int]]:
        if not grid or not grid[0]:
            return grid
        h, w = len(grid), len(grid[0])
        out = [list(row) for row in grid]
        dr, dc = self.direction

        if dc == 0:
            # Vertical gravity \u2014 process each column
            for c in range(w):
                col = [out[r][c] for r in range(h)]
                new_col = self._drop_line(col, forward=(dr > 0))
                for r in range(h):
                    out[r][c] = new_col[r]
        else:
            # Horizontal gravity \u2014 process each row
            for r in range(h):
                out[r] = self._drop_line(list(out[r]), forward=(dc > 0))

        return out

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "direction": self.direction,
            "affected_colors": (
                sorted(self.affected_colors) if self.affected_colors else None
            ),
        })
        return base

    # \u2500\u2500 parameter inference from training pairs \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

    @staticmethod
    def infer_from_pairs(
        train_pairs: List[Any], background: int = 0,
    ) -> List["GravityDropOperator"]:
        """Tries all four cardinal directions.  For each direction it
        first tests with *all* colours falling, then tries leaving each
        colour fixed in turn.  Returns every configuration that
        reproduces all training outputs exactly."""
        candidates: List["GravityDropOperator"] = []

        for pair in train_pairs:
            in_g, out_g = pair.input_grid, pair.output_grid
            if not in_g or not in_g[0]:
                return []
            if len(in_g) != len(out_g) or len(in_g[0]) != len(out_g[0]):
                return []
            # Gravity only rearranges cells \u2014 colour multiset must match
            if sorted(c for r in in_g for c in r) != sorted(
                c for r in out_g for c in r
            ):
                return []

        # Collect all non-background colours across every pair
        all_colors: Set[int] = set()
        for pair in train_pairs:
            for row in pair.input_grid:
                for c in row:
                    if c != background:
                        all_colors.add(c)

        for direction in GravityDropOperator.CARDINAL_DIRECTIONS:
            # Try 1: all colours fall
            test_all = GravityDropOperator(direction, None, background)
            if all(
                test_all.apply(p.input_grid) == p.output_grid
                for p in train_pairs
            ):
                candidates.append(test_all)
                continue  # no need to try partial for this direction

            # Try 2: one colour is fixed, the rest fall
            for fixed in all_colors:
                affected = all_colors - {fixed}
                if not affected:
                    continue
                test_partial = GravityDropOperator(
                    direction, affected, background,
                )
                if all(
                    test_partial.apply(p.input_grid) == p.output_grid
                    for p in train_pairs
                ):
                    candidates.append(test_partial)
                    break  # found working config for this direction

        return candidates


class FractalTilingOperator(SymbolicOperator):
    """Self-referential fractal tiling: the input grid serves as both
    the pattern *and* the placement map.

    For an N\u00d7M input, the output is (N\u00b7N)\u00d7(M\u00b7M).  Each non-zero cell
    in the input is replaced by a full copy of the input pattern;
    each zero cell becomes an all-zero N\u00d7M block.

    Solves ARC task families like 007bbfb7.
    """

    def __init__(self):
        super().__init__("FractalTiling", complexity=1.2)

    def apply(self, grid: List[List[int]]) -> List[List[int]]:
        if not grid or not grid[0]:
            return grid
        h, w = len(grid), len(grid[0])
        out_h, out_w = h * h, w * w
        out = [[0] * out_w for _ in range(out_h)]

        for br in range(h):
            for bc in range(w):
                if grid[br][bc] != 0:
                    # Stamp the full input pattern into this block
                    r_off = br * h
                    c_off = bc * w
                    for r in range(h):
                        for c in range(w):
                            out[r_off + r][c_off + c] = grid[r][c]

        return out

    @staticmethod
    def infer_from_pairs(
        train_pairs: List[Any], background: int = 0,
    ) -> List["FractalTilingOperator"]:
        """Detects the dimension-squaring signature (N\u2192N\u00b2, M\u2192M\u00b2)
        and verifies that fractal tiling reproduces all outputs."""
        op = FractalTilingOperator()
        for pair in train_pairs:
            in_g, out_g = pair.input_grid, pair.output_grid
            if not in_g or not in_g[0]:
                return []
            h_in, w_in = len(in_g), len(in_g[0])
            h_out, w_out = len(out_g), len(out_g[0])
            # Dimension signature: output must be exactly input\u00b2
            if h_out != h_in * h_in or w_out != w_in * w_in:
                return []
            if op.apply(in_g) != out_g:
                return []
        return [op]


class ObjectTransformOperator(SymbolicOperator):
    """Transforms isolated connected component objects filtered by color/size/position."""

    def __init__(self, target_color: int, new_color: int, filter_type: str = "all", dr: int = 0, dc: int = 0):
        super().__init__(f"ObjectTransform({target_color}->{new_color},{filter_type})", complexity=1.2)
        self.target_color = target_color
        self.new_color = new_color
        self.filter_type = filter_type
        self.dr = dr
        self.dc = dc

    def apply(self, grid: List[List[int]]) -> List[List[int]]:
        if not grid or not grid[0]:
            return grid
        h, w = len(grid), len(grid[0])
        objects = ObjectPerceptionEngine.detect_objects(grid)
        if not objects:
            return [list(r) for r in grid]

        target_objs = ObjectPerceptionEngine.filter_objects(
            objects, color=self.target_color, position_filter=self.filter_type if self.filter_type != "all" else None
        )
        target_ids = set(o.object_id for o in target_objs)

        transformed_objects: List[ConnectedObject] = []
        for obj in objects:
            if obj.object_id in target_ids:
                recolored = ObjectCompositionEngine.recolor_object(obj, self.new_color)
                if self.dr != 0 or self.dc != 0:
                    recolored = ObjectCompositionEngine.translate_object(recolored, self.dr, self.dc)
                transformed_objects.append(recolored)
            else:
                transformed_objects.append(obj)

        return ObjectCompositionEngine.render_canvas(transformed_objects, (h, w))


class AlignToAnchorOperator(SymbolicOperator):
    """Aligns target color objects to reference color anchor objects along specified edge."""

    def __init__(self, target_color: int, reference_color: int, edge: str = "top"):
        super().__init__(f"AlignToAnchor({target_color}->{reference_color},{edge})", complexity=1.3)
        self.target_color = target_color
        self.reference_color = reference_color
        self.edge = edge

    def apply(self, grid: List[List[int]]) -> List[List[int]]:
        if not grid or not grid[0]:
            return grid
        h, w = len(grid), len(grid[0])
        objects = ObjectPerceptionEngine.detect_objects(grid)
        targets = [o for o in objects if o.primary_color == self.target_color]
        refs = [o for o in objects if o.primary_color == self.reference_color]
        if not targets or not refs:
            return [list(r) for r in grid]

        ref_obj = refs[0]
        out_objects: List[ConnectedObject] = []
        for obj in objects:
            if obj.primary_color == self.target_color:
                aligned = align_to_anchor(obj, ref_obj, edge=self.edge)
                out_objects.append(aligned)
            else:
                out_objects.append(obj)

        return ObjectCompositionEngine.render_canvas(out_objects, (h, w))


class PlaceRelativeOperator(SymbolicOperator):
    """Positions target color objects relative to reference color anchor objects."""

    def __init__(self, target_color: int, reference_color: int, side: str = "right", spacing: int = 1):
        super().__init__(f"PlaceRelative({target_color}->{reference_color},{side})", complexity=1.3)
        self.target_color = target_color
        self.reference_color = reference_color
        self.side = side
        self.spacing = spacing

    def apply(self, grid: List[List[int]]) -> List[List[int]]:
        if not grid or not grid[0]:
            return grid
        h, w = len(grid), len(grid[0])
        objects = ObjectPerceptionEngine.detect_objects(grid)
        targets = [o for o in objects if o.primary_color == self.target_color]
        refs = [o for o in objects if o.primary_color == self.reference_color]
        if not targets or not refs:
            return [list(r) for r in grid]

        ref_obj = refs[0]
        out_objects: List[ConnectedObject] = []
        for obj in objects:
            if obj.primary_color == self.target_color:
                placed = place_relative(obj, ref_obj, side=self.side, spacing=self.spacing)
                out_objects.append(placed)
            else:
                out_objects.append(obj)

        return ObjectCompositionEngine.render_canvas(out_objects, (h, w))


class StackObjectsOperator(SymbolicOperator):
    """Stacks objects in vertical or horizontal direction."""

    def __init__(self, direction: str = "vertical", spacing: int = 1):
        super().__init__(f"StackObjects({direction})", complexity=1.4)
        self.direction = direction
        self.spacing = spacing

    def apply(self, grid: List[List[int]]) -> List[List[int]]:
        if not grid or not grid[0]:
            return grid
        h, w = len(grid), len(grid[0])
        objects = ObjectPerceptionEngine.detect_objects(grid)
        if not objects:
            return [list(r) for r in grid]

        sorted_objs = sort_objects_by_area(objects, reverse=True)
        stacked = stack_objects(sorted_objs, direction=self.direction, spacing=self.spacing)
        return ObjectCompositionEngine.render_canvas(stacked, (h, w))


class MirrorSymmetryOperator(SymbolicOperator):
    """Applies horizontal or vertical mirror symmetry completion."""

    def __init__(self, axis: str = "horizontal"):
        super().__init__(f"MirrorSymmetry({axis})", complexity=1.1)
        self.axis = axis

    def apply(self, grid: List[List[int]]) -> List[List[int]]:
        return apply_mirror_symmetry(grid, axis=self.axis)


class Rotational4FoldSymmetryOperator(SymbolicOperator):
    """Applies 4-fold rotational symmetry completion across 4 quadrants."""

    def __init__(self):
        super().__init__("Rotational4FoldSymmetry", complexity=1.2)

    def apply(self, grid: List[List[int]]) -> List[List[int]]:
        return reflect_4fold_symmetry(grid)


class CompleteSymmetryOperator(SymbolicOperator):
    """Completes missing 0-valued regions using fused mirror and rotational symmetry."""

    def __init__(self):
        super().__init__("CompleteSymmetry", complexity=1.2)

    def apply(self, grid: List[List[int]]) -> List[List[int]]:
        return complete_missing_region_via_symmetry(grid)


class TessellateLatticeOperator(SymbolicOperator):
    """Detects repeating unit cell and tessellates periodic lattice pattern."""

    def __init__(self):
        super().__init__("TessellateLattice", complexity=1.3)

    def apply(self, grid: List[List[int]]) -> List[List[int]]:
        if not grid or not grid[0]:
            return grid
        h, w = len(grid), len(grid[0])
        cell_dims = detect_periodic_lattice(grid)
        if not cell_dims:
            return [list(r) for r in grid]

        ch, cw = cell_dims
        unit_cell = [grid[r][:cw] for r in range(ch)]
        return tessellate_lattice(unit_cell, (h, w))


class ParameterSynthesisEngine:


    """Dynamic Parameter Synthesis Engine for ARC transformation operators."""

    @staticmethod
    def infer_parameters(train_pairs: List[Any]) -> List[SymbolicOperator]:
        """Dynamically infers candidate parameters from train pairs and ranks them by confidence."""
        candidates: List[SymbolicOperator] = [
            IdentityOperator(),
            BoundingBoxCropOperator(),
            LineExtendOperator(),
        ]

        if not train_pairs:
            return candidates

        # 1. Infer Grid Dimensions & Scale Factors
        for pair in train_pairs:
            in_g, out_g = pair.input_grid, pair.output_grid
            h_in, w_in = len(in_g), len(in_g[0])
            h_out, w_out = len(out_g), len(out_g[0])

            if h_out > 0 and w_out > 0 and h_in > 0 and w_in > 0:
                if h_out % h_in == 0 and w_out % w_in == 0:
                    scale_r = h_out // h_in
                    scale_c = w_out // w_in
                    if scale_r == scale_c and scale_r in [2, 3]:
                        candidates.append(BlockScaleOperator(scale_r))
                    candidates.append(TileReplicationOperator(scale_r, scale_c))

        # 2. Infer Rotation Angles & Reflection Axes
        candidates.append(Rotation180Operator())
        for angle in [90, 270]:
            candidates.append(RotationOperator(angle))
        candidates.append(HorizontalReflectionOperator())
        candidates.append(VerticalReflectionOperator())
        for axis in ["main_diagonal", "anti_diagonal"]:
            candidates.append(ReflectionOperator(axis))

        # 3. Infer Color Substitution Maps & Object Component Transforms
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
            for k, v in color_maps.items():
                candidates.append(ObjectMaskOperator(k, v))
                for filter_t in ["all", "largest", "smallest"]:
                    candidates.append(ObjectTransformOperator(k, v, filter_type=filter_t))

        # 4. Infer Spatial Translation Vectors
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

        # 5. Infer Region Infill Colors & Spatial Relational Operators
        for fill in [2, 3, 8]:
            candidates.append(RegionInfillOperator(fill))

        for dir_t in ["vertical", "horizontal"]:
            candidates.append(StackObjectsOperator(direction=dir_t))

        # Only generate relational operators for colors actually present in train_pairs
        present_colors = set(c for pair in train_pairs for r in pair.input_grid for c in r if c != 0)
        for pair in train_pairs:
            for r in pair.output_grid:
                for c in r:
                    if c != 0:
                        present_colors.add(c)

        for t_c in present_colors:
            for r_c in present_colors:
                if t_c != r_c:
                    for edge_t in ["top", "bottom", "left", "right", "center"]:
                        candidates.append(AlignToAnchorOperator(t_c, r_c, edge=edge_t))
                    for side_t in ["left", "right", "above", "below"]:
                        candidates.append(PlaceRelativeOperator(t_c, r_c, side=side_t))

        # 6. Global Symmetry Group & Pattern Lattice Engine Operators
        candidates.append(MirrorSymmetryOperator("horizontal"))
        candidates.append(MirrorSymmetryOperator("vertical"))
        candidates.append(Rotational4FoldSymmetryOperator())
        candidates.append(CompleteSymmetryOperator())
        candidates.append(TessellateLatticeOperator())

        # 7. Raycast Line Extension
        raycast_candidates = RaycastLineExtensionOperator.infer_from_pairs(train_pairs)
        candidates.extend(raycast_candidates)

        # 8. Gravity Drop
        gravity_candidates = GravityDropOperator.infer_from_pairs(train_pairs)
        candidates.extend(gravity_candidates)

        # 9. Fractal Tiling
        fractal_candidates = FractalTilingOperator.infer_from_pairs(train_pairs)
        candidates.extend(fractal_candidates)

        # Deduplicate candidates by name
        unique_candidates: Dict[str, SymbolicOperator] = {}
        for op in candidates:
            if op.name not in unique_candidates:
                unique_candidates[op.name] = op

        res = list(unique_candidates.values())
        res.sort(key=lambda op: op.complexity)
        return res



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

    def __init__(self, max_depth: int = 4, max_hypotheses: int = 5000, time_budget_sec: float = 3.0):
        self.max_depth = max_depth
        self.max_hypotheses = max_hypotheses
        self.time_budget_sec = time_budget_sec



    def search_dag_hypotheses(
        self, train_pairs: List[Any], candidate_operators: List[SymbolicOperator]
    ) -> List[SymbolicHypothesis]:
        """Explores N-depth acyclic operator paths, avoiding state cycles and respecting search budget limits."""
        import time
        start_time = time.time()
        hypotheses: List[SymbolicHypothesis] = []
        visited_paths: Set[Tuple[str, ...]] = set()

        # Seed queue with 1-op paths
        queue: List[List[SymbolicOperator]] = [[op] for op in candidate_operators]

        while queue and len(hypotheses) < self.max_hypotheses:
            if time.time() - start_time > self.time_budget_sec:
                break

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
                    if time.time() - start_time > self.time_budget_sec:
                        break

                    # Cycle prevention 1: Do not repeat exact same operator consecutively unless non-idempotent
                    if path[-1].name == next_op.name and not isinstance(next_op, BoundingBoxCropOperator):
                        continue

                    # Cycle prevention 2: Check if next_op creates a grid state cycle or has zero effect (no-op)
                    if train_pairs:
                        in_g0 = train_pairs[0].input_grid
                        grid_states = [in_g0]
                        curr = [list(r) for r in in_g0]
                        for op in path:
                            curr = op.apply(curr)
                            grid_states.append(curr)

                        next_curr = next_op.apply(curr)
                        # If next state is identical to current state or any prior state in path, prune
                        if next_curr == curr or any(next_curr == prev for prev in grid_states):
                            continue


                    queue.append(path + [next_op])

        return hypotheses



class SymbolicHypothesisGraph:
    """Symbolic Hypothesis Graph for generating, scoring, and executing general ARC rules via N-depth DAG search & Parameter Synthesis."""

    def __init__(self):
        self.hypotheses: List[SymbolicHypothesis] = []
        self.solved_trace: Optional[Dict[str, Any]] = None

    def _generate_candidate_operators(self, train_pairs: List[Any]) -> List[SymbolicOperator]:
        return ParameterSynthesisEngine.infer_parameters(train_pairs)

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
