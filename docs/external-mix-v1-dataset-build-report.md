# External Mix V1 Dataset Build Report

## Goal

External Mix V1 is an ignored, simulation-only training candidate that preserves every Local V3 training row and adds a capped, balanced subset of the public Udacity behavioral-cloning dataset. The goal is to add external visual diversity without allowing the external source's straight-heavy distribution to dominate Local V3's curve-rich signal.

## Source Datasets

Local V3 training input:

- Path: `data/processed/local_v3_training/train.csv`
- Rows: 10,657
- Source sessions: `v1`, `session_a_normal`, `session_b_new_training`, and `session_d_curve_focused`
- Distribution: 28.72% near-zero, 35.86% left, 35.41% right, and 27.20% strong turns
- Integrity: 0 missing images, 0 duplicate image paths, and 0 invalid steering labels

The separate Local V3 `validation.csv` exists but was not read into, copied to, or used by the candidate.

External input:

- Dataset ID: `udacity_behavioral_cloning_public`
- Root: `data/external/udacity_behavioral_cloning_public/extracted/data/`
- Rows: 8,036
- Images: 24,108 across the center, left, and right cameras
- Integrity: 0 missing references, 0 corrupt images, 0 duplicates, and 0 invalid or out-of-range steering labels
- Distribution: 60.74% near-zero, 19.06% left, 20.20% right, and 0.55% strong turns
- Source verdict: X2, valid but requiring balancing
- Archive SHA-256: `7ca6aba7f72df475de32959b3b7a5a825b345c94307e715639dc2a13eb61dd0c`

## Why External Data Was Capped

Adding the full external dataset would introduce 4,881 near-zero rows but only 44 strong-turn rows. That would weaken the Local V3 steering distribution and overrepresent straight driving. External rows were therefore limited to at most 25% of the final candidate, and near-zero external rows were limited to at most 25% of the external subset.

## Exact Sampling Rules

- Seed: 42
- Requested external rows: 3,000
- Camera policy: center camera only
- Side-camera steering offsets: none
- Near-zero bucket: `abs(steering) <= 0.05`
- Left bucket: `steering < -0.05`
- Right bucket: `steering > 0.05`
- Strong-turn bucket: `abs(steering) >= 0.5`
- External near-zero maximum: 750 rows, or 25% of the subset
- Remaining external capacity: balanced between left and right steering
- Strong-turn policy: retain strong rows before deterministically sampling softer rows within each direction
- Duplicate policy: no oversampling and no duplicate image paths
- Final order: deterministic seeded shuffle

The result selected 750 near-zero rows, 1,125 left rows, and 1,125 right rows. All 44 external strong-turn rows were retained. Exact strong-turn target matching was impossible because the full external source contains only 44 such rows.

## Output

Generated files are under `data/processed/external_mix_v1_training/`:

- `train.csv`
- `dataset_summary.json`
- `source_distribution.csv`
- `external_subset_report.csv`

This directory is ignored by Git. Raw external data, extracted images, and generated manifests were not committed.

## Row Counts and Ratios

| Component | Rows | Candidate share |
| --- | ---: | ---: |
| Local V3 internal | 10,657 | 78.03% |
| External Udacity subset | 3,000 | 21.97% |
| External Mix V1 total | 13,657 | 100.00% |

## Steering Distribution

| Dataset | Near-zero | Left | Right | Strong turns |
| --- | ---: | ---: | ---: | ---: |
| Local V3 train | 28.72% | 35.86% | 35.41% | 27.20% |
| Full external source | 60.74% | 19.06% | 20.20% | 0.55% |
| Selected external subset | 25.00% | 37.50% | 37.50% | 1.47% |
| External Mix V1 | 27.91% | 36.22% | 35.87% | 21.55% |

All 2,899 Local V3 strong-turn rows remain present. The combined strong-turn percentage falls by 5.65 percentage points because the external source is weak on strong turns, but remains above the 20% candidate gate.

## Source Distribution

| Source dataset / session | Rows |
| --- | ---: |
| `internal_local_v3` / `v1` | 2,360 |
| `internal_local_v3` / `session_a_normal` | 1,460 |
| `internal_local_v3` / `session_b_new_training` | 720 |
| `internal_local_v3` / `session_d_curve_focused` | 6,117 |
| `udacity_behavioral_cloning_public` / `external_udacity_public` | 3,000 |

## Validation Checks

- Required metadata columns present: yes
- Local V3 rows preserved: 10,657 of 10,657
- Missing local rows or unexpected internal paths: 0 / 0
- Local steering/session metadata mismatches: 0
- Missing images: 0
- Corrupt images: 0
- Duplicate rows: 0
- Duplicate image paths: 0
- Invalid or out-of-range steering labels: 0
- Session C2, Session E, or Session E2 training rows: 0
- External ratio within 25% cap: yes, 21.97%
- External near-zero cap respected: yes, exactly 25.00%
- Combined distribution gates: passed

The builder and validator compiled successfully. The complete repository suite passed 57 tests in the dependency-complete Python 3.10 environment.

## Verdict

M1 — External Mix V1 candidate ready for review.

M1 means the generated dataset passed automated integrity, governance, cap, and distribution gates. It does not authorize training, model evaluation, release, or simulator control.

## Limitations

- The external source contains only 44 strong-turn rows, so it adds very little strong-turn diversity.
- The external subset's 1.47% strong-turn share remains weak even after balancing.
- The combined strong-turn percentage is lower than Local V3 alone.
- The candidate has not demonstrated a model-quality improvement; that requires a future controlled experiment.
- External licensing and usage terms still require review before any public release claim.

## Future Training Recommendation

After human review, run exactly one controlled offline training experiment comparing the Local V3 baseline with External Mix V1 while holding the model, preprocessing, loss, seed, and evaluation protocol fixed. Do not use Session C2, Session E, or Session E2 as training data.

No model was trained in this task.
