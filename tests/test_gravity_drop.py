"""Unit tests for GravityDropOperator."""

from arc_explorer.symbolic import (
    GravityDropOperator,
    SymbolicHypothesisGraph,
)


class MockPair:
    """Lightweight stand-in for ARCTask training pairs."""

    def __init__(self, input_grid, output_grid):
        self.input_grid = input_grid
        self.output_grid = output_grid


# ── apply() behaviour tests ──────────────────────────────────────────


def test_gravity_drop_down():
    """Non-background cells in each column fall to the bottom of the grid."""
    grid = [
        [3, 0, 0],
        [0, 0, 0],
        [0, 0, 2],
        [0, 0, 0],
    ]
    op = GravityDropOperator(direction=(1, 0))
    result = op.apply(grid)
    expected = [
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [3, 0, 2],
    ]
    assert result == expected


def test_gravity_drop_left():
    """Non-background cells in each row slide to the left edge."""
    grid = [
        [0, 0, 3, 0, 2],
        [0, 1, 0, 0, 0],
    ]
    op = GravityDropOperator(direction=(0, -1))
    result = op.apply(grid)
    expected = [
        [3, 2, 0, 0, 0],
        [1, 0, 0, 0, 0],
    ]
    assert result == expected


def test_gravity_drop_with_fixed_obstacle():
    """Only specified colours fall; unaffected colours act as obstacles.

    Colour 5 is fixed; colour 3 falls down but stops above it.
    """
    grid = [
        [3, 0],
        [0, 0],
        [5, 0],
        [0, 0],
    ]
    op = GravityDropOperator(direction=(1, 0), affected_colors={3})
    result = op.apply(grid)
    expected = [
        [0, 0],
        [3, 0],
        [5, 0],
        [0, 0],
    ]
    assert result == expected


def test_gravity_drop_stacking():
    """Multiple objects in a column preserve their relative order when
    they stack at the bottom."""
    grid = [
        [1, 0],
        [0, 0],
        [2, 0],
        [0, 0],
        [3, 0],
    ]
    op = GravityDropOperator(direction=(1, 0))
    result = op.apply(grid)
    expected = [
        [0, 0],
        [0, 0],
        [1, 0],
        [2, 0],
        [3, 0],
    ]
    assert result == expected


def test_gravity_drop_up():
    """Gravity upward: cells rise to the top of the grid."""
    grid = [
        [0, 0],
        [0, 0],
        [0, 4],
        [7, 0],
    ]
    op = GravityDropOperator(direction=(-1, 0))
    result = op.apply(grid)
    expected = [
        [7, 4],
        [0, 0],
        [0, 0],
        [0, 0],
    ]
    assert result == expected


# ── parameter inference test ─────────────────────────────────────────


def test_infer_gravity_from_pairs():
    """infer_from_pairs correctly detects downward gravity and
    distinguishes fixed colours from falling ones."""

    # ---- Case 1: simple downward gravity, all colours ----
    pair_a = MockPair(
        input_grid=[
            [0, 3, 0],
            [0, 0, 0],
            [0, 0, 0],
        ],
        output_grid=[
            [0, 0, 0],
            [0, 0, 0],
            [0, 3, 0],
        ],
    )
    pair_b = MockPair(
        input_grid=[
            [2, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ],
        output_grid=[
            [0, 0, 0],
            [0, 0, 0],
            [2, 0, 0],
        ],
    )
    candidates = GravityDropOperator.infer_from_pairs([pair_a, pair_b])
    assert len(candidates) >= 1
    op = candidates[0]
    assert op.direction == (1, 0)  # downward

    # Verify it reproduces both pairs
    assert op.apply(pair_a.input_grid) == pair_a.output_grid
    assert op.apply(pair_b.input_grid) == pair_b.output_grid

    # ---- Case 2: partial gravity with a fixed colour ----
    pair_c = MockPair(
        input_grid=[
            [3, 0],
            [0, 0],
            [5, 0],
            [0, 0],
        ],
        output_grid=[
            [0, 0],
            [3, 0],
            [5, 0],
            [0, 0],
        ],
    )
    candidates_partial = GravityDropOperator.infer_from_pairs([pair_c])
    assert len(candidates_partial) >= 1
    op_p = candidates_partial[0]
    assert op_p.direction == (1, 0)
    assert op_p.apply(pair_c.input_grid) == pair_c.output_grid


# ── end-to-end DAG planner integration ───────────────────────────────


def test_dag_planner_selects_gravity():
    """SymbolicHypothesisGraph discovers and selects a gravity-based
    hypothesis for a task where cells fall to the bottom.

    The two training pairs have different grid sizes and different
    positions, so only gravity (not a fixed translation) can solve both.
    """
    pairs = [
        MockPair(
            input_grid=[
                [3, 0, 2],
                [0, 0, 0],
                [0, 0, 0],
            ],
            output_grid=[
                [0, 0, 0],
                [0, 0, 0],
                [3, 0, 2],
            ],
        ),
        MockPair(
            input_grid=[
                [0, 1, 0, 0],
                [0, 0, 0, 4],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
            ],
            output_grid=[
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 1, 0, 4],
            ],
        ),
    ]

    graph = SymbolicHypothesisGraph()
    best_hyp = graph.build_and_evaluate(pairs)

    assert best_hyp is not None
    assert not best_hyp.is_rejected
    assert best_hyp.score > 0.0

    # Verify the winning hypothesis reproduces every training pair exactly
    for pair in pairs:
        predicted = best_hyp.execute(pair.input_grid)
        assert predicted == pair.output_grid
