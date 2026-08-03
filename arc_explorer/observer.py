"""Perceptual observer and feature extractor for grid observations."""

from typing import Dict, Any, List, Set, Tuple
from arc_explorer.environment import Observation, Color, ACTION_DELTAS, Action


class StateFeatures:
    """Extracted perceptual features of an observation."""

    def __init__(
        self,
        color_counts: Dict[int, int],
        agent_pos: Tuple[int, int],
        adjacent_colors: Dict[str, int],
        symmetry_horizontal: bool,
        symmetry_vertical: bool,
        color_positions: Dict[int, List[Tuple[int, int]]],
    ):
        self.color_counts = color_counts
        self.agent_pos = agent_pos
        self.adjacent_colors = adjacent_colors
        self.symmetry_horizontal = symmetry_horizontal
        self.symmetry_vertical = symmetry_vertical
        self.color_positions = color_positions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "color_counts": self.color_counts,
            "agent_pos": self.agent_pos,
            "adjacent_colors": self.adjacent_colors,
            "symmetry_horizontal": self.symmetry_horizontal,
            "symmetry_vertical": self.symmetry_vertical,
            "color_positions": {k: list(v) for k, v in self.color_positions.items()},
        }


class Observer:
    """Observer that extracts symbolic structural features from grid observations."""

    @staticmethod
    def extract(obs: Observation) -> StateFeatures:
        color_counts: Dict[int, int] = {}
        color_positions: Dict[int, List[Tuple[int, int]]] = {}

        h = obs.height
        w = obs.width

        for r in range(h):
            for c in range(w):
                color = obs.grid[r][c]
                color_counts[color] = color_counts.get(color, 0) + 1
                if color not in color_positions:
                    color_positions[color] = []
                color_positions[color].append((r, c))

        # Adjacencies relative to agent
        ar, ac = obs.agent_pos
        adjacent_colors = {}
        for action, (dr, dc) in ACTION_DELTAS.items():
            nr, nc = ar + dr, ac + dc
            adjacent_colors[action.value] = obs.get_cell(nr, nc)

        # Symmetry checks
        sym_h = True
        sym_v = True

        for r in range(h):
            for c in range(w):
                if obs.grid[r][c] != obs.grid[h - 1 - r][c]:
                    sym_h = False
                if obs.grid[r][c] != obs.grid[r][w - 1 - c]:
                    sym_v = False

        return StateFeatures(
            color_counts=color_counts,
            agent_pos=obs.agent_pos,
            adjacent_colors=adjacent_colors,
            symmetry_horizontal=sym_h,
            symmetry_vertical=sym_v,
            color_positions=color_positions,
        )

    @staticmethod
    def compute_delta(obs_before: Observation, obs_after: Observation) -> Dict[str, Any]:
        """Calculates grid cell modifications between two observations."""
        changes: List[Dict[str, Any]] = []
        for r in range(min(obs_before.height, obs_after.height)):
            for c in range(min(obs_before.width, obs_after.width)):
                c_before = obs_before.grid[r][c]
                c_after = obs_after.grid[r][c]
                if c_before != c_after:
                    changes.append({
                        "pos": (r, c),
                        "from_color": c_before,
                        "to_color": c_after,
                    })

        pos_changed = obs_before.agent_pos != obs_after.agent_pos
        return {
            "num_cell_changes": len(changes),
            "changes": changes,
            "agent_moved": pos_changed,
            "pos_delta": (
                obs_after.agent_pos[0] - obs_before.agent_pos[0],
                obs_after.agent_pos[1] - obs_before.agent_pos[1],
            ),
        }
