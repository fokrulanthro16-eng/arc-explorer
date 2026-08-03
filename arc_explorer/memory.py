"""Episodic transition memory for storing and querying state-action experiences."""

from typing import List, Dict, Any, Optional
from arc_explorer.environment import Observation, Action
from arc_explorer.observer import Observer, StateFeatures


class Transition:
    """Represents a single step experience tuple."""

    def __init__(
        self,
        step: int,
        obs_before: Observation,
        action: Action,
        obs_after: Observation,
        features_before: StateFeatures,
        features_after: StateFeatures,
        delta: Dict[str, Any],
    ):
        self.step = step
        self.obs_before = obs_before
        self.action = action
        self.obs_after = obs_after
        self.features_before = features_before
        self.features_after = features_after
        self.delta = delta

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "obs_before": self.obs_before.to_dict(),
            "action": self.action.value,
            "obs_after": self.obs_after.to_dict(),
            "features_before": self.features_before.to_dict(),
            "features_after": self.features_after.to_dict(),
            "delta": self.delta,
        }


class Memory:
    """Episodic memory log storing agent observations and state transitions."""

    def __init__(self):
        self.transitions: List[Transition] = []

    def record(
        self,
        step: int,
        obs_before: Observation,
        action: Action,
        obs_after: Observation,
    ) -> Transition:
        features_before = Observer.extract(obs_before)
        features_after = Observer.extract(obs_after)
        delta = Observer.compute_delta(obs_before, obs_after)

        transition = Transition(
            step=step,
            obs_before=obs_before,
            action=action,
            obs_after=obs_after,
            features_before=features_before,
            features_after=features_after,
            delta=delta,
        )
        self.transitions.append(transition)
        return transition

    def get_history(self) -> List[Transition]:
        return list(self.transitions)


    def query_by_action(self, action: Action) -> List[Transition]:
        return [t for t in self.transitions if t.action == action]

    def size(self) -> int:
        return len(self.transitions)

    def clear(self) -> None:
        self.transitions.clear()

    def to_list(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self.transitions]
