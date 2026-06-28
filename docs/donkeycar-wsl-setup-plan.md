# DonkeyCar WSL Setup Plan

This plan prepares a safe WSL/Ubuntu path for collecting one small DonkeyCar simulator tub without modifying DarkDrive's Windows `.venv`.

## Detected WSL Status

Windows-side checks:

```text
git status: clean and synced with origin/main
wsl --status: WSL is installed, default version is 2
wsl --list --verbose: no installed Linux distributions
```

Ubuntu is not currently installed as a WSL distribution. Because there is no installed distro, WSL-side checks such as `lsb_release -a`, `python3 --version`, `pip3 --version`, and `git --version` cannot be run yet.

## Why DonkeyCar Must Stay Isolated

DarkDrive already has a working Windows research environment. The project `.venv` is used for OpenCV, PyTorch, dataset validation, conversion, and analysis. DonkeyCar may require a different Python version and simulator-related native dependencies.

Installing DonkeyCar into DarkDrive's Windows `.venv` could break the existing dataset and model-quality workflow. DonkeyCar should be installed in an isolated WSL/Ubuntu environment or a separate Windows environment.

## Recommended Setup Approach

Recommended path:

1. Install Ubuntu for WSL manually.
2. Open Ubuntu.
3. Create a separate DonkeyCar workspace under the Linux home directory.
4. Create a separate DonkeyCar virtual environment.
5. Install DonkeyCar according to the current official DonkeyCar documentation.
6. Collect one small simulator tub.
7. Copy the tub into DarkDrive's ignored external data folder.
8. Run DarkDrive's converter and validator from the DarkDrive project.

## Manual WSL Installation Step

Do not run this automatically from Codex. The user should run it manually in an elevated Windows terminal if Ubuntu is desired:

```powershell
wsl --install -d Ubuntu
```

After installation, restart the terminal if Windows asks for it, open Ubuntu, and finish the first-run username/password setup.

## WSL Environment Check Commands

After Ubuntu is installed, run these inside Ubuntu:

```bash
lsb_release -a
python3 --version
pip3 --version
git --version
```

## Documented Install Commands Only

These commands are documentation, not commands executed by Codex in this task:

```bash
sudo apt-get update
sudo apt install python3-pip python3-venv git
sudo apt-get install libmtdev1 libgl1 xclip
```

If package names or DonkeyCar requirements have changed, verify the latest official DonkeyCar installation instructions manually before installing.

## Isolated DonkeyCar Workspace

Create the DonkeyCar workspace outside DarkDrive:

```bash
mkdir -p ~/donkeycar-workspace
cd ~/donkeycar-workspace
python3 -m venv donkey-env
source donkey-env/bin/activate
python -m pip install --upgrade pip
```

Then install DonkeyCar according to the official DonkeyCar documentation for the installed Ubuntu and Python versions.

## Tub Collection Target

Collect a small simulator tub first. Recommended first tub size:

```text
500 to 1500 frames
```

Collection target:

- enough curves to avoid straight-only bias.
- intentional left and right recovery.
- minimal idle or menu frames.
- no real vehicle data.

## Copy Target

Windows target:

```text
C:\Users\tarik\OneDrive\Ekler\Desktop\darkdrive-ai-simulation\data\external\donkeycar\sample_tub\
```

WSL path equivalent:

```text
/mnt/c/Users/tarik/OneDrive/Ekler/Desktop/darkdrive-ai-simulation/data/external/donkeycar/sample_tub/
```

Example copy command from WSL after a tub exists:

```bash
mkdir -p /mnt/c/Users/tarik/OneDrive/Ekler/Desktop/darkdrive-ai-simulation/data/external/donkeycar/sample_tub
cp -r ~/donkeycar-workspace/<your_tub_folder>/* /mnt/c/Users/tarik/OneDrive/Ekler/Desktop/darkdrive-ai-simulation/data/external/donkeycar/sample_tub/
```

Replace `<your_tub_folder>` with the actual tub folder name.

## DarkDrive Conversion Command

Run from the DarkDrive project root after the tub has been copied:

```powershell
python scripts/convert_donkey_tub_to_darkdrive.py --input data/external/donkeycar/sample_tub --output data/processed/donkeycar/donkeycar_unified.csv --images-output data/processed/donkeycar/IMG --source-name donkeycar_sample
```

If `python` is not available on PATH, use:

```powershell
.\.venv\Scripts\python.exe scripts\convert_donkey_tub_to_darkdrive.py --input data\external\donkeycar\sample_tub --output data\processed\donkeycar\donkeycar_unified.csv --images-output data\processed\donkeycar\IMG --source-name donkeycar_sample
```

## DarkDrive Validation Command

Run from the DarkDrive project root:

```powershell
python scripts/validate_donkeycar_conversion.py --csv data/processed/donkeycar/donkeycar_unified.csv --images-dir data/processed/donkeycar/IMG
```

If `python` is not available on PATH, use:

```powershell
.\.venv\Scripts\python.exe scripts\validate_donkeycar_conversion.py --csv data\processed\donkeycar\donkeycar_unified.csv --images-dir data\processed\donkeycar\IMG
```

## Stop Conditions

Stop and reassess before training or merging if:

- Ubuntu installation is incomplete.
- DonkeyCar installation requires changing DarkDrive's `.venv`.
- collected tub has missing images.
- steering values are not numeric.
- near-zero steering dominates the tub.
- public dataset license/source is unclear.

No simulator control, websocket/autonomous mode, real vehicle control, training, or dataset merging belongs in this setup step.
