# Session E Independent Test Set Report

This report documents the validation of `session_e_independent_test`. The work is simulation-only. No training, checkpoint evaluation, model comparison, simulator control, websocket driving loop, autonomous mode, real vehicle control, or public-road claim was added.

## Purpose

Session E was intended to become a frozen independent test set recorded after the Local V3 baseline, EXP-007 road crop, EXP-008 Huber loss, and EXP-009 `cnn_v2` architecture experiments.

Session E must not be used for:

- training
- validation
- hyperparameter tuning
- crop selection
- loss selection
- architecture selection
- repeated model selection

## Source Path

```text
C:\Users\tarik\OneDrive\Ekler\Desktop\darkdrive-ai-simulation\data\processed\simulator_v2\session_e_independent_test
```

Files:

```text
data/processed/simulator_v2/session_e_independent_test/driving_log.csv
data/processed/simulator_v2/session_e_independent_test/IMG/
```

The CSV is headerless Udacity format:

```text
center,left,right,steering,throttle,brake,speed
```

Image paths in the CSV are absolute Windows paths pointing to the `session_e_independent_test/IMG/` folder.

## Validation Commands

Interpreter:

```text
C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe
```

Commands:

```powershell
& 'C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe' scripts\validate_simulator_dataset.py --csv data\processed\simulator_v2\session_e_independent_test\driving_log.csv --images-dir data\processed\simulator_v2\session_e_independent_test\IMG --format udacity
& 'C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe' scripts\session_dataset_report.py --csv data\processed\simulator_v2\session_e_independent_test\driving_log.csv --images-dir data\processed\simulator_v2\session_e_independent_test\IMG --format udacity --session-name session_e_independent_test
```

The session report generated `screenshots/session_e_independent_test_steering_distribution.png`, which remains ignored by Git.

## File And Validation Results

| Metric | Value |
| --- | ---: |
| CSV rows | 6379 |
| Total image files | 19137 |
| Center image references | 6379 |
| Left image references | 6379 |
| Right image references | 6379 |
| Center files on disk | 6379 |
| Left files on disk | 6379 |
| Right files on disk | 6379 |
| Missing center images | 0 |
| Missing left images | 0 |
| Missing right images | 0 |
| Corrupt / unreadable images | 0 |
| Image shape | 19137 images at 320x160 |
| Duplicate CSV rows | 0 |
| Duplicate image references | 0 |
| Duplicate image filenames on disk | 0 |
| Exact duplicate image files by MD5 | 0 |
| Invalid steering labels | 0 |
| Steering outside `[-1, 1]` | 0 |
| Newest image modification time | 2026-07-09 17:55:43.406 |

Official validator result: PASS.

## Steering Distribution

| Metric | Value |
| --- | ---: |
| Steering min | -1.000000 |
| Steering max | 1.000000 |
| Steering mean | 0.000864 |
| Steering std | 0.315431 |
| Near-zero steering, `abs <= 0.05` | 46.59% |
| Left steering, `< -0.05` | 26.09% |
| Right steering, `> 0.05` | 27.32% |
| Strong turns, `abs >= 0.5` | 9.72% |

Counts:

| Bucket | Count |
| --- | ---: |
| Near-zero | 2972 |
| Left | 1664 |
| Right | 1743 |
| Strong turns | 620 |

## Controls

| Control | Min | Mean | Max |
| --- | ---: | ---: | ---: |
| Throttle | 0.000000 | 0.936395 | 1.000000 |
| Brake | 0.000000 | 0.023379 | 1.000000 |
| Speed | 0.000038 | 28.194715 | 30.509890 |

## Temporal Sanity Checks

Sequence definitions:

- Medium steering run: contiguous same-sign frames with `abs(steering) >= 0.25`.
- Strong steering run: contiguous same-sign frames with `abs(steering) >= 0.5`.
- Sustained run: length of at least 5 adjacent frames.
- Long near-zero run: length of at least 30 frames.
- Stationary row: `speed <= 0.1`.

| Metric | Value |
| --- | ---: |
| Medium steering runs, `abs >= 0.25` | 675 |
| Medium run average length | 2.17 frames |
| Medium run max length | 71 frames |
| Sustained medium runs, length >= 5 | 38 |
| Sustained left medium runs | 22 |
| Sustained right medium runs | 16 |
| Strong steering runs, `abs >= 0.5` | 131 |
| Strong run average length | 4.73 frames |
| Strong run max length | 70 frames |
| Sustained strong runs, length >= 5 | 23 |
| Sustained left strong runs | 12 |
| Sustained right strong runs | 11 |
| Isolated medium spikes, length <= 2 | 560 |
| Long near-zero runs, length >= 30 | 3 |
| Longest near-zero run | 41 frames |
| Stationary rows, speed <= 0.1 | 87 |
| Stationary runs, speed <= 0.1 | 9 |
| Longest stationary run | 40 frames |

Timestamp checks from center-camera filenames:

| Check | Result |
| --- | ---: |
| Timestamp parse failures | 0 |
| Non-positive timestamp deltas | 0 |
| Gaps greater than 0.25s | 4 |
| Gaps greater than 0.50s | 4 |
| Largest timestamp gap | 46.718s |

The timestamp gaps look like simulator recording pauses or interruptions. They do not create missing images, malformed rows, or duplicate frames, but they are worth noting for any later sequence analysis.

## Representative Driving Assessment

Strengths:

- Row count is within the preferred 4000-7000 range.
- No missing or corrupt images were found.
- Left and right steering are both above 20%.
- Left/right balance is acceptable: 26.09% left and 27.32% right.
- Sustained left and right medium/strong steering runs exist.

Limitations:

- Near-zero steering is 46.59%, slightly above the preferred 25%-45% range.
- Strong turns are 9.72%, below the preferred 15% target.
- The session is clean and usable as data, but it is too straight-heavy and not strong-turn representative enough for a final frozen independent test set.

## Verdict

Verdict: **E2) Valid but not ideal**.

The recording is technically valid and useful for analysis, but it should not be frozen as the final independent test set because strong-turn coverage is too low and near-zero steering is slightly high.

## Freeze Decision

Session E is not frozen as the final independent test set.

Do not use this Session E recording for training, validation, hyperparameter tuning, crop selection, loss selection, architecture selection, or repeated model selection.

## Recommendation

Record a Session E2 candidate.

Session E2 should keep the current strengths:

- complete Udacity-style recording
- no missing images
- balanced left/right steering
- smooth representative driving

Session E2 should improve:

- reduce long straight-only/near-zero driving
- raise strong-turn coverage toward at least 15%
- include realistic left and right curves
- include mild recovery from off-center position
- avoid random steering, crashes, wall hits, and one-sided targeting

No model should be trained or evaluated on Session E in this task.
