# External Udacity Dataset Ingestion Report

## Dataset and source

- Dataset ID: `udacity_behavioral_cloning_public`
- Source URL: <https://d17h27t6h515a5.cloudfront.net/topher/2016/December/584f6edd_data/data.zip>
- Source type: public Udacity-format behavioral-cloning simulator dataset.
- Download completed: 2026-07-09 20:27:22 UTC.
- Archive size: 333,137,665 bytes.
- SHA-256: `7ca6aba7f72df475de32959b3b7a5a825b345c94307e715639dc2a13eb61dd0c`.

The ZIP, extracted images, source CSV, generated JSON metadata, and generated manifest are ignored by Git.

## Extraction and structure

- Extraction completed: 2026-07-09 20:28:48 UTC.
- Extraction path: `data/external/udacity_behavioral_cloning_public/extracted/`.
- Detected dataset root: `data/external/udacity_behavioral_cloning_public/extracted/data/`.
- Extracted files / bytes: 48,219 / 329,338,837.
- Structure: headered `driving_log.csv` with `center`, `left`, `right`, `steering`, `throttle`, `brake`, and `speed`; plus `IMG/`.

## Validation results

All image paths resolved across the 8,036 CSV rows: 8,036 center, 8,036 left, and 8,036 right references. The `IMG/` directory contains 24,108 files. No missing references, corrupt images, duplicate CSV rows, duplicate image references, duplicate filenames, invalid steering labels, or out-of-range steering labels were found.

| Metric | Result |
| --- | ---: |
| Steering min / mean / max | -0.942695 / 0.004070 / 1.000000 |
| Steering standard deviation | 0.128832 |
| Near-zero, abs(steering) <= 0.05 | 60.74% |
| Left, steering < -0.05 | 19.06% |
| Right, steering > 0.05 | 20.20% |
| Strong turn, abs(steering) >= 0.5 | 0.55% |
| Throttle min / mean / max | 0.000000 / 0.869660 / 0.985533 |
| Brake min / mean / max | 0.000000 / 0.001970 / 1.000000 |
| Speed min / mean / max | 0.502490 / 28.169839 / 30.709360 |

## Comparison with internal datasets

The external data is much more straight-heavy than Local V3 train (28.72% near-zero), Session C2 (41.32%), Session D (22.00%), and Session E (46.59%). Its left/right split is broadly balanced, but both sides are lower because most records are near zero. Strong-turn coverage (0.55%) is substantially below Local V3 (27.20%), C2 (14.89%), D (24.83%), and E (9.72%).

This source is not suitable as unbalanced direct training augmentation, because it would reinforce straight-driving dominance and adds very little strong-turn coverage. It could be considered for a separately reviewed, balanced auxiliary-pretraining or controlled-mix candidate, but no improvement is claimed without training.

## Verdict and training decision

Verdict: **X2 — External dataset valid but needs conversion/cleaning.** The data is structurally clean and checksummed, but its distribution requires an explicit balancing policy before a controlled experiment.

An ignored normalized manifest was created at `data/processed/external/udacity_behavioral_cloning_public/manifest.csv`: 8,036 rows, all references resolved. Center-only use would be technically possible later, and side-camera correction could be considered later. Neither conclusion authorizes training.

No model was trained in this task.

No model evaluation was run in this task.

External data was not merged into Local V3.

## License and next step

The source is a public Udacity classroom dataset, but its license and usage terms still require review before any public release claim. Treat it as local research data only.

Exact recommended next step: build an **External Mix V1 training candidate** with an explicit near-zero cap and preservation of scarce Local V3 strong-turn data, then review the mix. Do not train until that mix is approved.
