"""Replay logger for serializing, loading, and verifying agent reasoning traces."""

import json
import os
from typing import Dict, Any, Optional
from arc_explorer import __version__


class ReplayLogger:
    """Handles serialization and deserialization of exploration reasoning replays."""

    @staticmethod
    def save_replay(
        filepath: str,
        result: Dict[str, Any],
        memory: Optional[Any] = None,
        scenario_name: str = "Unknown Scenario",
    ) -> str:
        """Saves exploration trace and reasoning history to a JSON file."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

        payload = {
            "version": __version__,
            "scenario": scenario_name,
            "summary": {
                "total_steps": result["total_steps"],
                "hazard_count": result["hazard_count"],
                "rule_discovered": result["rule_discovered"],
                "inferred_rule_id": result["inferred_rule_id"],
                "inferred_rule_name": result["inferred_rule_name"],
                "discovery_score": result["discovery_score"],
            },
            "rankings": result["rankings"],
            "trace_logs": result["trace_logs"],
            "memory_transitions": memory.to_list() if memory else [],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        return filepath

    @staticmethod
    def load_replay(filepath: str) -> Dict[str, Any]:
        """Loads a saved JSON replay file."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Replay file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data

    @staticmethod
    def verify_replay(replay_data: Dict[str, Any]) -> bool:
        """Verifies integrity and consistency of a loaded replay file."""
        required_keys = ["version", "scenario", "summary", "trace_logs"]
        for key in required_keys:
            if key not in replay_data:
                return False

        summary = replay_data["summary"]
        if "discovery_score" not in summary or "inferred_rule_name" not in summary:
            return False

        return len(replay_data["trace_logs"]) == summary["total_steps"]

    @staticmethod
    def format_trace_summary(replay_data: Dict[str, Any]) -> str:
        """Formats a human-readable step-by-step summary of the reasoning trace."""
        lines = []
        lines.append("==================================================")
        lines.append(f" REPLAY TRACE: {replay_data.get('scenario', 'ARC Explorer')}")
        lines.append("==================================================")
        summary = replay_data["summary"]
        lines.append(f"Inferred Rule  : {summary['inferred_rule_name']} ({summary['inferred_rule_id']})")
        lines.append(f"Total Steps    : {summary['total_steps']}")
        lines.append(f"Hazards Hit    : {summary['hazard_count']}")
        lines.append(f"Discovery Score: {summary['discovery_score']} / 100.0")
        lines.append("--------------------------------------------------")
        lines.append("Step | Pos    | Action    | Hazard | Active Top Hypothesis")
        lines.append("-----+--------+-----------+--------+-----------------------")

        for log in replay_data.get("trace_logs", []):
            step = str(log["step"]).rjust(4)
            pos = str(log["pos"]).ljust(6)
            act = str(log["action"]).ljust(9)
            haz = "YES" if log["hazard_alert"] else "NO "
            hyp = str(log["top_hypothesis"])[:30]
            lines.append(f"{step} | {pos} | {act} | {haz}    | {hyp}")

        lines.append("==================================================")
        return "\n".join(lines)
