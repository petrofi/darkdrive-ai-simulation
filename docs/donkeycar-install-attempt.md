# DonkeyCar WSL Install Attempt

This document records the safest DonkeyCar install attempt status for DarkDrive. No DonkeyCar package was installed by Codex in this step because the Ubuntu distro was not visible from the Codex PowerShell WSL session.

## User-Confirmed Environment

The user confirmed the following from the Ubuntu WSL terminal:

```text
Ubuntu: Ubuntu 24.04.3 LTS
Python: Python 3.12.3
DarkDrive WSL path: /mnt/c/Users/tarik/OneDrive/Ekler/Desktop/darkdrive-ai-simulation
DarkDrive path access: confirmed
Isolated workspace: ~/donkeycar-workspace
Isolated virtual environment: ~/donkeycar-workspace/donkey-env
Active environment pip path: /home/darklove/donkeycar-workspace/donkey-env/lib/python3.12/site-packages/pip
```

## Codex Verification Status

The Windows-side repository is clean and synced.

From the Codex PowerShell session, WSL still reports no visible installed distro. Because of that, these commands could not be verified by Codex:

```bash
pip --version
python --version
which python
which pip
```

This also means Codex could not safely activate or use:

```text
~/donkeycar-workspace/donkey-env
```

## Pip Upgrade Status

Expected command already run by the user:

```bash
python -m pip install --upgrade pip setuptools wheel
```

Codex could not confirm the upgraded versions from this session because the Ubuntu distro is not visible here. The user should confirm from the active `donkey-env`:

```bash
source ~/donkeycar-workspace/donkey-env/bin/activate
python --version
pip --version
which python
which pip
```

Expected path shape:

```text
/home/darklove/donkeycar-workspace/donkey-env/bin/python
/home/darklove/donkeycar-workspace/donkey-env/bin/pip
```

## Required System Packages

Do not assume these were already installed. If a command asks for a sudo password, the user should run it manually in Ubuntu:

```bash
sudo apt-get update
sudo apt install python3-pip python3-venv git
sudo apt-get install libmtdev1 libgl1 xclip
```

These commands are OS-level setup commands. They are not DarkDrive `.venv` changes.

## Planned DonkeyCar Install Command

Only run this after `which python` and `which pip` both point into `~/donkeycar-workspace/donkey-env`:

```bash
pip install "donkeycar[pc]"
```

Do not run this globally. Do not run it inside the DarkDrive project folder. Do not use DarkDrive's Windows `.venv`.

## Python 3.12 Compatibility Risk

Ubuntu 24.04 uses Python 3.12.3. DonkeyCar and its simulator-related dependencies may not fully support Python 3.12 in every release. Possible failure modes include:

- unavailable wheels for native dependencies.
- dependency version conflicts.
- build failures for packages that expect older Python versions.
- simulator or GUI dependency problems.

If the install fails, do not force random package downgrades inside `donkey-env`.

## Fallback Plan

If `pip install "donkeycar[pc]"` fails:

1. Save the full error output.
2. Do not downgrade packages blindly.
3. Consider a separate WSL environment with an older DonkeyCar-supported Python version.
4. If DonkeyCar setup becomes too costly, continue with Udacity Session C2 right-recovery data collection.

## Import Test

After a successful install, run:

```bash
python -c "import donkeycar; print(donkeycar.__version__ if hasattr(donkeycar, '__version__') else 'donkeycar import ok')"
```

If this fails, document the error before attempting fixes.

## Current Install Result

```text
DonkeyCar install attempted by Codex: no
Reason: Ubuntu distro is not visible from the Codex WSL session, so the active isolated environment could not be verified.
DonkeyCar installed: not confirmed
Import test run by Codex: no
Training run: no
Dataset merge run: no
Simulator launched: no
Control code added: no
```

## Exact Next Command For User

Run inside the Ubuntu terminal where `donkey-env` exists:

```bash
source ~/donkeycar-workspace/donkey-env/bin/activate
python --version
pip --version
which python
which pip
```

If the paths point into `~/donkeycar-workspace/donkey-env`, the next install attempt is:

```bash
pip install "donkeycar[pc]"
```
