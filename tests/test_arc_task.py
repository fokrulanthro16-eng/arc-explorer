"""Unit tests for ARC task parser and environment adapter."""

import os
from arc_explorer.arc_task import ARCTask, ARCTaskRule, create_arc_task_environment
from arc_explorer.agent import ExplorerAgent
from arc_explorer.environment import Action


def test_arc_task_loading():
    sample_path = "samples/arc_task_color_swap.json"
    assert os.path.exists(sample_path)

    task = ARCTask.load_from_file(sample_path)
    assert task.task_id == "arc_task_color_swap"
    assert len(task.train_pairs) == 1
    assert len(task.test_pairs) == 1
    assert task.train_pairs[0].input_height == 3
    assert task.train_pairs[0].input_width == 3


def test_arc_task_environment_creation_and_step():
    sample_path = "samples/arc_task_color_swap.json"
    task = ARCTask.load_from_file(sample_path)
    env = create_arc_task_environment(task, pair_type="train", index=0)

    obs = env.reset()
    assert obs.step == 0
    assert obs.agent_pos == (0, 0)
    assert obs.grid[0][1] == 1  # Input has color 1 at (0,1)

    # Step interact on target cell (0,1) which has target color 2
    env.step(Action.MOVE_RIGHT)
    obs_after = env.step(Action.INTERACT)

    assert obs_after.grid[0][1] == 2  # Transformed to target color 2


def test_arc_task_agent_exploration():
    sample_path = "samples/arc_task_color_swap.json"
    task = ARCTask.load_from_file(sample_path)
    env = create_arc_task_environment(task, pair_type="train", index=0, max_steps=10)

    agent = ExplorerAgent()
    result = agent.run_exploration(env)

    assert result["total_steps"] > 0
    assert "inferred_rule_id" in result
    assert result["hazard_count"] == 0
