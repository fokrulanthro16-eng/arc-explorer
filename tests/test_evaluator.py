"""Unit tests for ARC Task Batch Evaluation Engine."""

import os
import json
import tempfile
import sys
from unittest.mock import patch
from arc_explorer.evaluator import BatchEvaluator, BatchEvalReport, TaskEvalResult
from arc_explorer.cli import main


def test_evaluator_valid_task():
    sample_path = "samples/arc_task_color_swap.json"
    assert os.path.exists(sample_path)

    res = BatchEvaluator.evaluate_single_file(sample_path)
    assert res.status == "COMPLETED"
    assert res.prediction_available is True
    assert res.exact_match is True
    assert res.runtime_sec > 0.0
    assert res.failure_reason == ""


def test_evaluator_malformed_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_json_file = os.path.join(tmpdir, "bad_syntax.json")
        with open(bad_json_file, "w", encoding="utf-8") as f:
            f.write("{ invalid json syntax ... ")

        res = BatchEvaluator.evaluate_single_file(bad_json_file)
        assert res.status == "ERROR"
        assert res.prediction_available is False
        assert res.exact_match is False
        assert "JSON Parse Error" in res.failure_reason


def test_evaluator_missing_fields_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        missing_fields_file = os.path.join(tmpdir, "missing_train.json")
        with open(missing_fields_file, "w", encoding="utf-8") as f:
            json.dump({"foo": "bar"}, f)

        res = BatchEvaluator.evaluate_single_file(missing_fields_file)
        assert res.status == "ERROR"
        assert res.prediction_available is False
        assert res.exact_match is False
        assert "Missing training pairs" in res.failure_reason


def test_evaluator_batch_folder_and_reports():
    with tempfile.TemporaryDirectory() as tmpdir:
        report = BatchEvaluator.evaluate_folder("samples")

        assert report.total_tasks >= 2
        assert report.completed_tasks >= 2
        assert report.exact_match_pct == 100.0
        assert report.exact_matches == 2
        assert report.avg_runtime_sec > 0.0
        assert report.median_runtime_sec > 0.0

        json_file = report.export_json(output_dir=tmpdir)
        csv_file = report.export_csv(output_dir=tmpdir)

        assert os.path.exists(json_file)
        assert os.path.exists(csv_file)

        with open(json_file, "r", encoding="utf-8") as f:
            j_data = json.load(f)
            assert j_data["metrics"]["total_tasks"] == report.total_tasks

        with open(csv_file, "r", encoding="utf-8") as f:
            csv_lines = f.readlines()
            assert len(csv_lines) >= 3
            assert "task_id" in csv_lines[0]




def test_cli_evaluate_command():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_args = ["arc-explorer", "evaluate", "--folder", "samples", "--output", tmpdir]
        with patch.object(sys, "argv", test_args):
            main()

        files = os.listdir(tmpdir)
        assert any(f.endswith(".json") for f in files)
        assert any(f.endswith(".csv") for f in files)
