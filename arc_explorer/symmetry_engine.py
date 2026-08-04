"""Global Symmetry Group & Pattern Lattice Engine for ARC-AGI tasks."""

from typing import List, Dict, Tuple, Optional, Any


def detect_mirror_symmetry(grid: List[List[int]]) -> Dict[str, bool]:
    """Detects horizontal and vertical mirror symmetry in a 2D grid matrix."""
    if not grid or not grid[0]:
        return {"horizontal": False, "vertical": False}

    h, w = len(grid), len(grid[0])
    h_sym = True
    v_sym = True

    # Horizontal mirror (left-right reflection)
    for r in range(h):
        for c in range(w // 2):
            if grid[r][c] != grid[r][w - 1 - c]:
                h_sym = False
                break

    # Vertical mirror (top-bottom reflection)
    for r in range(h // 2):
        for c in range(w):
            if grid[r][c] != grid[h - 1 - r][c]:
                v_sym = False
                break

    return {"horizontal": h_sym, "vertical": v_sym}


def apply_mirror_symmetry(grid: List[List[int]], axis: str = "horizontal") -> List[List[int]]:
    """Applies horizontal or vertical mirror completion across a 2D grid matrix."""
    if not grid or not grid[0]:
        return grid
    h, w = len(grid), len(grid[0])
    out = [list(r) for r in grid]

    if axis == "horizontal":
        for r in range(h):
            for c in range(w // 2):
                val = grid[r][c] if grid[r][c] != 0 else grid[r][w - 1 - c]
                out[r][c] = val
                out[r][w - 1 - c] = val
    elif axis == "vertical":
        for r in range(h // 2):
            for c in range(w):
                val = grid[r][c] if grid[r][c] != 0 else grid[h - 1 - r][c]
                out[r][c] = val
                out[h - 1 - r][c] = val

    return out


def detect_rotational_symmetry(grid: List[List[int]]) -> Dict[int, bool]:
    """Detects 90, 180, and 270 degree rotational symmetry in a square or rectangular grid."""
    if not grid or not grid[0]:
        return {90: False, 180: False, 270: False}

    h, w = len(grid), len(grid[0])
    is_square = (h == w)

    r180 = [list(reversed(row)) for row in reversed(grid)]
    sym180 = (grid == r180)

    sym90 = False
    sym270 = False

    if is_square:
        r90 = [list(row) for row in zip(*reversed(grid))]
        sym90 = (grid == r90)
        r270 = [list(row) for row in reversed(list(zip(*grid)))]
        sym270 = (grid == r270)

    return {90: sym90, 180: sym180, 270: sym270}


def reflect_4fold_symmetry(grid: List[List[int]]) -> List[List[int]]:
    """Applies 4-fold rotational symmetry completion across 4 quadrants."""
    if not grid or not grid[0]:
        return grid
    h, w = len(grid), len(grid[0])
    out = [list(r) for r in grid]

    for r in range(h):
        for c in range(w):
            if out[r][c] == 0:
                candidates = [
                    grid[r][w - 1 - c],
                    grid[h - 1 - r][c],
                    grid[h - 1 - r][w - 1 - c]
                ]
                if h == w:
                    candidates.append(grid[c][r])
                    candidates.append(grid[w - 1 - c][h - 1 - r])
                non_zero = [v for v in candidates if v != 0]
                if non_zero:
                    out[r][c] = non_zero[0]

    return out


def detect_periodic_lattice(grid: List[List[int]]) -> Optional[Tuple[int, int]]:
    """Detects repeating unit cell dimensions (cell_h, cell_w) in a periodic lattice."""
    if not grid or not grid[0]:
        return None
    h, w = len(grid), len(grid[0])

    for ch in range(1, h // 2 + 1):
        for cw in range(1, w // 2 + 1):
            if h % ch == 0 and w % cw == 0:
                unit_cell = [grid[r][:cw] for r in range(ch)]
                match = True
                for r in range(h):
                    for c in range(w):
                        if grid[r][c] != 0 and grid[r][c] != unit_cell[r % ch][c % cw]:
                            match = False
                            break
                    if not match:
                        break
                if match:
                    return (ch, cw)
    return None


def tessellate_lattice(unit_cell: List[List[int]], canvas_shape: Tuple[int, int]) -> List[List[int]]:
    """Tessellates a unit cell pattern across canvas_shape."""
    if not unit_cell or not unit_cell[0]:
        return []
    h, w = canvas_shape
    ch, cw = len(unit_cell), len(unit_cell[0])
    return [[unit_cell[r % ch][c % cw] for c in range(w)] for r in range(h)]


def complete_missing_region_via_symmetry(grid: List[List[int]], background_color: int = 0) -> List[List[int]]:
    """Completes missing 0-valued regions by fusing mirror and rotational symmetry partners."""
    if not grid or not grid[0]:
        return grid

    # 1. Apply Mirror Symmetry
    out = apply_mirror_symmetry(grid, axis="horizontal")
    out = apply_mirror_symmetry(out, axis="vertical")

    # 2. Apply 4-fold Rotational Symmetry
    out = reflect_4fold_symmetry(out)
    return out


