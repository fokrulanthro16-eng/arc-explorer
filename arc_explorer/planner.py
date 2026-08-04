"""Safe Experiment Planner balancing information gain against predicted environmental hazards and macro plans."""

from typing import Dict, Any, List, Tuple, Optional, Set
from arc_explorer.environment import Observation, Action
from arc_explorer.hypothesis import HypothesisTracker


class MacroGoal:
    """Represents a targeted macro goal, e.g., MOVE_TO(r, c) then INTERACT."""

    def __init__(self, target_pos: Tuple[int, int], action_type: Action, description: str = ""):
        self.target_pos = target_pos
        self.action_type = action_type
        self.description = description


def compute_path_actions(
    start_pos: Tuple[int, int],
    target_pos: Tuple[int, int],
    grid: Tuple[Tuple[int, ...], ...],
) -> List[Action]:
    """Computes cardinal movement action sequence from start_pos to target_pos avoiding obstacles."""
    if start_pos == target_pos:
        return []

    h = len(grid)
    w = len(grid[0]) if h > 0 else 0
    queue = [(start_pos, [])]
    visited = {start_pos}

    deltas = [
        ((-1, 0), Action.MOVE_UP),
        ((1, 0), Action.MOVE_DOWN),
        ((0, -1), Action.MOVE_LEFT),
        ((0, 1), Action.MOVE_RIGHT),
    ]

    while queue:
        (r, c), path = queue.pop(0)
        if (r, c) == target_pos:
            return path

        for (dr, dc), act in deltas:
            nr, nc = r + dr, c + dc
            if 0 <= nr < h and 0 <= nc < w:
                if grid[nr][nc] != 5:  # Avoid Color.GRAY wall
                    if (nr, nc) not in visited:
                        visited.add((nr, nc))
                        queue.append(((nr, nc), path + [act]))

    return []


class SafePlanner:
    """Planner that selects informative actions while respecting safety constraints and executing macro plans."""

    def __init__(
        self,
        hazard_threshold: float = 0.4,
        safety_weight: float = 3.0,
        novelty_weight: float = 0.5,
    ):
        self.hazard_threshold = hazard_threshold
        self.safety_weight = safety_weight
        self.novelty_weight = novelty_weight
        self.action_history: List[Tuple[Tuple[int, int], Action]] = []
        self.macro_queue: List[Action] = []
        self.visited_goals: Set[Tuple[Tuple[int, int], str]] = set()
        self.active_goal: Optional[MacroGoal] = None

    def generate_macro_plan(
        self, obs: Observation
    ) -> Optional[Tuple[MacroGoal, List[Action]]]:
        """Generates a macro-action plan sequence for unvisited target discrepancy goals."""
        target_grid = obs.info.get("target_output_grid")
        if not target_grid:
            return None

        current_grid = obs.grid
        h = len(current_grid)
        w = len(current_grid[0]) if h > 0 else 0

        discrepancies = []
        for r in range(h):
            for c in range(w):
                if r < len(target_grid) and c < len(target_grid[0]):
                    if current_grid[r][c] != target_grid[r][c]:
                        goal_key = ((r, c), Action.INTERACT.value)
                        if goal_key not in self.visited_goals:
                            dist = abs(r - obs.agent_pos[0]) + abs(c - obs.agent_pos[1])
                            discrepancies.append((dist, (r, c)))

        if not discrepancies:
            return None

        discrepancies.sort(key=lambda x: x[0])
        _, target_pos = discrepancies[0]

        path_actions = compute_path_actions(obs.agent_pos, target_pos, current_grid)
        full_sequence = path_actions + [Action.INTERACT]
        goal = MacroGoal(target_pos, Action.INTERACT, f"Target cell {target_pos}")
        return goal, full_sequence

    def select_action(
        self, obs: Observation, tracker: HypothesisTracker, visited_positions: List[Tuple[int, int]]
    ) -> Tuple[Action, Dict[str, Any]]:
        if obs.step == 1 or len(visited_positions) <= 1:
            self.action_history.clear()
            self.macro_queue.clear()
            self.visited_goals.clear()
            self.active_goal = None

        rankings = tracker.get_rankings()
        all_actions = list(Action)

        # 1. Compute safety for all actions
        action_safety: Dict[str, bool] = {}
        for action in all_actions:
            max_hazard_prob = 0.0
            for hyp in rankings:
                if hyp.score > 0.1:
                    _, pred_hazard = hyp.predict(obs, action)
                    if pred_hazard:
                        max_hazard_prob = max(max_hazard_prob, hyp.score)

            if action in [Action.MOVE_UP, Action.MOVE_DOWN, Action.MOVE_LEFT, Action.MOVE_RIGHT]:
                dr, dc = {"MOVE_UP": (-1, 0), "MOVE_DOWN": (1, 0), "MOVE_LEFT": (0, -1), "MOVE_RIGHT": (0, 1)}[action.value]
                target_cell = obs.get_cell(obs.agent_pos[0] + dr, obs.agent_pos[1] + dc)
                if target_cell == 5:  # Color.GRAY wall
                    max_hazard_prob = 1.0

            is_safe = max_hazard_prob < self.hazard_threshold
            action_safety[action.value] = is_safe

        # 2. Check if an active macro queue exists
        if not self.macro_queue:
            macro = self.generate_macro_plan(obs)
            if macro:
                self.active_goal, self.macro_queue = macro

        # 3. Attempt executing next step from macro queue
        if self.macro_queue:
            next_action = self.macro_queue[0]
            if action_safety.get(next_action.value, False):
                action = self.macro_queue.pop(0)
                if not self.macro_queue and self.active_goal:
                    self.visited_goals.add((self.active_goal.target_pos, self.active_goal.action_type.value))
                    self.active_goal = None

                self.action_history.append((obs.agent_pos, action))
                plan_info = {
                    "selected_action": action.value,
                    "best_utility": 10.0,
                    "action_utilities": {a.value: (10.0 if a == action else 0.0) for a in all_actions},
                    "action_safety": action_safety,
                    "macro_plan": True,
                }
                return action, plan_info
            else:
                # Abort macro queue safely if next action is predicted unsafe
                self.macro_queue.clear()
                self.active_goal = None

        # 4. Fallback: Local Safe Utility Selection
        best_action = None
        best_utility = -float("inf")
        action_utilities: Dict[str, float] = {}

        safe_actions = [a for a in all_actions if action_safety[a.value]]
        candidate_actions = safe_actions if safe_actions else all_actions

        for action in candidate_actions:
            dr_dc_map = {"MOVE_UP": (-1, 0), "MOVE_DOWN": (1, 0), "MOVE_LEFT": (0, -1), "MOVE_RIGHT": (0, 1)}
            novelty = 0.0
            if action.value in dr_dc_map:
                dr, dc = dr_dc_map[action.value]
                target_pos = (obs.agent_pos[0] + dr, obs.agent_pos[1] + dc)
                visit_count = visited_positions.count(target_pos)
                novelty = 1.0 / (1.0 + visit_count)
            elif action in [Action.INTERACT, Action.INSPECT]:
                r, c = obs.agent_pos
                current_color = obs.get_cell(r, c)
                adj_colors = [obs.get_cell(r + dr, c + dc) for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]]
                action_pos_count = sum(1 for p, a in self.action_history if p == (r, c) and a == action)

                if current_color not in [0, 5] or any(c not in [0, 5] for c in adj_colors):
                    novelty = 1.5 / (1.0 + action_pos_count)

                if obs.info.get("no_change", False) and obs.last_action in [Action.INTERACT, Action.INSPECT]:
                    last_pos = self.action_history[-1][0] if self.action_history else None
                    if last_pos == (r, c):
                        novelty = 0.0

            predicted_outcomes = []
            for hyp in rankings[:3]:
                pred_grid, pred_h = hyp.predict(obs, action)
                outcome_signature = (tuple(tuple(r) for r in pred_grid), pred_h)
                predicted_outcomes.append(outcome_signature)

            info_gain = len(set(predicted_outcomes))
            hazard_penalty = 0.0 if action_safety[action.value] else self.safety_weight
            utility = info_gain + (self.novelty_weight * novelty) - hazard_penalty

            action_utilities[action.value] = utility

            if utility > best_utility:
                best_utility = utility
                best_action = action

        if best_action is None:
            best_action = candidate_actions[0]

        self.action_history.append((obs.agent_pos, best_action))

        plan_info = {
            "selected_action": best_action.value,
            "best_utility": round(best_utility, 4),
            "action_utilities": {k: round(v, 4) for k, v in action_utilities.items()},
            "action_safety": action_safety,
            "macro_plan": False,
        }
        return best_action, plan_info
