# Dataset V2 Collection Plan

DarkDrive Dataset v2 should be collected locally in the simulator. No external dataset download is required for this iteration.

The goal is to reduce the current near-zero steering dominance and add recovery/off-center behavior before any simulator control work is attempted.

## Current Problem

Dataset v1 is valid, but it is not balanced enough for closed-loop behavior:

- Rows: 3706.
- Total images: 11118.
- Near-zero steering labels: 55.42%.
- p25, median, and p75 steering are all 0.0.
- Offline MAE: 0.174045.
- Offline RMSE: 0.246529.

This means the model sees too many "keep going straight" examples. A behavior cloning model trained on this distribution can learn a conservative center-biased policy that looks acceptable offline but fails when the car drifts away from the lane center.

## Total Target

Collect 8000 to 12000 new center-camera frames across several named sessions. If the simulator records left and right cameras too, keep them, but the first Dataset v2 training flow will still use center images unless a later experiment adds camera correction.

## Session A: Normal Lane Following

Target: 2000 frames.

Purpose:

- Keep a clean reference for normal lane-centered driving.
- Avoid making Dataset v2 only recovery data.
- Include smooth throttle and stable steering.

Collection guidance:

- Drive clean laps near lane center.
- Avoid long parked or idle segments.
- Include straight sections and gentle curves.

## Session B: Left Recovery Driving

Target: 2000 frames.

Purpose:

- Teach the model what to do when the car is left of lane center.
- Add examples where the visual state is off-center and the steering action returns the car to center.

Collection guidance:

- Drive slightly left of center.
- Recover smoothly to lane center.
- Do not stay off-center without correction.
- Repeat across straights and curves.

## Session C: Right Recovery Driving

Target: 2000 frames.

Purpose:

- Teach recovery from right-of-center positions.
- Balance the left-recovery examples from Session B.

Collection guidance:

- Drive slightly right of center.
- Recover smoothly to lane center.
- Avoid abrupt full-lock steering unless the vehicle truly needs it.
- Repeat across straights and curves.

## Session D: Curve-Focused Driving

Target: 3000 frames.

Purpose:

- Increase left and right turning examples.
- Reduce the model's tendency to understeer.
- Improve curve entry, apex, and exit behavior.

Collection guidance:

- Record curve-heavy laps.
- Include both left and right turns.
- Maintain moderate speed so labels are stable.
- Do not collect only straight-road cruising.

## Session E: Sharp Turns and Correction

Target: 2000 frames.

Purpose:

- Add stronger steering magnitudes.
- Teach correction after late curve entry and lane drift.
- Improve recovery from larger error states.

Collection guidance:

- Include sharper curve entries and exits.
- Add controlled corrections after being slightly misaligned.
- Avoid chaotic driving that does not return to lane center.

## Why Straight Driving Overload Hurts

Behavior cloning learns the average action for visual states. If most labels are close to 0.0, the model is rewarded for predicting small steering values. That can reduce offline loss while producing a weak driving policy that under-corrects in turns and recovery states.

## Why Recovery Driving Matters

In closed-loop simulation, the model will not stay exactly on the human-driving trajectory. Small prediction errors accumulate. Once the car is off-center, it sees camera states that were rare or absent in the original dataset. Recovery driving gives the model supervised examples for returning from those states.

## Why More Non-Zero Steering Is Needed

The current steering distribution is too centered. Dataset v2 should increase:

- Moderate left turns.
- Moderate right turns.
- Strong turns.
- Left-offset recovery.
- Right-offset recovery.

The target is not a perfectly flat steering histogram. The target is a dataset that contains enough non-zero steering to make recovery and turning behavior learnable.

## Expected Impact

Dataset v2 should improve:

- MAE on turning and recovery samples.
- RMSE by reducing large steering misses.
- Prediction variance, so predictions better match actual steering spread.
- Simulator driving stability when closed-loop work begins later.

This does not mean the model is ready for simulator control. Dataset v2 is a prerequisite for better offline research, not a control milestone.

## Recommended Folder Layout

```text
data/processed/simulator_v2/
|-- session_a_normal/
|   |-- IMG/
|   `-- driving_log.csv
|-- session_b_left_recovery/
|   |-- IMG/
|   `-- driving_log.csv
|-- session_c_right_recovery/
|   |-- IMG/
|   `-- driving_log.csv
|-- session_d_curves/
|   |-- IMG/
|   `-- driving_log.csv
`-- session_e_sharp_turns/
    |-- IMG/
    `-- driving_log.csv
```

Generated images and CSV files stay ignored by Git.

## Analysis Commands

Analyze each session:

```powershell
python scripts/session_dataset_report.py --csv data/processed/simulator_v2/session_a_normal/driving_log.csv --images-dir data/processed/simulator_v2/session_a_normal/IMG --format udacity --session-name session_a_normal
```

Compare Dataset v1 and Dataset v2:

```powershell
python scripts/compare_datasets.py --csv-a data/processed/simulator/driving_log.csv --images-dir-a data/processed/simulator/IMG --name-a dataset_v1 --csv-b data/processed/simulator_v2/session_a_normal/driving_log.csv --images-dir-b data/processed/simulator_v2/session_a_normal/IMG --name-b dataset_v2_session_a --format-a udacity --format-b udacity
```

Build local v2 training data:

```powershell
python scripts/build_local_v2_training_dataset.py --session dataset_v1,data/processed/simulator/driving_log.csv,data/processed/simulator/IMG --session session_a_normal,data/processed/simulator_v2/session_a_normal/driving_log.csv,data/processed/simulator_v2/session_a_normal/IMG --session session_b_left_recovery,data/processed/simulator_v2/session_b_left_recovery/driving_log.csv,data/processed/simulator_v2/session_b_left_recovery/IMG --session session_c_right_recovery,data/processed/simulator_v2/session_c_right_recovery/driving_log.csv,data/processed/simulator_v2/session_c_right_recovery/IMG --session session_d_curves,data/processed/simulator_v2/session_d_curves/driving_log.csv,data/processed/simulator_v2/session_d_curves/IMG --session session_e_sharp_turns,data/processed/simulator_v2/session_e_sharp_turns/driving_log.csv,data/processed/simulator_v2/session_e_sharp_turns/IMG --output-csv data/processed/local_v2_training/driving_log.csv --max-near-zero-ratio 0.35
```

