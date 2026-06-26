# Dataset Format

DarkDrive AI Simulation supports simple simulated driving logs for behavior cloning. The project remains simulation-only: no real vehicle control, no public road deployment, and no unsafe automation.

## Format A: Simple Format

Use this format for the first custom simulator logs:

```text
image_path,steering,throttle,brake,speed
data/processed/images/frame_000001.jpg,0.02,0.35,0.0,8.5
```

Columns:

- `image_path`: path to the front camera image.
- `steering`: continuous steering label.
- `throttle`: simulated throttle value.
- `brake`: simulated brake value.
- `speed`: simulated speed value.

For the first baseline model, only `image_path` and `steering` are used for training. The other columns are kept because they are useful for later analysis.

Standalone lane or road images are useful for OpenCV lane detection experiments, but they are not enough for steering model training unless they also have steering labels.

## Format B: Udacity-Style Format

Some educational self-driving datasets use a format like this:

```text
center,left,right,steering,throttle,brake,speed
IMG/center_000001.jpg,IMG/left_000001.jpg,IMG/right_000001.jpg,0.02,0.35,0.0,8.5
```

Columns:

- `center`: front/center camera image.
- `left`: left camera image.
- `right`: right camera image.
- `steering`: continuous steering label.
- `throttle`: simulated throttle value.
- `brake`: simulated brake value.
- `speed`: simulated speed value.

For now, the training script uses only the `center` camera image. The `left` and `right` images are ignored until the project adds camera correction and data augmentation.

## Recommended Next Step

Collect simulated driving frames into `data/processed/` and save the driving log as:

```text
data/processed/driving_log.csv
```

Start with clean, varied simulation data: straight roads, curves, gentle recovery examples, and different track sections. The sample CSV in `data/samples/` is only for pipeline testing and is not enough for real model learning.
