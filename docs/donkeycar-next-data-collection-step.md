# DonkeyCar Next Data Collection Step

DonkeyCar is installed in the isolated WSL environment, but DarkDrive should not train, merge, or add control code yet. The next step is to inspect the installed DonkeyCar CLI and identify the correct workflow for this version.

## First Command

Run inside Ubuntu with `donkey-env` active:

```bash
source ~/donkeycar-workspace/donkey-env/bin/activate
donkey --help
```

Read the help output before running project creation or simulator commands. Do not assume old DonkeyCar commands match the installed version.

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
