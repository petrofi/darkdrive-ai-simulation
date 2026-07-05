# Local V3 Dataset Build Report

This report documents the Local V3 session-aware dataset build. No model was trained, no simulator control was added, and no raw simulator data was overwritten.

## Scope

Local V3 is a simulation-only behavior-cloning dataset structure. It creates center-camera training and validation manifests that preserve `source_session` identity and keep the Session C2 right-recovery recording completely outside training.

## Source Sessions

| Role | Source session | Path | Raw rows |
| --- | --- | --- | ---: |
| Train | `v1` | `data/processed/simulator/` | 3706 |
| Train | `session_a_normal` | `data/processed/simulator_v2/session_a_normal/` | 2400 |
| Train | `session_b_new_training` | `data/processed/simulator_v2/session_b_new_training/` | 1126 |
| Train | `session_d_curve_focused` | `data/processed/simulator_v2/session_d_curve_focused/` | 7721 |
| Validation | `session_c2_right_recovery` | `data/processed/simulator_v2/session_c2_right_recovery/` | 4163 |

All source sessions converted with 0 missing images and 0 invalid steering labels.

## Outputs

```text
data/processed/local_v3_training/train.csv
data/processed/local_v3_training/validation.csv
data/processed/local_v3_training/dataset_summary.json
data/processed/local_v3_training/source_distribution.csv
```

The manifests reference existing source images. No image files were copied.

## Sampling and Balancing

Seed: `42`.

| Source session | Rule | Rows before | Rows after |
| --- | --- | ---: | ---: |
| `v1` | Keep all non-zero rows, cap near-zero rows at 30% | 3706 | 2360 |
| `session_a_normal` | Keep all non-zero rows, cap near-zero rows at 30% | 2400 | 1460 |
| `session_b_new_training` | Keep all non-zero rows, cap near-zero rows at 30% | 1126 | 720 |
| `session_d_curve_focused` | Keep all near-zero, right, and strong-left rows; downsample softer left rows | 7721 | 6117 |

The Session D rule preserved all 2388 right-steering rows and all 1021 strong-left rows, while reducing softer left rows from 2613 to 1009. This reduced Session D's left-heavy skew without discarding its strongest curve examples.

## Training Split Metrics

| Metric | Value |
| --- | ---: |
| Rows | 10657 |
| Resolved images | 10657 |
| Missing images | 0 |
| Corrupt images | 0 |
| Duplicate rows | 0 |
| Duplicate image paths | 0 |
| Invalid steering labels | 0 |
| Steering outside `[-1, 1]` | 0 |
| Steering min / max | -1.000000 / 1.000000 |
| Steering mean | -0.004052 |
| Steering std | 0.459112 |
| Near-zero steering | 28.72% |
| Left steering | 35.86% |
| Right steering | 35.41% |
| Strong turns | 27.20% |

Rows per training source:

| Source session | Rows |
| --- | ---: |
| `v1` | 2360 |
| `session_a_normal` | 1460 |
| `session_b_new_training` | 720 |
| `session_d_curve_focused` | 6117 |

Throttle, brake, and speed availability: 10657 / 10657 rows for each field.

## Validation Holdout Metrics

Validation uses the complete `session_c2_right_recovery` session.

| Metric | Value |
| --- | ---: |
| Rows | 4163 |
| Resolved images | 4163 |
| Missing images | 0 |
| Corrupt images | 0 |
| Duplicate rows | 0 |
| Duplicate image paths | 0 |
| Invalid steering labels | 0 |
| Steering outside `[-1, 1]` | 0 |
| Steering min / max | -1.000000 / 1.000000 |
| Steering mean | -0.017837 |
| Steering std | 0.347744 |
| Near-zero steering | 41.32% |
| Left steering | 30.22% |
| Right steering | 28.47% |
| Strong turns | 14.89% |

Rows per validation source:

| Source session | Rows |
| --- | ---: |
| `session_c2_right_recovery` | 4163 |

Throttle, brake, and speed availability: 4163 / 4163 rows for each field.

## Leakage Checks

| Check | Result |
| --- | ---: |
| Overlapping source sessions | 0 |
| Overlapping image paths | 0 |
| Overlapping CSV rows | 0 |
| Overlapping image filenames | 0 |
| Session C2 rows in training | 0 |
| Session D rows in validation | 0 |

No Session C2 image names, timestamps, source-session labels, image paths, or CSV rows appear in the training manifest.

## Distribution Comparison

| Dataset/session | Rows | Near-zero | Left | Right | Strong turns | Steering std |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Dataset v1 | 3706 | 55.42% | 22.26% | 22.32% | 14.87% | 0.350406 |
| Merged Local V2 | 8647 | 34.99% | 35.27% | 29.73% | 18.53% | 0.392077 |
| Session D | 7721 | 22.00% | 47.07% | 30.93% | 24.83% | 0.441348 |
| Session C2 validation | 4163 | 41.32% | 30.22% | 28.47% | 14.89% | 0.347744 |
| Local V3 train | 10657 | 28.72% | 35.86% | 35.41% | 27.20% | 0.459112 |

Interpretation:

- Local V3 reduces the Dataset v1 near-zero bias from 55.42% to 28.72%.
- Local V3 improves over merged Local V2 near-zero concentration and strong-turn coverage.
- Local V3 avoids Session D's left dominance: left/right are 35.86% / 35.41%.
- Session C2 remains an independent right-recovery validation holdout.

## Side-Camera Decision

The build uses center-camera images only. Side-camera correction labels are not generated because the current project has not implemented or validated a steering correction offset policy. This keeps Local V3 comparable with the prior center-camera baselines.

## Dataset Verdict

Verdict: **A) Local V3 dataset ready for session-aware training**.

Reasons:

- No missing or corrupt output images.
- No invalid steering labels.
- No train/validation source-session overlap.
- No train/validation image-path, filename, or CSV-row overlap.
- Training near-zero share is within the 25% to 32% target range.
- Left/right balance is close.
- Strong-turn coverage is preserved and improved.
- Build is deterministic with seed `42`.

## Exact Commands

`python` was not on PATH in this Codex PowerShell session, so the bundled Python runtime was used.

Build:

```powershell
& 'C:\Users\tarik\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts/build_local_v3_training_dataset.py --seed 42
```

Validate train:

```powershell
& 'C:\Users\tarik\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts/validate_darkdrive_dataset.py --csv data/processed/local_v3_training/train.csv
```

Validate holdout:

```powershell
& 'C:\Users\tarik\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts/validate_darkdrive_dataset.py --csv data/processed/local_v3_training/validation.csv
```

Compile and test:

```powershell
& 'C:\Users\tarik\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m py_compile scripts/build_local_v3_training_dataset.py src/utils/driving_log.py
& 'C:\Users\tarik\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_build_local_v3_training_dataset
```

## Next Task

Train and evaluate `models/steering_model_local_v3.pt` only after the training and evaluation CLIs support explicit `--train-csv` and `--validation-csv` inputs. Do not use the current random row split for Local V3.
