"""Symbolic hypothesis space, consistency scoring, and hypothesis tracker."""

from typing import List, Tuple, Dict, Any, Optional
import math
from arc_explorer.environment import Observation, Action, Color, ACTION_DELTAS


class BaseHypothesis:
    """Base class for symbolic candidate hypotheses."""

    def __init__(self, hyp_id: str, name: str, complexity: float = 1.0):
        self.hyp_id = hyp_id
        self.name = name
        self.complexity = complexity  # Complexity score for Occam simplicity prior
        self.score: float = 1.0  # Initial prior
        self.consistent_steps: int = 0
        self.evaluated_steps: int = 0

    def predict(
        self, obs: Observation, action: Action
    ) -> Tuple[List[List[int]], bool]:
        """
        Predicts expected next grid state and hazard alert.
        Returns (predicted_grid_2d, predicted_hazard_bool).
        """
        raise NotImplementedError

    def evaluate_consistency(
        self, obs_before: Observation, action: Action, obs_after: Observation
    ) -> bool:
        """Checks if transition matches hypothesis prediction exactly."""
        pred_grid, pred_hazard = self.predict(obs_before, action)
        actual_grid = [list(row) for row in obs_after.grid]
        actual_hazard = obs_after.hazard_alert

        grid_match = pred_grid == actual_grid
        hazard_match = pred_hazard == actual_hazard
        return grid_match and hazard_match

    def reset_stats(self):
        self.score = 1.0
        self.consistent_steps = 0
        self.evaluated_steps = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.hyp_id,
            "name": self.name,
            "complexity": self.complexity,
            "score": round(self.score, 4),
            "consistent_steps": self.consistent_steps,
            "evaluated_steps": self.evaluated_steps,
        }


# --- Generic Standard Movement Hypothesis (Default baseline) ---
class DefaultPhysicsHypothesis(BaseHypothesis):
    """Standard grid physics: movement shifts agent if target is empty, INTERACT/INSPECT does nothing."""

    def __init__(self):
        super().__init__("h_default", "Default Standard Grid Physics", complexity=0.5)

    def predict(
        self, obs: Observation, action: Action
    ) -> Tuple[List[List[int]], bool]:
        grid = [list(row) for row in obs.grid]
        if action in ACTION_DELTAS:
            dr, dc = ACTION_DELTAS[action]
            nr, nc = obs.agent_pos[0] + dr, obs.agent_pos[1] + dc
            if 0 <= nr < obs.height and 0 <= nc < obs.width:
                target_cell = obs.grid[nr][nc]
                if target_cell == Color.GRAY or target_cell == Color.GREEN:
                    # Gray wall or un-triggered hazard barrier
                    return grid, True
        return grid, False


# --- Scenario 1 Hypotheses: Color Propagation & Shift ---
class ColorShiftPropagationHypothesis(BaseHypothesis):
    """Hypothesis: Pushing adjacent RED cell propagates RED tile forward; pushing BLUE cell reflects BLUE vertically."""

    def __init__(self):
        super().__init__(
            "h_color_propagation",
            "Adjacent RED propagates on push; BLUE reflects vertically",
            complexity=1.2,
        )

    def predict(
        self, obs: Observation, action: Action
    ) -> Tuple[List[List[int]], bool]:
        grid = [list(row) for row in obs.grid]
        hazard = False

        if action in ACTION_DELTAS:
            dr, dc = ACTION_DELTAS[action]
            r, c = obs.agent_pos
            nr, nc = r + dr, c + dc

            if 0 <= nr < obs.height and 0 <= nc < obs.width:
                target_color = obs.grid[nr][nc]

                if target_color == Color.RED:
                    # RED propagates forward into next space if empty
                    nnr, nnc = nr + dr, nc + dc
                    if 0 <= nnr < obs.height and 0 <= nnc < obs.width:
                        if obs.grid[nnr][nnc] == Color.EMPTY:
                            grid[nnr][nnc] = Color.RED
                elif target_color == Color.BLUE:
                    # BLUE reflects across vertical axis
                    grid[nr][nc] = Color.EMPTY
                    grid[obs.height - 1 - nr][nc] = Color.BLUE
                elif target_color == Color.GRAY:
                    hazard = True

        return grid, hazard


# --- Scenario 2 Hypotheses: Key/Door Trigger Sequence ---
class TriggerBarrierHypothesis(BaseHypothesis):
    """Hypothesis: Interacting with YELLOW trigger unlocks GREEN barrier into EMPTY space."""

    def __init__(self):
        super().__init__(
            "h_trigger_barrier",
            "INTERACT on YELLOW trigger clears GREEN barrier; stepping on GREEN before trigger causes hazard",
            complexity=1.5,
        )

    def predict(
        self, obs: Observation, action: Action
    ) -> Tuple[List[List[int]], bool]:
        grid = [list(row) for row in obs.grid]
        hazard = False

        r, c = obs.agent_pos

        if action == Action.INTERACT:
            if obs.grid[r][c] == Color.YELLOW or any(
                obs.get_cell(r + dr, c + dc) == Color.YELLOW for dr, dc in ACTION_DELTAS.values()
            ):
                # Replace all GREEN barriers with EMPTY
                for gr in range(obs.height):
                    for gc in range(obs.width):
                        if grid[gr][gc] == Color.GREEN:
                            grid[gr][gc] = Color.EMPTY

        elif action in ACTION_DELTAS:
            dr, dc = ACTION_DELTAS[action]
            nr, nc = r + dr, c + dc
            if 0 <= nr < obs.height and 0 <= nc < obs.width:
                if obs.grid[nr][nc] == Color.GREEN:
                    hazard = True  # Crossing locked barrier yields hazard

        return grid, hazard


# --- Scenario 3 Hypotheses: Axial Pattern Completion ---
class SymmetricPatternFillHypothesis(BaseHypothesis):
    """Hypothesis: INTERACT on colored cell mirrors color to horizontal reflection (r, W-1-c)."""

    def __init__(self):
        super().__init__(
            "h_symmetric_pattern",
            "INTERACT on cell (r,c) copies color to horizontal symmetric position (r, W-1-c)",
            complexity=1.4,
        )

    def predict(
        self, obs: Observation, action: Action
    ) -> Tuple[List[List[int]], bool]:
        grid = [list(row) for row in obs.grid]
        hazard = False

        r, c = obs.agent_pos

        if action == Action.INTERACT:
            current_color = obs.grid[r][c]
            if current_color != Color.EMPTY:
                mirror_c = obs.width - 1 - c
                grid[r][mirror_c] = current_color

        return grid, hazard


class IncorrectAlternativeHypothesis(BaseHypothesis):
    """Control hypothesis: INTERACT clears surrounding grid cells (incorrect rule for testing contrast)."""

    def __init__(self):
        super().__init__(
            "h_incorrect_alt",
            "INTERACT clears adjacent non-empty tiles",
            complexity=2.5,
        )

    def predict(
        self, obs: Observation, action: Action
    ) -> Tuple[List[List[int]], bool]:
        grid = [list(row) for row in obs.grid]
        if action == Action.INTERACT:
            r, c = obs.agent_pos
            for dr, dc in ACTION_DELTAS.values():
                nr, nc = r + dr, c + dc
                if 0 <= nr < obs.height and 0 <= nc < obs.width:
                    grid[nr][nc] = Color.EMPTY
        return grid, False


class HypothesisTracker:
    """Tracks, evaluates, and ranks candidate hypotheses based on evidence and simplicity priors."""

    def __init__(self, candidates: Optional[List[BaseHypothesis]] = None):
        self.candidates: List[BaseHypothesis] = candidates or [
            DefaultPhysicsHypothesis(),
            ColorShiftPropagationHypothesis(),
            TriggerBarrierHypothesis(),
            SymmetricPatternFillHypothesis(),
            IncorrectAlternativeHypothesis(),
        ]

    def update(
        self, obs_before: Observation, action: Action, obs_after: Observation
    ) -> None:
        """Evaluates all candidate hypotheses on the latest state-action transition."""
        for hyp in self.candidates:
            is_consistent = hyp.evaluate_consistency(obs_before, action, obs_after)
            hyp.evaluated_steps += 1
            if is_consistent:
                hyp.consistent_steps += 1

            # Consistency ratio dominates; complexity prior acts as tie-breaker
            ratio = hyp.consistent_steps / max(1, hyp.evaluated_steps)
            tie_breaker = 1.0 - (0.02 * hyp.complexity)
            hyp.score = ratio * max(0.1, tie_breaker)


    def get_rankings(self) -> List[BaseHypothesis]:
        return sorted(self.candidates, key=lambda h: h.score, reverse=True)

    def get_best_hypothesis(self) -> BaseHypothesis:
        return self.get_rankings()[0]

    def confidence(self) -> float:
        rankings = self.get_rankings()
        if not rankings:
            return 0.0
        best_score = rankings[0].score
        if len(rankings) == 1 or best_score == 0.0:
            return best_score
        second_score = rankings[1].score
        # Margin of separation between top hypothesis and runner up
        return min(1.0, max(0.0, best_score - second_score + (rankings[0].consistent_steps / max(1, rankings[0].evaluated_steps))))

