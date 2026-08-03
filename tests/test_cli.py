"""Unit tests for CLI runner."""

import sys
from unittest.mock import patch
from arc_explorer.cli import run_scenario_demo, main


def test_cli_run_scenario_demo():
    result = run_scenario_demo(1)
    assert result["rule_discovered"] is True
    assert result["inferred_rule_id"] == "h_color_propagation"


def test_cli_main_benchmark():
    test_args = ["arc-explorer", "benchmark"]
    with patch.object(sys, "argv", test_args):
        main()
