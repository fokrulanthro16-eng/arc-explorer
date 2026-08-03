# ARC Explorer Baseline Evaluation Report

## Benchmark Summary

The ARC Explorer agent was evaluated across 3 hidden-rule scenarios designed to test different aspects of active hypothesis testing: color propagation & reflection, conditional key-door sequence unlocking, and symmetric pattern completion.

| Scenario | Hidden Rule Domain | Rule Discovered | Steps Taken | Hazards Hit | Baseline Score | Result |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Scenario 1** | Color Propagation & Reflection | **Yes** | 1 | 0 | **97.6 / 100** | **PASSED** |
| **Scenario 2** | Color Door Key Sequence | **Yes** | 25 | 0 | **97.0 / 100** | **PASSED** |
| **Scenario 3** | Symmetric Pattern Completion | **Yes** | 20 | 0 | **97.2 / 100** | **PASSED** |
| **Overall** | **Benchmark Composite** | **100% Success** | **15.3 avg** | **0 total** | **97.27 / 100** | **PASSED** |

---

## Detailed Scenario Performance

### Scenario 1: Color Propagation & Reflection
- **Task**: Determine dynamics of pushing RED and BLUE tiles.
- **Inferred Rule**: `h_color_propagation` (Adjacent RED propagates on push; BLUE reflects vertically).
- **Final Confidence Score**: 0.976 / 1.00.
- **Key Observation**: Agent executed `MOVE_RIGHT` onto RED tile. Observed RED cell propagate forward to (2,2) and achieved task objective in 1 step with zero safety violations.

### Scenario 2: Color Door Key Sequence
- **Task**: Navigate grid blocked by GREEN barrier without hitting hazards.
- **Inferred Rule**: `h_trigger_barrier` (INTERACT on YELLOW trigger clears GREEN barrier; crossing GREEN before trigger causes hazard).
- **Final Confidence Score**: 0.970 / 1.00.
- **Key Observation**: Agent navigated safely around GRAY walls, moved to YELLOW trigger at (2,0), executed `INTERACT` to clear GREEN barrier into EMPTY cells, and reached goal cell at (0,4) with zero hazard penalties.

### Scenario 3: Symmetric Pattern Completion
- **Task**: Complete horizontal symmetry across colored cells.
- **Inferred Rule**: `h_symmetric_pattern` (INTERACT on cell (r,c) copies color to horizontal symmetric position (r, W-1-c)).
- **Final Confidence Score**: 0.972 / 1.00.
- **Key Observation**: Agent positioned itself at non-empty cells and executed `INTERACT` actions, filling symmetric positions until full axial grid symmetry was established.

---

## Verification & Test Results
- Unit test suite (`tests/`): **14 / 14 tests passing** (0.09s total runtime).
- Replay trace integrity: **100% verified** across JSON serialization & loading.
