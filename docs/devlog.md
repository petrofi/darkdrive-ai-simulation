# Development Log

## Day 1: Project Structure Created

### Goal

Create the first clean foundation for DarkDrive AI Simulation as a simulation-only autonomous driving learning project.

### What Was Added

- GitHub-ready project folders.
- README with project goals, safety notice, roadmap summary, and future work.
- Documentation for roadmap, safety boundaries, development logs, and social media planning.
- Python package structure under `src/`.
- Initial code skeletons for data logging, lane detection, behavior cloning training, model definition, and inference.
- Placeholder folders for data, screenshots, and videos.
- Minimal Jupyter notebook for future data review.

### Next Step

Create a virtual environment, install dependencies, and test the lane detection script with a sample simulator image.

## Day 2: Lane Demo and AI Training Direction

### Goal

Move from a standalone lane detection demo toward a simulation-based AI driving training project.

### What Was Added

- Added sample road image.
- Added lane detection demo direction.
- Added behavior cloning AI training direction.
- Added baseline model plan.

### Next Step

Collect simulated driving images and control values, then train the baseline steering model using `data/processed/driving_log.csv`.

## Day 3: First Working Pipeline Verified

### Goal

Polish the project so it can be tested cleanly from a fresh clone using Windows PowerShell commands.

### What Was Verified

- Verified lane detection demo.
- Verified baseline behavior cloning training.
- Verified steering prediction inference.
- Added documentation for testing commands.
- Prepared the project for simulated driving dataset collection.

### Next Step

Collect real simulated driving frames and labels, then train the baseline model with a larger dataset in `data/processed/`.

## Day 4: Simulator Data Collection Phase

### Goal

Prepare the project for real simulated driving data collection using Udacity-style behavior cloning datasets.

### What Was Added

- Transitioned project to simulator data collection phase.
- Added simulator dataset folder structure.
- Added dataset validation script.
- Added simulation setup documentation.
- Prepared the project for real simulated driving data.

### Next Step

Collect a first simulator dataset with 200-500 frames, validate it, then train the baseline steering model in simulation-only mode.

## Day 6: Local Udacity Simulator Workflow

### Goal

Document the local Udacity simulator path and prepare the project for safe simulator output handling.

### What Was Added

- Found a working Udacity simulator executable folder.
- Added local simulator documentation.
- Prepared simulator output folder workflow.
- Added dataset validation and training commands for Udacity-style data.
- Noted that `win_sys_int` may not support behavior cloning data recording.

### Next Step

Launch the simulator manually, check whether it can export `IMG` frames and `driving_log.csv`, then either collect data there or move behavior cloning data collection to another simulator.

## Day 7: Data Collection Plan

### Goal

Clarify what data is missing and where training data should come from.

### What Was Added

- Documented that lane images alone are not enough for behavior cloning.
- Added a simulator data collection plan.
- Added recommended data source order: Udacity behavior cloning simulator, local `win_sys_int` if compatible, DonkeyCar Simulator, then CARLA.
- Added training commands for steering-labeled simulator data.
- Reviewed Udacity Behavioral Cloning reference project.
- Identified the `drive.py` websocket loop as a future integration reference.
- Decided to keep DarkDrive PyTorch-based.
- Added an adaptation plan for a PyTorch simulator-only driving loop.

### Next Step

Check whether the local simulator can export `IMG` frames and `driving_log.csv`; if not, move behavior cloning data collection to DonkeyCar Simulator.

## Day 8: Web Lane Image Batch

### Goal

Expand the OpenCV lane detection demo with a larger web image batch.

### What Was Added

- Added a Wikimedia Commons web image downloader for lane detection demos.
- Downloaded 500 open-license road/lane-related web images.
- Added a batch OpenCV lane image processing script.
- Processed 503 web lane images with 0 failures.
- Added source/license metadata and a processing report.

### Next Step

Use the web lane image batch to improve computer vision experiments, while collecting steering-labeled simulator data separately for behavior cloning.

## Day 9: Improved Steering Model and Synthetic Training

### Goal

Improve the behavior cloning model and run a larger training test without using unlabeled web images as steering data.

### What Was Added

- Upgraded `SteeringModel` to a compact NVIDIA-style CNN.
- Added training augmentation, MAE reporting, device selection, AdamW, and checkpoint metadata.
- Added a synthetic steering dataset generator for simulation-only pipeline development.
- Generated 1000 local synthetic steering frames.
- Trained the improved model for 8 epochs on the synthetic dataset.
- Saved a synthetic training loss chart.

### Training Result

```text
Training rows: 800
Validation rows: 200
Final training loss: 0.000789
Final validation loss: 0.000405
Final validation MAE: 0.0208
Example predicted steering: 0.0125
```

### Next Step

Replace the synthetic dataset with real simulator driving logs from DonkeyCar, Udacity behavior cloning simulator, or CARLA, then compare predictions against held-out simulator steering labels.

## Day 10: First Real Simulator Dataset

### Goal

Move the project from simulator dataset collection ready to simulator training ready.

### What Was Added

- Confirmed Udacity simulator recording works.
- Collected the first real simulator driving dataset.
- Prepared dataset analysis, validation, training, and evaluation workflow.
- Added robust handling for headerless Udacity CSV logs and moved Windows image paths.
- Trained the baseline PyTorch steering model on real simulator frames.
- Evaluated predictions on held-out simulator frames.
- Moved the project toward Simulator Training Ready level.

### Dataset Result

```text
Rows: 3706
Center images found: 3706
Left images found: 3706
Right images found: 3706
Steering min/max/mean/std: -1.000000 / 1.000000 / -0.013526 / 0.350406
Validation: PASS
```

### Training Result

```text
Training rows: 2965
Validation rows: 741
Best epoch: 10
Best validation loss: 0.060776
Evaluation MAE: 0.174045
Evaluation RMSE: 0.246529
```

### Next Step

Collect more balanced simulator driving data with recovery examples, then improve evaluation and only later implement a simulator-only autonomous drive loop.

## Day 11: Dataset V2 Session A Organization

### Goal

Move the new simulator recording into the Dataset v2 workflow and verify that generated simulator files stay out of Git.

### What Was Added

- Organized the new simulator recording from `veriler/`.
- Integrated it as Dataset v2 Session A: `data/processed/simulator_v2/session_a_normal/`.
- Ran session-level dataset analysis with `scripts/session_dataset_report.py`.
- Confirmed generated simulator images and `driving_log.csv` remain ignored by Git.

### Dataset Result

```text
Rows: 2400
Total simulator images: 7200
Center images found: 2400
Missing center images: 0
Steering min/max/mean/std: -1.000000 / 1.000000 / -0.012757 / 0.356202
Near-zero steering: 57.42%
Left steering: 28.17%
Right steering: 14.42%
Strong turns: 14.12%
Validation: PASS
```

### Next Step

Collect recovery-focused Dataset v2 sessions, especially right recovery and right-turn examples, because Session A is valid but does not reduce the near-zero steering problem.

## Day 12: Dataset V2 New Training Session Organization

### Goal

Move the new simulator recording from `yeni eğitim/` into the Dataset v2 structure and analyze it safely.

### What Was Added

- Organized the new simulator recording as `data/processed/simulator_v2/session_b_new_training/`.
- Ran session-level dataset analysis after the move.
- Confirmed generated simulator data remains ignored by Git.
- Added a session report documenting that the data is valid but not recovery-heavy.

### Dataset Result

```text
Rows: 1126
Total simulator images: 3378
Center images found: 1126
Missing center images: 0
Steering min/max/mean/std: -0.983591 / 0.932523 / -0.030387 / 0.244779
Near-zero steering: 55.24%
Left steering: 25.84%
Right steering: 18.92%
Strong turns: 8.17%
Validation: PASS
```

### Next Step

Collect a deliberate right-recovery and curve-focused session. The new session is valid, but it does not materially reduce the near-zero steering issue.

## Day 13: Dataset V2 Session Classification Review

### Goal

Re-analyze `session_b_new_training` and decide whether it should be treated as Session C Right Recovery.

### What Was Found

- `session_b_new_training` contains `IMG/` and `driving_log.csv`.
- Session analysis passed with 1126 rows and 0 missing center images.
- Right steering improved compared with Session A, but not enough to classify the data as right recovery.
- Strong-turn coverage was weaker than Session A.
- Generated simulator data remained ignored by Git.

### Dataset Result

```text
Rows: 1126
Center images found: 1126
Missing center images: 0
Steering min/max/mean/std: -0.983591 / 0.932523 / -0.030387 / 0.244779
Near-zero steering: 55.24%
Left steering: 25.84%
Right steering: 18.92%
Strong turns: 8.17%
Validation: PASS
Classification: weak mixed/normal training data
```

### Next Step

Collect a true Session C right-recovery recording with more right steering, fewer straight-driving frames, and stronger correction examples.
