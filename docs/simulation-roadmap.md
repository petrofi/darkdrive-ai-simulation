# Simulation Roadmap

## Phase 1: First Working Pipeline

Completed.

- OpenCV lane detection works.
- Baseline PyTorch steering prediction training works.
- Single-image steering prediction works.
- Dataset validation tooling exists.

## Phase 2: Try Local Udacity Simulator for Data Collection

Use the local simulator folder:

```text
C:\Users\tarik\Downloads\win_sys_int\win_sys_int
```

Decision point:

- If it produces `driving_log.csv` and `IMG` frames, use it for the first behavior cloning dataset.
- If it does not, do not waste time trying to force it into the workflow. Move data collection to DonkeyCar Simulator.

Data source priority:

1. Udacity Term 1 behavior cloning simulator, if available.
2. Current `win_sys_int` simulator, only if it exports behavior cloning data.
3. DonkeyCar Simulator for practical behavior cloning data collection.
4. CARLA later for richer camera sensor work.

## Phase 3: Train Model on Real Simulated Driving Data

Place validated simulator data under:

```text
data/processed/simulator/
```

Train the baseline model with the Udacity-style format.

Do not train the steering model on image-only lane datasets. Steering prediction requires images paired with steering labels.

## Phase 4: Evaluate Predictions

Run inference on held-out simulator images and compare predicted steering values against logged steering values.

## Phase 5: Later DonkeyCar/CARLA Integration

After validating the data and model workflow, expand to DonkeyCar Simulator or CARLA for richer simulator data and more professional evaluation.

All phases remain simulation-only. Do not add real vehicle control code or public road testing instructions.
