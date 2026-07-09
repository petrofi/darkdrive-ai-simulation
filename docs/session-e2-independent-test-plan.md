# Session E2 Independent Test Plan

Session E2 is intended to replace Session E as the candidate frozen independent test set for DarkDrive AI Simulation.

Session E2 must not be used for:

- training
- validation
- hyperparameter tuning
- crop selection
- loss selection
- architecture selection
- repeated model selection

Only an E1-quality frozen independent test set should be used later to test a selected candidate model or to compare a small fixed set of already-existing models with clear caveats.

## Why Session E Was Not Frozen

Session E was technically valid:

- Rows: 6379.
- Total images: 19137.
- Missing images: 0.
- Corrupt images: 0.
- Left/right steering: 26.09% / 27.32%.

Session E was not frozen because:

- Near-zero steering was 46.59%, slightly above the preferred range.
- Strong-turn coverage was 9.72%, below the preferred 15% target.
- Verdict: E2, valid but not ideal.

The recording was clean and balanced, but too straight-heavy for a final independent test set.

## Target Folder

Record Session E2 in the Udacity simulator using this folder:

```text
C:\Users\tarik\OneDrive\Ekler\Desktop\darkdrive-ai-simulation\data\processed\simulator_v2\session_e2_independent_test
```

Expected structure:

```text
data/processed/simulator_v2/session_e2_independent_test/
|-- IMG/
`-- driving_log.csv
```

Select `session_e2_independent_test` directly in the Udacity simulator recording window. Do not select `simulator_v2`.

## Collection Guidance

Session E2 should be representative, not artificially extreme. It should not be another Session D.

Recommended driving behavior:

- normal lane-following segments
- left curves
- right curves
- medium turns
- some strong turns
- small recovery corrections from slightly off-center positions
- smooth steering
- controlled speed

Avoid:

- long straight-only driving
- only recording hard turns
- random steering
- crashes or wall hits
- unrecoverable frames
- repeatedly targeting only one weakness

## Target Distribution

- Rows: 5000-7000.
- Missing images: 0.
- Corrupt images: 0.
- Near-zero steering: preferably 30%-42%.
- Left steering: preferably above 22%.
- Right steering: preferably above 22%.
- Strong turns: preferably at least 15%.
- Ideal strong-turn range: about 15%-22%.
- Left/right balance: both directions represented without extreme imbalance.

## Current Status

The target folder has been prepared:

```text
data/processed/simulator_v2/session_e2_independent_test/
data/processed/simulator_v2/session_e2_independent_test/IMG/
```

Recording is pending. No `driving_log.csv` exists yet, and `IMG/` currently contains no images.

No validation, training, model evaluation, or checkpoint comparison has been run for Session E2.
