"""Unit tests for ARC Prize / Kaggle competition evaluation and submission pipeline."""

import os
import json
import tempfile
import pytest
from arc_explorer.evaluator import BatchEvaluator
from arc_explorer.dataset_audit import audit_dataset_folder, validate_grid
from arc_explorer.submission import generate_submission, validate_submission_file
from arc_explorer.failure_clustering import cluster_failed_task, categorize_failed_tasks


def test_validate_grid():
    # Valid grid
    assert validate_grid([[0, 1], [2, 3]])
    # Invalid: non-integer
    assert not validate_grid([["a", 1], [2, 3]])
    # Invalid: value out of 0-9
    assert not validate_grid([[0, 10], [2, 3]])
    # Invalid: non-rectangular
    assert not validate_grid([[0, 1], [2]])
    # Invalid: empty
    assert not validate_grid([])


def test_dataset_audit():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create valid task file
        valid_file = os.path.join(tmpdir, "001.json")
        with open(valid_file, "w", encoding="utf-8") as f:
            json.dump({
                "train": [{"input": [[1]], "output": [[1]]}],
                "test": [{"input": [[1]]}]
            }, f)

        # Create malformed task file
        malformed_file = os.path.join(tmpdir, "002.json")
        with open(malformed_file, "w", encoding="utf-8") as f:
            f.write("{invalid json...")

        report = audit_dataset_folder(tmpdir)
        assert report.total_files == 2
        assert report.valid_tasks == 1
        assert len(report.malformed_files) == 1


def test_full_folder_evaluation_and_reports():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create sample task
        t_path = os.path.join(tmpdir, "0520f9ce.json")
        with open(t_path, "w", encoding="utf-8") as f:
            json.dump({
                "train": [{"input": [[1, 1], [1, 0]], "output": [[1, 1], [1, 2]]}],
                "test": [{"input": [[1, 1], [1, 0]]}]
            }, f)

        out_reports_dir = os.path.join(tmpdir, "reports")
        report = BatchEvaluator.evaluate_folder(folder_path=tmpdir)
        assert report.total_tasks == 1
        assert report.completed_tasks == 1

        res_files = report.export_full_training_reports(output_dir=out_reports_dir)
        assert os.path.exists(res_files["csv"])
        assert os.path.exists(res_files["markdown"])
        assert os.path.exists(res_files["failures"])


def test_multi_test_pair_submission_and_validation():
    with tempfile.TemporaryDirectory() as tmpdir:
        task_file = os.path.join(tmpdir, "multi_test.json")
        with open(task_file, "w", encoding="utf-8") as f:
            json.dump({
                "train": [{"input": [[1, 2]], "output": [[2, 1]]}],
                "test": [
                    {"input": [[3, 4]]},
                    {"input": [[5, 6]]}
                ]
            }, f)

        sub_file = os.path.join(tmpdir, "submission.json")
        sub_data = generate_submission(tmpdir, sub_file)

        assert "multi_test" in sub_data
        assert len(sub_data["multi_test"]) == 2
        assert "attempt_1" in sub_data["multi_test"][0]
        assert "attempt_2" in sub_data["multi_test"][0]

        is_valid, errors = validate_submission_file(tmpdir, sub_file)
        assert is_valid, f"Validation failed with errors: {errors}"

        assert len(errors) == 0


def test_submission_validation_errors():
    with tempfile.TemporaryDirectory() as tmpdir:
        task_file = os.path.join(tmpdir, "task_err.json")
        with open(task_file, "w", encoding="utf-8") as f:
            json.dump({
                "train": [{"input": [[1]], "output": [[1]]}],
                "test": [{"input": [[1]]}]
            }, f)

        sub_file = os.path.join(tmpdir, "bad_submission.json")

        # Missing task ID
        with open(sub_file, "w", encoding="utf-8") as f:
            json.dump({}, f)
        is_valid, errors = validate_submission_file(tmpdir, sub_file)
        assert not is_valid
        assert any("Missing task ID" in err for err in errors)

        # Invalid grid cell value (out of 0-9 range)
        with open(sub_file, "w", encoding="utf-8") as f:
            json.dump({
                "task_err": [{"attempt_1": [[99]], "attempt_2": [[1]]}]
            }, f)
        is_valid, errors = validate_submission_file(tmpdir, sub_file)
        assert not is_valid
        assert any("invalid grid" in err.lower() for err in errors)


def test_failure_clustering():
    class MockTask:
        train_pairs = []

    class MockResult:
        task_id = "test_fail"
        task = MockTask()
        failure_reason = "Exact grid match not achieved"

    clusters = categorize_failed_tasks([MockResult()])
    assert "unknown / unclassified" in clusters
    assert "test_fail" in clusters["unknown / unclassified"]
