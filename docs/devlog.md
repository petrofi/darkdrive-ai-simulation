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
