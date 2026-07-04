# Dataset V2 Session C2 Right Recovery Report

Session C2 was collected to improve right-steering and right-recovery behavior in the Udacity simulator workflow.

## Dataset Location

```text
data/processed/simulator_v2/session_c2_right_recovery/
|-- IMG/
`-- driving_log.csv
```

Generated simulator files in this folder remain ignored by Git.

## Collection Objective

The session was intended to add:

- More right-steering examples than earlier local sessions.
- Recovery-driving frames instead of mostly centered lane following.
- Stronger correction examples without introducing corrupt or missing data.
- A better candidate source for local Dataset v2 training.

## Physical Validation

Repository status before analysis:

```text
Branch: main
Status: clean
Latest commit: 884c34d docs: document donkeycar python312 compatibility issue
```

Physical files:

| Check | Result |
| --- | --- |
| `IMG/` exists | Yes |
| `driving_log.csv` exists | Yes |
| Files in `IMG/` | 12489 |
| CSV rows | 4163 |
| Newest CSV/image modification time | 2026-07-04 17:52:20 |
| Recording appears complete | Yes, with 0 missing images |

The CSV is headerless Udacity format:

```text
center,left,right,steering,throttle,brake,speed
```

All image path entries are absolute Windows paths. Existing path-resolution utilities handled them without modifying the raw CSV.

## Commands Used

```powershell
python scripts/session_dataset_report.py --csv data/processed/simulator_v2/session_c2_right_recovery/driving_log.csv --images-dir data/processed/simulator_v2/session_c2_right_recovery/IMG --format udacity --session-name session_c2_right_recovery
python scripts/compare_datasets.py --csv-a data/processed/simulator/driving_log.csv --images-dir-a data/processed/simulator/IMG --name-a dataset_v1 --format-a udacity --csv-b data/processed/simulator_v2/session_c2_right_recovery/driving_log.csv --images-dir-b data/processed/simulator_v2/session_c2_right_recovery/IMG --name-b session_c2_right_recovery --format-b udacity
python scripts/compare_datasets.py --csv-a data/processed/simulator_v2/session_a_normal/driving_log.csv --images-dir-a data/processed/simulator_v2/session_a_normal/IMG --name-a session_a_normal --format-a udacity --csv-b data/processed/simulator_v2/session_c2_right_recovery/driving_log.csv --images-dir-b data/processed/simulator_v2/session_c2_right_recovery/IMG --name-b session_c2_right_recovery --format-b udacity
python scripts/compare_datasets.py --csv-a data/processed/simulator_v2/session_b_new_training/driving_log.csv --images-dir-a data/processed/simulator_v2/session_b_new_training/IMG --name-a session_b_new_training --format-a udacity --csv-b data/processed/simulator_v2/session_c2_right_recovery/driving_log.csv --images-dir-b data/processed/simulator_v2/session_c2_right_recovery/IMG --name-b session_c2_right_recovery --format-b udacity
```

## Session Metrics

Thresholds:

- Near-zero steering: `abs(steering) <= 0.05`
- Left steering: `steering < -0.05`
- Right steering: `steering > 0.05`
- Strong turn: `abs(steering) >= 0.5`

| Metric | Value |
| --- | ---: |
| Total CSV rows | 4163 |
| Total image files | 12489 |
| Center image files | 4163 |
| Left image files | 4163 |
| Right image files | 4163 |
| Missing center images | 0 |
| Missing left images | 0 |
| Missing right images | 0 |
| Steering min | -1.000000 |
| Steering max | 1.000000 |
| Steering mean | -0.017837 |
| Steering std | 0.347744 |
| Near-zero steering | 41.32% |
| Left steering | 30.22% |
| Right steering | 28.47% |
| Strong turns | 14.89% |
| Throttle min / mean / max | 0.000000 / 0.934933 / 1.000000 |
| Brake min / mean / max | 0.000000 / 0.023336 / 1.000000 |
| Speed min / mean / max | 0.000038 / 27.783219 / 30.547250 |

## Data Quality Checks

| Check | Result |
| --- | ---: |
| Duplicate CSV rows | 0 |
| Duplicate image references | 0 |
| Exact duplicate image files by MD5 | 0 |
| Unreadable/corrupt images | 0 |
| Invalid steering values | 0 |
| Invalid throttle/brake/speed values | 0 |
| Steering outside `[-1, 1]` | 0 |
| Image shape | 12489 images at 320x160x3 |
| Longest near-zero run | 31 rows |
| Stationary rows, `abs(speed) <= 0.1` | 110 rows, 2.64% |
| Longest stationary run | 63 rows |
| Timestamp parse failures | 0 |
| Non-positive timestamp deltas | 0 |
| Recording gaps greater than 0.25s | 4 |
| Recording gaps greater than 0.50s | 3 |
| Largest recording gap | 27.250s |

The timestamp gaps look like pauses/resumes rather than malformed data. They do not create missing files or duplicate frames, but they are worth noting because adjacent-frame validation can still be optimistic.

## Comparison

| Metric | Dataset v1 | Session A | Session B New Training | Session C2 |
| --- | ---: | ---: | ---: | ---: |
| Rows | 3706 | 2400 | 1126 | 4163 |
| Missing images | 0 | 0 | 0 | 0 |
| Near-zero steering | 55.42% | 57.42% | 55.24% | 41.32% |
| Left steering | 22.26% | 28.17% | 25.84% | 30.22% |
| Right steering | 22.32% | 14.42% | 18.92% | 28.47% |
| Strong turns | Not recorded in v1 report | 14.12% | 8.17% | 14.89% |
| Steering mean | -0.013526 | -0.012757 | -0.030387 | -0.017837 |
| Steering std | 0.350406 | 0.356202 | 0.244779 | 0.347744 |

Session C2 is a real improvement for right steering and near-zero reduction:

- Right steering improved from 14.42% in Session A to 28.47%.
- Right steering improved from 18.92% in Session B to 28.47%.
- Near-zero steering dropped below the 45% target.
- Strong turns nearly reached the 15% target but missed by 0.11 percentage points.
- Left steering remains slightly higher than right steering.

## Quality Verdict

Verdict: **B) Usable but imperfect**.

Session C2 is valid and useful for Dataset v2. It passes missing-image, near-zero, and right-steering gates, and it provides meaningful recovery/correction coverage. It is not a strong standalone right-recovery session because strong-turn coverage is 14.89% instead of above 15%, and right steering does not exceed left steering.

## Training Inclusion

Session C2 was included in the merged local Dataset v2 because it passed validation and materially improved steering distribution. It contributed 3336 rows after near-zero balancing.

## Recommendation

Use Session C2 as part of Dataset v2, but do not treat it as sufficient proof of model readiness. The next data collection should add more curve-focused and strong-turn correction examples, with special attention to right-turn magnitude.
