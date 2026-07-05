# Local V3 Training Plan

This plan records the Local V3 session-aware dataset build and the next training requirement. It is simulation-only. No model was trained and no simulator control code was added.

## Final Dataset Structure

Generated manifests:

```text
data/processed/local_v3_training/train.csv
data/processed/local_v3_training/validation.csv
data/processed/local_v3_training/dataset_summary.json
data/processed/local_v3_training/source_distribution.csv
```

These files are generated artifacts and remain ignored by Git through `data/processed/*`.

CSV schema:

```text
image_path,steering,throttle,brake,speed,source_dataset,source_session
```

The current training dataset uses center-camera rows only. Extra source fields are intentionally retained so future training and evaluation can report source/session-level metrics.

## Training Sources

| Source session | Source path | Raw rows | Retained rows |
| --- | --- | ---: | ---: |
| Dataset v1, `v1` | `data/processed/simulator/` | 3706 | 2360 |
| Session A, `session_a_normal` | `data/processed/simulator_v2/session_a_normal/` | 2400 | 1460 |
| Session B, `session_b_new_training` | `data/processed/simulator_v2/session_b_new_training/` | 1126 | 720 |
| Session D, `session_d_curve_focused` | `data/processed/simulator_v2/session_d_curve_focused/` | 7721 | 6117 |

Training total: 10657 rows.

## Validation Holdout

The complete `session_c2_right_recovery` session is reserved for validation:

| Source session | Source path | Raw rows | Validation rows |
| --- | --- | ---: | ---: |
| Session C2, `session_c2_right_recovery` | `data/processed/simulator_v2/session_c2_right_recovery/` | 4163 | 4163 |

No Session C2 rows or image paths are present in training.

## Balancing Strategy

Build seed: `42`.

Rules:

- Dataset v1, Session A, and Session B keep all non-zero steering rows.
- Dataset v1, Session A, and Session B cap near-zero steering rows at 30% per retained source session.
- Session D keeps all near-zero rows, all right-steering rows, and all strong-left rows.
- Session D downsamples softer left-steering rows to target a retained left/right ratio of 0.85 inside Session D.
- Final training rows are shuffled deterministically after sampling.
- No images are copied; manifests reference the resolved source image files.

Retained near-zero rows:

| Source session | Near-zero before | Near-zero after |
| --- | ---: | ---: |
| `v1` | 2054 | 708 |
| `session_a_normal` | 1378 | 438 |
| `session_b_new_training` | 622 | 216 |

Session D left balancing:

| Metric | Rows |
| --- | ---: |
| Left rows before | 3634 |
| Left rows after | 2030 |
| Right rows retained | 2388 |
| Strong-left rows retained | 1021 |
| Softer-left rows before | 2613 |
| Softer-left rows after | 1009 |

## Final Distributions

| Split | Rows | Near-zero | Left | Right | Strong turns | Steering mean | Steering std |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Train | 10657 | 28.72% | 35.86% | 35.41% | 27.20% | -0.004052 | 0.459112 |
| Validation, complete C2 | 4163 | 41.32% | 30.22% | 28.47% | 14.89% | -0.017837 | 0.347744 |

Training source-session rows:

| Source session | Rows |
| --- | ---: |
| `v1` | 2360 |
| `session_a_normal` | 1460 |
| `session_b_new_training` | 720 |
| `session_d_curve_focused` | 6117 |

Validation source-session rows:

| Source session | Rows |
| --- | ---: |
| `session_c2_right_recovery` | 4163 |

## Leakage Checks

| Check | Result |
| --- | ---: |
| Overlapping source sessions | 0 |
| Overlapping image paths | 0 |
| Overlapping CSV rows | 0 |
| Overlapping image filenames | 0 |
| Session C2 rows in training | 0 |
| Session D rows in validation | 0 |
| Missing output images | 0 |
| Corrupt output images | 0 |
| Invalid steering labels | 0 |
| Duplicate train rows / paths | 0 / 0 |
| Duplicate validation rows / paths | 0 / 0 |

## Side-Camera Policy

Local V3 is center-camera only. The project has not yet implemented or tested side-camera steering correction labels, so left/right camera rows were not expanded into training examples. Side-camera correction should remain a separate experiment after the center-camera Local V3 model is evaluated.

## Training Readiness

Dataset verdict: **A) Local V3 dataset ready for session-aware training**.

Explicit manifest support is now implemented in `src/training/train_behavior_cloning.py`.

Supported explicit split arguments:

```text
--train-csv data/processed/local_v3_training/train.csv
--validation-csv data/processed/local_v3_training/validation.csv
```

Command used for the first Local V3 run:

```powershell
python src/training/train_behavior_cloning.py --train-csv data/processed/local_v3_training/train.csv --validation-csv data/processed/local_v3_training/validation.csv --format simple --epochs 15 --batch-size 32 --seed 42 --output models/steering_model_local_v3.pt --chart-output screenshots/training_loss_local_v3.png
```

First Local V3 result:

| Metric | Value |
| --- | ---: |
| Best validation loss | 0.100252 |
| Session C2 MAE | 0.215618 |
| Session C2 RMSE | 0.316627 |
| Right MAE | 0.249182 |
| Strong-turn MAE | 0.598862 |
| Prediction/actual std ratio | 0.656937 |
| Release verdict | R2, valid offline experiment, not promoted |

Validation requirements for future Local V3-family runs:

- Use `train.csv` only for optimization.
- Use `validation.csv` only for validation.
- Do not perform a random row re-split.
- Keep augmentation training-only.
- Select the best checkpoint by validation loss.
- Report overall MAE/RMSE, near-zero MAE, left MAE, right MAE, strong-turn MAE, zero-steering baseline, and prediction-vs-actual standard deviation.
- Report metrics by `source_session`.
- Track each rerun as a separate experiment rather than repeatedly tuning against Session C2.

## Acceptance Criteria

Local V3 model promotion will require material improvement over both prior baselines:

| Metric | Minimum expectation |
| --- | --- |
| Overall MAE | Better than v1 MAE 0.174045 |
| Overall RMSE | Better than v1 RMSE 0.246529 |
| Strong-turn MAE | Clearly better than local v2 strong-turn MAE 0.469480 |
| Right-steering MAE | Clearly better than local v2 right-steering MAE 0.256633 |
| Prediction std | Closer to actual steering std than local v2 compressed predictions |
| Validation split | Complete-session C2 validation reported, not a random row split |

## Safety Boundary

Local V3 remains simulation-only. It must not be presented as real vehicle readiness or public-road capability. Simulator control remains blocked until model evaluation, held-out-session metrics, and prediction stability gates pass.
