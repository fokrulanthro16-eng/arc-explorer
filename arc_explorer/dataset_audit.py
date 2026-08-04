"""Dataset Audit Module for ARC Prize / Kaggle competition workflows."""

import os
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class DatasetAuditReport:
    folder_path: str
    total_files: int = 0
    valid_tasks: int = 0
    malformed_files: List[str] = field(default_factory=list)
    duplicate_task_ids: List[str] = field(default_factory=list)
    invalid_grid_tasks: List[str] = field(default_factory=list)
    missing_test_pairs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "folder_path": self.folder_path,
            "total_files": self.total_files,
            "valid_tasks": self.valid_tasks,
            "malformed_files": self.malformed_files,
            "duplicate_task_ids": self.duplicate_task_ids,
            "invalid_grid_tasks": self.invalid_grid_tasks,
            "missing_test_pairs": self.missing_test_pairs,
        }


def validate_grid(grid: Any) -> bool:
    """Validates that a grid is a non-empty rectangular 2D list of integers 0-9."""
    if not isinstance(grid, list) or len(grid) == 0:
        return False
    row_len = None
    for row in grid:
        if not isinstance(row, list) or len(row) == 0:
            return False
        if row_len is None:
            row_len = len(row)
        elif len(row) != row_len:
            return False
        for cell in row:
            if not isinstance(cell, int) or cell < 0 or cell > 9:
                return False
    return True


def audit_dataset_folder(folder_path: str) -> DatasetAuditReport:
    """Audits a dataset folder for valid ARC tasks, malformed files, duplicates, and invalid grids."""
    report = DatasetAuditReport(folder_path=folder_path)

    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        return report

    filenames = [f for f in os.listdir(folder_path) if f.endswith(".json")]
    report.total_files = len(filenames)

    seen_ids: Dict[str, str] = {}

    for fname in filenames:
        fpath = os.path.join(folder_path, fname)
        task_id = fname[:-5]

        if task_id in seen_ids:
            report.duplicate_task_ids.append(task_id)
        else:
            seen_ids[task_id] = fname

        try:
            with open(fpath, "r", encoding="utf-8") as fp:
                data = json.load(fp)
        except Exception:
            report.malformed_files.append(fname)
            continue

        if not isinstance(data, dict) or "train" not in data:
            report.malformed_files.append(fname)
            continue

        train_pairs = data.get("train", [])
        if not isinstance(train_pairs, list) or len(train_pairs) == 0:
            report.malformed_files.append(fname)
            continue

        valid_grids = True
        for pair in train_pairs:
            if not isinstance(pair, dict):
                valid_grids = False
                break
            if not validate_grid(pair.get("input")) or not validate_grid(pair.get("output")):
                valid_grids = False
                break

        test_pairs = data.get("test", [])
        if not isinstance(test_pairs, list) or len(test_pairs) == 0:
            report.missing_test_pairs.append(fname)

        for pair in test_pairs:
            if isinstance(pair, dict) and "input" in pair:
                if not validate_grid(pair.get("input")):
                    valid_grids = False
                if "output" in pair and pair.get("output") is not None:
                    if not validate_grid(pair.get("output")):
                        valid_grids = False

        if not valid_grids:
            report.invalid_grid_tasks.append(fname)
        else:
            report.valid_tasks += 1

    return report
