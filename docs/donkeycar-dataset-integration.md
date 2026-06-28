# DonkeyCar Dataset Integration

DarkDrive can use DonkeyCar simulator data only as an offline research dataset. This workflow does not download data, train a model, add simulator control, or imply autonomous driving capability.

## What DonkeyCar Data Is

DonkeyCar is an open-source self-driving car and simulator ecosystem. Its simulator and car workflows often store driving sessions as "tubs": folders containing camera images plus JSON or catalog records with control labels such as steering angle and throttle.

For DarkDrive, DonkeyCar data is interesting because it can add more recovery-driving and non-zero steering examples than the current local Udacity-style simulator recordings. It is a second source domain, not a drop-in proof that the model will drive well.

## Common Tub Contents

A DonkeyCar tub may contain some combination of:

- image files in the tub root, `images/`, or another image folder.
- JSON record files such as `record_0.json`.
- catalog files such as `catalog_0.catalog`.
- manifest or metadata files describing inputs and record fields.
- control values such as `user/angle`, `user/throttle`, `pilot/angle`, or similar names.

The exact layout differs across DonkeyCar versions, so DarkDrive uses a best-effort converter instead of assuming one schema.

## Format Differences

Udacity-style simulator data uses one CSV:

```text
center,left,right,steering,throttle,brake,speed
```

DonkeyCar tub data is usually record-oriented:

```text
cam/image_array,user/angle,user/throttle
```

DarkDrive's unified research format is:

```text
image_path,steering,throttle,brake,speed,source_dataset
```

The DonkeyCar converter preserves steering values by default. If a source uses a different steering scale, use `--steering-scale` only after documenting the source convention. Brake is set to `0.0` when unavailable. Speed is set to `0.0` when unavailable so the unified CSV remains numeric and easy to validate.

## Risks

- Different camera angle and resolution can change the visual domain.
- Different track visuals can create source-domain mismatch.
- DonkeyCar steering labels may use a different normalization range.
- Public tub datasets may have unclear licensing.
- Mixing sources before source-specific evaluation can hide failures.

## Safe Integration Plan

1. Manually collect or download a DonkeyCar simulator tub only after checking source and license terms.
2. Place the tub under `data/external/donkeycar/`.
3. Convert it to DarkDrive unified CSV with `scripts/convert_donkey_tub_to_darkdrive.py`.
4. Validate the converted CSV with `scripts/validate_donkeycar_conversion.py`.
5. Compare source-specific steering metrics before merging.
6. Keep `source_dataset` in every converted row.
7. Do not train on mixed data until conversion quality and steering distribution pass review.

## Commands

Manual placement example:

```powershell
data/external/donkeycar/sample_tub/
```

Convert:

```powershell
python scripts/convert_donkey_tub_to_darkdrive.py --input data/external/donkeycar/sample_tub --output data/processed/donkeycar/donkeycar_unified.csv --images-output data/processed/donkeycar/IMG --source-name donkeycar_sample
```

Validate:

```powershell
python scripts/validate_donkeycar_conversion.py --csv data/processed/donkeycar/donkeycar_unified.csv --images-dir data/processed/donkeycar/IMG
```

Generated DonkeyCar source data, converted images, and converted CSV outputs are ignored by Git.
