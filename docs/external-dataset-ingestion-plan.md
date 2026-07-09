# External Udacity Dataset Ingestion Plan

The `udacity_behavioral_cloning_public` source is governed as an external, simulation-only research dataset. No external data is added to Local V3 or used to train or evaluate a model in the ingestion workflow.

## Controlled workflow

1. Download the configured archive into the ignored external raw-data folder.
2. Compute and record the archive SHA-256 checksum and provenance metadata.
3. Extract into an ignored folder with zip-slip protection and no implicit overwrite.
4. Detect the actual dataset root containing both `driving_log.csv` and `IMG/`.
5. Inspect the CSV schema, supporting headered or standard headerless Udacity logs.
6. Normalize POSIX, Windows, relative, and stale absolute image paths without changing the raw CSV.
7. Validate all center, left, and right image references and scan referenced images for structural corruption.
8. Calculate steering and available throttle, brake, and speed statistics.
9. Compare the external steering distribution with known internal datasets.
10. Create an ignored ingestion report and, only for X1 or X2 results, an optional ignored normalized manifest.

## Validation gates

- X1: structurally clean, checksummed, valid, and broadly usable for a future controlled experiment.
- X2: structurally usable but requires documented conversion, cleaning, deduplication, or balancing before an experiment.
- X3: invalid or unusable because the structure, images, labels, or archive cannot be verified.

Even an X1 result is not an approval to train. A later task must review any proposed data mix, split design, preprocessing, and experiment criteria before training begins.

## Commands

```powershell
python scripts/download_external_udacity_dataset.py
python scripts/extract_external_udacity_dataset.py
python scripts/validate_external_udacity_dataset.py
```

All generated raw and processed artifacts produced by these commands are Git-ignored.
