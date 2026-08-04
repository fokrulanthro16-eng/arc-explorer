"""Unit tests for Macro-Action Planner in ARC Explorer."""

import os
from arc_explorer.planner import SafePlanner, MacroGoal, compute_path_actions
from arc_explorer.environment import Action, Observation
from arc_explorer.hypothesis import HypothesisTracker
from arc_explorer.arc_task import ARCTask, create_arc_task_environment
from arc_explorer.agent import ExplorerAgent


def test_compute_path_actions():
    grid = (
        (0, 0, 0),
        (0, 5, 0),  # 5 is Color.GRAY wall
        (0, 0, 0),
    )
    start_pos = (0, 0)
    target_pos = (2, 2)

    path = compute_path_actions(start_pos, target_pos, grid)
    assert len(path) > 0
    # Verify path avoids obstacle at (1, 1)
    current_pos = list(start_pos)
    for act in path:
        dr, dc = {"MOVE_UP": (-1, 0), "MOVE_DOWN": (1, 0), "MOVE_LEFT": (0, -1), "MOVE_RIGHT": (0, 1)}[act.value]
        current_pos[0] += dr
        current_pos[1] += dc
        assert (current_pos[0], current_pos[1]) != (1, 1)

    assert tuple(current_pos) == target_pos


def test_macro_plan_generation_and_execution():
    planner = SafePlanner()
    target_grid = [
        [0, 2],
        [0, 0],
    ]
    obs = Observation(
        grid=[[0, 1], [0, 0]],
        agent_pos=(0, 0),
        step=1,
        info={"target_output_grid": target_grid},
    )

    macro = planner.generate_macro_plan(obs)
    assert macro is not None
    goal, sequence = macro
    assert goal.target_pos == (0, 1)
    assert sequence == [Action.MOVE_RIGHT, Action.INTERACT]

    tracker = HypothesisTracker()
    act1, info1 = planner.select_action(obs, tracker, [(0, 0)])
    assert act1 == Action.MOVE_RIGHT
    assert info1["macro_plan"] is True


def test_macro_planner_on_reflection_task():
    sample_path = "samples/arc_task_reflection.json"
    assert os.path.exists(sample_path)

    task = ARCTask.load_from_file(sample_path)
    env = create_arc_task_environment(task, pair_type="train", index=0, max_steps=30)
    agent = ExplorerAgent()

    result = agent.run_exploration(env, max_steps=30)
    assert result["total_steps"] > 0
    assert env.grid == env.rule.target_output_grid
