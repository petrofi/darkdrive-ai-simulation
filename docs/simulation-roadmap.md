# Simulation Roadmap

## Phase 1: First Working Pipeline

Completed.

- OpenCV lane detection works.
- Baseline PyTorch steering prediction training works.
- Single-image steering prediction works.
- Dataset validation tooling exists.

## Phase 2: Simulator Dataset Collection

Completed for the first local dataset.

The Udacity simulator successfully recorded a real simulator dataset:

```text
data/processed/simulator/
|-- IMG/
`-- driving_log.csv
```

Current validation result:

- Rows: 3706
- Center images found: 3706
- Left images found: 3706
- Right images found: 3706
- Missing center images: 0
- Steering range: -1.000000 to 1.000000
- Dataset validation: PASS

## Phase 3: Train Model on Real Simulated Driving Data

In progress.

The baseline PyTorch model has completed a first training run on the validated Udacity-style simulator dataset.

Do not train the steering model on image-only lane datasets. Steering prediction requires images paired with steering labels.

Next training improvements:

- collect more balanced recovery driving data
- use left/right camera images for augmentation
- compare multiple validation splits
- track MAE/RMSE over repeated runs
- keep trained checkpoints ignored by Git

## Phase 4: Evaluate Predictions

Started.

The first offline evaluation on held-out simulator images produced:

```text
Rows evaluated: 741
MAE: 0.174045
RMSE: 0.246529
```

Continue improving offline evaluation before attempting any simulator drive loop.

## Phase 5: Later DonkeyCar/CARLA Integration

After validating the data and model workflow, expand to DonkeyCar Simulator or CARLA for richer simulator data and more professional evaluation.

## Next Technical Target

Implement a PyTorch simulator drive loop inspired by Udacity's `drive.py`, but
only after real simulator dataset validation and PyTorch model training.

Planned future file:

```text
src/simulator/udacity_drive_pytorch.py
```

This future loop should:

- connect only to a simulator in autonomous mode
- receive simulator camera images
- run PyTorch `SteeringModel` inference
- send predicted steering back to the simulator only
- record simulator frames and predictions for evaluation

It must not add real vehicle control, public road testing instructions, or unsafe
deployment steps.

All phases remain simulation-only. Do not add real vehicle control code or public road testing instructions.
