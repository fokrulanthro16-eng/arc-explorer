# ARC Explorer Architecture Specification

## Overview

ARC Explorer implements a closed-loop active learning architecture for rule discovery in deterministic grid-world environments. The system operates without gradient-based training or external API dependencies, relying on symbolic hypothesis generation, Bayesian-like consistency scoring, and active experiment planning under safety constraints.

```
       +------------------+
       |   Environment    |
       +--------+---------+
                | Observation
                v
       +------------------+
       |     Observer     |
       +--------+---------+
                | Features & Deltas
                v
       +------------------+       +-------------------+
       | Episodic Memory  +------>+ HypothesisTracker |
       +------------------+       +---------+---------+
                                            |
                                            | Candidate Scores
                                            v
                                  +-------------------+
                                  |   Safe Planner    |
                                  +---------+---------+
                                            |
                                            | Action
                                            v
                                   [ Environment Step ]
```

---

## Core Subsystems

### 1. Environment & Observation (`environment.py`)
- **Grid State**: Represented as a 2D integer array where integers (0-9) map to distinct colors (`EMPTY`, `BLUE`, `RED`, `GREEN`, `YELLOW`, `GRAY`, etc.).
- **Action Space**: Discrete actions $\mathcal{A} = \{\text{MOVE\_UP}, \text{MOVE\_DOWN}, \text{MOVE\_LEFT}, \text{MOVE\_RIGHT}, \text{INTERACT}, \text{INSPECT}\}$.
- **Observation Object**: Immutable tuple snapshot of grid state, agent position, step counter, last action, accumulated reward, and hazard alert boolean.

### 2. Observer & Feature Extraction (`observer.py`)
- Extracts key relational metrics:
  - Color frequency counts and spatial position indices.
  - Cardinal adjacencies surrounding agent position $(r, c)$.
  - Axial symmetry indicators (horizontal and vertical mirror checks).
  - Transition delta calculation $\Delta S = S_{t+1} - S_t$.

### 3. Episodic Memory (`memory.py`)
- Maintains chronological log of transition tuples $(t, s_t, a_t, s_{t+1}, \phi(s_t), \phi(s_{t+1}), \Delta s_t)$.
- Provides indexing utilities for counterfactual checking against candidate hypotheses.

### 4. Hypothesis Engine & Tracker (`hypothesis.py`)
- Maintains a pool of symbolic rule hypotheses $\mathcal{H} = \{h_1, h_2, \dots, h_k\}$.
- Each hypothesis $h_i$ implements a prediction function $\hat{f}_{h_i}(s_t, a_t) \to (\hat{s}_{t+1}, \hat{\text{hazard}})$.
- **Consistency Score**:
  $$S(h_i) = \frac{\text{consistent steps}}{\text{evaluated steps}} \times \max\left(0.1, 1.0 - 0.02 \times \text{complexity}(h_i)\right)$$
  - Consistency ratio dominates over simplicity prior. Complexity serves as a tie-breaker when evidence is underconstrained.

### 5. Safe Experiment Planner (`planner.py`)
- Selects optimal action $a^*$ maximizing expected utility while respecting safety constraints:
  $$\text{Utility}(a) = \text{InfoGain}(a) + \alpha \cdot \text{Novelty}(a) - \beta \cdot \text{HazardPenalty}(a)$$
- **Safety Pre-filtering**: Actions predicted to trigger environmental hazards with probability exceeding $\tau_{hazard} = 0.4$ are excluded from execution whenever safe alternative actions exist.

### 7. ARC Task Subsystem (`arc_task.py`)
- **ARCTask Container**: Reads and parses official ARC-AGI JSON data into structured `ARCPair` objects representing training and testing grid pairs.
- **ARCTaskRule**: Adapts input grid transformations into an environment rule where agent interactions modify matrix elements to achieve target ARC outputs.
- **Environment Adapter**: `create_arc_task_environment()` converts any train/test ARC task pair into an active `GridWorld` environment compatible with `ExplorerAgent`.

