# Kaggle Udacity Dataset Manual Download

Status update: manual download and EXP-016 validation are complete. This document remains as the reproducible acquisition procedure. See `docs/kaggle-udacity-dataset-validation-report.md` for actual results.

## Dataset

- Dataset ID: `kaggle_udacity_behavioral_cloning_lake_jungle`
- Kaggle dataset: Udacity Self Driving Car - Behavioural Cloning
- Source page: <https://www.kaggle.com/datasets/andy8744/udacity-self-driving-car-behavioural-cloning>

## Why Manual Download Is Required

The 2026-07-10 access check found:

```text
Kaggle CLI found: no
~/.kaggle/kaggle.json found: no
KAGGLE_USERNAME configured: no
KAGGLE_KEY configured: no
```

No token or secret value was read or printed. No download was attempted.

## Local Placement

Download the archive from the Kaggle source page and rename it to:

```text
kaggle_udacity_behavioral_cloning_lake_jungle.zip
```

Place it at this exact ignored path:

```text
C:\Users\tarik\OneDrive\Ekler\Desktop\darkdrive-ai-simulation\data\external\kaggle_udacity_behavioral_cloning_lake_jungle\raw\kaggle_udacity_behavioral_cloning_lake_jungle.zip
```

Do not extract it into a tracked directory. Do not add it with `git add -f`.

## First Command After Placement

From the project root, record the archive checksum without exposing credentials:

```powershell
Get-FileHash -Algorithm SHA256 'data/external/kaggle_udacity_behavioral_cloning_lake_jungle/raw/kaggle_udacity_behavioral_cloning_lake_jungle.zip' | Format-List Algorithm,Hash,Path
```

Then rerun the Kaggle extraction/validation task. The existing single-root Udacity extractor must not be assumed sufficient because this Kaggle archive may contain multiple tracks or schema variants. A candidate-specific run must safely reject zip-slip paths, discover every track root, and validate each track independently.

## Optional Kaggle CLI Command Later

If the Kaggle CLI and credentials are configured in a future task, the documented command is:

```powershell
kaggle datasets download -d andy8744/udacity-self-driving-car-behavioural-cloning -p data/external/kaggle_udacity_behavioral_cloning_lake_jungle/raw
```

Do not print `KAGGLE_KEY`, `kaggle.json`, or API tokens in logs.

## Required Validation

Before any manifest or training decision, validation must check every detected track/root for:

- supported camera columns: `center/left/right` or `centercam/leftcam/rightcam`
- steering column: `steering` or `steering_angle`
- throttle, brake/reverse, and speed availability
- row and image counts
- missing or corrupt images
- duplicate image paths
- invalid steering labels
- steering min/max/mean/standard deviation
- near-zero, left, right, and strong-turn percentages
- license and data-card notes
- whether distribution is meaningfully better than the previous source's 60.74% near-zero and 0.55% strong-turn coverage

Those checks now pass for jungle (K1) and identify `make` as valid but weak (K2). The data still must not be trained or merged until a future jungle-only candidate manifest is reviewed.
