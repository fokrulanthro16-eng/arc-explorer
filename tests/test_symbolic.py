"""Unit tests for Symbolic Hypothesis Graph Reasoning Engine."""

import os
from arc_explorer.symbolic import (
    SymbolicHypothesisGraph,
    SymbolicHypothesis,
    BoundingBoxCropOperator,
    BlockScaleOperator,
    TileReplicationOperator,
    ColorMapOperator,
)
from arc_explorer.arc_task import ARCTask


def test_symbolic_operators():
    # Crop
    crop = BoundingBoxCropOperator()
    assert crop.apply([[0, 0], [0, 3]]) == [[3]]

    # Scale 2x
    scale = BlockScaleOperator(2)
    assert scale.apply([[1]]) == [[1, 1], [1, 1]]

    # Tile repeat 2x2
    tile = TileReplicationOperator(2, 2)
    assert tile.apply([[5]]) == [[5, 5], [5, 5]]

    # Color map
    cmap = ColorMapOperator({3: 4})
    assert cmap.apply([[3, 1]]) == [[4, 1]]


def test_symbolic_hypothesis_graph_on_reflection():
    task = ARCTask.load_from_file("data/arc_training/3c9b0459.json")
    graph = SymbolicHypothesisGraph()
    best_hyp = graph.build_and_evaluate(task.train_pairs)

    assert best_hyp is not None
    assert not best_hyp.is_rejected
    assert best_hyp.score > 0.0
    assert graph.solved_trace is not None
    assert graph.solved_trace["train_pairs_count"] > 0
