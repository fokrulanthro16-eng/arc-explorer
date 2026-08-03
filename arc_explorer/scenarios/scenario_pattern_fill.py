"""Scenario 3: Symmetric pattern completion cellular automaton rule."""

from typing import List, Tuple, Dict, Any
from arc_explorer.environment import BaseRule, GridWorld, Color, Action, ACTION_DELTAS


class PatternFillRule(BaseRule):
    """
    Rule 3:
    - INTERACT on cell (r, c) copies its non-empty color to horizontal symmetric position (r, W-1-c).
    - Stepping into GRAY wall alerts hazard.
    - Achieving full horizontal symmetry across non-empty cells sets info['success'] = True.
    """

    def __init__(self):
        super().__init__(
            name="Symmetric Pattern Completion",
            description="INTERACT on cell (r,c) mirrors its color to (r, W-1-c); completing symmetry succeeds.",
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

        if action == Action.INTERACT:
            current_color = next_grid[r][c]
            if current_color != Color.EMPTY and current_color != Color.GRAY:
                mirror_c = w - 1 - c
                if next_grid[r][mirror_c] != current_color:
                    next_grid[r][mirror_c] = current_color
                    reward = 15.0

        elif action in ACTION_DELTAS:
            dr, dc = ACTION_DELTAS[action]
            nr, nc = r + dr, c + dc
            if not (0 <= nr < h and 0 <= nc < w):
                hazard = True
            elif next_grid[nr][nc] == Color.GRAY:
                hazard = True
            else:
                next_pos = (nr, nc)

        # Check full symmetry condition
        is_symmetric = True
        for row in next_grid:
            for col_idx in range(w):
                if row[col_idx] != row[w - 1 - col_idx]:
                    is_symmetric = False
                    break

        if is_symmetric:
            reward += 30.0
            info["success"] = True

        return next_grid, next_pos, reward, hazard, state_vars, info


def create_scenario_3() -> GridWorld:
    """Initializes Scenario 3 GridWorld instance."""
    initial_grid = [
        [5, 5, 5, 5, 5],
        [5, 1, 0, 0, 5],  # Color 1 (BLUE) at (1,1)
        [5, 0, 0, 0, 5],
        [5, 6, 0, 0, 5],  # Color 6 (MAGENTA) at (3,1)
        [5, 5, 5, 5, 5],
    ]
    initial_pos = (2, 1)
    rule = PatternFillRule()
    return GridWorld(initial_grid=initial_grid, initial_pos=initial_pos, rule=rule, max_steps=20)
