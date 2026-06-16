# 30-Day Roadmap

DarkDrive AI Simulation starts as a simulation-only learning and portfolio project. The first month focuses on building visible progress, keeping the code readable, and creating artifacts that are useful for GitHub and short progress videos.

## AI Training Roadmap

### Phase 1: OpenCV Lane Detection Demo

Use `data/samples/road_sample.jpg` to run a visible lane detection result and verify the local computer vision workflow.

### Phase 2: Driving Data Format

Use simulated driving logs with the following CSV columns:

```text
image_path,steering,throttle,brake,speed
```

### Phase 3: Baseline PyTorch CNN Steering Model

Train a simple `SteeringModel` that accepts RGB camera images and predicts one continuous steering value.

### Phase 4: Training Script Using Simulated Driving Logs

Use `src/training/train_behavior_cloning.py` to load images and steering values from simulation logs, train the baseline model, and save a local model artifact.

### Phase 5: Single-Image Steering Inference

Use `src/inference/predict_steering.py` to load a trained model and predict steering from one simulated camera image.

### Phase 6: Simulator Integration Later

Connect the data collection and model evaluation workflow to DonkeyCar Simulator or CARLA later. Evaluation remains simulation-only.

## Week 1: Project Setup, DonkeyCar Simulation, Data Collection, Lane Detection Prototype

### Goals

- Create the initial GitHub-ready project structure.
- Install the Python dependencies.
- Prepare DonkeyCar Simulator notes and setup instructions.
- Define the driving log format.
- Capture or prepare sample frames for experiments.
- Build the first OpenCV lane detection prototype.

### Deliverables

- Clean repository structure.
- Safety notes and development log.
- First lane detection output saved in `screenshots/`.
- Initial sample driving log format.

## Week 2: CARLA Setup, Camera Sensor, Traffic Simulation, Driving Logs

### Goals

- Prepare the CARLA workspace folder for future simulation work.
- Document CARLA installation notes and hardware expectations.
- Study camera sensor outputs and coordinate systems.
- Design a driving log format that can work with multiple simulators.
- Explore traffic and route simulation concepts.

### Deliverables

- CARLA notes in `simulator/carla/README.md`.
- Updated driving log examples.
- First design notes for simulator-agnostic data collection.

## Week 3: Dataset Preparation, Behavior Cloning Model, First Model Training, First Simulation Test

### Goals

- Review collected images and steering labels.
- Build a simple dataset loader.
- Create a baseline CNN steering model.
- Run the first behavior cloning training experiment when data is available.
- Test model predictions on held-out simulation frames.

### Deliverables

- Baseline `SteeringModel`.
- Training skeleton with clear missing-data messages.
- First steering prediction script.
- Initial notes about model behavior and failure cases.

## Week 4: Model Improvements, Evaluation, GitHub Polish, Final Demo Video

### Goals

- Improve preprocessing and training workflow.
- Compare model predictions against logged steering values.
- Create plots for steering distribution and training results.
- Polish the README and documentation.
- Record a final month-one demo video.

### Deliverables

- GitHub-ready documentation.
- Screenshots and demo clips.
- Evaluation notes.
- Final progress Reel or short demo video.
