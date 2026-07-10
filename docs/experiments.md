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
| EXP-006-local-v3-session-aware-training | Train: `data/processed/local_v3_training/train.csv`, 10657 rows; validation: complete `session_c2_right_recovery`, 4163 rows | 15 | 0.001 | Same compact PyTorch CNN as EXP-001/003, 188219 parameters | 0.100252 | 0.215618 | 0.316627 | Explicit split training worked, but the model did not beat the zero-steering baseline. Strong-turn MAE was 0.598862, right MAE was 0.249182, prediction std was 0.228446 versus actual std 0.347744, and MAE was 0.72% worse than the zero-steering baseline. Local V2's lower Session C2 score is historical context only because Session C2 contributed to Local V2 training. Verdict: R2, valid offline experiment, not promoted. | Do not release. Review prediction samples and test preprocessing/loss/architecture changes as separate fixed-split experiments. |
| EXP-007-road-focused-crop-preprocessing | Train: `data/processed/local_v3_training/train.csv`, 10657 rows; validation: complete `session_c2_right_recovery`, 4163 rows; preprocessing `road_crop_v1` y=[55,150) before resize | 15 | 0.001 | Same compact PyTorch CNN as EXP-006, 188219 parameters | 0.094317 | 0.215280 | 0.307111 | One-variable preprocessing experiment. RMSE, strong-turn MAE, direction error, and std ratio improved, but MAE improved only 0.000338, right MAE regressed slightly to 0.249969, near-zero MAE regressed to 0.151936, and the model still missed the zero-steering baseline by 0.56%. Verdict: P2, valid experiment with no meaningful improvement. | Do not release and do not run another crop variant against Session C2. Next single-variable experiment: Huber loss on the same fixed split. |
| EXP-008-huber-loss-smoothl1 | Train: `data/processed/local_v3_training/train.csv`, 10657 rows; validation: complete `session_c2_right_recovery`, 4163 rows; baseline preprocessing; SmoothL1Loss beta=1.0 | 15 | 0.001 | Same compact PyTorch CNN as EXP-006, 188219 parameters | 0.049741 | 0.213646 | 0.320153 | One-variable loss experiment. MAE improved slightly, zero-baseline improvement became +0.20%, strong-turn MAE improved to 0.575495, and std ratio improved to 0.705915. However RMSE worsened, right MAE regressed materially to 0.276358, and direction error regressed to 17.44%. Verdict: H2, valid experiment with no meaningful improvement. | Do not release and do not run another loss variant. Next single-variable experiment: slightly stronger CNN architecture on the same fixed split. |
| EXP-009-slightly-stronger-cnn-architecture | Train: `data/processed/local_v3_training/train.csv`, 10657 rows; validation: complete `session_c2_right_recovery`, 4163 rows; baseline preprocessing; MSE loss | 15 | 0.001 | `cnn_v2` / `SteeringModelV2`, 726103 parameters, BatchNorm2d + ELU conv stack | 0.098543 | 0.217054 | 0.313915 | One-variable architecture experiment. RMSE improved slightly, but MAE regressed, right MAE regressed to 0.261968, strong-turn MAE regressed to 0.612222, std ratio fell to 0.599089, zero-baseline comparison worsened to -1.39%, and direction error regressed to 19.03%. Verdict: A2, valid experiment with no meaningful improvement. | Do not release and do not run another architecture variant against Session C2 in this task. Next single step: collect an independent Session E test set before further model-selection work. |
| EXP-010-session-e-independent-test-set-validation | `data/processed/simulator_v2/session_e_independent_test/`, 6379 rows, 19137 images, intended frozen independent test session | N/A | N/A | Dataset validation only | N/A | N/A | N/A | Session E validates technically: 0 missing/corrupt images, 0 duplicate rows, balanced left/right steering at 26.09% / 27.32%, and PASS validator result. Distribution is not ideal for a final frozen test set: near-zero is 46.59% and strong turns are 9.72%. Verdict: E2, valid but not ideal. No training or model evaluation was run. | Do not freeze this recording as the final independent test set. Re-record a Session E2 candidate with less straight-only driving and at least 15% strong-turn coverage. |
| EXP-011-session-e2-independent-test-set-prep | Target: `data/processed/simulator_v2/session_e2_independent_test/`, intended replacement candidate for Session E | N/A | N/A | Dataset preparation only | N/A | N/A | N/A | Session E2 folder and `IMG/` subfolder prepared. Recording is pending; no `driving_log.csv` or images exist yet. Session E2 must not be used for training, validation, tuning, crop/loss/architecture selection, or repeated model selection. No validation, training, or model evaluation was run. | Human must record Session E2 in the Udacity simulator by selecting `session_e2_independent_test` directly. Target 5000-7000 rows, near-zero 30%-42%, left/right both above 22%, and strong turns at least 15%. |
| EXP-012-external-udacity-dataset-ingestion | Public Udacity-format source, 8,036 rows and 24,108 images; raw and manifests ignored | N/A | N/A | Download, extraction, and validation only | N/A | N/A | N/A | Archive SHA-256 recorded; all center/left/right references resolved; 0 missing/corrupt images, duplicates, and invalid/out-of-range labels. Verdict X2 because near-zero steering is 60.74% and strong turns are only 0.55%. No training or model evaluation was run. | Build an External Mix V1 training candidate for review with explicit balancing; do not train it yet. |
| EXP-013-external-mix-v1-training-candidate | Local V3 train, 10,657 rows, plus a deterministic 3,000-row center-camera subset of `udacity_behavioral_cloning_public`; generated candidate ignored | N/A | N/A | Dataset build and validation only | N/A | N/A | N/A | Hypothesis: a capped external subset can add visual diversity without destroying Local V3 curve strength. External cap strategy: seed 42, at most 25% of final rows, external near-zero at most 25%, balanced left/right, strong turns retained first. Final 13,657-row distribution: 27.91% near-zero, 36.22% left, 35.87% right, and 21.55% strong turns. Integrity checks found 0 missing/corrupt images, duplicate rows/paths, invalid labels, or forbidden sessions. Verdict M1, ready for human review. No training or model evaluation was run. | Review External Mix V1, then run exactly one controlled Local V3 baseline versus External Mix V1 experiment only if approved. |
| EXP-014-left-right-camera-correction | Planned: Local V3 plus side-camera correction | TBD | 0.001 initial | Same as EXP-001 | TBD | TBD | TBD | Test correction magnitude around 0.15 to 0.25 after verifying steering sign convention. | Compare against Local V3 center-only result after a fresh independent test set is available. |
| EXP-015-nvidia-bc-cnn | Planned: fixed Local V3 split | TBD | TBD | NVIDIA Behavioral Cloning style CNN | TBD | TBD | TBD | Architecture comparison after data improvement and a fresh independent test set. | Compare against same-data compact CNN. |
| EXP-016-temporal-stability | Planned: held-out validation videos | TBD | TBD | Best single-frame model plus smoothing/frame stacking candidate | TBD | TBD | TBD | Measure oscillation, steering delta, and lag. | Decide if model can enter simulator-only closed-loop test. |

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
