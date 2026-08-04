"""Unit tests for Streamlit UI helper module."""

import os
import tempfile
from arc_explorer.ui_helpers import (
    render_grid_html,
    run_benchmark_evaluation,
    list_available_replays,
    load_and_verify_replay,
    scan_all_task_folders,
    resolve_task_folder_path,
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
        assert len(data["trace_logs"]) == 1  # Single-step trace verification


def test_single_step_and_empty_grid_rendering():
    # Single element grid
    html_single = render_grid_html([[1]], (0, 0))
    assert "🤖" in html_single
    assert "Blue" in html_single

    # Empty grid boundary check
    html_empty = render_grid_html([], (0, 0))
    assert "<div" in html_empty


def test_task_folder_detection_and_resolution():
    """Test scan_all_task_folders and resolve_task_folder_path using an
    isolated temporary directory so the test never depends on the size
    of the user's local ARC dataset."""
    import json

    num_fixture_files = 5

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a known sub-folder with fixture JSON files
        task_dir = os.path.join(tmpdir, "tasks", "arc_training")
        os.makedirs(task_dir)
        for i in range(num_fixture_files):
            fpath = os.path.join(task_dir, f"task_{i:04d}.json")
            with open(fpath, "w") as f:
                json.dump({"train": [], "test": []}, f)

        # scan_all_task_folders should discover the fixture folder
        detected = scan_all_task_folders(tmpdir)
        assert "tasks/arc_training" in detected
        assert detected["tasks/arc_training"] == num_fixture_files

        # resolve_task_folder_path – valid relative path
        abs_p, exists, count, msg = resolve_task_folder_path("tasks/arc_training", tmpdir)
        assert exists
        assert count == num_fixture_files
        assert f"Found {num_fixture_files} ARC task JSON files" in msg

        # resolve_task_folder_path – non-existent path
        _, exists_bad, count_bad, msg_bad = resolve_task_folder_path(
            "non_existent_folder_xyz", tmpdir
        )
        assert not exists_bad
        assert count_bad == 0
        assert "Folder not found" in msg_bad
