"""Unit tests for ReplayLogger trace saving, loading, verification, and summary formatting."""

import os
import tempfile
from arc_explorer.agent import ExplorerAgent
from arc_explorer.scenarios import create_scenario_1
from arc_explorer.replay import ReplayLogger


def test_replay_save_load_verify():
    env = create_scenario_1()
    agent = ExplorerAgent()
    result = agent.run_exploration(env)

    with tempfile.TemporaryDirectory() as tmpdir:
        replay_path = os.path.join(tmpdir, "test_trace.json")
        saved_file = ReplayLogger.save_replay(replay_path, result, memory=agent.memory, scenario_name="Test Scenario")

        assert os.path.exists(saved_file)

        loaded_data = ReplayLogger.load_replay(saved_file)
        assert ReplayLogger.verify_replay(loaded_data) is True
        assert loaded_data["summary"]["inferred_rule_id"] == "h_color_propagation"

        summary_text = ReplayLogger.format_trace_summary(loaded_data)
        assert "REPLAY TRACE: Test Scenario" in summary_text
        assert "Inferred Rule" in summary_text
