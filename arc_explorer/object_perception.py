"""Connected Component Object Perception & Composition Engine for ARC-AGI tasks."""

from typing import List, Dict, Tuple, Optional, Any, Set
from collections import deque


class ConnectedObject:
    """Represents an isolated 2D connected component object and its spatial properties."""

    def __init__(self, object_id: int, pixels: List[Tuple[int, int]], colors: Dict[Tuple[int, int], int]):
        self.object_id = object_id
        self.pixels = pixels
        self.colors = colors

        # Primary color & color distribution
        color_counts: Dict[int, int] = {}
        for p in pixels:
            c = colors[p]
            color_counts[c] = color_counts.get(c, 0) + 1
        self.color_counts = color_counts
        self.primary_color = max(color_counts.keys(), key=lambda k: color_counts[k]) if color_counts else 0

        # Bounding box
        rows = [p[0] for p in pixels]
        cols = [p[1] for p in pixels]
        self.min_r, self.max_r = min(rows), max(rows)
        self.min_c, self.max_c = min(cols), max(cols)
        self.height = self.max_r - self.min_r + 1
        self.width = self.max_c - self.min_c + 1

        # Area & Centroid
        self.area = len(pixels)
        self.centroid = (sum(rows) / self.area, sum(cols) / self.area) if self.area > 0 else (0.0, 0.0)

        # Shape signature (relative offsets normalized to (0,0))
        self.shape_signature = frozenset((r - self.min_r, c - self.min_c) for r, c in pixels)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_id": self.object_id,
            "primary_color": self.primary_color,
            "area": self.area,
            "bbox": [self.min_r, self.max_r, self.min_c, self.max_c],
            "height": self.height,
            "width": self.width,
            "centroid": [round(self.centroid[0], 2), round(self.centroid[1], 2)],
        }


class ObjectPerceptionEngine:
    """Detects and extracts connected component objects from 2D grid matrices."""

    @staticmethod
    def detect_objects(grid: List[List[int]], connectivity: int = 4, background_color: int = 0) -> List[ConnectedObject]:
        if not grid or not grid[0]:
            return []

        h, w = len(grid), len(grid[0])
        visited = [[False] * w for _ in range(h)]
        objects: List[ConnectedObject] = []
        obj_id = 1

        # 4-way or 8-way directional offsets
        dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        if connectivity == 8:
            dirs += [(-1, -1), (-1, 1), (1, -1), (1, 1)]

        for r in range(h):
            for c in range(w):
                if not visited[r][c] and grid[r][c] != background_color:
                    pixels: List[Tuple[int, int]] = []
                    colors: Dict[Tuple[int, int], int] = {}
                    queue = deque([(r, c)])
                    visited[r][c] = True

                    while queue:
                        curr_r, curr_c = queue.popleft()
                        pixels.append((curr_r, curr_c))
                        colors[(curr_r, curr_c)] = grid[curr_r][curr_c]

                        for dr, dc in dirs:
                            nr, nc = curr_r + dr, curr_c + dc
                            if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc]:
                                if grid[nr][nc] != background_color:
                                    visited[nr][nc] = True
                                    queue.append((nr, nc))

                    obj = ConnectedObject(obj_id, pixels, colors)
                    objects.append(obj)
                    obj_id += 1

        return objects

    @staticmethod
    def filter_objects(
        objects: List[ConnectedObject],
        color: Optional[int] = None,
        min_area: Optional[int] = None,
        max_area: Optional[int] = None,
        position_filter: Optional[str] = None,
    ) -> List[ConnectedObject]:
        filtered = objects[:]
        if color is not None:
            filtered = [o for o in filtered if o.primary_color == color]
        if min_area is not None:
            filtered = [o for o in filtered if o.area >= min_area]
        if max_area is not None:
            filtered = [o for o in filtered if o.area <= max_area]
        if position_filter == "top_most" and filtered:
            min_r = min(o.min_r for o in filtered)
            filtered = [o for o in filtered if o.min_r == min_r]
        elif position_filter == "largest" and filtered:
            max_a = max(o.area for o in filtered)
            filtered = [o for o in filtered if o.area == max_a]
        elif position_filter == "smallest" and filtered:
            min_a = min(o.area for o in filtered)
            filtered = [o for o in filtered if o.area == min_a]
        return filtered


class ObjectCompositionEngine:
    """Renders connected component objects onto output canvas grids."""

    @staticmethod
    def render_canvas(
        objects: List[ConnectedObject],
        canvas_shape: Tuple[int, int],
        background_color: int = 0
    ) -> List[List[int]]:
        h, w = canvas_shape
        canvas = [[background_color] * w for _ in range(h)]
        for obj in objects:
            for r, c in obj.pixels:
                if 0 <= r < h and 0 <= c < w:
                    canvas[r][c] = obj.colors.get((r, c), obj.primary_color)
        return canvas

    @staticmethod
    def translate_object(obj: ConnectedObject, dr: int, dc: int) -> ConnectedObject:
        new_pixels = [(r + dr, c + dc) for r, c in obj.pixels]
        new_colors = {(r + dr, c + dc): val for (r, c), val in obj.colors.items()}
        return ConnectedObject(obj.object_id, new_pixels, new_colors)

    @staticmethod
    def recolor_object(obj: ConnectedObject, new_color: int) -> ConnectedObject:
        new_colors = {p: new_color for p in obj.pixels}
        return ConnectedObject(obj.object_id, obj.pixels, new_colors)
