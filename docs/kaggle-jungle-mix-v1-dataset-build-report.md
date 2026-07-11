# Kaggle Jungle Mix V1 Dataset Build Report

## Goal

Build and validate a controlled, ignored training candidate that combines every Local V3 training row with every reviewed Kaggle Jungle center-camera row. This task did not modify Local V3 manifests, use validation data, train a model, or evaluate a checkpoint.

## Source Datasets

- Local base: `data/processed/local_v3_training/train.csv`, 10,657 rows.
- External candidate: `data/processed/external/kaggle_jungle_candidate/manifest.csv`, 3,404 rows.
- Included external track: `self_driving_car_dataset_jungle`.
- Excluded external track: `self_driving_car_dataset_make`.
- Excluded validation/training sources: Session C2, Session E, Session E2, and `udacity_behavioral_cloning_public`.

Jungle was included because it has balanced left/right steering and 26.38% strong turns. `make` was excluded because it is 80.41% near-zero, only 2.72% right, and only 1.88% strong. The Kaggle dataset-specific license remains unresolved.

## Mix Strategy

- Retain 100% of Local V3 training rows in their existing order.
- Append 100% of Kaggle Jungle candidate rows in their existing order.
- Use center-camera rows only.
- Do not sample, shuffle, oversample, copy images, or add side-camera steering offsets.
- Preserve Local V3 source sessions and datasets.
- Preserve Jungle dataset, track, row index, camera, and producer center-path provenance.
- Do not read from or modify `data/processed/local_v3_training/validation.csv`.

## Output

Generated files remain ignored under `data/processed/kaggle_jungle_mix_v1_training/`:

- `train.csv`
- `dataset_summary.json`
- `source_distribution.csv`

## Row Counts And External Ratio

| Component | Rows | Share |
| --- | ---: | ---: |
| Local V3 | 10,657 | 75.79% |
| Kaggle Jungle | 3,404 | 24.21% |
| Total | 14,061 | 100.00% |

All Local V3 and Jungle rows and their source order were preserved exactly.

## Steering Distribution

| Bucket | Rows | Percent |
| --- | ---: | ---: |
| Near-zero, `abs(steering) <= 0.05` | 4,661 | 33.15% |
| Left, `steering < -0.05` | 4,703 | 33.45% |
| Right, `steering > 0.05` | 4,697 | 33.40% |
| Strong turn, `abs(steering) >= 0.5` | 3,797 | 27.00% |

Steering min/mean/max are -1.000000 / -0.001549 / 1.000000, with population standard deviation 0.456601.

## Source Distribution

| Dataset | Session | Track | Rows | Candidate share |
| --- | --- | --- | ---: | ---: |
| `local_simulator_v1` | `v1` | N/A | 2,360 | 16.78% |
| `local_simulator_v2` | `session_a_normal` | N/A | 1,460 | 10.38% |
| `local_simulator_v2` | `session_b_new_training` | N/A | 720 | 5.12% |
| `local_simulator_v2` | `session_d_curve_focused` | N/A | 6,117 | 43.50% |
| `kaggle_udacity_behavioral_cloning_lake_jungle` | `external_kaggle_jungle` | `self_driving_car_dataset_jungle` | 3,404 | 24.21% |

All 14,061 rows use the center camera. Throttle, brake, and speed are available for every row.

## Validation Checks

| Check | Result |
| --- | ---: |
| Missing images | 0 |
| Corrupt images, full scan | 0 |
| Duplicate rows / image paths / image filenames | 0 / 0 / 0 |
| Invalid / out-of-range steering labels | 0 / 0 |
| `make` rows | 0 |
| Session C2/E/E2 rows | 0 |
| Non-center rows | 0 |
| Local V3 rows preserved | 10,657 / 10,657 |
| Jungle rows preserved | 3,404 / 3,404 |

The builder compiled successfully. Ten focused temporary-data tests passed, and the full repository suite passed 88 tests.

## Comparison

| Candidate | Rows | Near-zero | Left | Right | Strong |
| --- | ---: | ---: | ---: | ---: | ---: |
| Local V3 train | 10,657 | 28.72% | 35.86% | 35.41% | 27.20% |
| Kaggle Jungle source | 3,404 | 47.00% | 25.88% | 27.12% | 26.38% |
| Previous External Mix V1 | 13,657 | 27.91% | 36.22% | 35.87% | 21.55% |
| Kaggle Jungle Mix V1 | 14,061 | 33.15% | 33.45% | 33.40% | 27.00% |

Kaggle Jungle Mix V1 keeps strong-turn coverage within 0.20 percentage points of Local V3 while adding 3,404 external images. It is more near-zero than Local V3, but directions remain almost exactly balanced. Unlike the previous external source, Jungle itself has 26.38% strong turns, so the combined candidate does not dilute Local V3's curve strength to the previous mix's 21.55%. The weak `make` track and straight-heavy prior external source are absent.

## Candidate Verdict

**KM1 — Kaggle Jungle Mix V1 candidate ready for review.**

The mix passes integrity, row-preservation, exclusion, external-ratio, direction-balance, and strong-turn gates. KM1 is a dataset-candidate verdict only; it does not authorize training or model promotion.

## Limitations

- Kaggle dataset-specific license/terms remain unresolved.
- The 24.21% external share and domain shift have not been tested by a model.
- No independent model generalization or closed-loop simulator behavior was evaluated.
- Session C2 has already influenced prior model-selection decisions and remains excluded from training.
- No side-camera correction policy was implemented.

## Future Training Recommendation

This recommendation was completed exactly once in EXP-019 with the Local V3 baseline configuration fixed and training data as the single changed variable. Do not repeat the run or tune further against Session C2; Session E2 independent evaluation is now the next evidence gate.

No model was trained in this task.
