# DonkeyCar Next Data Collection Step

DonkeyCar 2.5.8 is installed in the isolated WSL Python 3.12 environment, but the CLI currently fails. DarkDrive should not train, merge, collect DonkeyCar data, or add control code until the CLI issue is resolved or a fallback path is selected.

## Current Blocker

`donkey --help` fails on Python 3.12 with:

```text
AttributeError: module 'collections' has no attribute 'MutableMapping'
```

Root cause: old `tornado 4.5.3` dependency is incompatible with Python 3.12.

## First Command

Run inside Ubuntu only after creating a clean compatible DonkeyCar environment:

```bash
donkey --help
```

Read the help output before running project creation or simulator commands. Do not assume old DonkeyCar commands match the installed version.

## Next-Step Options

### Option A: Clean Python 3.11/3.10 DonkeyCar Environment

Create a fresh DonkeyCar environment with Python 3.11 or Python 3.10, isolated from DarkDrive and isolated from the current broken Python 3.12 `donkey-env`.

Goal:

- reinstall DonkeyCar cleanly.
- verify `import donkeycar`.
- verify `donkey --help`.
- only then identify the project/tub workflow.

This is the recommended path if DonkeyCar remains important for Dataset v2 research.

### Option B: Pause DonkeyCar And Continue Udacity Session C2

Pause DonkeyCar setup and return to the already working Udacity simulator workflow.

Goal:

- collect Session C2 right-recovery data.
- reduce near-zero steering bias.
- increase right steering and strong-turn coverage.

This is the fastest path toward improving the current DarkDrive model bottleneck.

## Identify The Installed Workflow

Use `donkey --help` to determine how this installed version handles:

- creating a car/project folder.
- configuring simulator mode.
- recording a tub.
- locating the generated tub folder.
- choosing camera/image output settings.

Do not start training from DonkeyCar. The target output is only a small DonkeyCar tub dataset.

## Target Dataset

Collect one small simulator-only tub first:

```text
500 to 1500 frames
```

Target behavior:

- curves.
- left recovery.
- right recovery.
- minimal straight-only driving.
- no menu/idle frames if possible.

## Final Tub Target For DarkDrive

After recording, copy the finished tub into:

```text
/mnt/c/Users/tarik/OneDrive/Ekler/Desktop/darkdrive-ai-simulation/data/external/donkeycar/sample_tub/
```

Windows equivalent:

```text
C:\Users\tarik\OneDrive\Ekler\Desktop\darkdrive-ai-simulation\data\external\donkeycar\sample_tub\
```

The source tub folder is ignored by Git.

## DarkDrive Conversion Reminder

After the tub is copied, run from the DarkDrive project root:

```powershell
python scripts/convert_donkey_tub_to_darkdrive.py --input data/external/donkeycar/sample_tub --output data/processed/donkeycar/donkeycar_unified.csv --images-output data/processed/donkeycar/IMG --source-name donkeycar_sample
```

If Windows `python` is not on PATH:

```powershell
.\.venv\Scripts\python.exe scripts\convert_donkey_tub_to_darkdrive.py --input data\external\donkeycar\sample_tub --output data\processed\donkeycar\donkeycar_unified.csv --images-output data\processed\donkeycar\IMG --source-name donkeycar_sample
```

## DarkDrive Validation Reminder

```powershell
python scripts/validate_donkeycar_conversion.py --csv data/processed/donkeycar/donkeycar_unified.csv --images-dir data/processed/donkeycar/IMG
```

If Windows `python` is not on PATH:

```powershell
.\.venv\Scripts\python.exe scripts\validate_donkeycar_conversion.py --csv data\processed\donkeycar\donkeycar_unified.csv --images-dir data\processed\donkeycar\IMG
```

## Stop Conditions

Stop before training or merging if:

- `donkey --help` does not show a clear project/tub workflow.
- the simulator workflow requires extra large downloads.
- the tub folder structure is unclear.
- the converted dataset has missing images.
- steering labels are not numeric.
- near-zero steering dominates the tub.
