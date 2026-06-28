# Dataset V2 Session B New Training Report

This report classifies `session_b_new_training` after re-analysis. The session is valid, but it should not be renamed to Session C Right Recovery.

## Dataset Location

```text
data/processed/simulator_v2/session_b_new_training/
|-- IMG/
`-- driving_log.csv
```

Generated simulator files in this folder remain ignored by Git.

## Purpose

The folder likely came from a raw recording originally named `yeni eğitim`. It was inspected to determine whether it should become:

- Session C Right Recovery
- Session B Left Recovery
- Mixed/normal training data
- Not useful

## Metrics

Command:

```powershell
python scripts/session_dataset_report.py --csv data/processed/simulator_v2/session_b_new_training/driving_log.csv --images-dir data/processed/simulator_v2/session_b_new_training/IMG --format udacity --session-name session_b_new_training
```

Results:

| Metric | Value |
| --- | ---: |
| Total rows | 1126 |
| Center image count | 1126 |
| Missing image count | 0 |
| Steering min | -0.983591 |
| Steering max | 0.932523 |
| Steering mean | -0.030387 |
| Steering std | 0.244779 |
| Near-zero steering, abs <= 0.05 | 55.24% |
| Left steering, steering < -0.05 | 25.84% |
| Right steering, steering > 0.05 | 18.92% |
| Strong turns, abs >= 0.5 | 8.17% |

Validation result: PASS.

## Comparison To Session A

| Metric | Session A Normal | Session B New Training | Change |
| --- | ---: | ---: | ---: |
| Rows | 2400 | 1126 | -1274 |
| Near-zero steering | 57.42% | 55.24% | -2.18 pp |
| Left steering | 28.17% | 25.84% | -2.33 pp |
| Right steering | 14.42% | 18.92% | +4.50 pp |
| Strong turns | 14.12% | 8.17% | -5.95 pp |

Right steering coverage improved compared with Session A, but not enough to classify this as a right-recovery session. Left steering is still higher than right steering, near-zero steering is still very high, and strong-turn coverage is weaker.

## Verdict

Classification: weak mixed/normal training data.

This session is valid and may be useful as additional local simulator data, but it should not replace the planned Session C Right Recovery. It does not provide enough right-steering or strong-correction coverage to solve the Dataset v2 steering-balance goal.

The folder should remain:

```text
data/processed/simulator_v2/session_b_new_training/
```

It should not be renamed to:

```text
data/processed/simulator_v2/session_c_right_recovery/
```

## Next Recommended Session

Collect Session C2: more right recovery.

Target behavior:

- Start slightly left of lane center.
- Steer right to recover back to lane center.
- Include right curves and right-turn exits.
- Avoid long straight segments.
- Aim for right steering greater than left steering.
- Aim for near-zero steering below 45%.
- Increase strong correction examples without chaotic driving.

