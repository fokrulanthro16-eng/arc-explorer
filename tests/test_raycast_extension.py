"""Unit tests for RaycastLineExtensionOperator."""

from arc_explorer.symbolic import (
    RaycastLineExtensionOperator,
    SymbolicHypothesisGraph,
)


class MockPair:
    """Lightweight stand-in for ARCTask training pairs."""

    def __init__(self, input_grid, output_grid):
        self.input_grid = input_grid
        self.output_grid = output_grid


# ── apply() behaviour tests ──────────────────────────────────────────


def test_horizontal_ray_extension():
    """Single seed at the left edge extends rightward to the grid boundary."""
    grid = [
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [3, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
    ]
    op = RaycastLineExtensionOperator(
        ray_color=3, directions=[(0, 1)], bidirectional=False,
    )
    result = op.apply(grid)
    assert result[2] == [3, 3, 3, 3, 3]
    # Other rows must stay untouched
    assert result[0] == [0, 0, 0, 0, 0]
    assert result[4] == [0, 0, 0, 0, 0]


def test_vertical_ray_extension():
    """Single seed at the top extends downward to the grid boundary."""
    grid = [
        [0, 0, 2, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]
    op = RaycastLineExtensionOperator(
        ray_color=2, directions=[(1, 0)], bidirectional=False,
    )
    result = op.apply(grid)
    for r in range(4):
        assert result[r][2] == 2
    # Neighbouring column stays zero
    assert all(result[r][1] == 0 for r in range(4))


def test_diagonal_ray_extension():
    """Seed at top-left corner extends along the main diagonal."""
    grid = [
        [4, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]
    op = RaycastLineExtensionOperator(
        ray_color=4, directions=[(1, 1)], bidirectional=False,
    )
    result = op.apply(grid)
    for i in range(4):
        assert result[i][i] == 4
    # Off-diagonal stays zero
    assert result[0][1] == 0
    assert result[1][0] == 0


def test_bidirectional_extension():
    """Seed at centre extends in both horizontal directions."""
    grid = [
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 7, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
    ]
    op = RaycastLineExtensionOperator(
        ray_color=7, directions=[(0, 1)], bidirectional=True,
    )
    result = op.apply(grid)
    assert result[2] == [7, 7, 7, 7, 7]
    # Rows above and below unaffected
    assert result[0] == [0, 0, 0, 0, 0]
    assert result[4] == [0, 0, 0, 0, 0]


def test_stop_at_blocker():
    """Ray stops when it encounters any non-background, non-ray colour."""
    grid = [
        [0, 3, 0, 0, 5, 0],
    ]
    op = RaycastLineExtensionOperator(
        ray_color=3, directions=[(0, 1)], bidirectional=False,
    )
    result = op.apply(grid)
    # Ray fills cells 2-3 but cannot pass through blocker colour 5
    assert result[0] == [0, 3, 3, 3, 5, 0]


# ── parameter inference tests ────────────────────────────────────────


def test_infer_from_training_pairs():
    """infer_from_pairs correctly extracts direction, colour, stop colours,
    and bidirectionality from synthetic training pairs."""

    # ---- Case 1: unidirectional rightward extension ----
    pair_a = MockPair(
        input_grid=[
            [0, 0, 0, 0],
            [3, 0, 0, 0],
            [0, 0, 0, 0],
        ],
        output_grid=[
            [0, 0, 0, 0],
            [3, 3, 3, 3],
            [0, 0, 0, 0],
        ],
    )
    pair_b = MockPair(
        input_grid=[
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [3, 0, 0, 0, 0],
        ],
        output_grid=[
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [3, 3, 3, 3, 3],
        ],
    )
    candidates = RaycastLineExtensionOperator.infer_from_pairs([pair_a, pair_b])
    assert len(candidates) >= 1
    op = candidates[0]
    assert op.ray_color == 3
    assert (0, 1) in op.directions  # eastward
    assert not op.bidirectional

    # ---- Case 2: bidirectional horizontal ----
    pair_c = MockPair(
        input_grid=[
            [0, 0, 0, 0, 0],
            [0, 0, 4, 0, 0],
            [0, 0, 0, 0, 0],
        ],
        output_grid=[
            [0, 0, 0, 0, 0],
            [4, 4, 4, 4, 4],
            [0, 0, 0, 0, 0],
        ],
    )
    candidates_bi = RaycastLineExtensionOperator.infer_from_pairs([pair_c])
    assert len(candidates_bi) >= 1
    op_bi = candidates_bi[0]
    assert op_bi.ray_color == 4
    assert op_bi.bidirectional

    # ---- Case 3: stop-colour detection ----
    pair_d = MockPair(
        input_grid=[[6, 0, 0, 5]],
        output_grid=[[6, 6, 6, 5]],
    )
    candidates_stop = RaycastLineExtensionOperator.infer_from_pairs([pair_d])
    assert len(candidates_stop) >= 1
    op_stop = candidates_stop[0]
    assert 5 in op_stop.stop_colors


# ── end-to-end DAG planner integration ───────────────────────────────


def test_dag_planner_selects_raycast():
    """SymbolicHypothesisGraph discovers and selects a raycast-based
    hypothesis for a task that only the raycast operator can solve
    (blocker colour prevents LineExtendOperator from matching)."""
    pairs = [
        MockPair(
            input_grid=[
                [0, 0, 0, 0, 0],
                [6, 0, 0, 5, 0],
                [0, 0, 0, 0, 0],
            ],
            output_grid=[
                [0, 0, 0, 0, 0],
                [6, 6, 6, 5, 0],
                [0, 0, 0, 0, 0],
            ],
        ),
        MockPair(
            input_grid=[
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [6, 0, 5, 0],
            ],
            output_grid=[
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [6, 6, 5, 0],
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
