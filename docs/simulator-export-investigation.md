# Simulator Export Investigation

This document records whether the installed Udacity simulator can be used to
collect behavior cloning training data for DarkDrive AI Simulation.

## Summary

The installed simulator appears to be the Udacity System Integration / Capstone
simulator, not the Udacity Term 1 Behavior Cloning simulator.

Current finding:

- No evidence was found that this installed simulator can export a behavior
  cloning dataset with `driving_log.csv` and an `IMG/` image folder.
- A manual UI check also showed only `Manual` and `Camera` options, with no
  visible recording, training data, save-folder, or dataset export control.
- The simulator may still be useful for visual/manual simulator testing.
- It should not be treated as the main dataset collection tool for behavior
  cloning.

DarkDrive should stay simulation-only. This investigation does not add real
vehicle control code, public road instructions, or unsafe deployment steps.

## Local Simulator Inspected

Local path:

```text
C:\Users\tarik\Downloads\win_sys_int\win_sys_int
```

Observed files:

```text
win_sys_int/
|-- sys_int.exe
`-- sys_int_Data/
```

The local Unity metadata file contains:

```text
Udacity
self_driving_car_nanodegree_program
```

The `StreamingAssets` folder contains simulator scene assets such as:

```text
parkingLot.ply
Simon2.ply
```

Searches for behavior cloning export indicators did not find a built-in dataset
output structure:

- No existing `driving_log.csv`
- No existing `IMG/` export folder
- No obvious recording/export folder
- No clear local file names indicating behavior cloning data recording

## Manual UI Check

The simulator was also opened manually. The visible interface showed:

- `Manual`
- `Camera`
- live telemetry values such as throttle, steer, brake, acceleration, and speed

The visible interface did **not** show:

- a recording button
- a training mode recorder
- a save folder selector
- an `IMG/` export option
- a `driving_log.csv` export option

This supports the conclusion that the installed `sys_int.exe` simulator is not
the correct tool for collecting Udacity-style behavior cloning datasets.

## Can This Version Export `driving_log.csv` and `IMG/`?

Based on the local file inspection and Udacity simulator naming, this installed
version should be considered **not confirmed for behavior cloning export**.

The likely answer is:

```text
No, this installed System Integration simulator is probably not the correct
Udacity simulator for exporting driving_log.csv and IMG/ behavior cloning data.
```

Confidence level: high.

The installed folder name `win_sys_int`, executable name `sys_int.exe`, local
file inspection, and manual UI check all point to the System Integration /
Capstone build rather than the Term 1 Behavior Cloning simulator.

## How Behavior Cloning Recordings Are Normally Created

In the Udacity Term 1 Behavior Cloning simulator, recordings are normally
created in training mode:

1. Start the Term 1 Behavior Cloning simulator.
2. Choose training/manual driving mode.
3. Select or create a recording folder.
4. Drive manually in the simulator.
5. The simulator saves camera frames under an `IMG/` folder.
6. The simulator writes a `driving_log.csv` file.

The expected behavior cloning format is:

```csv
center,left,right,steering,throttle,brake,speed
```

For the current DarkDrive baseline model, only the `center` camera image is used
for training. The `left` and `right` camera images are future work.

## Why The Installed System Integration Simulator Is Limited

The installed simulator is likely intended for Udacity's later System
Integration / Capstone workflow, not for Term 1 behavior cloning data recording.

Important differences:

- Behavior cloning needs supervised training pairs:
  `camera image -> steering angle`.
- The Term 1 simulator is designed around manual driving and recording
  image/steering datasets.
- The System Integration / Capstone simulator is designed around simulator
  integration and runtime control experiments.
- The local `win_sys_int` build does not show the expected behavior cloning
  recording outputs during file inspection.

If the System Integration simulator does not expose a recording UI, using it for
behavior cloning would require building a separate telemetry/image logging
client. That is not the fastest path for this project right now.

## Recommended Fastest Alternative

### 1. Udacity Term 1 Behavior Cloning Simulator

This is the fastest path if the correct simulator build can be found and run.

Why:

- It is closest to the expected dataset format.
- It can produce `IMG/` and `driving_log.csv` style data.
- It matches the current DarkDrive training script format:
  `center,left,right,steering,throttle,brake,speed`.

Recommended use:

```text
Use this first if it launches correctly on the local machine.
```

### 2. DonkeyCar Simulator

This is the next best practical option.

Why:

- It is built for simulation-based driving experiments.
- It has documentation for simulator workflows.
- It is suitable for portfolio-friendly behavior cloning experiments.

Recommended use:

```text
Use this if the Udacity Term 1 simulator is hard to find, unstable, or too old.
```

### 3. CARLA

CARLA is the strongest long-term simulator option, but it is heavier than needed
for the immediate next step.

Why:

- It is professional and widely used in autonomous driving research.
- It supports camera sensors and rich simulation environments.
- It has a larger setup and integration cost.

Recommended use:

```text
Use CARLA after the baseline dataset/training loop is proven with a simpler
simulator.
```

## Recommended Next Action

1. Stop using the installed `sys_int.exe` as the behavior cloning data
   collection path.
2. Use the Udacity Term 1 Behavior Cloning simulator if available.
3. If that is not practical, move to DonkeyCar Simulator.
4. Put collected simulator data here:

```text
data/processed/simulator/
|-- IMG/
`-- driving_log.csv
```

5. Validate the dataset:

```powershell
python scripts/validate_simulator_dataset.py --csv data/processed/simulator/driving_log.csv --images-dir data/processed/simulator/IMG --format udacity
```

6. Train only after validation passes:

```powershell
python src/training/train_behavior_cloning.py --csv data/processed/simulator/driving_log.csv --format udacity --epochs 5 --batch-size 32 --output models/steering_model_v1.pt
```

## References

- Udacity self-driving car simulator releases:
  https://github.com/udacity/self-driving-car-sim
- Udacity behavior cloning project:
  https://github.com/udacity/CarND-Behavioral-Cloning-P3
- DonkeyCar simulator documentation:
  https://docs.donkeycar.com/guide/deep_learning/simulator/

## Safety Note

This project is simulation-only.

Do not use this project for:

- Real vehicle control
- RC car control in the current phase
- Public road testing
- Unsafe deployment

The current goal is only to collect simulated driving data, train a baseline
steering model, and evaluate predictions inside simulation.
