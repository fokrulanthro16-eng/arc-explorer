"""Submission Generator & Validator for ARC Prize / Kaggle competition workflows."""

import os
import json
from typing import Dict, List, Any, Tuple
from arc_explorer.arc_task import ARCTask
from arc_explorer.symbolic import SymbolicHypothesisGraph, IdentityOperator, SymbolicHypothesis
from arc_explorer.dataset_audit import validate_grid


def generate_submission(task_folder: str, output_filepath: str) -> Dict[str, Any]:
    """Generates an ARC Prize competition submission JSON file for all tasks in task_folder."""
    if not os.path.exists(task_folder) or not os.path.isdir(task_folder):
        raise ValueError(f"Task folder does not exist: {task_folder}")

    sub_basename = os.path.basename(output_filepath)
    filenames = sorted([f for f in os.listdir(task_folder) if f.endswith(".json") and f != sub_basename])
    submission: Dict[str, List[Dict[str, List[List[int]]]]] = {}


    for fname in filenames:
        fpath = os.path.join(task_folder, fname)
        task_id = fname[:-5]

        try:
            task = ARCTask.load_from_file(fpath)
        except Exception:
            # Fallback for malformed task files
            submission[task_id] = [{"attempt_1": [[0]], "attempt_2": [[0]]}]
            continue


        # Infer symbolic rule pipeline from training pairs
        graph = SymbolicHypothesisGraph()
        best_hyp = graph.build_and_evaluate(task.train_pairs)

        test_predictions: List[Dict[str, List[List[int]]]] = []

        # Load raw test pairs to preserve all test inputs
        with open(fpath, "r", encoding="utf-8") as fp:
            raw_data = json.load(fp)
        raw_test_pairs = raw_data.get("test", [])

        if not raw_test_pairs:
            raw_test_pairs = [{"input": [[0]]}]

        for pair_data in raw_test_pairs:
            input_grid = pair_data.get("input", [[0]])
            if not validate_grid(input_grid):
                input_grid = [[0]]

            try:
                pred_grid = best_hyp.execute(input_grid)
                if not validate_grid(pred_grid):
                    pred_grid = [list(r) for r in input_grid]
            except Exception:
                pred_grid = [list(r) for r in input_grid]

            test_predictions.append({
                "attempt_1": pred_grid,
                "attempt_2": pred_grid,
            })

        submission[task_id] = test_predictions

    os.makedirs(os.path.dirname(os.path.abspath(output_filepath)), exist_ok=True)
    with open(output_filepath, "w", encoding="utf-8") as fp:
        json.dump(submission, fp, indent=2)

    return submission


def validate_submission_file(task_folder: str, submission_filepath: str) -> Tuple[bool, List[str]]:
    """Validates an offline ARC submission JSON file against task_folder requirements."""
    errors: List[str] = []

    if not os.path.exists(submission_filepath):
        return False, [f"Submission file does not exist: {submission_filepath}"]

    try:
        with open(submission_filepath, "r", encoding="utf-8") as fp:
            submission = json.load(fp)
    except Exception as e:
        return False, [f"Invalid JSON in submission file: {str(e)}"]

    if not isinstance(submission, dict):
        return False, ["Submission root must be a JSON object (dict)"]

    sub_basename = os.path.basename(submission_filepath)
    filenames = sorted([f for f in os.listdir(task_folder) if f.endswith(".json") and f != sub_basename])


    for fname in filenames:
        task_id = fname[:-5]
        fpath = os.path.join(task_folder, fname)

        if task_id not in submission:
            errors.append(f"Missing task ID '{task_id}' in submission")
            continue

        pred_list = submission[task_id]
        if not isinstance(pred_list, list) or len(pred_list) == 0:
            errors.append(f"Task '{task_id}' prediction must be a non-empty list of prediction objects")
            continue

        with open(fpath, "r", encoding="utf-8") as fp:
            raw_data = json.load(fp)
        raw_test_pairs = raw_data.get("test", [])
        expected_test_count = len(raw_test_pairs) if raw_test_pairs else 1

        if len(pred_list) != expected_test_count:
            errors.append(
                f"Task '{task_id}' has {expected_test_count} test pairs, but submission provides {len(pred_list)}"
            )

        # Collect training output grids to detect data leaks
        train_outputs = [pair.get("output") for pair in raw_data.get("train", []) if "output" in pair]

        for idx, pred_obj in enumerate(pred_list):
            if not isinstance(pred_obj, dict):
                errors.append(f"Task '{task_id}' prediction item [{idx}] is not an object")
                continue

            if "attempt_1" not in pred_obj or "attempt_2" not in pred_obj:
                errors.append(f"Task '{task_id}' prediction item [{idx}] must contain 'attempt_1' and 'attempt_2'")
                continue

            for attempt_key in ["attempt_1", "attempt_2"]:
                grid = pred_obj[attempt_key]
                if not validate_grid(grid):
                    errors.append(
                        f"Task '{task_id}' {attempt_key} item [{idx}] is an invalid grid (non-rectangular, empty, or cells outside 0-9)"
                    )
                # Check for training data leakage (if test input is not identical to train input)
                if expected_test_count > 0 and len(train_outputs) > 0:
                    # Target leak check: If attempt grid equals training output but test input != train input
                    test_in = raw_test_pairs[idx].get("input") if idx < len(raw_test_pairs) else None
                    for train_pair in raw_data.get("train", []):
                        if grid == train_pair.get("output") and test_in != train_pair.get("input") and grid != test_in:
                            errors.append(
                                f"Task '{task_id}' {attempt_key} item [{idx}] leaked training output target"
                            )

    is_valid = len(errors) == 0
    return is_valid, errors
