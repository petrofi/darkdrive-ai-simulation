# Dataset V2 Session B Report

A new root-level simulator recording folder named `yeni eğitim/` was organized into Dataset v2.

## Dataset Location

```text
data/processed/simulator_v2/session_b_new_training/
|-- IMG/
`-- driving_log.csv
```

The original folder name was kept out of Git and the generated simulator data remains ignored.

## Session Type

Session B: new local simulator training recording.

This session is not labeled as a confirmed left-recovery or right-recovery session because the steering distribution does not clearly show recovery-focused behavior. It is treated as a general Dataset v2 training session until the driving intent is confirmed.

## Analysis Summary

Command:

```powershell
python scripts/session_dataset_report.py --csv data/processed/simulator_v2/session_b_new_training/driving_log.csv --images-dir data/processed/simulator_v2/session_b_new_training/IMG --format udacity --session-name session_b_new_training
```

Results:

| Metric | Value |
| --- | ---: |
| Total rows | 1126 |
| Total simulator images | 3378 |
| Center images found | 1126 |
| Missing center images | 0 |
| Steering min | -0.983591 |
| Steering max | 0.932523 |
| Steering mean | -0.030387 |
| Steering std | 0.244779 |
| Near-zero steering, abs <= 0.05 | 55.24% |
| Left steering, steering < -0.05 | 25.84% |
| Right steering, steering > 0.05 | 18.92% |
| Strong turns, abs >= 0.5 | 8.17% |

Validation result: PASS.

## Strengths

- The session has a valid Udacity-style `driving_log.csv`.
- All center images resolve successfully after moving the dataset.
- Steering labels include both left and right values.
- The dataset is safe for offline analysis and future merging.

## Weaknesses

- Near-zero steering remains high at 55.24%.
- Steering standard deviation is lower than Dataset v1 and Session A.
- Strong turns are only 8.17%.
- Right steering is still underrepresented compared with left steering.
- This session does not materially solve the steering-balance bottleneck.

## Does It Reduce The V1 Near-Zero Problem?

Not meaningfully.

Dataset v1 near-zero steering:

```text
55.42%
```

Dataset v2 Session B near-zero steering:

```text
55.24%
```

This is only a tiny improvement. Session B is valid, but it should not be considered the recovery dataset the project still needs.

## Recommended Next Session

Collect a deliberate right-recovery and curve-focused session next:

- Start slightly right of lane center.
- Steer smoothly back left toward lane center.
- Include right turns and curve exits.
- Avoid long straight segments with steering near 0.0.
- Target fewer near-zero labels and more moderate-to-strong corrections.

