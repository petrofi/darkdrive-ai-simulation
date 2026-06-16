# Model Notes

DarkDrive AI Simulation uses behavior cloning as the first AI training direction. The project remains simulation-only and is designed for education, portfolio work, and safe experimentation.

## What Behavior Cloning Is

Behavior cloning trains a model to imitate examples from a dataset. In this project, the dataset comes from simulated driving. Each row connects a camera image with driving values such as steering, throttle, brake, and speed.

For the first model:

- Input: RGB front camera image.
- Output: one continuous steering angle.
- Training source: simulated driving logs.
- Evaluation target: simulated environments only.

## Why Start With a Simple CNN

A small convolutional neural network is a good baseline because it can learn visual patterns from images without hiding too much complexity. It is easier to inspect, train, and improve than a large pretrained model.

The first version is intentionally modest:

- No pretrained models.
- No complex multi-sensor architecture.
- No real-time deployment logic.
- No real vehicle control.

## Why Use Simulated Data

Simulated data keeps the project safe and repeatable. It also makes it easier to collect many examples, test failures, and improve the model without any public road testing.

Simulation also helps with portfolio storytelling because each improvement can be shown with screenshots, logs, videos, and evaluation notes.

## Safety Boundary

This project does not control a real vehicle. It does not include public road deployment instructions, real car control code, or unsafe automation. Any model predictions are for simulation and learning only.

## Future Improvement Ideas

- Collect more simulated data.
- Add curves and different tracks.
- Add data augmentation.
- Build a model evaluation dashboard.
- Integrate CARLA camera sensors.
- Compare predictions against logged steering values.
