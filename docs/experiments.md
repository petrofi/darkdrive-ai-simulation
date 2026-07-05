# Experiments

This file is the experiment tracking ledger for DarkDrive AI Simulation.

## Required Experiment Fields

Each future experiment must record:

- Experiment ID
- Dataset
- Epochs
- Learning Rate
- Architecture
- Validation Loss
- MAE
- RMSE
- Observations
- Next Action

## Experiment Table

| Experiment ID | Dataset | Epochs | Learning Rate | Architecture | Validation Loss | MAE | RMSE | Observations | Next Action |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | --- | --- |
| EXP-001-baseline-sim-v1 | `data/processed/simulator/driving_log.csv`, 3706 samples, center camera only | 10 | 0.001 | Compact PyTorch CNN, ELU, dropout | 0.060776 | 0.174045 | 0.246529 | Learned real steering signal, but labels are 55.42% near zero and MAE improves only 9.95% over zero baseline. | Collect balanced recovery dataset before simulator control. |
| EXP-002-merged-dataset-bc-v1 | Local Udacity simulator data + external behavior cloning dataset | 15 planned | 0.001 initial | Same as EXP-001 | TBD | TBD | TBD | Goal: reduce always-zero steering bias and improve turning prediction. Record rows, near-zero percentage, validation loss, MAE, RMSE, and notes. | Build merged dataset with `scripts/build_merged_training_dataset.py`, then train `steering_model_merged_v1.pt`. |
| EXP-003-local-simulator-v2-recovery | `data/processed/local_v2_training/driving_log.csv`, 8647 samples, center camera only, Dataset v1 + Sessions A/B/C2 | 15 | 0.001 | Same as EXP-001 | 0.092040 | 0.211307 | 0.303382 | Dataset distribution improved: near-zero 34.99%, right steering 29.73%, strong turns 18.53%. Model underperformed v1 and under-predicted right/strong turns. | Do not release. Collect Session D curve-focused data before another local v2 training run. |
| EXP-004-session-d-curve-focused-data | `data/processed/simulator_v2/session_d_curve_focused/driving_log.csv`, 7721 rows, 23163 images | N/A | N/A | Dataset collection and validation only | N/A | N/A | N/A | Hypothesis: sustained curve data will address steering magnitude under-prediction. Distribution: 22.00% near-zero, 47.07% left, 30.93% right, 24.83% strong turns, 0 missing/corrupt images. Temporal analysis found 210 sustained medium steering runs and 80 sustained strong steering runs. Verdict: strong curve-focused session, left-heavy but useful. | Include in Local V3 plan with Session C2; do not train until the dataset build and session-aware split are reviewed. |
| EXP-005-local-v3-session-aware-dataset-build | Train: `data/processed/local_v3_training/train.csv`, 10657 rows, center camera only; validation: complete `session_c2_right_recovery`, 4163 rows | N/A | N/A | Dataset build and validation only | N/A | N/A | N/A | Hypothesis: a session-aware V3 split can reduce near-zero bias, preserve strong turns, and avoid random adjacent-frame leakage. Train distribution: 28.72% near-zero, 35.86% left, 35.41% right, 27.20% strong turns. Leakage checks: 0 source-session, image-path, filename, and CSV-row overlap. Verdict: A, ready for session-aware training. | Extend training/evaluation CLIs to accept explicit train/validation CSV files, then train `steering_model_local_v3.pt`. |
| EXP-006-local-v3-session-aware-training | Train: `data/processed/local_v3_training/train.csv`, 10657 rows; validation: complete `session_c2_right_recovery`, 4163 rows | 15 | 0.001 | Same compact PyTorch CNN as EXP-001/003, 188219 parameters | 0.100252 | 0.215618 | 0.316627 | Explicit split training worked, but Session C2 result did not improve over Local V2. Strong-turn MAE was 0.598862, right MAE was 0.249182, prediction std was 0.228446 versus actual std 0.347744, and MAE was 0.72% worse than the zero-steering baseline. Verdict: R2, valid offline experiment, not promoted. | Do not release. Review prediction samples and test crop/normalization or architecture changes as separate fixed-split experiments. |
| EXP-007-left-right-camera-correction | Planned: Local V3 plus side-camera correction | TBD | 0.001 initial | Same as EXP-001 | TBD | TBD | TBD | Test correction magnitude around 0.15 to 0.25 after verifying steering sign convention. | Compare against Local V3 center-only result. |
| EXP-008-nvidia-bc-cnn | Planned: fixed Local V3 split | TBD | TBD | NVIDIA Behavioral Cloning style CNN | TBD | TBD | TBD | Architecture comparison after data improvement. | Compare against same-data compact CNN. |
| EXP-009-temporal-stability | Planned: held-out validation videos | TBD | TBD | Best single-frame model plus smoothing/frame stacking candidate | TBD | TBD | TBD | Measure oscillation, steering delta, and lag. | Decide if model can enter simulator-only closed-loop test. |

## Experiment Template

Copy this row for new experiments:

| Experiment ID | Dataset | Epochs | Learning Rate | Architecture | Validation Loss | MAE | RMSE | Observations | Next Action |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | --- | --- |
| EXP-YYYY-NN-name | Dataset path, sample count, camera usage, split policy | 0 | 0.000 | Architecture name | 0.000000 | 0.000000 | 0.000000 | Key result and failure mode. | Keep, reject, or run next experiment. |

## Recommended Extra Metadata

The required table is the minimum. For research-grade comparison, also record:

- Date.
- Git commit hash.
- Random seed.
- Batch size.
- Weight decay.
- Loss function.
- Augmentation settings.
- Image size.
- Crop policy.
- Validation split method.
- Checkpoint path.
- Training chart path.
- Prediction plot path.
- Dataset analysis plot paths.

## Experiment Rules

- Do not compare architectures using different validation splits.
- Do not compare data strategies without naming the dataset version.
- Do not report validation loss without MAE and RMSE.
- Do not treat offline evaluation as proof of simulator driving readiness.
- Keep generated checkpoints out of Git unless a deliberate model-release policy is added later.
- Prefer one major change per experiment.

## Baseline Interpretation

EXP-001 is a valid baseline, not a release model.

Reasons:

- It uses real simulator data.
- It has validated images and labels.
- It has offline MAE/RMSE.
- It does not have recovery-heavy training data.
- It does not have session-level validation.
- It does not have temporal stability evaluation.
