# DonkeyCar WSL Install Success

This document records the successful DonkeyCar installation inside an isolated WSL virtual environment. DarkDrive's Windows `.venv` was not modified.

## Environment

```text
WSL Ubuntu version: Ubuntu 24.04.3 LTS
DonkeyCar environment path: ~/donkeycar-workspace/donkey-env
Python version: Python 3.12.3
pip path: /home/darklove/donkeycar-workspace/donkey-env/lib/python3.12/site-packages/pip
```

## Install Command Used

Run inside the active isolated environment:

```bash
pip install "donkeycar[pc]"
```

Installed DonkeyCar version:

```text
Not recorded in repository documentation yet. Verify with `pip show donkeycar`.
```

## Compatibility Issue

The installation/import flow hit this error:

```text
ModuleNotFoundError: No module named 'pkg_resources'
```

This is a Python packaging compatibility issue. Some packages still import `pkg_resources`, which historically came from `setuptools`.

## Fix Used

The issue was fixed inside `donkey-env` by pinning `setuptools`:

```bash
python -m pip install "setuptools==80.9.0"
```

This fix must stay inside:

```text
~/donkeycar-workspace/donkey-env
```

Do not apply DonkeyCar dependency changes to DarkDrive's Windows `.venv`.

## Final Verification Commands

Run these inside Ubuntu with `donkey-env` active:

```bash
source ~/donkeycar-workspace/donkey-env/bin/activate
python -c "import donkeycar; print(donkeycar.__version__ if hasattr(donkeycar, '__version__') else 'donkeycar import ok')"
donkey --help
pip show donkeycar setuptools
```

## Current Safety Boundary

The install success only proves DonkeyCar can be imported and the CLI can be inspected. It does not mean a dataset has been collected, converted, validated, merged, trained, or connected to simulator control.

Still blocked:

- training.
- dataset merging.
- simulator control.
- websocket/autonomous mode.
- real vehicle control code.
- large dataset downloads.
