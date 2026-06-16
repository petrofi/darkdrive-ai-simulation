# Simulation Roadmap

## Step 1: Install a Self-Driving Car Simulator

Choose a simulator suitable for behavior cloning data collection, such as an educational self-driving car simulator or CARLA.

## Step 2: Drive Manually in Training Mode

Use manual driving to create examples of smooth steering, stable speed, and recovery from small mistakes.

## Step 3: Collect Camera Frames and `driving_log.csv`

Record camera frames and driving values in a simulator dataset. Keep the project simulation-only.

## Step 4: Place Data Into `data/processed/simulator/`

Use this structure:

```text
data/processed/simulator/
|-- IMG/
`-- driving_log.csv
```

## Step 5: Validate Dataset

Run the validation script to check CSV columns, center image paths, row count, and steering statistics.

## Step 6: Train Behavior Cloning Model

Train the baseline PyTorch model using the Udacity-style dataset format.

## Step 7: Evaluate Steering Predictions

Run inference on held-out simulator images and compare predictions against logged steering values.

## Step 8: Connect Model Back to Simulator Only After Validation

Only evaluate model behavior inside simulation after validating the dataset and prediction outputs. Do not add real vehicle control code.
