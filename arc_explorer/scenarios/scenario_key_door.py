"""Scenario 2: Sequence-dependent key-door barrier unlock rule."""

from typing import List, Tuple, Dict, Any
from arc_explorer.environment import BaseRule, GridWorld, Color, Action, ACTION_DELTAS


class KeyDoorRule(BaseRule):
    """
    Rule 2:
    - Stepping into GREEN barrier without unlocking triggers hazard alert.
    - Executing INTERACT at YELLOW trigger (2,0) unlocks all GREEN barriers, converting them to EMPTY.
    - Stepping into cleared GREEN tile allows access to goal area.
    """

    def __init__(self):
        super().__init__(
            name="Color Door Key Sequence",
            description="INTERACT on YELLOW trigger unlocks GREEN barrier; crossing GREEN before trigger alerts hazard.",
        )

    def step(
        self,
        grid: List[List[int]],
        agent_pos: Tuple[int, int],
        action: Action,
        state_vars: Dict[str, Any],
    ) -> Tuple[List[List[int]], Tuple[int, int], float, bool, Dict[str, Any], Dict[str, Any]]:
        next_grid = [list(row) for row in grid]
        h = len(next_grid)
        w = len(next_grid[0])
        r, c = agent_pos
        next_pos = agent_pos
        reward = 0.0
        hazard = False
        info: Dict[str, Any] = {}

        unlocked = state_vars.get("unlocked", False)

        if action == Action.INTERACT:
            # Check if standing on or adjacent to YELLOW trigger (Color.YELLOW = 4)
            if next_grid[r][c] == Color.YELLOW or any(
                0 <= r + dr < h and 0 <= c + dc < w and next_grid[r + dr][c + dc] == Color.YELLOW
                for dr, dc in ACTION_DELTAS.values()
            ):
                unlocked = True
                state_vars["unlocked"] = True
                # Replace all GREEN barriers (3) with EMPTY (0)
                for gr in range(h):
                    for gc in range(w):
                        if next_grid[gr][gc] == Color.GREEN:
                            next_grid[gr][gc] = Color.EMPTY
                reward = 10.0

        elif action in ACTION_DELTAS:
            dr, dc = ACTION_DELTAS[action]
            nr, nc = r + dr, c + dc

            if not (0 <= nr < h and 0 <= nc < w):
                hazard = True
            else:
                target_cell = next_grid[nr][nc]
                if target_cell == Color.GRAY:
                    hazard = True
                elif target_cell == Color.GREEN and not unlocked:
                    hazard = True
                else:
                    next_pos = (nr, nc)
                    if (nr, nc) == (0, 4):  # Goal cell
                        reward = 50.0
                        info["success"] = True

        return next_grid, next_pos, reward, hazard, state_vars, info


def create_scenario_2() -> GridWorld:
    """Initializes Scenario 2 GridWorld instance."""
    initial_grid = [
        [0, 0, 5, 0, 8],  # Goal at (0,4) = 8 (TEAL)
        [0, 0, 5, 0, 0],
        [4, 0, 3, 0, 0],  # Trigger 4 (YELLOW) at (2,0), Barrier 3 (GREEN) at (2,2)
        [0, 0, 5, 0, 0],
        [0, 0, 5, 0, 0],
    ]
    initial_pos = (4, 0)
    rule = KeyDoorRule()
    return GridWorld(initial_grid=initial_grid, initial_pos=initial_pos, rule=rule, max_steps=25)
