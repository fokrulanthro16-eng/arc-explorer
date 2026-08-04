"""Unit tests for Parameter Synthesis Engine & Dynamic Parameter Inference."""

from arc_explorer.symbolic import (
    RotationOperator,
    ReflectionOperator,
    ObjectMaskOperator,
    ParameterSynthesisEngine,
)


class MockPair:

    def __init__(self, input_grid, output_grid):
        self.input_grid = input_grid
        self.output_grid = output_grid


def test_rotation_operators():
    grid = [
        [1, 2],
        [3, 4],
    ]
    r90 = RotationOperator(90)
    assert r90.apply(grid) == [[3, 1], [4, 2]]

    r180 = RotationOperator(180)
    assert r180.apply(grid) == [[4, 3], [2, 1]]

    r270 = RotationOperator(270)
    assert r270.apply(grid) == [[2, 4], [1, 3]]


def test_reflection_operators():
    grid = [
        [1, 2],
        [3, 4],
    ]
    r_h = ReflectionOperator("horizontal")
    assert r_h.apply(grid) == [[2, 1], [4, 3]]

    r_v = ReflectionOperator("vertical")
    assert r_v.apply(grid) == [[3, 4], [1, 2]]

    r_diag = ReflectionOperator("main_diagonal")
    assert r_diag.apply(grid) == [[1, 3], [2, 4]]

    r_antidiag = ReflectionOperator("anti_diagonal")
    assert r_antidiag.apply(grid) == [[4, 2], [3, 1]]


def test_object_mask_operator():
    grid = [
        [1, 2],
        [2, 3],
    ]
    mask = ObjectMaskOperator(2, 9)
    assert mask.apply(grid) == [[1, 9], [9, 3]]


def test_parameter_synthesis_engine_inference():
    pair = MockPair([[1, 2], [3, 4]], [[3, 1], [4, 2]])
    candidates = ParameterSynthesisEngine.infer_parameters([pair])

    op_names = [op.name for op in candidates]
    assert "Rotation90" in op_names
    assert "Reflection(main_diagonal)" in op_names
    assert "Rotation180" in op_names
