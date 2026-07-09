# Session E Independent Test Plan

Session E is a frozen independent test set for DarkDrive AI Simulation.

It is recorded after the Local V3 baseline, EXP-007 road crop, EXP-008 Huber loss, and EXP-009 `cnn_v2` architecture experiments. Its purpose is to protect future evaluation from repeated Session C2 model-selection pressure.

## Target Folder

Record Session E in the Udacity simulator using this folder:

```text
C:\Users\tarik\OneDrive\Ekler\Desktop\darkdrive-ai-simulation\data\processed\simulator_v2\session_e_independent_test
```

Expected structure:

```text
data/processed/simulator_v2/session_e_independent_test/
|-- IMG/
`-- driving_log.csv
```

Select `session_e_independent_test` directly in the Udacity simulator recording window. Do not select `simulator_v2`.

## Frozen Test Set Rule

Session E must not be used for:

- training
- validation
- hyperparameter tuning
- crop selection
- loss selection
- architecture selection
- repeated model selection

Session E should be used later only to test a selected candidate model or to compare a small fixed set of already-existing models with clear caveats.

## Collection Guidance

Recommended driving behavior:

- representative normal driving
- left curves
- right curves
- medium turns
- some strong turns
- recovery from slight off-center position
- smooth driving
- controlled speed

Avoid:

- excessive long straight-only driving
- intentional random steering
- crashes, wall hits, or unrecoverable frames
- repeatedly targeting only one weakness, such as only left curves or only right curves

## Recommended Targets

- Rows: 4000-7000.
- Missing images: 0.
- Corrupt images: 0.
- Near-zero steering: preferably 25%-45%.
- Left steering: preferably above 20%.
- Right steering: preferably above 20%.
- Strong turns: preferably at least 15%.
- Direction balance: not extremely left-heavy or right-heavy.
- Driving character: realistic mixed driving session.

Session E does not need to maximize strong-turn percentage like Session D. It should be more representative and independent.

## Current Status

The target folder has been prepared:

```text
data/processed/simulator_v2/session_e_independent_test/
data/processed/simulator_v2/session_e_independent_test/IMG/
```

Recording is pending. No `driving_log.csv` exists yet, and `IMG/` currently contains no images.

No validation, training, or model evaluation has been run for Session E.
