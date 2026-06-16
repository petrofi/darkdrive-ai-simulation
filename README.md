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
|   |-- model-notes.md
|   |-- dataset-format.md
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
|-- models/
|-- screenshots/
`-- videos/
```

## First Demo: Lane Detection with Sample Road Image

The first working demo runs a simple OpenCV lane detection pipeline on the included sample image. This is a computer vision experiment only and does not control any real vehicle.

The default demo input is:

```text
data/samples/road_sample.jpg
```

`road_sample.jpg` is only a demo/test image for computer vision experiments. It exists so the lane detection script can produce a visible output quickly in a simulation-focused portfolio workflow.

### Windows PowerShell Setup

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate the virtual environment:

```powershell
.\.venv\Scripts\activate
```

Install project requirements:

```powershell
pip install -r requirements.txt
```

Run the lane detection demo:

```powershell
python src/lane_detection/basic_lane_detection.py --image data/samples/road_sample.jpg --output screenshots/lane_detection_result.png
```

If the input image is found and OpenCV can process it, the output image will be saved to:

```text
screenshots/lane_detection_result.png
```

## First Working Pipeline

The first local pipeline has been tested end to end with the included demo image, a sample driving log, and a baseline PyTorch steering model.

This is only a baseline test pipeline. The current model is not a real driving model yet, and it must not be used for real vehicle control. Real learning will require simulated driving data collected across different tracks, turns, speeds, and recovery situations.

### Visual Demo

![Lane detection result](screenshots/lane_detection_result.png)

### 1. Lane Detection Test

Command:

```powershell
python src/lane_detection/basic_lane_detection.py --image data/samples/road_sample.jpg --output screenshots/lane_detection_result.png
```

Output:

```text
Detected 13 lane-like line segment(s).
Success: lane detection result saved to screenshots/lane_detection_result.png
```

### 2. Baseline Training Test

Command:

```powershell
python src/training/train_behavior_cloning.py --csv data/samples/sample_driving_log.csv --epochs 1 --batch-size 1 --output models/steering_model_v1.pt
```

Output:

```text
Simulation-only training mode.
Starting baseline behavior cloning training...
Epoch 1/1 - loss: 0.012405
Model saved to models\steering_model_v1.pt
```

### 3. Single-Image Inference Test

Command:

```powershell
python src/inference/predict_steering.py --model models/steering_model_v1.pt --image data/samples/road_sample.jpg
```

Output:

```text
Predicted steering angle: -0.0141
```

## AI Training Direction: Behavior Cloning

DarkDrive AI Simulation is evolving toward a baseline behavior cloning workflow for simulated driving data.

- The model learns from simulated driving data.
- Input: front camera image.
- Output: one continuous steering angle.
- Training data format: `image_path, steering, throttle, brake, speed`.
- Evaluation stays inside simulation.
- This is not real vehicle control.
- This is a portfolio and education project.

The first AI model is a small PyTorch CNN. It is intentionally simple so the data flow is easy to understand before adding larger datasets, better preprocessing, or simulator integration.

## How to Run AI Skeleton

The training script expects a simulated driving log at:

```text
data/processed/driving_log.csv
```

The CSV should use this format:

```text
image_path,steering,throttle,brake,speed
data/samples/road_sample.jpg,0.0,0.3,0.0,10.0
```

`data/samples/sample_driving_log.csv` is included only to demonstrate the expected format. It is not real training data.

Run the training skeleton:

```powershell
python src/training/train_behavior_cloning.py --csv data/processed/driving_log.csv --format simple --epochs 5 --batch-size 32 --output models/steering_model_v1.pt
```

Run single-image inference after a model has been trained:

```powershell
python src/inference/predict_steering.py --model models/steering_model_v1.pt --image data/samples/road_sample.jpg
```

Trained `.pt` and `.pth` model files are ignored by Git so large experiment artifacts do not get committed by accident.

## Training with Simulated Driving Data

The sample CSV is only for pipeline testing. Real model learning requires many simulated driving frames collected from a simulator such as DonkeyCar Simulator or CARLA.

Two dataset formats are supported:

- Simple format: `image_path,steering,throttle,brake,speed`
- Udacity-style format: `center,left,right,steering,throttle,brake,speed`

For the Udacity-style format, the current baseline trainer uses only the `center` camera image. Left and right camera images are reserved for future data augmentation work.

Train with the simple format:

```powershell
python src/training/train_behavior_cloning.py --csv data/processed/driving_log.csv --format simple --epochs 5 --batch-size 32 --output models/steering_model_v1.pt
```

Train with the Udacity-style format:

```powershell
python src/training/train_behavior_cloning.py --csv data/processed/driving_log.csv --format udacity --epochs 5 --batch-size 32 --output models/steering_model_v1.pt
```

The training script prints training and validation loss for each epoch and saves a loss chart to:

```text
screenshots/training_loss.png
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
