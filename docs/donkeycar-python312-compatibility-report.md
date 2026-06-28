# DonkeyCar Python 3.12 Compatibility Report

This report documents the DonkeyCar compatibility result for the isolated WSL environment. It does not modify DarkDrive's Windows `.venv` and does not add training, dataset merging, simulator control, websocket/autonomous mode, or real vehicle control code.

## Environment

```text
OS: Ubuntu 24.04.3 LTS
Python: Python 3.12.3
Virtual environment: ~/donkeycar-workspace/donkey-env
pip path: /home/darklove/donkeycar-workspace/donkey-env/bin/pip
DarkDrive WSL path: /mnt/c/Users/tarik/OneDrive/Ekler/Desktop/darkdrive-ai-simulation
```

## Install Result

Install command used inside `donkey-env`:

```bash
pip install "donkeycar[pc]"
```

Installed version:

```text
donkeycar 2.5.8
```

Packaging fix applied inside `donkey-env`:

```bash
python -m pip install "setuptools==80.9.0"
```

This restored `pkg_resources` availability for packages that still import it.

## Import Test

Result:

```text
donkeycar import works
```

This means the Python package can be imported in the isolated environment.

## CLI Test

Command:

```bash
donkey --help
```

Result:

```text
FAIL
```

Exact error:

```text
AttributeError: module 'collections' has no attribute 'MutableMapping'
```

Trace summary:

```text
donkeycar 2.5.8 imports tornado.web
tornado 4.5.3 uses collections.MutableMapping
Python 3.12 no longer supports that old collections API
```

## Root Cause

This is a Python 3.12 compatibility issue caused by old DonkeyCar dependency resolution. DonkeyCar 2.5.8 pulls or allows an old Tornado dependency (`tornado 4.5.3`) that still references `collections.MutableMapping`.

`collections.MutableMapping` was moved to `collections.abc` long ago and is no longer available through the old access path in Python 3.12. The result is a broken DonkeyCar CLI even though `import donkeycar` works.

## Why Random Patching Is Risky

Randomly upgrading Tornado or monkey-patching imports is risky because:

- DonkeyCar 2.5.8 may rely on old Tornado behavior.
- newer Tornado versions may break DonkeyCar internals differently.
- patching installed packages by hand makes the environment hard to reproduce.
- dependency changes could hide the next incompatibility instead of fixing the environment cleanly.
- the goal is dataset acquisition, not maintaining a forked DonkeyCar runtime.

## Recommended Next Path

Recommended:

1. Create a clean DonkeyCar environment with Python 3.11 or Python 3.10.
2. Keep it outside DarkDrive and outside the Windows `.venv`.
3. Reinstall DonkeyCar inside the clean environment.
4. Test `import donkeycar`.
5. Test `donkey --help`.
6. Only if the CLI works, continue toward small simulator tub collection.

Fallback:

If DonkeyCar setup remains costly, pause DonkeyCar and continue with Udacity Session C2 right-recovery data collection. That path is already supported by the DarkDrive Dataset v2 workflow and directly targets the current model bottleneck.

## Current Verdict

```text
Python 3.12 DonkeyCar install: partially successful
Package import: works
Donkey CLI: fails
Usable for CLI/data collection: no
Recommended action: retry in clean Python 3.11/3.10 environment or continue Udacity Session C2
```
