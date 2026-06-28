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
| EXP-003-local-simulator-v2-recovery | Dataset v1 + recovery/off-center/curve-focused Dataset v2 | 15 planned | 0.001 initial | Same as EXP-001 | TBD | TBD | TBD | Name: Local Simulator Dataset v2 - Recovery Driving. Goal: reduce near-zero steering dominance and improve recovery/turn prediction. Record total rows, near-zero percentage, steering std, validation loss, MAE, RMSE, and improvement over EXP-001. | Collect Dataset v2 sessions, build `data/processed/local_v2_training/driving_log.csv`, then train `steering_model_local_v2.pt`. |
| EXP-004-left-right-camera-correction | Planned: Dataset v2 plus side-camera correction | TBD | 0.001 initial | Same as EXP-001 | TBD | TBD | TBD | Test correction magnitude around 0.15 to 0.25 after verifying steering sign convention. | Compare against EXP-003. |
| EXP-005-nvidia-bc-cnn | Planned: fixed Dataset v2 split | TBD | TBD | NVIDIA Behavioral Cloning style CNN | TBD | TBD | TBD | Architecture comparison after data improvement. | Compare against same-data compact CNN. |
| EXP-006-temporal-stability | Planned: held-out validation videos | TBD | TBD | Best single-frame model plus smoothing/frame stacking candidate | TBD | TBD | TBD | Measure oscillation, steering delta, and lag. | Decide if model can enter simulator-only closed-loop test. |

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
