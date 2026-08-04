"""Unit tests for Connected Component Object Perception & Composition Engine."""

from arc_explorer.object_perception import (
    ObjectPerceptionEngine,
    ObjectCompositionEngine,
)
from arc_explorer.symbolic import ObjectTransformOperator


def test_object_detection_properties():
    grid = [
        [0, 2, 2, 0],
        [0, 2, 0, 0],
        [0, 0, 0, 3],
    ]
    objects = ObjectPerceptionEngine.detect_objects(grid, connectivity=4)
    assert len(objects) == 2

    # Object 1 (color 2)
    obj_color2 = [o for o in objects if o.primary_color == 2][0]
    assert obj_color2.area == 3
    assert obj_color2.min_r == 0 and obj_color2.max_r == 1
    assert obj_color2.min_c == 1 and obj_color2.max_c == 2
    assert obj_color2.height == 2 and obj_color2.width == 2

    # Object 2 (color 3)
    obj_color3 = [o for o in objects if o.primary_color == 3][0]
    assert obj_color3.area == 1
    assert obj_color3.min_r == 2 and obj_color3.min_c == 3


def test_object_filtering_and_transformation():
    grid = [
        [1, 1, 0, 0],
        [0, 0, 0, 1],
    ]
    objects = ObjectPerceptionEngine.detect_objects(grid)
    largest = ObjectPerceptionEngine.filter_objects(objects, position_filter="largest")
    assert len(largest) == 1
    assert largest[0].area == 2

    smallest = ObjectPerceptionEngine.filter_objects(objects, position_filter="smallest")
    assert len(smallest) == 1
    assert smallest[0].area == 1


def test_object_transform_operator_application():
    # Transform color 1 to color 4 only on the largest object
    grid = [
        [1, 1, 0, 0],
        [0, 0, 0, 1],
    ]
    op = ObjectTransformOperator(target_color=1, new_color=4, filter_type="largest")
    out = op.apply(grid)
    expected = [
        [4, 4, 0, 0],
        [0, 0, 0, 1],
    ]
    assert out == expected
