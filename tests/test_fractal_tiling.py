"""Unit tests for FractalTilingOperator."""

from arc_explorer.symbolic import (
    FractalTilingOperator,
    SymbolicHypothesisGraph,
)


class MockPair:
    """Lightweight stand-in for ARCTask training pairs."""

    def __init__(self, input_grid, output_grid):
        self.input_grid = input_grid
        self.output_grid = output_grid


# ── apply() behaviour tests ──────────────────────────────────────────


def test_fractal_tiling_basic():
    """Each non-zero cell of the input is replaced by the full input
    pattern; each zero cell becomes an all-zero block."""
    grid = [
        [1, 0],
        [0, 1],
    ]
    op = FractalTilingOperator()
    result = op.apply(grid)
    expected = [
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1],
    ]
    assert result == expected


def test_fractal_tiling_3x3():
    """3x3 pattern expands to 9x9 — mirrors ARC task 007bbfb7 pair 1."""
    grid = [
        [4, 0, 4],
        [0, 0, 0],
        [0, 4, 0],
    ]
    op = FractalTilingOperator()
    result = op.apply(grid)
    expected = [
        [4, 0, 4, 0, 0, 0, 4, 0, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 4, 0, 0, 0, 0, 0, 4, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 4, 0, 4, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 4, 0, 0, 0, 0],
    ]
    assert result == expected


def test_fractal_tiling_all_filled():
    """When every cell is non-zero the output is a full tile repeat."""
    grid = [
        [3, 3],
        [3, 3],
    ]
    op = FractalTilingOperator()
    result = op.apply(grid)
    expected = [
        [3, 3, 3, 3],
        [3, 3, 3, 3],
        [3, 3, 3, 3],
        [3, 3, 3, 3],
    ]
    assert result == expected


def test_fractal_tiling_single_cell():
    """A 1x1 grid with a non-zero value stays as-is."""
    grid = [[5]]
    op = FractalTilingOperator()
    result = op.apply(grid)
    assert result == [[5]]


def test_fractal_tiling_all_zero():
    """All-zero input produces an all-zero expanded output."""
    grid = [
        [0, 0],
        [0, 0],
    ]
    op = FractalTilingOperator()
    result = op.apply(grid)
    expected = [
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]
    assert result == expected


# ── parameter inference test ─────────────────────────────────────────


def test_infer_fractal_from_pairs():
    """infer_from_pairs detects the N->N*N dimension signature and
    verifies that fractal tiling reproduces the outputs."""
    pair_a = MockPair(
        input_grid=[
            [1, 0],
            [0, 1],
        ],
        output_grid=[
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ],
    )
    pair_b = MockPair(
        input_grid=[
            [2, 2],
            [0, 0],
        ],
        output_grid=[
            [2, 2, 2, 2],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
        ],
    )
    candidates = FractalTilingOperator.infer_from_pairs([pair_a, pair_b])
    assert len(candidates) >= 1
    op = candidates[0]
    assert op.apply(pair_a.input_grid) == pair_a.output_grid
    assert op.apply(pair_b.input_grid) == pair_b.output_grid


# ── end-to-end DAG planner integration ───────────────────────────────


def test_dag_planner_selects_fractal_tiling():
    """SymbolicHypothesisGraph discovers the fractal tiling hypothesis
    for a task matching the 007bbfb7 pattern class."""
    pairs = [
        MockPair(
            input_grid=[
                [0, 0, 0],
                [0, 0, 2],
                [2, 0, 2],
            ],
            output_grid=[
                [0, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0, 2],
                [0, 0, 0, 0, 0, 0, 2, 0, 2],
                [0, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 2, 0, 0, 0, 0, 0, 2],
                [2, 0, 2, 0, 0, 0, 2, 0, 2],
            ],
        ),
        MockPair(
            input_grid=[
                [6, 6, 0],
                [6, 0, 0],
                [0, 6, 6],
            ],
            output_grid=[
                [6, 6, 0, 6, 6, 0, 0, 0, 0],
                [6, 0, 0, 6, 0, 0, 0, 0, 0],
                [0, 6, 6, 0, 6, 6, 0, 0, 0],
                [6, 6, 0, 0, 0, 0, 0, 0, 0],
                [6, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 6, 6, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 6, 6, 0, 6, 6, 0],
                [0, 0, 0, 6, 0, 0, 6, 0, 0],
                [0, 0, 0, 0, 6, 6, 0, 6, 6],
            ],
        ),
    ]

    graph = SymbolicHypothesisGraph()
    best_hyp = graph.build_and_evaluate(pairs)

    assert best_hyp is not None
    assert not best_hyp.is_rejected
    assert best_hyp.score > 0.0

    for pair in pairs:
        predicted = best_hyp.execute(pair.input_grid)
        assert predicted == pair.output_grid
