# ARC Explorer

**ARC Explorer** is a CPU-only active hypothesis learning baseline designed for ARC-style (Abstraction and Reasoning Corpus) deterministic grid environments. It demonstrates active environment exploration, safe experiment planning under uncertainty, symbolic hypothesis tracking, and reasoning replay.

> [!NOTE]
> ARC Explorer is a research baseline exploring hypothesis-driven active exploration in structured grid worlds. It is not an AGI system.

---

## Key Components

1. **GridWorld (`arc_explorer.environment`)**: Deterministic 2D color grid environment supporting movement, interactions, inspection, and hazard signals.
2. **Observer (`arc_explorer.observer`)**: Perceptual feature extractor analyzing cell adjacencies, color distributions, symmetry, and grid state deltas.
3. **Episodic Memory (`arc_explorer.memory`)**: Transition store logging experience tuples $(s_t, a_t, s_{t+1}, \Delta s)$.
4. **Hypothesis Tracker (`arc_explorer.hypothesis`)**: Symbolic hypothesis engine evaluating consistency scores and simplicity priors across candidate rule hypotheses.
5. **Safe Experiment Planner (`arc_explorer.planner`)**: Action selection engine balancing information gain against predicted environmental hazards.
6. **Explorer Agent (`arc_explorer.agent`)**: Autonomous agent loop coordinating active experimentation and rule inference.
7. **Replay Logger (`arc_explorer.replay`)**: Serializes step-by-step reasoning trajectories into structured JSON replays.

---

## Installation & Setup

Requirements: Python 3.10+ (CPU-only, no GPU or paid APIs needed).

```bash
git clone https://github.com/example/ARC-Explorer.git
cd ARC-Explorer
pip install -r requirements.txt
```

---

## Usage & CLI

### Run Demonstration
Run an exploration run on Scenario 1:
```bash
python -m arc_explorer.cli run --scenario 1 --save-replay replays/scenario_1.json
```

Run all 3 hidden-rule scenarios:
```bash
python -m arc_explorer.cli run --scenario all
```

### Replay Reasoning Trace
Load and inspect a saved JSON trace:
```bash
python -m arc_explorer.cli replay --file replays/scenario_1.json
```

### Benchmark Evaluation
Run benchmark suite across all scenarios:
```bash
python -m arc_explorer.cli benchmark
```

---

## Verification & Testing

Execute the test suite with `pytest`:
```bash
python -m pytest -v
```

---

## License
[MIT License](LICENSE)
