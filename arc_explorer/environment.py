"""GridWorld environment and core data structures for ARC Explorer."""

from enum import Enum
from typing import List, Tuple, Dict, Any, Optional
import copy


class Color(int, Enum):
    EMPTY = 0
    BLUE = 1
    RED = 2
    GREEN = 3
    YELLOW = 4
    GRAY = 5
    MAGENTA = 6
    ORANGE = 7
    TEAL = 8
    MAROON = 9


class Action(str, Enum):
    MOVE_UP = "MOVE_UP"
    MOVE_DOWN = "MOVE_DOWN"
    MOVE_LEFT = "MOVE_LEFT"
    MOVE_RIGHT = "MOVE_RIGHT"
    INTERACT = "INTERACT"
    INSPECT = "INSPECT"

    @classmethod
    def movement_actions(cls) -> List["Action"]:
        return [cls.MOVE_UP, cls.MOVE_DOWN, cls.MOVE_LEFT, cls.MOVE_RIGHT]


ACTION_DELTAS = {
    Action.MOVE_UP: (-1, 0),
    Action.MOVE_DOWN: (1, 0),
    Action.MOVE_LEFT: (0, -1),
    Action.MOVE_RIGHT: (0, 1),
}


class Observation:
    """Immutable view of the grid environment at a specific timestep."""

    def __init__(
        self,
        grid: List[List[int]],
        agent_pos: Tuple[int, int],
        step: int,
        last_action: Optional[Action] = None,
        last_reward: float = 0.0,
        hazard_alert: bool = False,
        done: bool = False,
        info: Optional[Dict[str, Any]] = None,
    ):
        self.grid = tuple(tuple(row) for row in grid)
        self.agent_pos = agent_pos
        self.step = step
        self.last_action = last_action
        self.last_reward = last_reward
        self.hazard_alert = hazard_alert
        self.done = done
        self.info = info or {}

    @property
    def height(self) -> int:
        return len(self.grid)

    @property
    def width(self) -> int:
        return len(self.grid[0]) if self.grid else 0

    def get_cell(self, r: int, c: int) -> int:
        if 0 <= r < self.height and 0 <= c < self.width:
            return self.grid[r][c]
        return Color.GRAY  # Out of bounds treated as boundary/wall

    def to_dict(self) -> Dict[str, Any]:
        return {
            "grid": [list(row) for row in self.grid],
            "agent_pos": self.agent_pos,
            "step": self.step,
            "last_action": self.last_action.value if self.last_action else None,
            "last_reward": self.last_reward,
            "hazard_alert": self.hazard_alert,
            "done": self.done,
            "info": self.info,
        }

    def __repr__(self) -> str:
        return f"Observation(step={self.step}, pos={self.agent_pos}, done={self.done}, hazard={self.hazard_alert})"


class BaseRule:
    """Base class for hidden environmental rules."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def step(
        self,
        grid: List[List[int]],
        agent_pos: Tuple[int, int],
        action: Action,
        state_vars: Dict[str, Any],
    ) -> Tuple[List[List[int]], Tuple[int, int], float, bool, Dict[str, Any], Dict[str, Any]]:
        """
        Calculates environmental transition.
        Returns (next_grid, next_pos, reward, hazard, next_state_vars, info).
        """
        raise NotImplementedError


class GridWorld:
    """Deterministic GridWorld environment driven by a hidden rule."""

    def __init__(
        self,
        initial_grid: List[List[int]],
        initial_pos: Tuple[int, int],
        rule: BaseRule,
        max_steps: int = 50,
    ):
        self.initial_grid = [list(row) for row in initial_grid]
        self.initial_pos = initial_pos
        self.rule = rule
        self.max_steps = max_steps

        self.grid = [list(row) for row in initial_grid]
        self.agent_pos = initial_pos
        self.step_count = 0
        self.done = False
        self.state_vars: Dict[str, Any] = {}
        self.last_action: Optional[Action] = None

    def reset(self) -> Observation:
        self.grid = [list(row) for row in self.initial_grid]
        self.agent_pos = self.initial_pos
        self.step_count = 0
        self.done = False
        self.state_vars = {}
        self.last_action = None
        initial_info = {}
        if hasattr(self.rule, "target_output_grid"):
            initial_info["target_output_grid"] = getattr(self.rule, "target_output_grid")
        return self._make_observation(last_reward=0.0, hazard_alert=False, info=initial_info)


    def step(self, action: Action) -> Observation:
        if self.done:
            raise RuntimeError("Cannot step in a finished environment. Call reset() first.")

        self.step_count += 1
        self.last_action = action

        next_grid, next_pos, reward, hazard, next_vars, info = self.rule.step(
            self.grid, self.agent_pos, action, self.state_vars
        )

        self.grid = next_grid
        self.agent_pos = next_pos
        self.state_vars = next_vars

        if self.step_count >= self.max_steps or info.get("success", False):
            self.done = True

        return self._make_observation(last_reward=reward, hazard_alert=hazard, info=info)

    def _make_observation(
        self,
        last_reward: float,
        hazard_alert: bool,
        info: Optional[Dict[str, Any]] = None,
    ) -> Observation:
        return Observation(
            grid=self.grid,
            agent_pos=self.agent_pos,
            step=self.step_count,
            last_action=self.last_action,
            last_reward=last_reward,
            hazard_alert=hazard_alert,
            done=self.done,
            info=info,
        )

    def render_ascii(self) -> str:
        symbols = {
            Color.EMPTY: ".",
            Color.BLUE: "B",
            Color.RED: "R",
            Color.GREEN: "G",
            Color.YELLOW: "Y",
            Color.GRAY: "#",
            Color.MAGENTA: "M",
            Color.ORANGE: "O",
            Color.TEAL: "T",
            Color.MAROON: "X",
        }
        lines = []
        for r in range(len(self.grid)):
            row_str = []
            for c in range(len(self.grid[0])):
                if (r, c) == self.agent_pos:
                    row_str.append("A")
                else:
                    row_str.append(symbols.get(self.grid[r][c], "?"))
            lines.append(" ".join(row_str))
        return "\n".join(lines)

