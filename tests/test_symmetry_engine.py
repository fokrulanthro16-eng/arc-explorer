"""Unit tests for Global Symmetry Group & Pattern Lattice Engine."""

from arc_explorer.symmetry_engine import (
    detect_mirror_symmetry,
    apply_mirror_symmetry,
    detect_rotational_symmetry,
    reflect_4fold_symmetry,
    detect_periodic_lattice,
    tessellate_lattice,
    complete_missing_region_via_symmetry,
)
from arc_explorer.symbolic import (
    MirrorSymmetryOperator,
    Rotational4FoldSymmetryOperator,
    CompleteSymmetryOperator,
    TessellateLatticeOperator,
)



def test_mirror_symmetry_detection_and_application():
    grid = [
        [1, 2, 0],
        [3, 4, 0],
    ]

    sym = detect_mirror_symmetry(grid)
    assert not sym["horizontal"]

    # Apply horizontal mirror completion
    completed = apply_mirror_symmetry(grid, axis="horizontal")
    assert completed == [
        [1, 2, 1],
        [3, 4, 3],
    ]
    assert detect_mirror_symmetry(completed)["horizontal"]


def test_rotational_symmetry_detection_and_completion():
    grid = [
        [1, 2, 1],
        [2, 0, 2],
        [1, 2, 1],
    ]
    sym = detect_rotational_symmetry(grid)
    assert sym[180]

    out = reflect_4fold_symmetry(grid)
    assert out[1][1] == 0 or out == grid


def test_periodic_lattice_detection_and_tessellation():
    # 2x2 unit cell repeating across 4x4
    grid = [
        [1, 2, 1, 2],
        [3, 4, 3, 4],
        [1, 2, 1, 2],
        [3, 4, 3, 4],
    ]

    cell_dims = detect_periodic_lattice(grid)
    assert cell_dims == (2, 2)

    unit_cell = [[1, 2], [3, 4]]
    tessellated = tessellate_lattice(unit_cell, (4, 4))
    assert tessellated == grid


def test_complete_missing_region_via_symmetry():
    # Symmetric 3x3 grid with missing center and right edge
    grid = [
        [2, 3, 0],
        [3, 0, 3],
        [0, 3, 2],
    ]
    completed = complete_missing_region_via_symmetry(grid)
    assert completed[0][2] == 2
    assert completed[2][0] == 2


def test_symbolic_symmetry_operators():
    grid = [
        [1, 2, 0],
        [3, 4, 0],
    ]
    op = MirrorSymmetryOperator("horizontal")
    out = op.apply(grid)
    assert out[0][2] == 1 and out[1][2] == 3
