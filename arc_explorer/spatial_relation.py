"""Spatial Relational & Anchor Alignment Engine for ARC-AGI tasks."""

from typing import List, Dict, Tuple, Optional, Any
from arc_explorer.object_perception import ConnectedObject, ObjectPerceptionEngine, ObjectCompositionEngine


def compute_relative_displacement(obj_a: ConnectedObject, obj_b: ConnectedObject) -> Tuple[int, int]:
    """Computes relative displacement vector (dr, dc) from obj_a centroid to obj_b centroid."""
    dr = int(round(obj_b.centroid[0] - obj_a.centroid[0]))
    dc = int(round(obj_b.centroid[1] - obj_a.centroid[1]))
    return dr, dc


def align_to_anchor(
    target_obj: ConnectedObject, reference_obj: ConnectedObject, edge: str = "top"
) -> ConnectedObject:
    """Aligns target_obj to reference_obj along specified edge ('top', 'bottom', 'left', 'right', 'center')."""
    if edge == "top":
        dr = reference_obj.min_r - target_obj.min_r
        dc = 0
    elif edge == "bottom":
        dr = reference_obj.max_r - target_obj.max_r
        dc = 0
    elif edge == "left":
        dr = 0
        dc = reference_obj.min_c - target_obj.min_c
    elif edge == "right":
        dr = 0
        dc = reference_obj.max_c - target_obj.max_c
    elif edge == "center":
        dr = int(round(reference_obj.centroid[0] - target_obj.centroid[0]))
        dc = int(round(reference_obj.centroid[1] - target_obj.centroid[1]))
    else:
        dr, dc = 0, 0

    return ObjectCompositionEngine.translate_object(target_obj, dr, dc)


def place_relative(
    target_obj: ConnectedObject, reference_obj: ConnectedObject, side: str, spacing: int = 1
) -> ConnectedObject:
    """Positions target_obj relative to reference_obj ('left', 'right', 'above', 'below')."""
    if side == "left":
        dc = reference_obj.min_c - spacing - target_obj.max_c
        dr = reference_obj.min_r - target_obj.min_r
    elif side == "right":
        dc = reference_obj.max_c + spacing - target_obj.min_c
        dr = reference_obj.min_r - target_obj.min_r
    elif side == "above":
        dr = reference_obj.min_r - spacing - target_obj.max_r
        dc = reference_obj.min_c - target_obj.min_c
    elif side == "below":
        dr = reference_obj.max_r + spacing - target_obj.min_r
        dc = reference_obj.min_c - target_obj.min_c
    else:
        dr, dc = 0, 0

    return ObjectCompositionEngine.translate_object(target_obj, dr, dc)


def place_left_of(target_obj: ConnectedObject, reference_obj: ConnectedObject, spacing: int = 1) -> ConnectedObject:
    return place_relative(target_obj, reference_obj, "left", spacing)


def place_right_of(target_obj: ConnectedObject, reference_obj: ConnectedObject, spacing: int = 1) -> ConnectedObject:
    return place_relative(target_obj, reference_obj, "right", spacing)


def place_above(target_obj: ConnectedObject, reference_obj: ConnectedObject, spacing: int = 1) -> ConnectedObject:
    return place_relative(target_obj, reference_obj, "above", spacing)


def place_below(target_obj: ConnectedObject, reference_obj: ConnectedObject, spacing: int = 1) -> ConnectedObject:
    return place_relative(target_obj, reference_obj, "below", spacing)


def sort_objects_by_area(objects: List[ConnectedObject], reverse: bool = True) -> List[ConnectedObject]:
    return sorted(objects, key=lambda o: o.area, reverse=reverse)


def sort_objects_by_centroid(objects: List[ConnectedObject], axis: str = "r") -> List[ConnectedObject]:
    idx = 0 if axis == "r" else 1
    return sorted(objects, key=lambda o: o.centroid[idx])


def stack_objects(objects: List[ConnectedObject], direction: str = "vertical", spacing: int = 1) -> List[ConnectedObject]:
    if not objects:
        return []
    stacked: List[ConnectedObject] = [objects[0]]
    for i in range(1, len(objects)):
        ref = stacked[-1]
        curr = objects[i]
        if direction == "vertical":
            placed = place_below(curr, ref, spacing=spacing)
        else:
            placed = place_right_of(curr, ref, spacing=spacing)
        stacked.append(placed)
    return stacked


