# Better External Data Scout Report

## Goal

Identify the most promising next steering-labeled data source without downloading everything, fabricating metrics, merging data, training a model, or evaluating a checkpoint.

## Why The Previous External Dataset Was Weak

The first public Udacity source was structurally valid: 8,036 rows, 24,108 images, no missing/corrupt references, and valid labels. Its distribution was poor for the identified model weaknesses:

- 60.74% near-zero steering
- 19.06% left
- 20.20% right
- 0.55% strong turns

External Mix V1 capped this source at 3,000 rows and preserved all Local V3 rows, but EXP-014 received EM2: valid experiment, no meaningful improvement. Strong-turn MAE and prediction variance improved, while overall MAE, RMSE, right MAE, zero-baseline comparison, and direction error regressed.

More rows are therefore not the selection objective. Better data means trustworthy image/steering pairs with useful curve, recovery, left/right, and strong-turn coverage, plus clear provenance, access, and license notes.

## Sources Reviewed

| Candidate | Priority | Decision |
| --- | ---: | --- |
| Kaggle Udacity lake/jungle candidate | 4 | Best next practical source, pending manual access, license review, and per-track validation |
| Kaggle DonkeyCar tubs | 3 | Promising controls, but access, schema, scale, license, and domain remain unknown |
| `autorope/donkey_datasets` | 3 | Known DonkeyCar 4.x tub source; use one reviewed tub only after conversion and license clarification |
| CARLA controlled generation | 3 | Best future controlled-data route, but requires a separate heavy setup task |
| comma2k19 | 2 | Research/domain-adaptation source; too large and mismatched for immediate simulator training |

No candidate received priority 5 because none was both immediately accessible and already proven to have suitable steering distribution and clear usage terms.

## Kaggle Access Result

Access check on 2026-07-10:

- Kaggle CLI: not installed or on `PATH`
- `~/.kaggle/kaggle.json`: absent
- `KAGGLE_USERNAME`: not set
- `KAGGLE_KEY`: not set

Only presence booleans were checked. No secret content was read or printed.

## Download, Extraction, And Validation Result

Not performed. Without Kaggle CLI credentials or a manually placed archive, there was no source file to checksum, extract, inspect, or validate. No Kaggle row counts, image counts, label distributions, licenses, or K1/K2/K3 verdicts are claimed.

The exact manual placement and checksum step are documented in `docs/kaggle-udacity-dataset-manual-download.md`.

## DonkeyCar, comma2k19, And CARLA

- DonkeyCar: relevant image/steering/throttle concepts, but tub conversion, steering-scale validation, per-tub distribution checks, and license clarification are mandatory.
- comma2k19: official documentation describes about 100 GB of real highway video and sensor/CAN logs. It is valuable for later domain adaptation, not direct DarkDrive training.
- CARLA: can generate controlled synchronized labels and recovery scenarios later, but installation and exporter design belong in a separate task.

Details are in `docs/external-dataset-source-notes.md`.

## Data Decision

Use `kaggle_udacity_behavioral_cloning_lake_jungle` as the next access candidate, not as approved training data. It has the highest expected domain match, but remains priority 4 until its license, track structure, image integrity, label schema, and steering distributions are verified.

## Exact Next Action

The human should manually download the Kaggle archive, place it at the documented ignored path, record its SHA-256, and rerun extraction/validation. Do not build a mix or train from it yet.

No model was trained in this task.

No checkpoint evaluation was run.

No dataset was merged into training.
