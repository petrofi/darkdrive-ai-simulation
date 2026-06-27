# Udacity Behavioral Cloning Reference

This document summarizes the official Udacity Behavioral Cloning project as a
reference for DarkDrive AI Simulation.

Reference repository:

```text
https://github.com/udacity/CarND-Behavioral-Cloning-P3
```

DarkDrive uses this project only as an educational reference. DarkDrive remains
a PyTorch-based, simulation-only project.

## What The Udacity Project Does

The Udacity Behavioral Cloning project trains a neural network to imitate human
driving behavior in a simulator.

The core idea is:

```text
camera image -> steering angle
```

A human first drives the car manually in the simulator. During that manual
drive, the simulator records camera frames and control values. The model is then
trained to predict the steering angle from the camera image.

After training, the trained model can be connected back to the simulator in
autonomous mode. The simulator sends a camera image, the model predicts a
steering value, and the drive script sends the steering command back to the
simulator.

## Dataset Format

The Udacity-style driving log uses this format:

```csv
center,left,right,steering,throttle,brake,speed
```

Column meaning:

- `center`: front center camera image path
- `left`: front left camera image path
- `right`: front right camera image path
- `steering`: steering angle label
- `throttle`: throttle value
- `brake`: brake value
- `speed`: simulator speed value

DarkDrive currently trains only on the `center` camera image. The `left` and
`right` camera images are useful future work for recovery training and data
augmentation.

## Training Goal

The training goal is supervised regression:

```text
input: simulator camera image
output: one continuous steering angle
```

This is behavior cloning because the model learns from examples of manual
driving behavior instead of learning from hand-written lane-following rules.

## Simulator Loop

The Udacity simulator integration is commonly structured like this:

1. The simulator runs in autonomous mode.
2. The simulator sends the current camera image to `drive.py`.
3. `drive.py` preprocesses the image.
4. The trained model predicts a steering angle.
5. `drive.py` sends steering and throttle values back to the simulator through
   a Socket.IO/websocket-style connection.
6. The simulator applies those values inside the simulator environment.

This loop is simulator-only. It is not real vehicle control.

## Why This Is Relevant To DarkDrive

DarkDrive is building the same educational concept with a modern PyTorch code
path:

```text
simulated camera image -> PyTorch SteeringModel -> predicted steering angle
```

The Udacity project is useful because it shows the complete learning loop:

- collect simulator driving data
- train an image-to-steering model
- run inference in a simulator loop
- evaluate whether the model can stay on track in simulation

DarkDrive should borrow the architecture and dataset concept, not the old Keras
implementation.

## Udacity vs DarkDrive

| Area | Udacity Behavioral Cloning | DarkDrive AI Simulation |
| --- | --- | --- |
| Main framework | Keras | PyTorch |
| Model artifact | `model.h5` | `.pt` checkpoint |
| Training entry point | project-specific Keras training code | `src/training/train_behavior_cloning.py` |
| Single-image inference | usually part of simulator loop | `src/inference/predict_steering.py` |
| Simulator loop | `drive.py` | not implemented yet |
| Simulator communication | Socket.IO/websocket-style simulator connection | future PyTorch simulator integration |
| Dataset format | `center,left,right,steering,throttle,brake,speed` | supports Udacity-style format |
| Driving mode | autonomous mode inside simulator | future simulation-only autonomous mode |
| Real vehicle control | not part of this DarkDrive phase | not allowed |

## What DarkDrive Should Borrow

- The dataset format.
- The idea of mapping camera images to steering angles.
- The simulator-only autonomous evaluation loop.
- The separation between training and simulator inference.

## What DarkDrive Should Not Copy

- Old Keras model code.
- `model.h5`-based checkpoint handling.
- Project-wide Keras structure.
- Any code that implies real vehicle deployment.

## Safety Boundary

DarkDrive must not claim that the model already drives in simulation until the
future simulator loop is implemented and tested. The current project has a
working PyTorch training/inference pipeline, but simulator driving is still
future work.
