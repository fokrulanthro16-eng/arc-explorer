"""Command Line Interface for running ARC Explorer demonstrations, replaying traces, and benchmarking."""

import argparse
import sys
import os
from typing import Dict, Any
from arc_explorer import __version__
from arc_explorer.agent import ExplorerAgent
from arc_explorer.scenarios import create_scenario_1, create_scenario_2, create_scenario_3
from arc_explorer.replay import ReplayLogger


def run_scenario_demo(scenario_num: int, save_replay_path: str = None) -> Dict[str, Any]:
    scenarios = {
        1: ("Scenario 1: Color Propagation & Reflection", create_scenario_1),
        2: ("Scenario 2: Color Door Key Sequence", create_scenario_2),
        3: ("Scenario 3: Symmetric Pattern Completion", create_scenario_3),
    }

    if scenario_num not in scenarios:
        print(f"Error: Unknown scenario number {scenario_num}. Choose from 1, 2, or 3.")
        sys.exit(1)

    name, creator = scenarios[scenario_num]
    print("==================================================")
    print(f" RUNNING DEMONSTRATION: {name}")
    print("==================================================")

    env = creator()
    agent = ExplorerAgent()

    print("Initial Grid Observation:")
    print(env.render_ascii())
    print("--------------------------------------------------")

    result = agent.run_exploration(env)

    print("\n--- Exploration Steps & Observations ---")
    for log in result["trace_logs"]:
        haz_str = " [HAZARD!]" if log["hazard_alert"] else ""
        print(
            f"Step {log['step']:2d} | Pos: {log['pos']} | Action: {log['action']:10s} "
            f"| Top Hyp: {log['top_hypothesis']} (score={log['top_score']:.2f}){haz_str}"
        )

    print("--------------------------------------------------")
    print("DEMONSTRATION RESULTS SUMMARY:")
    print(f"  Rule Discovered : {result['rule_discovered']}")
    print(f"  Inferred Rule   : {result['inferred_rule_name']} ({result['inferred_rule_id']})")
    print(f"  Rule Score      : {result['rule_score']} / 1.00")
    print(f"  Steps Taken     : {result['total_steps']}")
    print(f"  Hazards Hit     : {result['hazard_count']}")
    print(f"  Discovery Score : {result['discovery_score']} / 100.0")
    print("==================================================\n")

    if save_replay_path:
        out_file = ReplayLogger.save_replay(
            save_replay_path, result, memory=agent.memory, scenario_name=name
        )
        print(f"[+] Replay trace saved to: {out_file}")

    return result


def main():
    parser = argparse.ArgumentParser(
        prog="arc-explorer",
        description="ARC Explorer: Local CPU-only active hypothesis testing agent baseline.",
    )
    parser.add_version = f"v{__version__}"
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # 'run' subcommand
    run_parser = subparsers.add_parser("run", help="Run active exploration demonstration")
    run_parser.add_argument(
        "--scenario",
        type=str,
        default="1",
        help="Scenario number to run (1, 2, 3, or 'all')",
    )
    run_parser.add_argument(
        "--save-replay",
        type=str,
        default=None,
        help="Optional filepath to save replay JSON trace",
    )

    # 'replay' subcommand
    replay_parser = subparsers.add_parser("replay", help="Load and view a saved JSON reasoning trace")
    replay_parser.add_argument(
        "--file",
        type=str,
        required=True,
        help="Path to JSON replay trace file",
    )

    # 'benchmark' subcommand
    subparsers.add_parser("benchmark", help="Run all 3 scenarios and display baseline benchmark report")

    # 'evaluate' subcommand
    eval_parser = subparsers.add_parser("evaluate", help="Batch evaluate ARC JSON tasks in a folder")
    eval_parser.add_argument(
        "--folder",
        type=str,
        default="data/arc_training",
        help="Path to folder containing ARC JSON task files",
    )
    eval_parser.add_argument(
        "--output",
        type=str,
        default="reports",
        help="Output directory to save evaluation JSON, CSV, and markdown reports",
    )

    # 'audit-dataset' subcommand
    audit_parser = subparsers.add_parser("audit-dataset", help="Audit local dataset folders for valid ARC task files")
    audit_parser.add_argument(
        "--folder",
        type=str,
        default="data/arc_training",
        help="Path to folder containing ARC JSON task files to audit",
    )

    # 'submit' subcommand
    submit_parser = subparsers.add_parser("submit", help="Generate Kaggle / ARC Prize competition submission JSON")
    submit_parser.add_argument(
        "--folder",
        type=str,
        required=True,
        help="Path to task folder (e.g., data/arc_test or data/arc_training)",
    )
    submit_parser.add_argument(
        "--output",
        type=str,
        default="submission.json",
        help="Output filepath for generated submission JSON",
    )

    # 'validate-submission' subcommand
    val_parser = subparsers.add_parser("validate-submission", help="Validate an ARC submission JSON file offline")
    val_parser.add_argument(
        "--tasks",
        type=str,
        required=True,
        help="Path to task folder used for prediction",
    )
    val_parser.add_argument(
        "--submission",
        type=str,
        default="submission.json",
        help="Path to submission JSON file to validate",
    )

    args = parser.parse_args()

    if args.command == "run":
        if args.scenario.lower() == "all":
            for sc in [1, 2, 3]:
                replay_path = f"replays/scenario_{sc}_replay.json" if args.save_replay else None
                run_scenario_demo(sc, save_replay_path=replay_path)
        else:
            sc_num = int(args.scenario)
            run_scenario_demo(sc_num, save_replay_path=args.save_replay)

    elif args.command == "replay":
        replay_data = ReplayLogger.load_replay(args.file)
        if not ReplayLogger.verify_replay(replay_data):
            print("Error: Invalid or corrupted replay trace file.")
            sys.exit(1)
        print(ReplayLogger.format_trace_summary(replay_data))

    elif args.command == "benchmark":
        print("==================================================")
        print(" RUNNING BENCHMARK EVALUATION ACROSS ALL SCENARIOS")
        print("==================================================")
        scores = []
        for sc in [1, 2, 3]:
            env_fn = {1: create_scenario_1, 2: create_scenario_2, 3: create_scenario_3}[sc]
            env = env_fn()
            agent = ExplorerAgent()
            res = agent.run_exploration(env)
            scores.append(res["discovery_score"])
            status = "PASSED" if res["rule_discovered"] and res["hazard_count"] == 0 else "FAILED"
            print(f"Scenario {sc}: {status} | Rule: {res['inferred_rule_name']} | Score: {res['discovery_score']:.1f}/100 | Steps: {res['total_steps']}")

        avg_score = sum(scores) / len(scores)
        print("--------------------------------------------------")
        print(f"Overall Baseline Benchmark Score: {avg_score:.2f} / 100.0")
        print("==================================================")

    elif args.command == "evaluate":
        from arc_explorer.evaluator import BatchEvaluator
        print("==================================================")
        print(f" BATCH EVALUATING ARC TASKS IN: {args.folder}")
        print("==================================================")

        def print_progress(idx, total, fname):
            print(f"[{idx}/{total}] Processing task file: {fname}...")

        report = BatchEvaluator.evaluate_folder(
            folder_path=args.folder, progress_callback=print_progress
        )

        json_path = report.export_json(output_dir=args.output)
        csv_path = report.export_csv(output_dir=args.output)
        full_reports = report.export_full_training_reports(output_dir=args.output)

        print("--------------------------------------------------")
        print("BATCH EVALUATION SUMMARY METRICS:")
        print(f"  Total Tasks Evaluated : {report.total_tasks}")
        print(f"  Completed Tasks       : {report.completed_tasks}")
        print(f"  Failed Tasks          : {report.failed_tasks}")
        print(f"  Exact Matches         : {report.exact_matches}")
        print(f"  Exact-Match Accuracy  : {report.exact_match_pct:.2f}%")
        print(f"  Average Runtime       : {report.avg_runtime_sec:.4f}s")
        print(f"  Median Runtime        : {report.median_runtime_sec:.4f}s")
        print(f"  Total Runtime         : {report.total_runtime_sec:.4f}s")
        print("--------------------------------------------------")
        print(f"[+] Exported JSON report: {json_path}")
        print(f"[+] Exported CSV summary: {csv_path}")
        print(f"[+] Exported Full Training Report: {full_reports['markdown']}")
        print(f"[+] Exported Full Failures JSON  : {full_reports['failures']}")
        print("==================================================")

    elif args.command == "audit-dataset":
        from arc_explorer.dataset_audit import audit_dataset_folder
        print("==================================================")
        print(f" AUDITING DATASET FOLDER: {args.folder}")
        print("==================================================")
        audit_res = audit_dataset_folder(args.folder)
        print(f"  Folder Path           : {audit_res.folder_path}")
        print(f"  Total Files           : {audit_res.total_files}")
        print(f"  Valid ARC Tasks       : {audit_res.valid_tasks}")
        print(f"  Malformed Files       : {len(audit_res.malformed_files)}")
        print(f"  Duplicate Task IDs    : {len(audit_res.duplicate_task_ids)}")
        print(f"  Invalid Grid Tasks    : {len(audit_res.invalid_grid_tasks)}")
        print(f"  Missing Test Pairs    : {len(audit_res.missing_test_pairs)}")
        print("==================================================")

    elif args.command == "submit":
        from arc_explorer.submission import generate_submission
        print("==================================================")
        print(f" GENERATING ARC SUBMISSION FROM: {args.folder}")
        print("==================================================")
        sub = generate_submission(args.folder, args.output)
        print(f"[+] Generated submission containing {len(sub)} tasks -> {args.output}")
        print("==================================================")

    elif args.command == "validate-submission":
        from arc_explorer.submission import validate_submission_file
        print("==================================================")
        print(f" VALIDATING SUBMISSION FILE: {args.submission}")
        print("==================================================")
        is_valid, errors = validate_submission_file(args.tasks, args.submission)
        if is_valid:
            print(" VALIDATION SUCCESSFUL! Submission schema is 100% compliant with ARC competition standard.")
        else:
            print(f" VALIDATION FAILED ({len(errors)} errors found):")
            for err in errors[:10]:
                print(f"  - {err}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more errors.")
            sys.exit(1)
        print("==================================================")

    else:
        parser.print_help()



if __name__ == "__main__":
    main()
