"""Integration tests proving agent discovers and replays rules in all 3 scenarios."""

import pytest
from arc_explorer.agent import ExplorerAgent
from arc_explorer.scenarios import create_scenario_1, create_scenario_2, create_scenario_3


def test_scenario_1_discovery():
    env = create_scenario_1()
    agent = ExplorerAgent()
    result = agent.run_exploration(env)

    assert result["rule_discovered"] is True
    assert result["inferred_rule_id"] == "h_color_propagation"
    assert result["hazard_count"] == 0
    assert result["discovery_score"] >= 80.0


def test_scenario_2_discovery():
    env = create_scenario_2()
    agent = ExplorerAgent()
    result = agent.run_exploration(env)

    assert result["rule_discovered"] is True
    assert result["inferred_rule_id"] == "h_trigger_barrier"
    assert result["hazard_count"] == 0
    assert result["discovery_score"] >= 80.0


def test_scenario_3_discovery():
    env = create_scenario_3()
    agent = ExplorerAgent()
    result = agent.run_exploration(env)

    assert result["rule_discovered"] is True
    assert result["inferred_rule_id"] == "h_symmetric_pattern"
    assert result["hazard_count"] == 0
    assert result["discovery_score"] >= 80.0
