"""Scenario 1: Color symmetry and propagation rule."""

from typing import List, Tuple, Dict, Any
from arc_explorer.environment import BaseRule, GridWorld, Color, Action, ACTION_DELTAS


class ColorPropagationRule(BaseRule):
    """
    Rule 1:
    - Pushing RED tile shifts RED tile forward into adjacent empty cell.
    - Pushing BLUE tile reflects BLUE vertically (r -> H-1-r).
    - Stepping into GRAY wall triggers hazard alert.
    """

    def __init__(self):
        super().__init__(
            name="Color Propagation & Reflection",
            description="RED tile propagates on push; BLUE tile reflects vertically; GRAY wall gives hazard.",
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

        if action in ACTION_DELTAS:
            dr, dc = ACTION_DELTAS[action]
            nr, nc = r + dr, c + dc

            if not (0 <= nr < h and 0 <= nc < w):
                hazard = True
            else:
                target_cell = next_grid[nr][nc]
                if target_cell == Color.GRAY:
                    hazard = True
                elif target_cell == Color.RED:
                    # Propagate RED tile forward if next cell empty
                    nnr, nnc = nr + dr, nc + dc
                    if 0 <= nnr < h and 0 <= nnc < w and next_grid[nnr][nnc] == Color.EMPTY:
                        next_grid[nnr][nnc] = Color.RED
                        next_pos = (nr, nc)
                        reward = 5.0
                    else:
                        hazard = True
                elif target_cell == Color.BLUE:
                    # Reflect BLUE tile vertically
                    next_grid[nr][nc] = Color.EMPTY
                    reflect_r = h - 1 - nr
                    next_grid[reflect_r][nc] = Color.BLUE
                    next_pos = (nr, nc)
                    reward = 5.0
                elif target_cell == Color.EMPTY:
                    next_pos = (nr, nc)

        # Success condition: RED propagated and BLUE reflected
        has_propagated_red = next_grid[2][2] == Color.RED
        has_reflected_blue = next_grid[3][3] == Color.BLUE
        if has_propagated_red or has_reflected_blue:
            reward += 10.0
            info["success"] = True

        return next_grid, next_pos, reward, hazard, state_vars, info


def create_scenario_1() -> GridWorld:
    """Initializes Scenario 1 GridWorld instance."""
    initial_grid = [
        [5, 5, 5, 5, 5],
        [5, 0, 0, 1, 5],  # 1 = BLUE at (1,3)
        [0, 2, 0, 0, 5],  # 2 = RED at (2,1)
        [5, 0, 0, 0, 5],
        [5, 5, 5, 5, 5],
    ]
    initial_pos = (2, 0)
    rule = ColorPropagationRule()
    return GridWorld(initial_grid=initial_grid, initial_pos=initial_pos, rule=rule, max_steps=20)
