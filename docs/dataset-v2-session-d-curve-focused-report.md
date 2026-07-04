# Dataset V2 Session D Curve-Focused Report

This report documents validation and analysis of the Session D curve-focused Udacity simulator recording.

## Scope

Session D is simulation-only data. It was collected to address the current model failure mode: steering magnitude under-prediction on curves and strong turns. No model was trained, no dataset was merged, and no simulator control code was added during this validation step.

## Dataset Location

```text
data/processed/simulator_v2/session_d_curve_focused/
|-- IMG/
`-- driving_log.csv
```

Generated simulator images and `driving_log.csv` remain ignored by Git.

## Collection Purpose

The goal was to add curve-heavy examples with sustained medium and strong steering, smoother curve entry/apex/exit behavior, and less near-zero steering than previous sessions.

Target heuristics:

- Missing images: 0.
- Corrupt images: 0.
- Near-zero steering below 35%.
- Left steering at least 25%.
- Right steering at least 25%.
- Strong turns above 22%.
- Sustained curve sequences rather than isolated steering spikes.

These are research heuristics, not claims of autonomous driving readiness.

## File Validation

| Check | Result |
| --- | ---: |
| CSV rows | 7721 |
| Total image files | 23163 |
| Center images found | 7721 |
| Left images found | 7721 |
| Right images found | 7721 |
| Missing center images | 0 |
| Missing left images | 0 |
| Missing right images | 0 |
| Corrupt images | 0 |
| Image shape | 23163 images at 160x320x3 |
| Duplicate CSV rows | 0 |
| Duplicate image filenames | 0 |
| Duplicate center image references | 0 |
| Duplicate left image references | 0 |
| Duplicate right image references | 0 |
| Invalid / NaN steering labels | 0 |
| Steering outside [-1, 1] | 0 |
| Newest file modification time | 2026-07-04 23:28:04 |

The CSV is headerless Udacity format:

```text
center,left,right,steering,throttle,brake,speed
```

Image paths are absolute Windows paths.

## Commands Used

```powershell
python scripts/validate_simulator_dataset.py --csv data/processed/simulator_v2/session_d_curve_focused/driving_log.csv --images-dir data/processed/simulator_v2/session_d_curve_focused/IMG --format udacity
python scripts/session_dataset_report.py --csv data/processed/simulator_v2/session_d_curve_focused/driving_log.csv --images-dir data/processed/simulator_v2/session_d_curve_focused/IMG --format udacity --session-name session_d_curve_focused
```

The session report generated an ignored plot:

```text
screenshots/session_d_curve_focused_steering_distribution.png
```

## Steering Distribution

Thresholds:

- Near-zero steering: `abs(steering) <= 0.05`
- Left steering: `steering < -0.05`
- Right steering: `steering > 0.05`
- Strong turn: `abs(steering) >= 0.5`

| Metric | Value |
| --- | ---: |
| Steering min | -1.000000 |
| Steering max | 1.000000 |
| Steering mean | -0.035870 |
| Steering std | 0.441348 |
| Near-zero steering | 22.00% |
| Left steering | 47.07% |
| Right steering | 30.93% |
| Strong turns | 24.83% |

Control values:

| Control | Min | Mean | Max |
| --- | ---: | ---: | ---: |
| Throttle | 0.000000 | 0.984849 | 1.000000 |
| Brake | 0.000000 | 0.005857 | 1.000000 |
| Speed | 0.000078 | 29.596229 | 30.525380 |

## Temporal Curve Analysis

Sequence definitions used for this analysis:

- Medium steering sequence: contiguous same-sign frames with `abs(steering) >= 0.25`.
- Strong steering sequence: contiguous same-sign frames with `abs(steering) >= 0.5`.
- Sustained sequence: run length of at least 5 adjacent frames.
- Isolated medium spike: medium steering run length of 1 or 2 frames.
- Long near-zero run: near-zero run length of at least 30 frames.
- Stationary row: `speed <= 0.1`.

| Temporal metric | Count | Average length | Max length |
| --- | ---: | ---: | ---: |
| Medium steering runs, `abs >= 0.25` | 1354 | 2.61 frames | 27 frames |
| Sustained medium steering runs, length >= 5 | 210 | 5.93 frames | 27 frames |
| Sustained left medium curve runs | 129 | 5.82 frames | 25 frames |
| Sustained right medium curve runs | 81 | 6.11 frames | 27 frames |
| Strong steering runs, `abs >= 0.5` | 690 | 2.78 frames | 26 frames |
| Sustained strong steering runs, length >= 5 | 80 | 6.23 frames | 26 frames |
| Isolated medium steering spikes, length <= 2 | 778 | 1.31 frames | 2 frames |
| Long near-zero runs, length >= 30 | 1 | 30.00 frames | 30 frames |
| Stationary runs, speed <= 0.1 | 2 | 10.00 frames | 14 frames |

Timestamp checks from center-camera filenames:

| Check | Result |
| --- | ---: |
| Timestamp parse failures | 0 |
| Non-positive timestamp deltas | 0 |
| Gaps greater than 0.25s | 0 |
| Gaps greater than 0.50s | 0 |
| Largest timestamp gap | 0.115s |

Interpretation:

- Session D contains real sustained curve behavior, not only aggregate steering imbalance.
- Left and right sustained curve sequences both exist.
- Left curves are overrepresented compared with right curves.
- Near-zero cruising does not dominate.
- Stationary frames are minimal.
- No suspicious recording gaps were detected.
- No crash or wall-contact sequence is obvious from labels, speed, timestamps, or duplicate-frame checks, but visual review would still be needed before closed-loop release decisions.

## Comparison Against Previous Sessions

| Dataset/session | Rows | Near-zero | Left | Right | Strong turns | Steering std |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Dataset v1 | 3706 | 55.42% | 22.26% | 22.32% | 14.87% | 0.350406 |
| Session A normal | 2400 | 57.42% | 28.17% | 14.42% | 14.12% | 0.356202 |
| Session B new training | 1126 | 55.24% | 25.84% | 18.92% | 8.17% | 0.244779 |
| Session C2 right recovery | 4163 | 41.32% | 30.22% | 28.47% | 14.89% | 0.347744 |
| Merged local Dataset v2 | 8647 | 34.99% | 35.27% | 29.73% | 18.53% | 0.392077 |
| Session D curve focused | 7721 | 22.00% | 47.07% | 30.93% | 24.83% | 0.441348 |

Session D improves the main curve-related targets:

- Strong-turn coverage improves beyond every prior local session and the merged local Dataset v2.
- Near-zero steering drops far below v1, A, B, C2, and merged local Dataset v2.
- Steering standard deviation is higher than every prior local dataset/session listed above.
- Right steering clears the 25% target.
- Sustained medium and strong steering sequences exist.

Main limitation:

- The session is left-heavy: left steering is 47.07% versus right steering at 30.93%. This is useful for curve learning but should be balanced carefully during Local V3 construction.

## Quality Verdict

Verdict: **A) Strong curve-focused session**.

Reasons:

- Missing images: 0.
- Corrupt images: 0.
- Strong-turn coverage is clearly improved at 24.83%.
- Near-zero steering is low at 22.00%.
- Both left and right sustained curve sequences are present.
- Timestamp and duplicate checks do not show recording quality problems.
- The session is suitable for Local V3 training, with a note to manage its left-heavy distribution.

## Training Inclusion Decision

Session D should be included in the next Local V3 training dataset. It should not simply be appended unbalanced. The Local V3 builder should preserve `source_session`, include Session C2, include Session D, downsample near-zero-heavy v1/A/B rows, and use a session-aware validation strategy.

## Recommended Next Experiment

Prepare Local V3 training data using:

- Dataset v1 for baseline normal driving coverage.
- Session A/B only if downsampled and clearly labeled.
- Session C2 for right-recovery/right-turn coverage.
- Session D for sustained curve and strong-turn coverage.

Do not train until the Local V3 dataset build plan is reviewed.
