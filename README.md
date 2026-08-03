# ARC Explorer

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-14%20passed-brightgreen.svg)](tests/)

**ARC Explorer** is a lightweight, CPU-only research baseline designed for active hypothesis testing and rule discovery in deterministic grid-world environments inspired by ARC-AGI. The system observes state transitions, plans safe informative experiments to discriminate candidate hypotheses, tracks rule consistency using simplicity priors, and serializes step-by-step reasoning replays.

> [!NOTE]
> ARC Explorer is a small, deterministic research baseline for studying safe active learning and symbolic rule inference in grid environments. It does not claim real ARC-AGI-3 performance or general artificial intelligence.

---

## Architecture Overview

ARC Explorer follows a closed-loop active perception and decision-making pipeline:

```
  +------------------+
  |   GridWorld      | <---------------+
  +--------+---------+                 |
           | Observation               |
           v                           | Action
  +------------------+                 |
  |     Observer     |                 |
  +--------+---------+                 |
           | Features & State Delta    |
           v                           |
  +------------------+       +---------+---------+
  | Episodic Memory  +------>+ HypothesisTracker |
  +------------------+       +---------+---------+
                                       |
                                       | Candidate Scores
                                       v
                             +-------------------+
                             |   Safe Planner    |
                             +-------------------+
```

- **GridWorld (`arc_explorer.environment`)**: 2D grid environment supporting integer color codes (0-9), discrete agent movements, object interactions, hazard triggers, and ASCII rendering.
- **Observer (`arc_explorer.observer`)**: Feature extraction engine computing cardinal adjacencies, color frequency distributions, axial symmetries, and transition state deltas.
- **Episodic Memory (`arc_explorer.memory`)**: Transition store logging experience tuples $(s_t, a_t, s_{t+1}, \Delta s)$.
- **Hypothesis Tracker (`arc_explorer.hypothesis`)**: Evaluates consistency ratios and Occam simplicity priors across candidate rule hypotheses.
- **Safe Experiment Planner (`arc_explorer.planner`)**: Balances information gain (diversity of hypothesis predictions) against hazard risk probabilities to select safe actions.
- **Replay Logger (`arc_explorer.replay`)**: Serializes full reasoning traces to structured JSON files for step-by-step inspection and replay.

---

## Repository Structure

```
ARC-Explorer/
├── arc_explorer/
│   ├── __init__.py               # Package metadata and version info
│   ├── environment.py            # GridWorld env, Color/Action enums, BaseRule
│   ├── observer.py               # Observer feature extractor and state delta engine
│   ├── memory.py                 # Episodic transition memory store
│   ├── hypothesis.py             # Symbolic candidate hypotheses & HypothesisTracker
│   ├── planner.py                # Safe experiment planner with hazard pre-filtering
│   ├── agent.py                  # ExplorerAgent active exploration loop
│   ├── replay.py                 # ReplayLogger JSON serialization & player
│   ├── cli.py                    # CLI entry point (run, replay, benchmark)
│   └── scenarios/
│       ├── __init__.py           # Scenario factory loader
│       ├── scenario_color_propagation.py # Scenario 1: Color propagation & reflection
│       ├── scenario_key_door.py          # Scenario 2: Conditional key-door barrier sequence
│       └── scenario_pattern_fill.py       # Scenario 3: Symmetric pattern fill completion
├── tests/
│   ├── test_environment.py       # Grid rendering, movement, observation bounds
│   ├── test_observer_memory.py   # Feature extraction, delta calculation, memory log
│   ├── test_hypothesis_planner.py# Consistency evaluation & hazard pre-filtering
│   ├── test_agent_scenarios.py   # End-to-end rule discovery on Scenarios 1, 2, 3
│   ├── test_replay.py            # Replay serialization, verification, trace format
│   └── test_cli.py               # CLI subcommand execution tests
├── replays/                      # Generated JSON reasoning replay traces
├── architecture.md               # Detailed architectural specification
├── evaluation.md                 # Baseline benchmark evaluation report
├── requirements.txt              # Project dependencies (pytest)
├── .gitignore                    # Python build & bytecode ignore rules
├── LICENSE                       # MIT License
└── README.md                     # Project documentation
```

---

## Installation Commands

Clone the repository and install dependencies using standard Python 3.10+:

```bash
# Clone the repository
git clone https://github.com/fokrulanthro16-eng/arc-explorer.git
cd arc-explorer

# Create virtual environment (optional)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Usage & Commands

### 1. Run Scenario Demonstration
Run an exploration run on Scenario 1 and display step-by-step observations:
```bash
python -m arc_explorer.cli run --scenario 1 --save-replay replays/scenario_1.json
```

Run all 3 hidden-rule scenarios in sequence:
```bash
python -m arc_explorer.cli run --scenario all
```

### 2. Replay Reasoning Trace
Load and format a saved JSON reasoning trace:
```bash
python -m arc_explorer.cli replay --file replays/scenario_1.json
```

### 3. Run Benchmark Suite
Run the full benchmark evaluation across all 3 scenarios:
```bash
python -m arc_explorer.cli benchmark
```

### 4. Run Test Suite
Execute unit and integration tests with `pytest`:
```bash
python -m pytest -v
```

---

## Sample Benchmark Output

```text
==================================================
 RUNNING BENCHMARK EVALUATION ACROSS ALL SCENARIOS
==================================================
Scenario 1: PASSED | Rule: Adjacent RED propagates on push; BLUE reflects vertically | Score: 97.6/100 | Steps: 1
Scenario 2: PASSED | Rule: INTERACT on YELLOW trigger clears GREEN barrier; stepping on GREEN before trigger causes hazard | Score: 97.0/100 | Steps: 25
Scenario 3: PASSED | Rule: INTERACT on cell (r,c) copies color to horizontal symmetric position (r, W-1-c) | Score: 97.2/100 | Steps: 20
--------------------------------------------------
Overall Baseline Benchmark Score: 97.27 / 100.0
==================================================
```

---

## Sample Replay Output

```text
==================================================
 REPLAY TRACE: Scenario 1: Color Propagation & Reflection
==================================================
Inferred Rule  : Adjacent RED propagates on push; BLUE reflects vertically (h_color_propagation)
Total Steps    : 1
Hazards Hit    : 0
Discovery Score: 97.6 / 100.0
--------------------------------------------------
Step | Pos    | Action    | Hazard | Active Top Hypothesis
-----+--------+-----------+--------+-----------------------
   1 | [2, 0] | MOVE_RIGHT | NO     | Adjacent RED propagates on pus
==================================================
```

---

## Current Limitations

1. **Pre-defined Candidate Hypothesis Pool**: Candidate hypotheses are currently defined programmatically within the hypothesis space rather than dynamically generated via open-ended program synthesis.
2. **Deterministic Grid Assumption**: The environment model assumes fully deterministic state transitions $T(s, a) \to s'$.
3. **Discrete Action Space**: Actions are limited to standard cardinal grid moves, interaction, and inspection.
4. **Grid Size Scale**: Designed for small grid dimensions ($5 \times 5$ to $10 \times 10$).

---

## Future Roadmap

- [ ] **LLM/Neuro-symbolic Candidate Proposal**: Integrate local LLMs (e.g. Ollama/DeepSeek/Llama-3) to dynamically synthesize candidate hypothesis code given initial state observations.
- [ ] **Program Synthesis Integration**: Incorporate domain-specific language (DSL) primitives (similar to DreamCoder/ARC DSL) for open-ended rule search.
- [ ] **Stochastic Environment Dynamics**: Extend safety planner to handle probabilistic transition rules and noisy observation sensors.
- [ ] **ARC-AGI Image/JSON Converter**: Support loading official ARC-AGI task JSON files directly into GridWorld environments.

---

## License

[MIT License](LICENSE)
