"""Unit tests for N-depth Symbolic DAG Planner & Multi-Stage Reasoning."""

from arc_explorer.symbolic import (
    SymbolicDAGPlanner,
    SymbolicHypothesis,
    BoundingBoxCropOperator,
    HorizontalReflectionOperator,
    ColorMapOperator,
    SymbolicHypothesisGraph,
)


class MockPair:

    def __init__(self, input_grid, output_grid):
        self.input_grid = input_grid
        self.output_grid = output_grid


def test_dag_planner_multi_stage_reasoning():
    # 3-stage transformation: BoundingBoxCrop -> HorizontalReflection -> ColorMap{3: 4}
    in_grid = [
        [0, 0, 0, 0],
        [0, 3, 1, 0],
        [0, 0, 0, 0],
    ]
    # 1. Crop -> [[3, 1]]
    # 2. HorizontalReflection -> [[1, 3]]
    # 3. ColorMap{3: 4} -> [[1, 4]]
    out_grid = [[1, 4]]

    pair = MockPair(in_grid, out_grid)
    graph = SymbolicHypothesisGraph()
    best_hyp = graph.build_and_evaluate([pair], max_depth=4)

    assert best_hyp is not None
    assert not best_hyp.is_rejected
    assert len(best_hyp.operators) >= 2
    assert best_hyp.execute(in_grid) == out_grid


def test_dag_planner_cycle_prevention():
    in_grid = [[1, 2], [3, 4]]
    out_grid = [[1, 2], [3, 4]]
    pair = MockPair(in_grid, out_grid)

    planner = SymbolicDAGPlanner(max_depth=3)
    candidate_ops = [
        HorizontalReflectionOperator(),
        HorizontalReflectionOperator(),
    ]

    hyps = planner.search_dag_hypotheses([pair], candidate_ops)
    # Ensure redundant 2-reflection cycle (Reflection -> Reflection -> Reflection) is pruned
    signatures = [tuple(op.name for op in h.operators) for h in hyps]
    assert ("HorizontalReflection", "HorizontalReflection") not in signatures
