# Dataset V2 Session A Report

Dataset v2 collection has started with a normal-driving simulator recording.

## Dataset Location

```text
data/processed/simulator_v2/session_a_normal/
|-- IMG/
`-- driving_log.csv
```

The source folder was the root-level `veriler/` folder. It was moved into the Dataset v2 structure as Session A.

## Session Type

Session A: normal lane following.

Purpose:

- Capture clean lane-centered simulator driving.
- Provide a local Dataset v2 reference session.
- Keep a normal-driving baseline before recovery-heavy sessions are added.

## Analysis Summary

Command:

```powershell
python scripts/session_dataset_report.py --csv data/processed/simulator_v2/session_a_normal/driving_log.csv --images-dir data/processed/simulator_v2/session_a_normal/IMG --format udacity --session-name session_a_normal
```

Results:

| Metric | Value |
| --- | ---: |
| Total rows | 2400 |
| Total simulator images | 7200 |
| Center images found | 2400 |
| Missing center images | 0 |
| Steering min | -1.000000 |
| Steering max | 1.000000 |
| Steering mean | -0.012757 |
| Steering std | 0.356202 |
| Near-zero steering, abs <= 0.05 | 57.42% |
| Left steering, steering < -0.05 | 28.17% |
| Right steering, steering > 0.05 | 14.42% |
| Strong turns, abs >= 0.5 | 14.12% |

Validation result: PASS.

## Strengths

- The session has a valid Udacity-style `driving_log.csv`.
- Center image resolution works.
- Missing center image count is zero.
- Steering spans the full simulator range from -1.0 to 1.0.
- It provides a useful normal-driving baseline for Dataset v2.

## Weaknesses

- Near-zero steering is 57.42%, which is slightly worse than Dataset v1's 55.42%.
- Right steering is underrepresented compared with left steering.
- This session alone does not solve the recovery/off-center data gap.
- It should not be used as proof of improved model quality.

## Does It Reduce The V1 Near-Zero Problem?

No. Session A is valid, but it does not reduce the near-zero steering problem by itself.

Dataset v1 near-zero steering:

```text
55.42%
```

Dataset v2 Session A near-zero steering:

```text
57.42%
```

Session A is useful as normal-driving coverage, but the next recordings must be recovery-focused and should add more non-zero steering labels.

## Recommended Next Session

Collect a recovery session next, with special attention to right recovery and right turns because Session A is left-heavy:

- Drive slightly right of center.
- Recover smoothly back to lane center.
- Include curve exits and corrections.
- Avoid long straight segments with steering close to 0.0.

This can be recorded as `session_c_right_recovery` or collected immediately after `session_b_left_recovery` if the planned A-B-C-D-E order is kept.

