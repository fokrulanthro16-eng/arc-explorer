"""ARC Task loader, JSON parser, and GridWorld environment adapter."""

import json
import os
from typing import Dict, Any, List, Tuple, Optional
from arc_explorer.environment import BaseRule, GridWorld, Color, Action, ACTION_DELTAS


class ARCPair:
    """Represents a single input-output grid pair in an ARC task."""

    def __init__(self, input_grid: List[List[int]], output_grid: Optional[List[List[int]]] = None):
        self.input_grid = [list(r) for r in input_grid]
        self.output_grid = [list(r) for r in output_grid] if output_grid is not None else None

    @property
    def input_height(self) -> int:
        return len(self.input_grid)

    @property
    def input_width(self) -> int:
        return len(self.input_grid[0]) if self.input_grid else 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input": self.input_grid,
            "output": self.output_grid,
        }


class ARCTask:
    """Official ARC-AGI Task container parsing JSON data."""

    def __init__(self, task_id: str, train_pairs: List[ARCPair], test_pairs: List[ARCPair]):
        self.task_id = task_id
        self.train_pairs = train_pairs
        self.test_pairs = test_pairs

    @classmethod
    def load_from_dict(cls, data: Dict[str, Any], task_id: str = "custom_task") -> "ARCTask":
        """Parses ARC task dictionary into ARCTask instance."""
        train_pairs = [
            ARCPair(input_grid=p["input"], output_grid=p.get("output"))
            for p in data.get("train", [])
        ]
        test_pairs = [
            ARCPair(input_grid=p["input"], output_grid=p.get("output"))
            for p in data.get("test", [])
        ]
        return cls(task_id=task_id, train_pairs=train_pairs, test_pairs=test_pairs)

    @classmethod
    def load_from_file(cls, filepath: str) -> "ARCTask":
        """Loads and parses an official ARC JSON task file."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"ARC task file not found: {filepath}")

        task_id = os.path.splitext(os.path.basename(filepath))[0]
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls.load_from_dict(data, task_id=task_id)


class ARCTaskRule(BaseRule):
    """
    Rule adapter for ARC task transformation:
    - INTERACT on cell (r, c) transforms cell color to match target output grid cell.
    - Movement actions shift agent position.
    - Environment succeeds when grid state matches target_output_grid.
    """

    def __init__(self, target_output_grid: Optional[List[List[int]]] = None):
        super().__init__(
            name="ARC Task Target Transformation",
            description="Agent interacts with input grid cells to match target ARC output transformation.",
        )
        self.target_output_grid = [list(r) for r in target_output_grid] if target_output_grid else None

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
            if self.target_output_grid and 0 <= r < len(self.target_output_grid) and 0 <= c < len(self.target_output_grid[0]):
                target_color = self.target_output_grid[r][c]
                if next_grid[r][c] != target_color:
                    next_grid[r][c] = target_color
                    reward = 10.0
                else:
                    info["no_change"] = True
            else:
                info["no_change"] = True

        elif action in ACTION_DELTAS:
            dr, dc = ACTION_DELTAS[action]
            nr, nc = r + dr, c + dc
            if 0 <= nr < h and 0 <= nc < w:
                next_pos = (nr, nc)
            else:
                hazard = True

        # Check task completion
        if self.target_output_grid and next_grid == self.target_output_grid:
            reward += 50.0
            info["success"] = True

        return next_grid, next_pos, reward, hazard, state_vars, info


def create_arc_task_environment(
    task: ARCTask, pair_type: str = "train", index: int = 0, max_steps: int = 30
) -> GridWorld:
    """Converts an ARC task pair into a GridWorld environment."""
    pairs = task.train_pairs if pair_type == "train" else task.test_pairs
    if not pairs or index >= len(pairs):
        raise ValueError(f"No {pair_type} pair at index {index} in task {task.task_id}.")

    pair = pairs[index]
    initial_grid = pair.input_grid
    rule = ARCTaskRule(target_output_grid=pair.output_grid)
    initial_pos = (0, 0)

    return GridWorld(
        initial_grid=initial_grid,
        initial_pos=initial_pos,
        rule=rule,
        max_steps=max_steps,
    )
