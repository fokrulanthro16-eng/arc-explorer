"""Unit tests for Streamlit UI helper module."""

import os
import tempfile
from arc_explorer.ui_helpers import (
    render_grid_html,
    run_benchmark_evaluation,
    list_available_replays,
    load_and_verify_replay,
)
from arc_explorer.agent import ExplorerAgent
from arc_explorer.scenarios import create_scenario_1
from arc_explorer.replay import ReplayLogger


def test_render_grid_html():
    grid = [[0, 1], [2, 3]]
    agent_pos = (0, 0)
    html = render_grid_html(grid, agent_pos)

    assert "<div" in html
    assert "🤖" in html  # Agent icon marker
    assert "Empty" in html
    assert "Blue" in html


def test_run_benchmark_evaluation_dynamic():
    res = run_benchmark_evaluation()

    assert "overall_score" in res
    assert "scenario_results" in res
    assert len(res["scenario_results"]) == 3
    assert res["total_passed"] == 3
    assert res["overall_score"] > 80.0

    # Ensure scores are dynamic numbers, not hardcoded strings
    for sc in res["scenario_results"]:
        assert isinstance(sc["score"], float)
        assert sc["passed"] is True
        assert sc["hazards"] == 0


def test_replay_helpers():
    env = create_scenario_1()
    agent = ExplorerAgent()
    result = agent.run_exploration(env)

    with tempfile.TemporaryDirectory() as tmpdir:
        replay_file = os.path.join(tmpdir, "ui_test_replay.json")
        ReplayLogger.save_replay(replay_file, result, memory=agent.memory, scenario_name="UI Test")

        replays = list_available_replays(tmpdir)
        assert len(replays) == 1
        assert replays[0] == replay_file

        success, data, err = load_and_verify_replay(replay_file)
        assert success is True
        assert err == ""
        assert data["summary"]["inferred_rule_id"] == "h_color_propagation"
