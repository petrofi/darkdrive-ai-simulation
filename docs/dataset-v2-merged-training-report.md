# Dataset V2 Merged Training Report

This report documents the local Dataset v2 training CSV built from validated Udacity simulator sessions.

## Source Sessions

| Source | CSV | Images |
| --- | --- | --- |
| Dataset v1 | `data/processed/simulator/driving_log.csv` | `data/processed/simulator/IMG` |
| Session A normal | `data/processed/simulator_v2/session_a_normal/driving_log.csv` | `data/processed/simulator_v2/session_a_normal/IMG` |
| Session B new training | `data/processed/simulator_v2/session_b_new_training/driving_log.csv` | `data/processed/simulator_v2/session_b_new_training/IMG` |
| Session C2 right recovery | `data/processed/simulator_v2/session_c2_right_recovery/driving_log.csv` | `data/processed/simulator_v2/session_c2_right_recovery/IMG` |

All raw session folders remain preserved and ignored by Git.

## Build Command

```powershell
python scripts/build_local_v2_training_dataset.py --output-csv data/processed/local_v2_training/driving_log.csv --max-near-zero-ratio 0.35 --seed 42 --session v1,data/processed/simulator/driving_log.csv,data/processed/simulator/IMG --session session_a_normal,data/processed/simulator_v2/session_a_normal/driving_log.csv,data/processed/simulator_v2/session_a_normal/IMG --session session_b_new_training,data/processed/simulator_v2/session_b_new_training/driving_log.csv,data/processed/simulator_v2/session_b_new_training/IMG --session session_c2_right_recovery,data/processed/simulator_v2/session_c2_right_recovery/driving_log.csv,data/processed/simulator_v2/session_c2_right_recovery/IMG
```

## Builder Behavior

The builder:

- Reads each source session as Udacity format.
- Uses center-camera images only.
- Resolves existing image paths without modifying raw CSV files.
- Writes a simple-format training CSV with `image_path`, `steering`, `throttle`, `brake`, `speed`, `source_dataset`, and `session_name`.
- Preserves session identity through `session_name`.
- Downsamples near-zero steering rows with seed 42.
- Caps near-zero steering at 35% while preserving turning rows.

No labels were invented.

## Pre-Balancing Distribution

| Metric | Value |
| --- | ---: |
| Rows | 11395 |
| Near-zero steering | 5774, 50.67% |
| Left steering | 3050, 26.77% |
| Right steering | 2571, 22.56% |
| Strong turns | 1602, 14.06% |
| Steering std | 0.341692 |

## Final Dataset Metrics

Validation command:

```powershell
python scripts/validate_darkdrive_dataset.py --csv data/processed/local_v2_training/driving_log.csv --images-dir data/processed/local_v2_training
```

Final output:

| Metric | Value |
| --- | ---: |
| Total merged rows | 8647 |
| Found images | 8647 |
| Missing images | 0 |
| Duplicate rows | 0 |
| Duplicate image paths | 0 |
| Invalid steering values | 0 |
| Steering min | -1.000000 |
| Steering max | 1.000000 |
| Steering mean | -0.021734 |
| Steering std | 0.392077 |
| Near-zero steering | 34.99% |
| Left steering | 35.27% |
| Right steering | 29.73% |
| Strong turns | 18.53% |

Rows by source/session:

| Source/session | Rows |
| --- | ---: |
| `local_simulator_v1` | 2746 |
| `local_simulator_v2` | 5901 |
| `v1` | 2746 |
| `session_a_normal` | 1736 |
| `session_b_new_training` | 829 |
| `session_c2_right_recovery` | 3336 |

## Comparison Against Dataset v1

| Metric | Dataset v1 | Local Dataset v2 |
| --- | ---: | ---: |
| Rows | 3706 | 8647 |
| Missing images | 0 | 0 |
| Near-zero steering | 55.42% | 34.99% |
| Left steering | 22.26% | 35.27% |
| Right steering | 22.32% | 29.73% |
| Strong turns | Not recorded in v1 report | 18.53% |
| Steering std | 0.350406 | 0.392077 |

Dataset v2 is distribution-improved for the intended offline research goal. It reduces near-zero dominance, increases right-steering representation, and increases strong-turn coverage without missing images.

## Known Limitations

- Only center-camera frames are used.
- The merged set is still left-heavy: 35.27% left versus 29.73% right.
- Near-zero downsampling improves label balance but removes some normal-driving coverage.
- Validation and training use a random row split in the current pipeline, so adjacent simulator frames may make validation optimistic.
- No session-aware split is implemented yet.
- This dataset does not prove closed-loop simulator readiness.

## Decision

The merged local Dataset v2 passed validation and was used for offline training of `models/steering_model_local_v2.pt`.
