"""Unit tests for environment module and GridWorld mechanics."""

import pytest
from arc_explorer.environment import GridWorld, Color, Action, BaseRule, Observation


class DummyRule(BaseRule):
    def __init__(self):
        super().__init__("Dummy", "Dummy rule for testing")

    def step(self, grid, agent_pos, action, state_vars):
        next_grid = [list(r) for r in grid]
        r, c = agent_pos
        if action == Action.MOVE_RIGHT and c + 1 < len(grid[0]):
            return next_grid, (r, c + 1), 1.0, False, state_vars, {}
        return next_grid, agent_pos, 0.0, False, state_vars, {}


def test_gridworld_initialization_and_reset():
    grid = [[0, 1], [2, 3]]
    pos = (0, 0)
    rule = DummyRule()
    env = GridWorld(grid, pos, rule)

    obs = env.reset()
    assert obs.step == 0
    assert obs.agent_pos == (0, 0)
    assert obs.grid == ((0, 1), (2, 3))
    assert obs.get_cell(0, 1) == Color.BLUE
    assert obs.get_cell(1, 0) == Color.RED
    assert obs.get_cell(9, 9) == Color.GRAY  # Out of bounds wall


def test_gridworld_stepping():
    grid = [[0, 0], [0, 0]]
    env = GridWorld(grid, (0, 0), DummyRule(), max_steps=5)
    env.reset()

    obs1 = env.step(Action.MOVE_RIGHT)
    assert obs1.agent_pos == (0, 1)
    assert obs1.step == 1
    assert obs1.last_reward == 1.0
    assert obs1.hazard_alert is False


def test_ascii_render():
    grid = [[0, 1], [5, 2]]
    env = GridWorld(grid, (0, 0), DummyRule())
    env.reset()
    ascii_out = env.render_ascii()
    assert "A" in ascii_out  # Agent marker
    assert "B" in ascii_out  # Blue color marker
    assert "#" in ascii_out  # Gray wall marker
