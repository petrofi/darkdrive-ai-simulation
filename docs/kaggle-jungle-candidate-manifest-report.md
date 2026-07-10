# Kaggle Jungle Candidate Manifest Report

## Goal

Build and validate a provenance-preserving, center-camera-only candidate manifest from the reviewed K1 Kaggle jungle track. This task did not create a training mix, change Local V3, train a model, or evaluate a checkpoint.

## Source Selection

- Dataset: `kaggle_udacity_behavioral_cloning_lake_jungle`
- Included track: `self_driving_car_dataset_jungle`
- Source CSV: `data/external/kaggle_udacity_behavioral_cloning_lake_jungle/extracted/self_driving_car_dataset_jungle/driving_log.csv`
- Explicitly excluded track: `self_driving_car_dataset_make`
- Excluded-track reason: `make` is technically valid but has 80.41% near-zero steering, only 2.72% right steering, and only 1.88% strong turns.
- License status: unresolved; no archive-specific license, README, or terms file was found.

The track root was discovered recursively. The headerless seven-column Udacity schema and its local `IMG/` directory were verified before output was written.

## Output

Generated files remain ignored under `data/processed/external/kaggle_jungle_candidate/`:

- `manifest.csv`
- `dataset_summary.json`
- `source_distribution.csv`

Git ignore verification matched `data/processed/external/*`. No generated manifest, external CSV, ZIP, extracted image, model, screenshot, or metrics artifact is committed.

## Manifest Schema

| Column | Policy |
| --- | --- |
| `image_path` | Resolved absolute path to the local center image |
| `steering` | Finite source steering value in `[-1, 1]` |
| `throttle`, `brake`, `speed` | Preserved numeric source controls |
| `source_dataset` | `kaggle_udacity_behavioral_cloning_lake_jungle` |
| `source_track` | `self_driving_car_dataset_jungle` |
| `source_row_index` | Original headerless CSV line number, starting at 1 |
| `camera` | `center` |
| `is_external` | `true` |
| `original_center_path` | Unmodified producer-side center reference after whitespace trimming |
| `original_left_path` | Producer-side left reference retained only as provenance |
| `original_right_path` | Producer-side right reference retained only as provenance |

## Center-Camera Policy

All 3,404 jungle CSV rows are retained in their original order. Only center images become candidate rows because their steering labels are directly aligned with the source log. Left and right image references are preserved only as metadata. No side-camera images and no steering correction offsets are used.

## Validation Results

| Check | Result |
| --- | ---: |
| Manifest rows | 3,404 |
| Resolved center / left / right source references | 3,404 / 3,404 / 3,404 |
| Missing manifest images | 0 |
| Corrupt manifest images, full scan | 0 |
| Duplicate rows / image paths / image filenames | 0 / 0 / 0 |
| Invalid / out-of-range steering labels | 0 / 0 |
| Throttle / brake / speed values available | 3,404 / 3,404 / 3,404 |
| `make` rows | 0 |
| Session C2/E/E2 rows | 0 |
| Non-center rows | 0 |

Steering distribution:

| Bucket | Rows | Percent |
| --- | ---: | ---: |
| Near-zero, `abs(steering) <= 0.05` | 1,600 | 47.00% |
| Left, `steering < -0.05` | 881 | 25.88% |
| Right, `steering > 0.05` | 923 | 27.12% |
| Strong turn, `abs(steering) >= 0.5` | 898 | 26.38% |

Steering min/mean/max are -1.000000 / 0.006287 / 1.000000, with population standard deviation 0.448626. Every row belongs to the intended dataset, jungle track, center camera, and external-data provenance group.

## Source-Preservation Check

The generated row count and near-zero, left, right, and strong-turn percentages were compared with the ignored EXP-016 validation metadata. Every value matched exactly, with delta 0. The candidate therefore preserves the complete validated jungle distribution without filtering, sampling, or shuffling.

## Dataset Comparison

| Dataset | Rows | Near-zero | Left | Right | Strong |
| --- | ---: | ---: | ---: | ---: | ---: |
| Kaggle jungle candidate | 3,404 | 47.00% | 25.88% | 27.12% | 26.38% |
| Previous external Udacity source | 8,036 | 60.74% | 19.06% | 20.20% | 0.55% |
| Local V3 train | 10,657 | 28.72% | 35.86% | 35.41% | 27.20% |

The jungle candidate is substantially stronger than the previous external Udacity source for curve and strong-turn coverage. Its strong-turn share is close to Local V3, but it is more near-zero and less direction-heavy than Local V3. That makes it a useful future external candidate, not a replacement for Local V3 and not a ready-made training mix.

## Candidate Verdict

**J1 — Jungle candidate manifest ready for review.**

The center-only manifest exists, all manifest images passed a full integrity scan, labels and provenance are valid, duplicate image paths are absent, the K2 `make` track is excluded, the validated distribution is preserved, and no forbidden internal session appears.

J1 does not authorize training. A future mix needs an explicit cap, composition policy, leakage checks, license review, and separate human approval.

## Limitations

- Dataset-specific license/terms remain unresolved.
- Only source-file and offline manifest integrity were evaluated.
- No side-camera correction policy was implemented or tested.
- No domain-shift or model-generalization claim can be made from manifest statistics.
- No closed-loop simulator behavior was tested.

## Verification

- `python -m py_compile scripts/build_kaggle_jungle_candidate_manifest.py`: passed with the repository's working Python 3.10 runtime.
- `python -m unittest discover -s tests`: 78 tests passed.
- Actual build command: `python scripts/build_kaggle_jungle_candidate_manifest.py --force`.

## Recommended Next Task

Review this manifest, then build a controlled Kaggle Jungle Mix V1 candidate in a later task. Keep `make` excluded by default and do not train until the mix policy and unresolved license gate are reviewed.

No model was trained in this task.
