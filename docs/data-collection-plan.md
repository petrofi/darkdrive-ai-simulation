# Data Collection Plan

DarkDrive AI Simulation has a working first pipeline. The next phase is collecting real simulated driving data for behavior cloning.

## Current Gap

The project already has:

- OpenCV lane detection demo.
- Baseline PyTorch behavior cloning training.
- Single-image steering inference.
- Simple and Udacity-style dataset format support.
- Dataset validation tooling.

The project is missing a real simulated driving dataset:

```text
data/processed/simulator/
|-- IMG/
`-- driving_log.csv
```

The current sample image and sample CSV are only for pipeline testing. They are not enough for real model learning.

## Lane Images vs Steering-Labeled Data

Lane detection and behavior cloning need different data.

Lane detection can use standalone road or lane images. Good public references for computer vision experiments include:

- TuSimple benchmark: https://github.com/TuSimple/tusimple-benchmark
- BDD100K dataset information: https://arxiv.org/abs/1805.04687

Behavior cloning needs image and control-label pairs. Each training row should connect a camera image with values like:

```text
steering, throttle, brake, speed
```

Without steering labels, road images are not enough to train the steering model.

## Recommended Data Source Order

1. Use a Udacity Term 1 behavior cloning simulator if available.
2. Test the local `win_sys_int` simulator only if it can export `IMG` frames and `driving_log.csv`.
3. If `win_sys_int` cannot export behavior cloning data, move to DonkeyCar Simulator.
4. Use CARLA later for a more professional camera sensor workflow.

The inspected local simulator path is:

```text
C:\Users\tarik\Downloads\win_sys_int\win_sys_int
```

It contains `sys_int.exe`, which likely means it is the Udacity System Integration simulator. That simulator may be useful for visual/manual testing, but it should not be assumed to support behavior cloning data recording.

## Training Dataset Target

Use these rough targets:

- First test: 200-500 frames.
- First useful training: 1000-3000 frames.
- Better training: 5000+ frames.

The dataset should include straight sections, curves, and recovery examples. Avoid training only on perfect center-lane driving.

## Training Workflow

Prepare the output folder:

```powershell
python scripts/prepare_simulator_output.py
```

Validate simulator data:

```powershell
python scripts/validate_simulator_dataset.py --csv data/processed/simulator/driving_log.csv --images-dir data/processed/simulator/IMG --format udacity
```

Train the baseline model:

```powershell
python src/training/train_behavior_cloning.py --csv data/processed/simulator/driving_log.csv --images-dir data/processed/simulator/IMG --format udacity --epochs 5 --batch-size 32 --output models/steering_model_v1.pt
```

Run prediction on one simulator frame:

```powershell
python src/inference/predict_steering.py --model models/steering_model_v1.pt --image data/processed/simulator/IMG/example.jpg
```

## Safety Boundary

This project remains simulation-only. Do not add real vehicle control code, RC car integration, public road testing, or deployment automation.
