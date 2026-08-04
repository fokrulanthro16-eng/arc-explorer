"""ARC Task Batch Evaluation Engine for automated evaluation of ARC JSON tasks."""

import os
import json
import time
import statistics
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Tuple
from arc_explorer.arc_task import ARCTask, create_arc_task_environment
from arc_explorer.agent import ExplorerAgent
from arc_explorer.symbolic import SymbolicHypothesisGraph



class TaskEvalResult:
    """Evaluation result record for a single ARC JSON task."""

    def __init__(
        self,
        task_id: str,
        filename: str,
        status: str,
        prediction_available: bool,
        exact_match: bool,
        runtime_sec: float,
        failure_reason: str = "",
        inferred_rule_id: str = "N/A",
        inferred_rule_name: str = "N/A",
        discovery_score: float = 0.0,
        predicted_grid: Optional[List[List[int]]] = None,
        expected_grid: Optional[List[List[int]]] = None,
    ):
        self.task_id = task_id
        self.filename = filename
        self.status = status  # "COMPLETED", "FAILED", "ERROR"
        self.prediction_available = prediction_available
        self.exact_match = exact_match
        self.runtime_sec = round(runtime_sec, 4)
        self.failure_reason = failure_reason
        self.inferred_rule_id = inferred_rule_id
        self.inferred_rule_name = inferred_rule_name
        self.discovery_score = round(discovery_score, 2)
        self.predicted_grid = predicted_grid
        self.expected_grid = expected_grid

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "filename": self.filename,
            "status": self.status,
            "prediction_available": self.prediction_available,
            "exact_match": self.exact_match,
            "runtime_sec": self.runtime_sec,
            "failure_reason": self.failure_reason,
            "inferred_rule_id": self.inferred_rule_id,
            "inferred_rule_name": self.inferred_rule_name,
            "discovery_score": self.discovery_score,
            "predicted_grid": self.predicted_grid,
            "expected_grid": self.expected_grid,
        }


class BatchEvalReport:
    """Summary report for a batch task evaluation run."""

    def __init__(
        self,
        folder_path: str,
        task_results: List[TaskEvalResult],
        total_runtime_sec: float,
    ):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.folder_path = folder_path
        self.task_results = task_results
        self.total_runtime_sec = round(total_runtime_sec, 4)

        self.total_tasks = len(task_results)
        self.completed_tasks = sum(1 for r in task_results if r.status == "COMPLETED")
        self.failed_tasks = sum(1 for r in task_results if r.status in ["FAILED", "ERROR"])
        self.exact_matches = sum(1 for r in task_results if r.exact_match)
        self.exact_match_pct = (
            round((self.exact_matches / self.total_tasks) * 100.0, 2)
            if self.total_tasks > 0
            else 0.0
        )

        runtimes = [r.runtime_sec for r in task_results]
        self.avg_runtime_sec = round(statistics.mean(runtimes), 4) if runtimes else 0.0
        self.median_runtime_sec = round(statistics.median(runtimes), 4) if runtimes else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "folder_path": self.folder_path,
            "metrics": {
                "total_tasks": self.total_tasks,
                "completed_tasks": self.completed_tasks,
                "failed_tasks": self.failed_tasks,
                "exact_matches": self.exact_matches,
                "exact_match_pct": self.exact_match_pct,
                "avg_runtime_sec": self.avg_runtime_sec,
                "median_runtime_sec": self.median_runtime_sec,
                "total_runtime_sec": self.total_runtime_sec,
            },
            "task_results": [r.to_dict() for r in self.task_results],
        }

    def export_json(self, output_dir: str = "reports") -> str:
        """Exports batch evaluation report to a JSON file."""
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, f"arc_batch_eval_{self.timestamp}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        return filepath

    def export_csv(self, output_dir: str = "reports") -> str:
        """Exports task-level evaluation summary table to a CSV file."""
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, f"arc_batch_eval_{self.timestamp}.csv")
        headers = [
            "task_id",
            "filename",
            "status",
            "prediction_available",
            "exact_match",
            "runtime_sec",
            "discovery_score",
            "inferred_rule_id",
            "inferred_rule_name",
            "failure_reason",
        ]

        lines = [",".join(headers)]
        for r in self.task_results:
            row = [
                f'"{r.task_id}"',
                f'"{r.filename}"',
                f'"{r.status}"',
                str(r.prediction_available),
                str(r.exact_match),
                str(r.runtime_sec),
                str(r.discovery_score),
                f'"{r.inferred_rule_id}"',
                f'"{r.inferred_rule_name}"',
                f'"{r.failure_reason}"',
            ]
            lines.append(",".join(row))

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return filepath


class BatchEvaluator:
    """Evaluator engine for batch execution of ARC JSON tasks."""

    @staticmethod
    def evaluate_single_file(filepath: str, max_steps: int = 30) -> TaskEvalResult:
        """Evaluates a single ARC JSON task file."""
        filename = os.path.basename(filepath)
        start_time = time.time()

        if not os.path.exists(filepath):
            return TaskEvalResult(
                task_id=filename,
                filename=filename,
                status="ERROR",
                prediction_available=False,
                exact_match=False,
                runtime_sec=time.time() - start_time,
                failure_reason=f"File not found: {filepath}",
            )

        try:
            task = ARCTask.load_from_file(filepath)
        except Exception as e:
            return TaskEvalResult(
                task_id=os.path.splitext(filename)[0],
                filename=filename,
                status="ERROR",
                prediction_available=False,
                exact_match=False,
                runtime_sec=time.time() - start_time,
                failure_reason=f"JSON Parse Error: {str(e)}",
            )

        if not task.train_pairs:
            return TaskEvalResult(
                task_id=task.task_id,
                filename=filename,
                status="ERROR",
                prediction_available=False,
                exact_match=False,
                runtime_sec=time.time() - start_time,
                failure_reason="Missing training pairs ('train' field empty or absent)",
            )

        try:
            # 1. Build & Evaluate Symbolic Hypothesis Graph on all training pairs
            graph = SymbolicHypothesisGraph()
            best_hyp = graph.build_and_evaluate(task.train_pairs)

            env = create_arc_task_environment(task, pair_type="train", index=0, max_steps=max_steps)
            agent = ExplorerAgent()
            result = agent.run_exploration(env, max_steps=max_steps)

            runtime = time.time() - start_time
            predicted_grid = [list(r) for r in env.grid]
            expected_grid = env.rule.target_output_grid

            exact_match = False
            if expected_grid is not None:
                exact_match = (predicted_grid == expected_grid)

            is_completed = result["rule_discovered"] or (exact_match and result["hazard_count"] == 0)
            status = "COMPLETED" if is_completed else "FAILED"
            failure_reason = "" if is_completed else (
                f"Hazards hit: {result['hazard_count']}" if result["hazard_count"] > 0 else "Exact grid match not achieved"
            )

            # Export symbolic reasoning trace for solved task
            if exact_match and graph.solved_trace:
                os.makedirs("replays", exist_ok=True)
                trace_file = os.path.join("replays", f"symbolic_trace_{task.task_id}.json")
                with open(trace_file, "w", encoding="utf-8") as tf:
                    json.dump({
                        "task_id": task.task_id,
                        "exact_match": exact_match,
                        "symbolic_trace": graph.solved_trace,
                        "trace_logs": best_hyp.trace_logs,
                    }, tf, indent=2)

            inferred_id = best_hyp.hyp_id if best_hyp else result["inferred_rule_id"]
            inferred_name = best_hyp.name if best_hyp else result["inferred_rule_name"]
            score = 100.0 if exact_match else result["discovery_score"]

            return TaskEvalResult(
                task_id=task.task_id,
                filename=filename,
                status=status,
                prediction_available=True,
                exact_match=exact_match,
                runtime_sec=runtime,
                failure_reason=failure_reason,
                inferred_rule_id=inferred_id,
                inferred_rule_name=inferred_name,
                discovery_score=score,
                predicted_grid=predicted_grid,
                expected_grid=expected_grid,
            )


        except Exception as e:
            return TaskEvalResult(
                task_id=task.task_id,
                filename=filename,
                status="ERROR",
                prediction_available=False,
                exact_match=False,
                runtime_sec=time.time() - start_time,
                failure_reason=f"Execution Error: {str(e)}",
            )

    @classmethod
    def evaluate_folder(
        cls,
        folder_path: str,
        max_steps: int = 30,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> BatchEvalReport:
        """Evaluates all valid JSON task files in a specified folder."""
        batch_start = time.time()

        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        files = [
            f for f in sorted(os.listdir(folder_path))
            if f.endswith(".json") and not f.startswith(".")
        ]

        total_files = len(files)
        task_results: List[TaskEvalResult] = []

        for idx, filename in enumerate(files, 1):
            if progress_callback:
                progress_callback(idx, total_files, filename)

            filepath = os.path.join(folder_path, filename)
            res = cls.evaluate_single_file(filepath, max_steps=max_steps)
            task_results.append(res)

        total_runtime = time.time() - batch_start
        return BatchEvalReport(
            folder_path=folder_path,
            task_results=task_results,
            total_runtime_sec=total_runtime,
        )
