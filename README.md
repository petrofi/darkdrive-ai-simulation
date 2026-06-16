# DarkDrive AI Simulation

A simulation-based autonomous driving AI project focused on computer vision, data collection, lane detection, and behavior cloning.

## Safety Notice

This project does not control a real vehicle. It is developed only for simulation, education, and portfolio purposes.

## Project Goals

- Learn autonomous driving basics in simulation
- Collect driving data
- Process camera frames
- Build a lane detection prototype
- Train a simple steering prediction model
- Evaluate model behavior in simulation

## Tech Stack

- Python
- OpenCV
- NumPy
- Pandas
- Matplotlib
- PyTorch
- Jupyter
- Optional later: DonkeyCar simulator integration
- Optional later: CARLA Python API

## Folder Structure

```text
darkdrive-ai-simulation/
|-- README.md
|-- requirements.txt
|-- .gitignore
|-- docs/
|   |-- roadmap.md
|   |-- devlog.md
|   |-- safety-notes.md
|   `-- reels-plan.md
|-- simulator/
|   |-- donkeycar/
|   |   `-- README.md
|   `-- carla/
|       `-- README.md
|-- data/
|   |-- raw/
|   |-- processed/
|   `-- samples/
|-- src/
|   |-- data_collection/
|   |-- lane_detection/
|   |-- models/
|   |-- training/
|   `-- inference/
|-- notebooks/
|-- screenshots/
`-- videos/
```

## 30-Day Roadmap Summary

- Week 1: Set up the project, connect to DonkeyCar Simulator, collect initial driving data, and build a basic OpenCV lane detection prototype.
- Week 2: Prepare CARLA workspace notes, explore camera sensors, traffic simulation concepts, and driving log formats.
- Week 3: Prepare datasets, define a baseline behavior cloning model, run first training experiments, and test predictions in simulation.
- Week 4: Improve the model, evaluate behavior, polish GitHub documentation, and create a final demo video.

## Current Status

Phase 0: Project setup and documentation

## Future Work

- DonkeyCar simulator integration
- CARLA simulator integration
- Lane detection improvements
- Behavior cloning model training
- Model evaluation dashboard
