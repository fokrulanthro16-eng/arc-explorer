"""UI Helper utilities for Streamlit dashboard rendering and execution."""

import os
from typing import Dict, Any, List, Tuple
from arc_explorer.environment import Color
from arc_explorer.agent import ExplorerAgent
from arc_explorer.scenarios import create_scenario_1, create_scenario_2, create_scenario_3
from arc_explorer.replay import ReplayLogger


COLOR_HEX_MAP = {
    Color.EMPTY: {"name": "Empty", "bg": "#1E293B", "fg": "#94A3B8"},
    Color.BLUE: {"name": "Blue", "bg": "#2563EB", "fg": "#FFFFFF"},
    Color.RED: {"name": "Red", "bg": "#DC2626", "fg": "#FFFFFF"},
    Color.GREEN: {"name": "Green", "bg": "#16A34A", "fg": "#FFFFFF"},
    Color.YELLOW: {"name": "Yellow", "bg": "#CA8A04", "fg": "#FFFFFF"},
    Color.GRAY: {"name": "Gray Wall", "bg": "#475569", "fg": "#CBD5E1"},
    Color.MAGENTA: {"name": "Magenta", "bg": "#C026D3", "fg": "#FFFFFF"},
    Color.ORANGE: {"name": "Orange", "bg": "#EA580C", "fg": "#FFFFFF"},
    Color.TEAL: {"name": "Teal Goal", "bg": "#0D9488", "fg": "#FFFFFF"},
    Color.MAROON: {"name": "Maroon", "bg": "#881337", "fg": "#FFFFFF"},
}


def render_grid_html(grid: List[List[int]], agent_pos: Tuple[int, int], cell_size: int = 60) -> str:
    """Generates an HTML/CSS visual grid matrix representation of the environment state."""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0

    html = [
        f'<div style="display: grid; grid-template-columns: repeat({width}, {cell_size}px); '
        f'gap: 6px; background-color: #0F172A; padding: 12px; border-radius: 10px; '
        f'box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3); width: fit-content; margin: 10px 0;">'
    ]

    for r in range(height):
        for c in range(width):
            color_val = grid[r][c]
            color_info = COLOR_HEX_MAP.get(color_val, {"name": "Unknown", "bg": "#334155", "fg": "#FFFFFF"})
            is_agent = (r, c) == tuple(agent_pos)

            cell_content = "🤖" if is_agent else f"<span style='font-size: 10px; opacity: 0.8;'>{color_info['name']}</span>"
            border_style = "border: 3px solid #38BDF8; box-shadow: 0 0 10px #38BDF8;" if is_agent else "border: 1px solid rgba(255,255,255,0.1);"

            html.append(
                f'<div style="width: {cell_size}px; height: {cell_size}px; background-color: {color_info["bg"]}; '
                f'color: {color_info["fg"]}; display: flex; align-items: center; justify-content: center; '
                f'font-size: {22 if is_agent else 11}px; font-weight: bold; border-radius: 6px; {border_style} '
                f'user-select: none;" title="Pos: ({r},{c}) | Color: {color_info["name"]}">'
                f'{cell_content}</div>'
            )

    html.append('</div>')
    return "".join(html)


def run_benchmark_evaluation() -> Dict[str, Any]:
    """Dynamically runs ExplorerAgent across all 3 scenarios and computes benchmark metrics."""
    scenario_creators = [
        (1, "Scenario 1: Color Propagation & Reflection", create_scenario_1),
        (2, "Scenario 2: Color Door Key Sequence", create_scenario_2),
        (3, "Scenario 3: Symmetric Pattern Completion", create_scenario_3),
    ]

    scenario_results = []
    scores = []

    for sc_id, name, creator_fn in scenario_creators:
        env = creator_fn()
        agent = ExplorerAgent()
        result = agent.run_exploration(env)

        is_passed = result["rule_discovered"] and result["hazard_count"] == 0
        scenario_results.append({
            "id": sc_id,
            "name": name,
            "passed": is_passed,
            "status": "PASSED" if is_passed else "FAILED",
            "inferred_rule_id": result["inferred_rule_id"],
            "inferred_rule_name": result["inferred_rule_name"],
            "rule_score": result["rule_score"],
            "steps": result["total_steps"],
            "hazards": result["hazard_count"],
            "score": result["discovery_score"],
        })

        scores.append(result["discovery_score"])

    overall_score = round(sum(scores) / len(scores), 2) if scores else 0.0
    return {
        "scenario_results": scenario_results,
        "overall_score": overall_score,
        "total_passed": sum(1 for r in scenario_results if r["passed"]),
        "total_scenarios": len(scenario_results),
    }


def list_available_replays(replay_dir: str = "replays") -> List[str]:
    """Scans and lists available JSON replay files."""
    if not os.path.exists(replay_dir):
        return []
    return [
        os.path.join(replay_dir, f)
        for f in sorted(os.listdir(replay_dir))
        if f.endswith(".json")
    ]


def list_available_arc_tasks(samples_dir: str = "samples") -> List[str]:
    """Scans and lists available ARC task JSON files."""
    if not os.path.exists(samples_dir):
        return []
    return [
        os.path.join(samples_dir, f)
        for f in sorted(os.listdir(samples_dir))
        if f.endswith(".json") and "arc_task" in f
    ]


def load_and_verify_replay(filepath: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Loads and validates a replay JSON file, returning (success, data, error_message)."""
    try:
        data = ReplayLogger.load_replay(filepath)
        if not ReplayLogger.verify_replay(data):
            return False, None, "Invalid replay file format or missing required trace logs."
        return True, data, ""
    except Exception as e:
        return False, None, str(e)

