"""Explorer Agent that orchestrates observation, active experiment planning, memory logging, and hypothesis discovery."""

from typing import Dict, Any, List, Optional
from arc_explorer.environment import GridWorld, Observation, Action
from arc_explorer.memory import Memory
from arc_explorer.hypothesis import HypothesisTracker, BaseHypothesis
from arc_explorer.planner import SafePlanner


class ExplorerAgent:
    """Autonomous explorer agent for active rule discovery in GridWorld environments."""

    def __init__(
        self,
        candidate_hypotheses: Optional[List[BaseHypothesis]] = None,
        confidence_threshold: float = 0.85,
    ):
        self.tracker = HypothesisTracker(candidates=candidate_hypotheses)
        self.planner = SafePlanner()
        self.memory = Memory()
        self.confidence_threshold = confidence_threshold
        self.visited_positions: List[tuple] = []
        self.trace_logs: List[Dict[str, Any]] = []

    def run_exploration(
        self, env: GridWorld, max_steps: Optional[int] = None
    ) -> Dict[str, Any]:
        """Runs the active exploration loop on the environment until rule discovery or max steps."""
        self.memory.clear()
        self.visited_positions.clear()
        self.trace_logs.clear()

        steps_limit = max_steps or env.max_steps
        obs = env.reset()
        self.visited_positions.append(obs.agent_pos)

        hazard_count = 0
        rule_discovered = False
        final_rule: Optional[BaseHypothesis] = None

        for step in range(1, steps_limit + 1):
            if obs.done:
                break

            # 1. Select safe informative action
            action, plan_info = self.planner.select_action(
                obs, self.tracker, self.visited_positions
            )

            # 2. Execute step in environment
            next_obs = env.step(action)
            if next_obs.hazard_alert:
                hazard_count += 1

            self.visited_positions.append(next_obs.agent_pos)

            # 3. Record to episodic memory
            transition = self.memory.record(step, obs, action, next_obs)

            # 4. Update hypothesis tracker with empirical evidence
            self.tracker.update(obs, action, next_obs)

            # Log step trace
            best_hyp = self.tracker.get_best_hypothesis()
            step_log = {
                "step": step,
                "pos": obs.agent_pos,
                "action": action.value,
                "hazard_alert": next_obs.hazard_alert,
                "top_hypothesis": best_hyp.name,
                "top_hypothesis_id": best_hyp.hyp_id,
                "top_score": round(best_hyp.score, 4),
                "planner_safety": plan_info["action_safety"],
            }
            self.trace_logs.append(step_log)

            # 5. Check rule discovery termination condition
            top_hyp = self.tracker.get_best_hypothesis()
            if top_hyp.score >= 0.75 and top_hyp.evaluated_steps >= 1:
                rule_discovered = True
                final_rule = top_hyp


            obs = next_obs

        # Calculate final discovery score (0 to 100)
        final_hyp = self.tracker.get_best_hypothesis()
        score = max(0.0, (final_hyp.score * 100.0) - (hazard_count * 20.0))

        return {
            "total_steps": len(self.trace_logs),
            "hazard_count": hazard_count,
            "rule_discovered": rule_discovered,
            "inferred_rule_id": final_hyp.hyp_id,
            "inferred_rule_name": final_hyp.name,
            "rule_score": round(final_hyp.score, 4),
            "discovery_score": round(score, 2),
            "rankings": [h.to_dict() for h in self.tracker.get_rankings()],
            "trace_logs": self.trace_logs,
        }
