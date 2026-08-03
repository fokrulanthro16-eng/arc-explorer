"""Unit tests for Hypothesis evaluation engine and Safe Planner."""

from arc_explorer.environment import Observation, Action, Color
from arc_explorer.hypothesis import (
    HypothesisTracker,
    ColorShiftPropagationHypothesis,
    TriggerBarrierHypothesis,
    DefaultPhysicsHypothesis,
)
from arc_explorer.planner import SafePlanner


def test_hypothesis_evaluation():
    tracker = HypothesisTracker()
    obs_before = Observation(
        grid=[
            [5, 5, 5],
            [0, 2, 0],
            [5, 5, 5],
        ],
        agent_pos=(1, 0),
        step=1,
    )
    obs_after = Observation(
        grid=[
            [5, 5, 5],
            [0, 2, 2],
            [5, 5, 5],
        ],
        agent_pos=(1, 1),
        step=2,
    )

    tracker.update(obs_before, Action.MOVE_RIGHT, obs_after)
    rankings = tracker.get_rankings()

    assert rankings[0].hyp_id == "h_color_propagation"
    assert rankings[0].score > 0.5


def test_safe_planner_hazard_avoidance():
    tracker = HypothesisTracker([TriggerBarrierHypothesis()])
    planner = SafePlanner(hazard_threshold=0.2)

    # Grid with GREEN barrier (Color.GREEN = 3) at (0, 1)
    obs = Observation(
        grid=[
            [0, 3],
            [0, 0],
        ],
        agent_pos=(0, 0),
        step=1,
    )

    # Green barrier produces hazard under TriggerBarrierHypothesis
    action, info = planner.select_action(obs, tracker, [(0, 0)])
    assert info["action_safety"]["MOVE_RIGHT"] is False
    assert action != Action.MOVE_RIGHT
