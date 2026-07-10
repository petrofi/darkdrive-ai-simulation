# Kaggle Udacity Dataset Validation Report

## Dataset And Source

- Dataset ID: `kaggle_udacity_behavioral_cloning_lake_jungle`
- Source: Kaggle, Udacity Self Driving Car - Behavioural Cloning
- Source URL: <https://www.kaggle.com/datasets/andy8744/udacity-self-driving-car-behavioural-cloning>
- Download method: manual browser download
- Validation date: 2026-07-10

## Root-Level Placement Correction

The human initially placed these untracked external artifacts in the repository root:

```text
kaggle_udacity_behavioral_cloning_lake_jungle.zip
kaggle_udacity_behavioral_cloning_lake_jungle/
```

Emergency root-level ignore rules were added before movement. The artifacts were then moved, without overwriting an existing target, to:

```text
data/external/kaggle_udacity_behavioral_cloning_lake_jungle/raw/kaggle_udacity_behavioral_cloning_lake_jungle.zip
data/external/kaggle_udacity_behavioral_cloning_lake_jungle/extracted/
data/external/kaggle_udacity_behavioral_cloning_lake_jungle/metadata/
```

Move verification matched the source and target exactly:

- ZIP: 294,399,633 bytes before and after
- Extracted files: 22,004 before and after
- Extracted bytes: 294,206,140 before and after
- Root-level Kaggle ZIP/folder remaining: 0

All corrected external-data paths are ignored by Git.

## ZIP And Extraction State

| Field | Value |
| --- | --- |
| ZIP path | `data/external/kaggle_udacity_behavioral_cloning_lake_jungle/raw/kaggle_udacity_behavioral_cloning_lake_jungle.zip` |
| ZIP size | 294,399,633 bytes |
| ZIP modified time | 2026-07-10 17:19:41 UTC |
| SHA-256 | `b8bde91d71b4fca7639962eb24374e519cf01dec48650b026079e46ccf74ceba` |
| Extracted path | `data/external/kaggle_udacity_behavioral_cloning_lake_jungle/extracted/` |
| Extracted files / bytes | 22,004 / 294,206,140 |
| Extraction mode | Manually pre-extracted, then relocated |

The existing extracted data was used as instructed and was not overwritten. Because extraction occurred manually before this task, zip-slip protection cannot be verified retroactively for that extraction event. The new validator includes safe ZIP extraction with traversal/symlink/collision rejection for future runs, and its zip-slip rejection is covered by an offline test.

Generated checksum, extraction, and validation JSON files are under the ignored `metadata/` directory.

## Detected Roots And Schemas

Two candidate roots were discovered recursively:

| Track ID | CSV | Image folder | Schema |
| --- | --- | --- | --- |
| `self_driving_car_dataset_jungle` | `driving_log.csv` | `IMG/` | Headerless Udacity: center, left, right, steering, throttle, brake, speed |
| `self_driving_car_dataset_make` | `driving_log.csv` | `IMG/` | Headerless Udacity: center, left, right, steering, throttle, brake, speed |

The second folder is documented exactly as supplied: `self_driving_car_dataset_make`. It was not renamed or assumed to mean another track.

Both CSVs contained absolute Windows paths from the original producer. Validation normalized those paths and resolved each reference by filename against the local track `IMG/` folder without modifying the raw CSV.

## `self_driving_car_dataset_jungle`

| Metric | Result |
| --- | ---: |
| CSV rows | 3,404 |
| Total images | 10,212 |
| Center / left / right images | 3,404 / 3,404 / 3,404 |
| Missing center / left / right | 0 / 0 / 0 |
| Corrupt images | 0 |
| Duplicate CSV rows / image paths / filenames | 0 / 0 / 0 |
| Invalid / out-of-range steering labels | 0 / 0 |
| Steering min / mean / max | -1.000000 / 0.006287 / 1.000000 |
| Steering standard deviation | 0.448626 |
| Near-zero | 1,600 / 47.00% |
| Left | 881 / 25.88% |
| Right | 923 / 27.12% |
| Strong turns | 898 / 26.38% |
| Throttle / brake / speed available | 3,404 / 3,404 / 3,404 |
| Reverse available | 0 |

Verdict: **K1 — Strong external candidate.**

Reasons:

- Schema and all center/left/right references are valid.
- Full image scan found no corruption.
- Left/right distribution is balanced and useful.
- Near-zero share is materially lower than the previous source.
- Strong-turn coverage is 26.38%, far above the previous 0.55%.

K1 makes this track eligible for a later candidate-manifest review. It does not authorize training or mixing.

## `self_driving_car_dataset_make`

| Metric | Result |
| --- | ---: |
| CSV rows | 3,930 |
| Total images | 11,790 |
| Center / left / right images | 3,930 / 3,930 / 3,930 |
| Missing center / left / right | 0 / 0 / 0 |
| Corrupt images | 0 |
| Duplicate CSV rows / image paths / filenames | 0 / 0 / 0 |
| Invalid / out-of-range steering labels | 0 / 0 |
| Steering min / mean / max | -1.000000 / -0.034529 / 1.000000 |
| Steering standard deviation | 0.133388 |
| Near-zero | 3,160 / 80.41% |
| Left | 663 / 16.87% |
| Right | 107 / 2.72% |
| Strong turns | 74 / 1.88% |
| Throttle / brake / speed available | 3,930 / 3,930 / 3,930 |
| Reverse available | 0 |

Verdict: **K2 — Valid but weak.**

Reasons:

- Files and labels are technically valid.
- Near-zero share is excessive at 80.41%.
- Right steering is only 2.72%.
- Left/right balance ratio is 0.161.
- Strong-turn share is only 1.88%.

This track must not be included wholesale in a future candidate.

## Comparison With Previous External Dataset

| Source / track | Rows | Near-zero | Left | Right | Strong turns | Integrity verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Previous public Udacity source | 8,036 | 60.74% | 19.06% | 20.20% | 0.55% | X2, valid but straight-heavy |
| Kaggle jungle | 3,404 | 47.00% | 25.88% | 27.12% | 26.38% | K1 |
| Kaggle `make` | 3,930 | 80.41% | 16.87% | 2.72% | 1.88% | K2 |

The jungle track is genuinely better for DarkDrive's identified curve/strong-turn gap despite being smaller. The `make` track is worse on near-zero concentration and directional balance. Dataset size is therefore not used as the deciding factor.

## License And Governance

No license, README, terms, or data-card file was present in the extracted archive. The Kaggle page's dataset-specific license/usage terms still require human review before public release or broader reuse. Treat the data as local research material only.

No normalized or training manifest was generated. No data was merged into Local V3 or External Mix V1.

## Recommendation

In a later task, build a center-camera candidate manifest from the K1 jungle track only, preserving provenance and performing a final manifest-level review. Do not train in that task unless a separate experiment is explicitly approved. Keep the K2 `make` track excluded by default.

No model was trained in this task.

No checkpoint evaluation was run.
