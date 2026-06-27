# Udacity To DarkDrive Adaptation Plan

This document describes how DarkDrive can adapt the Udacity Behavioral Cloning
concept without copying the old Keras implementation.

DarkDrive remains:

- PyTorch-based
- simulation-only
- education and portfolio focused
- not connected to real vehicles
- not intended for public road testing

## Goal

Adapt the proven educational workflow:

```text
simulator camera image -> steering model -> simulator steering response
```

using DarkDrive's existing PyTorch model, training script, inference script, and
safety boundaries.

## Phase A: Use Udacity Dataset Format For Training

Use the Udacity-style driving log:

```csv
center,left,right,steering,throttle,brake,speed
```

For the current baseline, use only:

```text
center -> steering
```

The `left` and `right` cameras should stay reserved for later recovery training
and augmentation.

Required project command:

```powershell
python scripts/validate_simulator_dataset.py --csv data/processed/simulator/driving_log.csv --images-dir data/processed/simulator/IMG --format udacity
```

## Phase B: Train PyTorch SteeringModel

Train DarkDrive's PyTorch `SteeringModel` on validated simulator data.

Required project command:

```powershell
python src/training/train_behavior_cloning.py --csv data/processed/simulator/driving_log.csv --format udacity --epochs 5 --batch-size 32 --output models/steering_model_v1.pt
```

Output:

```text
models/steering_model_v1.pt
```

This checkpoint is ignored by Git because trained model files can become large
and are experiment artifacts.

## Phase C: Create A PyTorch Equivalent Of `drive.py`

Future file:

```text
src/simulator/udacity_drive_pytorch.py
```

Purpose:

- connect to the simulator in autonomous mode
- receive camera images
- preprocess images using the same shape and normalization as training
- load the PyTorch checkpoint
- predict steering
- send steering and throttle values back to the simulator

This phase should be implemented only after the real simulator dataset is
validated and the PyTorch model trains successfully on simulator data.

## Phase D: Connect Only In Autonomous Mode

The simulator drive loop should connect only to the simulator's autonomous mode.

It must not:

- control a real vehicle
- control an RC car in this phase
- include public road testing instructions
- present simulator control as real-world driving

## Phase E: Record Simulator Evaluation

After the simulator-only drive loop works, record evaluation artifacts:

- simulator frames
- predicted steering values
- optional simulator speed
- optional cross-track or recovery notes
- short demo video

These artifacts should be used to evaluate model behavior and explain results in
the GitHub portfolio.

## Implementation Rules

- Keep the training stack in PyTorch.
- Do not copy old Keras code directly.
- Do not convert DarkDrive to Keras.
- Keep simulator integration isolated under `src/simulator/`.
- Keep generated videos, simulator frames, and trained checkpoints ignored by
  Git unless a small visual demo is intentionally documented.

## Current Status

The simulator drive loop is not implemented yet. A safe placeholder exists so
the planned architecture is visible without sending any simulator commands.
