"""Safe Experiment Planner balancing information gain against predicted environmental hazards."""

from typing import Dict, Any, List, Tuple
from arc_explorer.environment import Observation, Action
from arc_explorer.hypothesis import HypothesisTracker


class SafePlanner:
    """Planner that selects informative actions while respecting safety constraints."""

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

    def select_action(
        self, obs: Observation, tracker: HypothesisTracker, visited_positions: List[Tuple[int, int]]
    ) -> Tuple[Action, Dict[str, Any]]:
        if obs.step == 1 or len(visited_positions) <= 1:
            self.action_history.clear()

        rankings = tracker.get_rankings()
        all_actions = list(Action)

        best_action = None
        best_utility = -float("inf")
        action_utilities: Dict[str, float] = {}
        action_safety: Dict[str, bool] = {}

        # 1. Compute safety for all actions
        for action in all_actions:
            max_hazard_prob = 0.0
            for hyp in rankings:
                if hyp.score > 0.1:
                    _, pred_hazard = hyp.predict(obs, action)
                    if pred_hazard:
                        max_hazard_prob = max(max_hazard_prob, hyp.score)

            # Check for grid boundaries / gray walls in default physics
            if action in [Action.MOVE_UP, Action.MOVE_DOWN, Action.MOVE_LEFT, Action.MOVE_RIGHT]:
                dr, dc = {"MOVE_UP": (-1, 0), "MOVE_DOWN": (1, 0), "MOVE_LEFT": (0, -1), "MOVE_RIGHT": (0, 1)}[action.value]
                target_cell = obs.get_cell(obs.agent_pos[0] + dr, obs.agent_pos[1] + dc)
                if target_cell == 5:  # Color.GRAY wall
                    max_hazard_prob = 1.0

            is_safe = max_hazard_prob < self.hazard_threshold
            action_safety[action.value] = is_safe

        # 2. Filter candidate actions: prioritize safe actions if available
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
                # Object interaction bonus if standing on or near non-empty tile
                r, c = obs.agent_pos
                current_color = obs.get_cell(r, c)
                adj_colors = [obs.get_cell(r + dr, c + dc) for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]]
                action_pos_count = sum(1 for p, a in self.action_history if p == (r, c) and a == action)

                if current_color not in [0, 5] or any(c not in [0, 5] for c in adj_colors):
                    novelty = 1.5 / (1.0 + action_pos_count)

                # Zero out novelty for interactions at positions where no change occurred
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
        }
        return best_action, plan_info

