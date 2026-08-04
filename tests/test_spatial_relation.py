"""Unit tests for Spatial Relational & Anchor Alignment Engine."""

from arc_explorer.object_perception import ObjectPerceptionEngine
from arc_explorer.spatial_relation import (
    align_to_anchor,
    place_left_of,
    place_right_of,
    place_above,
    place_below,
    stack_objects,
    sort_objects_by_area,
    sort_objects_by_centroid,
    compute_relative_displacement,
)
from arc_explorer.symbolic import (
    AlignToAnchorOperator,
    PlaceRelativeOperator,
    StackObjectsOperator,
)



def test_spatial_relative_displacement():
    grid = [
        [1, 0, 0, 0],
        [0, 0, 0, 2],
    ]
    objects = ObjectPerceptionEngine.detect_objects(grid)
    obj1 = [o for o in objects if o.primary_color == 1][0]
    obj2 = [o for o in objects if o.primary_color == 2][0]

    dr, dc = compute_relative_displacement(obj1, obj2)
    assert dr == 1 and dc == 3


def test_align_to_anchor_edges():
    # Anchor (color 1) at top-left [0,0], Target (color 2) at [2,2]
    grid = [
        [1, 0, 0],
        [0, 0, 0],
        [0, 0, 2],
    ]
    objects = ObjectPerceptionEngine.detect_objects(grid)
    obj1 = [o for o in objects if o.primary_color == 1][0]
    obj2 = [o for o in objects if o.primary_color == 2][0]

    aligned_top = align_to_anchor(obj2, obj1, edge="top")
    assert aligned_top.min_r == 0


def test_place_relative_directions():
    grid = [
        [0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0],
        [0, 0, 0, 2, 0],
    ]
    objects = ObjectPerceptionEngine.detect_objects(grid)
    obj1 = [o for o in objects if o.primary_color == 1][0]
    obj2 = [o for o in objects if o.primary_color == 2][0]

    placed_right = place_right_of(obj2, obj1, spacing=1)
    assert placed_right.min_c == obj1.max_c + 2

    placed_below = place_below(obj2, obj1, spacing=1)
    assert placed_below.min_r == obj1.max_r + 2


def test_sort_and_stack_objects():
    grid = [
        [1, 1, 0, 2],
        [1, 1, 0, 0],
    ]
    objects = ObjectPerceptionEngine.detect_objects(grid)
    by_area = sort_objects_by_area(objects, reverse=True)
    assert by_area[0].primary_color == 1
    assert by_area[1].primary_color == 2

    stacked = stack_objects(by_area, direction="vertical", spacing=1)
    assert len(stacked) == 2
    assert stacked[1].min_r > stacked[0].max_r


def test_symbolic_relational_operators():
    grid = [
        [1, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 2],
    ]
    op = AlignToAnchorOperator(target_color=2, reference_color=1, edge="top")
    out = op.apply(grid)
    assert out[0][3] == 2  # Target color 2 aligned to top edge (row 0)
