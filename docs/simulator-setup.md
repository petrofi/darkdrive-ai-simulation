# Simulator Setup

DarkDrive AI Simulation is moving into the simulator data collection phase. The goal is to collect camera images and driving values from a simulator, then train a baseline behavior cloning model.

## Why We Are Using Simulation

Simulation keeps the project safe, repeatable, and portfolio-friendly. It lets us collect driving examples, test failures, and improve the model without using a real vehicle or public roads.

This project does not include real vehicle control code, public road testing instructions, or unsafe deployment steps.

## What Data We Need

For behavior cloning, each training example needs:

- A front camera image.
- A steering value.
- Optional throttle, brake, and speed values for analysis.

The first simulator dataset should use the Udacity-style format:

```text
center,left,right,steering,throttle,brake,speed
```

For now, training uses only the `center` camera image. The `left` and `right` camera images are future work.

## Dataset Format

Expected CSV columns:

```text
center,left,right,steering,throttle,brake,speed
```

Example row:

```text
IMG/center_000001.jpg,IMG/left_000001.jpg,IMG/right_000001.jpg,0.02,0.35,0.0,8.5
```

## Folder Structure

Place simulator data here:

```text
data/processed/simulator/
|-- IMG/
|   `-- camera frame images
`-- driving_log.csv
```

The repository tracks only `.gitkeep` placeholders. Generated simulator images and `driving_log.csv` stay ignored by Git.

## Manual Driving Data Collection Plan

1. Start the simulator in a training or manual driving mode.
2. Drive smoothly around the track.
3. Collect center camera frames and driving values.
4. Save images under `data/processed/simulator/IMG/`.
5. Save the driving log as `data/processed/simulator/driving_log.csv`.
6. Validate the dataset before training.
7. Train the baseline model only after the dataset passes validation.

## Minimum Dataset Target

- First test: 200-500 frames.
- First useful training: 1000-3000 frames.
- Better training: 5000+ frames.

## Safety Note

This phase is simulation-only. Do not connect this project to a real car, RC car, public road workflow, or unsafe deployment pipeline.
