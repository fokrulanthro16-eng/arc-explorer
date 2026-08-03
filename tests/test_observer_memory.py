"""Unit tests for Observer feature extraction and Memory episodic transition logging."""

from arc_explorer.environment import Observation, Action, Color
from arc_explorer.observer import Observer
from arc_explorer.memory import Memory


def test_observer_feature_extraction():
    grid = [
        [0, 1, 0],
        [0, 0, 0],
        [0, 1, 0],
    ]
    obs = Observation(grid=grid, agent_pos=(1, 1), step=1)
    features = Observer.extract(obs)

    assert features.color_counts[Color.EMPTY] == 7
    assert features.color_counts[Color.BLUE] == 2
    assert features.symmetry_horizontal is True
    assert features.symmetry_vertical is True
    assert features.adjacent_colors[Action.MOVE_UP.value] == Color.BLUE


def test_observer_delta_computation():
    obs1 = Observation(grid=[[0, 1], [0, 0]], agent_pos=(0, 0), step=1)
    obs2 = Observation(grid=[[0, 0], [0, 2]], agent_pos=(0, 1), step=2)

    delta = Observer.compute_delta(obs1, obs2)
    assert delta["agent_moved"] is True
    assert delta["num_cell_changes"] == 2
    assert delta["pos_delta"] == (0, 1)


def test_memory_recording_and_query():
    memory = Memory()
    obs1 = Observation(grid=[[0, 0]], agent_pos=(0, 0), step=1)
    obs2 = Observation(grid=[[0, 0]], agent_pos=(0, 1), step=2)

    t = memory.record(1, obs1, Action.MOVE_RIGHT, obs2)
    assert memory.size() == 1
    assert memory.get_history()[0] == t

    queries = memory.query_by_action(Action.MOVE_RIGHT)
    assert len(queries) == 1
    assert queries[0].action == Action.MOVE_RIGHT

    memory.clear()
    assert memory.size() == 0
