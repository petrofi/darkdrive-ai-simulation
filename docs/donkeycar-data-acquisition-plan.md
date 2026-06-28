# DonkeyCar Data Acquisition Plan

DarkDrive already has a DonkeyCar conversion and validation workflow. The next step is not training and not simulator control. The next step is to obtain one small, license-safe DonkeyCar simulator tub and validate whether it is useful.

## Recommendation

Use **Option A: collect a small DonkeyCar simulator tub manually through WSL/Ubuntu or a separate DonkeyCar environment**, then copy only the finished tub into:

```text
data/external/donkeycar/sample_tub/
```

This is safer than installing DonkeyCar into DarkDrive's existing `.venv` and safer than using a public tub with unclear license terms.

## Current Environment Finding

PowerShell did not find global `python` or `pip` on PATH. The project virtual environment exists:

```text
.venv Python: 3.13.12
.venv pip: 26.1.2
```

Do not install DonkeyCar into this `.venv` without a separate compatibility review. DonkeyCar projects often have their own dependency expectations, and mixing them into DarkDrive risks breaking the current OpenCV/PyTorch research environment.

## Acquisition Options

| Option | Difficulty | Risk to DarkDrive | Expected Value | Time Cost | Dataset Quality | Converter Compatibility | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A) WSL/Ubuntu or separate DonkeyCar environment, manually collect a small simulator tub | Medium | Low if kept separate | High | Medium | High if collected intentionally with turns and recovery | High after tub validation | Recommended |
| B) Small public DonkeyCar tub only if source/license is clear | Low to medium | Low | Medium | Low | Unknown until inspected | Medium to high | Conditional |
| C) Skip DonkeyCar and continue Udacity Session C2 right recovery | Low | Lowest | High for current model bottleneck | Low | High if collected intentionally | Already supported | Best fallback |

## Why Option A Is Safest

- It protects the existing DarkDrive `.venv`.
- It avoids unclear-license public data.
- It gives control over steering distribution, recovery behavior, and track coverage.
- It produces a real DonkeyCar tub that can test the converter honestly.
- It keeps the project simulation-only and dataset-only.

## What The User Must Do Manually

1. Decide whether to set up DonkeyCar in WSL/Ubuntu or a separate Windows environment.
2. Follow current official DonkeyCar simulator setup documentation.
3. Collect a small simulator tub, ideally 500 to 1500 frames.
4. Include purposeful non-zero steering:
   - right recovery
   - left recovery
   - curves
   - minimal straight-only driving
5. Copy the completed tub into:

```text
data/external/donkeycar/sample_tub/
```

6. Do not commit the tub. It is ignored by Git.

## What Codex Can Automate Later

After the tub is manually placed, Codex can:

- inspect the tub structure.
- run the converter.
- run the validator.
- report steering distribution.
- compare the DonkeyCar tub against Dataset v2 Session A and `session_b_new_training`.
- recommend whether to collect more data, convert more tubs, or stay with Udacity Session C2.

Codex should not automatically install DonkeyCar, download public datasets, train, merge, or add control code without explicit approval.

## Windows vs WSL Notes

### WSL/Ubuntu Recommended Path

Use WSL/Ubuntu or another isolated environment for DonkeyCar. Keep it outside the DarkDrive `.venv`.

Documented setup outline only:

```bash
# Run inside WSL/Ubuntu, not inside DarkDrive's .venv.
python3 --version
python3 -m venv donkeycar-env
source donkeycar-env/bin/activate
python -m pip install --upgrade pip
# Then follow the current official DonkeyCar installation and simulator guide.
```

### Windows Fallback

Use a separate Windows virtual environment, not DarkDrive's `.venv`.

Documented setup outline only:

```powershell
# Run outside the DarkDrive project virtual environment.
py -m venv donkeycar-env
.\donkeycar-env\Scripts\activate
python -m pip install --upgrade pip
# Then follow the current official DonkeyCar installation and simulator guide.
```

The fallback is acceptable only if DonkeyCar dependencies support the installed Windows Python version. If there is dependency friction, stop and use WSL/Ubuntu.

## DarkDrive Conversion Command

After the tub exists at `data/external/donkeycar/sample_tub/`, convert it:

```powershell
python scripts/convert_donkey_tub_to_darkdrive.py --input data/external/donkeycar/sample_tub --output data/processed/donkeycar/donkeycar_unified.csv --images-output data/processed/donkeycar/IMG --source-name donkeycar_sample
```

If `python` is not available on PATH, use the project venv for conversion only:

```powershell
.\.venv\Scripts\python.exe scripts\convert_donkey_tub_to_darkdrive.py --input data\external\donkeycar\sample_tub --output data\processed\donkeycar\donkeycar_unified.csv --images-output data\processed\donkeycar\IMG --source-name donkeycar_sample
```

## DarkDrive Validation Command

Validate the converted dataset:

```powershell
python scripts/validate_donkeycar_conversion.py --csv data/processed/donkeycar/donkeycar_unified.csv --images-dir data/processed/donkeycar/IMG
```

If `python` is not available on PATH:

```powershell
.\.venv\Scripts\python.exe scripts\validate_donkeycar_conversion.py --csv data\processed\donkeycar\donkeycar_unified.csv --images-dir data\processed\donkeycar\IMG
```

## Acceptance Gate

Do not merge or train until:

- converted row count is non-zero.
- missing image count is zero.
- steering is numeric.
- `source_dataset` is present.
- near-zero, left, right, and strong-turn percentages are reviewed.
- source/license is documented if the tub came from a public dataset.
