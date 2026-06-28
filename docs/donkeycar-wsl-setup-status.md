# DonkeyCar WSL Setup Status

This status report records the current DonkeyCar WSL environment check for DarkDrive. No DonkeyCar installation, dataset download, training, merge, simulator control, websocket/autonomous mode, or real vehicle control code was added.

## User-Provided Ubuntu Terminal Status

The user reported this status from an Ubuntu WSL terminal:

```text
Ubuntu: Ubuntu 24.04.3 LTS, codename noble
Python: Python 3.12.3
pip: pip 24.0 from /usr/lib/python3/dist-packages/pip
git: git version 2.43.0
```

## Codex-Observed Windows/WSL Status

From the Codex PowerShell environment:

```text
DarkDrive Windows path exists: yes
DarkDrive Windows path: C:\Users\tarik\OneDrive\Ekler\Desktop\darkdrive-ai-simulation
WSL status: installed
WSL default version: 2
WSL distro list: no installed Linux distributions visible to this Codex session
```

The following WSL commands failed from this Codex session because no distro was visible:

```text
wsl lsb_release -a
wsl python3 --version
wsl pip3 --version
wsl git --version
wsl ls /mnt/c/Users/tarik/OneDrive/Ekler/Desktop/darkdrive-ai-simulation
wsl git -C /mnt/c/Users/tarik/OneDrive/Ekler/Desktop/darkdrive-ai-simulation status --short --branch
```

Common distro names were also not visible from this session:

```text
wsl -d Ubuntu lsb_release -a
wsl -d Ubuntu-24.04 lsb_release -a
wsl -d Ubuntu-22.04 lsb_release -a
```

## DarkDrive Path Accessibility

Windows-side path check passed:

```text
C:\Users\tarik\OneDrive\Ekler\Desktop\darkdrive-ai-simulation
```

WSL-side path check could not be completed from Codex because the Ubuntu distro was not visible to this session. The expected WSL path remains:

```text
/mnt/c/Users/tarik/OneDrive/Ekler/Desktop/darkdrive-ai-simulation
```

The user should verify this from the Ubuntu terminal:

```bash
ls /mnt/c/Users/tarik/OneDrive/Ekler/Desktop/darkdrive-ai-simulation
git -C /mnt/c/Users/tarik/OneDrive/Ekler/Desktop/darkdrive-ai-simulation status --short --branch
```

## Isolated DonkeyCar Workspace

`donkey-env` was not created by Codex because the Ubuntu distro was not accessible from this Codex WSL session.

Run these manually inside the Ubuntu terminal that reports Ubuntu 24.04.3:

```bash
mkdir -p ~/donkeycar-workspace
cd ~/donkeycar-workspace
python3 -m venv donkey-env
source ~/donkeycar-workspace/donkey-env/bin/activate
python --version
pip --version
```

If venv creation fails because `python3-venv` is missing, stop and run:

```bash
sudo apt install python3-venv
```

## Pip Upgrade Status

Pip was not upgraded by Codex because `donkey-env` was not created in this session.

After activating `donkey-env`, run this inside the isolated environment only:

```bash
python -m pip install --upgrade pip setuptools wheel
```

## DonkeyCar Installation Status

DonkeyCar was not installed. That is intentional.

The likely next OS package commands should remain manual and should be run only inside Ubuntu after confirming the current official DonkeyCar documentation:

```bash
sudo apt-get update
sudo apt install python3-pip python3-venv git
sudo apt-get install libmtdev1 libgl1 xclip
```

DonkeyCar installation should happen only while this environment is active:

```text
~/donkeycar-workspace/donkey-env
```

## Next Required Step

Open the same Ubuntu terminal that reports Ubuntu 24.04.3 and run:

```bash
ls /mnt/c/Users/tarik/OneDrive/Ekler/Desktop/darkdrive-ai-simulation
mkdir -p ~/donkeycar-workspace
cd ~/donkeycar-workspace
python3 -m venv donkey-env
source ~/donkeycar-workspace/donkey-env/bin/activate
python --version
pip --version
```

Then report the output before installing DonkeyCar.
