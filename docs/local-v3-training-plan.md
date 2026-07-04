# Local V3 Training Plan

This plan proposes the next simulation-only training dataset and evaluation workflow after validating Session D curve-focused data. It does not build a dataset and does not train a model.

## Goal

Build a Local V3 training dataset that directly targets the current model failure mode:

- Steering magnitude under-prediction.
- Weak right-steering and strong-turn prediction.
- Local Dataset v2 model performing worse than the Dataset v1 baseline.
- Random row split optimism from adjacent simulator frames.

## Raw Data Preservation

Preserve all existing raw simulator recordings exactly as collected:

- `data/processed/simulator/`
- `data/processed/simulator_v2/session_a_normal/`
- `data/processed/simulator_v2/session_b_new_training/`
- `data/processed/simulator_v2/session_c2_right_recovery/`
- `data/processed/simulator_v2/session_d_curve_focused/`

Do not overwrite previous checkpoints:

- `models/steering_model_v1.pt`
- `models/steering_model_v2_synthetic.pt`
- `models/steering_model_sim_v1.pt`
- `models/steering_model_local_v2.pt`

Future output path:

```text
data/processed/local_v3_training/
```

Future model path:

```text
models/steering_model_local_v3.pt
```

Both paths are ignored by Git.

## Proposed Training Composition

Use a unified simple-format CSV with at least these fields:

```text
image_path,steering,throttle,brake,speed,source_dataset,source_session
```

Recommended composition:

| Source | Proposed use |
| --- | --- |
| Dataset v1 | Keep a reduced sample for normal driving and baseline continuity |
| Session A normal | Downsample heavily because near-zero is high and right steering is weak |
| Session B new training | Downsample; keep only useful non-zero coverage |
| Session C2 right recovery | Include strongly because it improves right steering and recovery coverage |
| Session D curve focused | Include strongly because it improves sustained curve and strong-turn coverage |

## Balancing Strategy

Recommended first-pass policy:

- Cap near-zero rows at about 25% to 30% of Local V3.
- Preserve all or most strong-turn rows from Sessions C2 and D.
- Preserve enough normal driving rows to avoid creating a curve-only model.
- Avoid letting Session D's left-heavy distribution dominate the final dataset.
- Prefer source/session-aware sampling over blind global shuffling.

Session D is strong but left-heavy:

```text
Left steering: 47.07%
Right steering: 30.93%
Strong turns: 24.83%
Near-zero: 22.00%
```

Local V3 should use C2 and right-turn rows to keep right-side coverage competitive.

## Validation Split

Do not use a random row split as the primary validation result.

Use a complete session-aware holdout where practical:

- Candidate validation holdout: Session D if testing curve generalization from v1/A/B/C2.
- Candidate alternative: hold out Session C2 if training includes Session D and the goal is right-recovery validation.
- Best research option: collect a smaller independent Session E or D2 and use it as an untouched test session.

Avoid placing adjacent frames from the same recording into both training and validation when possible.

## Camera Usage

Start with center-camera training for the first Local V3 comparison so the data effect can be isolated against v1 and local v2.

Do not introduce side-camera correction labels in the same experiment unless it is explicitly tracked as a separate experiment. If side cameras are used later, document:

- steering correction magnitude,
- sign convention,
- source sessions,
- whether side-camera rows are training-only or also evaluated separately.

## Evaluation Requirements

Report at minimum:

- Best validation loss.
- MAE and RMSE.
- Zero-steering baseline MAE and improvement percentage.
- Prediction standard deviation versus actual steering standard deviation.
- Near-zero error.
- Left-steering error.
- Right-steering error.
- Strong-turn error.
- Source/session-level metrics.
- Held-out-session metrics.

Recommended subgroup thresholds:

- Near-zero: `abs(steering) <= 0.05`
- Left: `steering < -0.05`
- Right: `steering > 0.05`
- Strong turns: `abs(steering) >= 0.5`

## Acceptance Criteria

Local V3 should not be promoted unless it improves materially over both v1 and local v2:

| Metric | Minimum expectation |
| --- | --- |
| Overall MAE | Better than v1 MAE 0.174045 |
| Overall RMSE | Better than v1 RMSE 0.246529 |
| Strong-turn MAE | Clearly better than local v2 strong-turn MAE 0.469480 |
| Right-steering MAE | Clearly better than local v2 right-steering MAE 0.256633 |
| Prediction std | Closer to actual steering std than local v2's compressed predictions |
| Validation split | Session-aware result reported, not only random row split |

If Local V3 improves only on the random row split, do not approve simulator-control work.

## Follow-up Options

If Local V3 improves:

- Add side-camera correction as a separate experiment.
- Compare the compact CNN against an NVIDIA-style behavior cloning CNN on the same fixed split.
- Add temporal prediction stability metrics before any simulator-only closed-loop work.

If Local V3 does not improve:

- Collect a more balanced Session D2 or Session E focused on right curves and strong corrections.
- Revisit image crop/normalization before scaling architecture.
- Review prediction samples to identify whether failures are visual, label-distribution, or split-policy related.

## Safety Boundary

Local V3 remains simulation-only. It must not be presented as real vehicle readiness or public-road capability. Simulator control remains blocked until the release checklist and held-out evaluation gates pass.
