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

## Day 14: DonkeyCar Dataset Integration Workflow

### Goal

Prepare a safe external dataset path for DonkeyCar simulator tub data without downloading datasets, training, or adding simulator control.

### What Was Added

- Added ignored folders for manually placed DonkeyCar source data and converted outputs.
- Added `scripts/convert_donkey_tub_to_darkdrive.py` for best-effort DonkeyCar tub conversion into DarkDrive unified CSV format.
- Added `scripts/validate_donkeycar_conversion.py` for converted dataset validation.
- Documented DonkeyCar tub risks, format differences, and merge gates.
- Confirmed the workflow stays simulation-only and generated data remains ignored by Git.

### Next Step

Manually collect a small DonkeyCar simulator tub, convert it, validate missing images and steering distribution, then compare it against local Udacity Session A and `session_b_new_training` before any merge or training decision.

## Day 15: DonkeyCar Data Acquisition Plan

### Goal

Choose the safest way to obtain a small DonkeyCar simulator tub without disrupting the existing DarkDrive environment.

### What Was Added

- Added a DonkeyCar data acquisition plan.
- Compared WSL/Ubuntu collection, public tub reuse, and continuing Udacity Session C2.
- Kept the project simulation-only and dataset-only.
- No training or control code was added.

### Environment Finding

```text
Global python on PATH: not found
Global pip on PATH: not found
Project .venv Python: 3.13.12
Project .venv pip: 26.1.2
```

### Next Step

Use WSL/Ubuntu or a separate DonkeyCar environment to manually collect one small tub, then place it under `data/external/donkeycar/sample_tub/` for conversion and validation.

## Day 16: DonkeyCar WSL Setup Plan

### Goal

Check whether WSL/Ubuntu is available and prepare a safe setup path for DonkeyCar simulator tub collection.

### What Was Added

- Prepared a DonkeyCar WSL setup plan.
- Added a WSL manual checklist for collecting one small simulator tub.
- Kept DonkeyCar separate from the DarkDrive Windows `.venv`.
- No training, merging, or control code was added.

### Environment Finding

```text
WSL status: installed
WSL default version: 2
Installed Linux distributions: none
Ubuntu status: not installed
WSL Python/pip/git status: unavailable until a distro is installed
```

### Next Step

Install Ubuntu for WSL manually, create an isolated DonkeyCar workspace, collect one small simulator tub, then copy it into `data/external/donkeycar/sample_tub/`.

## Day 17: DonkeyCar WSL Environment Verification

### Goal

Verify the Ubuntu WSL environment and prepare the isolated DonkeyCar workspace outside DarkDrive.

### What Was Found

- User-provided Ubuntu terminal status reports Ubuntu 24.04.3 LTS, Python 3.12.3, pip 24.0, and git 2.43.0.
- The DarkDrive Windows project path exists.
- The Codex PowerShell WSL session reports WSL version 2 but no visible installed distro.
- WSL-side DarkDrive path access and `donkey-env` creation could not be completed from this Codex session.

### What Was Added

- Added a DonkeyCar WSL setup status report.
- Documented the exact manual commands to create `~/donkeycar-workspace/donkey-env` from the working Ubuntu terminal.
- Kept DarkDrive Windows `.venv` untouched.
- No training, merging, dataset download, or control code was added.

### Next Step

Run the documented workspace and venv commands inside the same Ubuntu terminal that reports Ubuntu 24.04.3, then report the output before installing DonkeyCar.

## Day 18: DonkeyCar WSL Install Attempt Preparation

### Goal

Prepare the safest DonkeyCar installation attempt inside the isolated WSL `donkey-env`.

### What Was Found

- User confirmed Ubuntu 24.04.3, Python 3.12.3, DarkDrive WSL path access, and an isolated `~/donkeycar-workspace/donkey-env`.
- User confirmed the active pip path is inside `/home/darklove/donkeycar-workspace/donkey-env/`.
- Codex still cannot see an installed WSL distro from this PowerShell session, so it cannot safely run the install inside `donkey-env`.

### What Was Added

- Documented the planned `pip install "donkeycar[pc]"` command.
- Documented Python 3.12 compatibility risks.
- Documented fallback options if DonkeyCar installation fails.
- Kept DarkDrive Windows `.venv` untouched.
- No training, merging, dataset download, or control code was added.

### Next Step

Run the documented `python --version`, `pip --version`, `which python`, and `which pip` checks inside Ubuntu. If they point into `~/donkeycar-workspace/donkey-env`, run the DonkeyCar install command manually and report the result.

## Day 19: DonkeyCar WSL Install Success

### Goal

Document the successful DonkeyCar installation inside the isolated WSL `donkey-env`.

### What Was Added

- Documented DonkeyCar installation inside `~/donkeycar-workspace/donkey-env`.
- Documented the `pkg_resources` compatibility issue.
- Documented the fix using `python -m pip install "setuptools==80.9.0"` inside `donkey-env`.
- Added the next safe data collection step: inspect `donkey --help` before creating a car/project or tub.
- Confirmed DarkDrive Windows `.venv` remains untouched.
- No training, merging, dataset download, or control code was added.

### Next Step

Run `donkey --help` inside the active WSL `donkey-env`, identify the installed version's project/tub workflow, then collect only a small simulator tub for conversion into DarkDrive.

## Day 20: DonkeyCar Python 3.12 Compatibility Review

### Goal

Determine whether the isolated WSL DonkeyCar install is usable for CLI-based data collection.

### What Was Found

- DonkeyCar 2.5.8 installed inside the isolated Python 3.12 `donkey-env`.
- `import donkeycar` works after pinning `setuptools==80.9.0`.
- `donkey --help` fails with `AttributeError: module 'collections' has no attribute 'MutableMapping'`.
- The failure comes from old `tornado 4.5.3` usage under Python 3.12.

### Decision

Do not patch randomly. Use a clean Python 3.11/3.10 DonkeyCar environment, or pause DonkeyCar and continue Udacity Session C2 right-recovery data collection.

### Safety

DarkDrive Windows `.venv` remains untouched. No training, merging, dataset download, or control code was added.

## Day 21: Dataset V2 Session C2 And Local V2 Model Review

### Goal

Validate the new `session_c2_right_recovery` Udacity simulator recording, build a local Dataset v2 only if it passed, train a new offline model, and document the result without committing raw data or model checkpoints.

### What Was Found

- Repository started clean on `main`.
- Session C2 contained `IMG/` and `driving_log.csv`.
- Session C2 had 4163 CSV rows and 12489 image files.
- Center, left, and right image references all resolved with 0 missing images.
- All 12489 images were readable at 320x160x3.
- Duplicate CSV rows, duplicate image references, corrupt images, invalid labels, and steering values outside `[-1, 1]` were all 0.
- A few recording timestamp gaps were found, including one 27.250s pause, but no missing files or malformed rows resulted.

### Session C2 Result

```text
Rows: 4163
Center / left / right images found: 4163 / 4163 / 4163
Missing center / left / right images: 0 / 0 / 0
Steering min/max/mean/std: -1.000000 / 1.000000 / -0.017837 / 0.347744
Near-zero steering: 41.32%
Left steering: 30.22%
Right steering: 28.47%
Strong turns: 14.89%
Verdict: B) Usable but imperfect
```

Session C2 passed the missing-image, near-zero, and right-steering gates. It missed the strong-turn target by 0.11 percentage points and still had slightly more left than right steering.

### Dataset V2 Result

Built `data/processed/local_v2_training/driving_log.csv` from Dataset v1, Session A, `session_b_new_training`, and Session C2 with a 35% near-zero cap.

```text
Rows: 8647
Missing images: 0
Duplicate rows: 0
Near-zero steering: 34.99%
Left steering: 35.27%
Right steering: 29.73%
Strong turns: 18.53%
Steering min/max/mean/std: -1.000000 / 1.000000 / -0.021734 / 0.392077
```

### Training And Evaluation Result

Trained `models/steering_model_local_v2.pt` for 15 epochs with seed 42, batch size 32, augmentation on, and a deterministic random 80/20 row split.

```text
Training rows: 6918
Validation rows: 1729
Device: cpu
Best epoch: 15
Best validation loss: 0.092040
Final training loss: 0.080739
Final validation loss: 0.092040
Evaluation MAE: 0.211307
Evaluation RMSE: 0.303382
Zero-steering baseline MAE: 0.261022
```

Compared with v1, the model result is worse:

```text
V1 MAE/RMSE: 0.174045 / 0.246529
Local v2 MAE/RMSE: 0.211307 / 0.303382
```

The local v2 model beats the zero-steering baseline by 19.05%, but it under-predicts right and strong turns. Final release verdict: R1, not ready.

### Git Safety

Raw simulator sessions, the merged local v2 CSV, model checkpoints, and generated screenshots remained ignored. No simulator control code was added.

### Next Step

Collect Session D curve-focused data before another local v2 training run.

## Day 22: Dataset V2 Session D Curve-Focused Validation

### Goal

Validate the new `session_d_curve_focused` Udacity simulator recording and decide whether it is strong enough to support a future Local V3 training dataset.

### What Was Found

- Repository started clean on `main` and synchronized with `origin/main`.
- Generated Session D data, future Local V3 data, and model checkpoint paths are ignored by Git.
- Session D contained `IMG/` and `driving_log.csv`.
- Session D had 7721 CSV rows and 23163 image files.
- Center, left, and right image references all resolved with 0 missing images.
- All 23163 images were readable at 160x320x3.
- Duplicate CSV rows, duplicate image filenames, duplicate image references, invalid steering labels, corrupt images, and steering values outside `[-1, 1]` were all 0.
- Timestamp parsing found 0 failures, 0 non-positive deltas, and no gaps above 0.25s.

### Session D Result

```text
Rows: 7721
Center / left / right images found: 7721 / 7721 / 7721
Missing center / left / right images: 0 / 0 / 0
Steering min/max/mean/std: -1.000000 / 1.000000 / -0.035870 / 0.441348
Near-zero steering: 22.00%
Left steering: 47.07%
Right steering: 30.93%
Strong turns: 24.83%
Verdict: A) Strong curve-focused session
```

Temporal curve analysis found sustained curve behavior, not only isolated steering spikes:

```text
Sustained medium steering runs, length >= 5: 210
Sustained left medium curve runs: 129
Sustained right medium curve runs: 81
Sustained strong steering runs, length >= 5: 80
Longest near-zero run: 30 frames
Largest timestamp gap: 0.115s
```

Session D is useful for Local V3 training, but it is left-heavy and should be balanced with Session C2/right-turn coverage during dataset construction.

### Training Decision

Training was intentionally deferred. No Local V3 dataset was built and no checkpoint was created.

### Documentation Added

- Added `docs/dataset-v2-session-d-curve-focused-report.md`.
- Added `docs/local-v3-training-plan.md`.
- Updated `docs/experiments.md` with `EXP-004-session-d-curve-focused-data`.
- Refreshed the relevant research roadmap, release checklist, and Dataset v2 collection notes.

### Git Safety

Raw simulator images, `driving_log.csv`, generated screenshots, and model checkpoints remained ignored. Only documentation files were prepared for commit.

## Day 23: Local V3 Session-Aware Dataset Build

### Goal

Build a Local V3 dataset structure with explicit train and validation manifests, preserving session identity and avoiding adjacent-frame leakage from random row splitting.

### What Was Added

- Added `scripts/build_local_v3_training_dataset.py`.
- Built `data/processed/local_v3_training/train.csv` from Dataset v1, Session A, Session B, and Session D.
- Reserved the complete `session_c2_right_recovery` recording as `validation.csv`.
- Preserved `source_session` and `source_dataset` in every manifest row.
- Used center-camera rows only; side-camera correction labels remain a future separate experiment.
- Added focused unit tests for deterministic sampling, holdout isolation, missing-image failure, duplicate-path detection, and steering distribution metrics.

### Dataset Result

```text
Train rows: 10657
Validation rows: 4163
Train near-zero / left / right / strong: 28.72% / 35.86% / 35.41% / 27.20%
Validation near-zero / left / right / strong: 41.32% / 30.22% / 28.47% / 14.89%
Missing images: 0
Corrupt images: 0
Invalid steering labels: 0
Train/validation source overlap: 0
Train/validation image-path overlap: 0
Train/validation CSV-row overlap: 0
Train/validation image-filename overlap: 0
Verdict: A) Local V3 dataset ready for session-aware training
```

### Training Decision

Training was intentionally deferred. The current training script still performs its own random row split, so the next task is to extend training and evaluation to accept explicit `train.csv` and `validation.csv` manifests before training `models/steering_model_local_v3.pt`.

### Git Safety

Generated Local V3 manifests, raw simulator datasets, model checkpoints, and generated plots remained ignored by Git. No raw data or model files were staged.

## Day 24: Local V3 Session-Aware Training And Evaluation

### Goal

Extend the trainer and evaluator to use explicit Local V3 train/validation manifests, train `models/steering_model_local_v3.pt`, and evaluate it on the complete Session C2 holdout without random row re-splitting.

### What Was Added

- Added `--train-csv` and `--validation-csv` support to `src/training/train_behavior_cloning.py`.
- Preserved the old single `--csv` random-split workflow for backward compatibility.
- Added pre-training safety checks for missing images, invalid labels, train/validation image-path overlap, and `source_session` overlap.
- Added `--validation-csv` support to `scripts/evaluate_steering_model.py`.
- Added overall, subgroup, steering-bin, zero-baseline, prediction-variance, direction-error, and source-session evaluation metrics.
- Fixed unittest discovery with `tests/__init__.py`.
- Added focused session-aware trainer and evaluator tests.

### Training Result

```text
Interpreter: .venv\Scripts\python.exe
Python: 3.13.14
PyTorch: 2.12.0+cpu
Device: CPU
Train rows: 10657
Validation rows: 4163
Epochs: 15
Batch size: 32
Seed: 42
Parameters: 188219
Training duration: 432.77 seconds
Best epoch: 3
Best validation loss: 0.100252
Final training loss: 0.111446
Final validation loss: 0.113804
Final training MAE: 0.238593
Final validation MAE: 0.221872
```

### Session C2 Evaluation Result

```text
Rows evaluated: 4163
MAE: 0.215618
RMSE: 0.316627
Zero-steering baseline MAE: 0.214081
MAE improvement over zero baseline: -0.72%
Near-zero MAE: 0.139037
Left MAE: 0.288706
Right MAE: 0.249182
Strong-turn MAE: 0.598862
Prediction std: 0.228446
Actual std: 0.347744
Prediction/actual std ratio: 0.656937
Incorrect direction rate: 16.46%
```

### Session C2 Comparison

On the same Session C2 validation manifest:

```text
V1 MAE/RMSE: 0.225056 / 0.332471
Local V2 MAE/RMSE: 0.193998 / 0.267838
Local V3 MAE/RMSE: 0.215618 / 0.316627
```

Local V3 improved over v1 on this holdout but did not improve over Local V2's Session C2 score. Local V2's Session C2 score is historical context only, not an independent holdout result, because Session C2 contributed to the Local V2 training dataset.

### Release Decision

Verdict: R2, valid offline experiment, not promoted.

Training and evaluation completed without leakage, but the model does not beat the zero-steering MAE baseline. Simulator control remains blocked.

### Git Safety

The Local V3 checkpoint, generated metrics JSON files, generated screenshots, generated Local V3 CSV manifests, raw simulator datasets, and model checkpoints remained ignored by Git.

## Day 25: EXP-007 Road-Focused Crop Preprocessing

### Goal

Run exactly one controlled preprocessing experiment on the fixed Local V3 split: add a deterministic road-focused crop before resize and keep all other major variables unchanged.

### What Was Added

- Added shared preprocessing profiles in `src/utils/image_preprocessing.py`.
- Added `baseline` and `road_crop_v1` support to training, evaluation, and single-image inference.
- Stored preprocessing metadata in new checkpoints.
- Made evaluation and inference read checkpoint preprocessing metadata when available.
- Preserved backward compatibility: old checkpoints without metadata default to `baseline`.
- Added focused preprocessing tests for shape, crop boundaries, invalid profile handling, deterministic validation, metadata fallback, and shared preprocessing consistency.

### Crop Definition

```text
Profile: road_crop_v1
Source frame: 320x160
Crop: x=[0, full width), y=[55,150)
Resize after crop: 160x80
Pixel scaling: unchanged, [0,1]
```

### Training Result

```text
Interpreter: C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe
Device: CPU
Train rows: 10657
Validation rows: 4163
Epochs: 15
Batch size: 32
Seed: 42
Parameters: 188219
Training duration: 409.065 seconds
Best epoch: 5
Best validation loss: 0.094317
Final training loss: 0.119376
Final validation loss: 0.107179
Final training MAE: 0.245646
Final validation MAE: 0.209884
Checkpoint: models/steering_model_local_v3_crop_v1.pt
```

### Session C2 Evaluation Result

```text
Rows evaluated: 4163
MAE: 0.215280
RMSE: 0.307111
Zero-steering baseline MAE: 0.214081
MAE improvement over zero baseline: -0.56%
Near-zero MAE: 0.151936
Left MAE: 0.269212
Right MAE: 0.249969
Strong-turn MAE: 0.574012
Prediction std: 0.233060
Actual std: 0.347744
Prediction/actual std ratio: 0.670205
Incorrect direction rate: 16.00%
```

### Controlled Comparison

```text
Local V3 baseline MAE/RMSE: 0.215618 / 0.316627
Local V3 road_crop_v1 MAE/RMSE: 0.215280 / 0.307111
Baseline right/strong MAE: 0.249182 / 0.598862
Crop right/strong MAE: 0.249969 / 0.574012
Baseline std ratio: 0.656937
Crop std ratio: 0.670205
```

The crop improved RMSE, strong-turn MAE, direction error, and prediction variance slightly. It did not materially improve overall MAE, it still missed the zero-steering baseline, near-zero MAE regressed, and right MAE regressed slightly.

### Verdict

Verdict: P2, valid experiment with no meaningful improvement.

Do not run another crop variant against Session C2 in this task. Recommended next single-variable experiment: Huber loss on the same fixed Local V3 split.

### Git Safety

The crop checkpoint, generated metrics JSON files, generated screenshots, generated Local V3 CSV manifests, raw simulator datasets, and model checkpoints remained ignored by Git. No simulator control code was added.

## Day 26: EXP-008 Huber Loss / SmoothL1Loss

### Goal

Run exactly one controlled loss-function experiment on the fixed Local V3 split: replace MSE with Huber-style `SmoothL1Loss(beta=1.0)` while keeping baseline preprocessing and every other major variable unchanged.

### What Was Added

- Tightened configurable regression loss support in `src/training/train_behavior_cloning.py`.
- Preserved `mse` as the default loss for backward compatibility.
- Implemented `huber` as `torch.nn.SmoothL1Loss(beta=1.0)`.
- Added clear loss metadata to checkpoints: name, PyTorch class, beta, and delta.
- Added focused tests for default MSE, Huber selection, unsupported loss handling, checkpoint metadata, and baseline preprocessing defaults.

### Training Result

```text
Interpreter: C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe
Device: CPU
Train rows: 10657
Validation rows: 4163
Preprocessing: baseline
Loss: SmoothL1Loss(beta=1.0)
Epochs: 15
Batch size: 32
Seed: 42
Parameters: 188219
Training duration: 496.612 seconds
Best epoch: 7
Best validation loss: 0.049741
Final training loss: 0.056181
Final validation loss: 0.052497
Final training MAE: 0.238528
Final validation MAE: 0.218696
Checkpoint: models/steering_model_local_v3_huber.pt
```

### Session C2 Evaluation Result

```text
Rows evaluated: 4163
MAE: 0.213646
RMSE: 0.320153
Zero-steering baseline MAE: 0.214081
MAE improvement over zero baseline: 0.20%
Near-zero MAE: 0.132261
Left MAE: 0.265846
Right MAE: 0.276358
Strong-turn MAE: 0.575495
Prediction std: 0.245478
Actual std: 0.347744
Prediction/actual std ratio: 0.705915
Incorrect direction rate: 17.44%
```

### Controlled Comparison

```text
Local V3 MSE MAE/RMSE: 0.215618 / 0.316627
Local V3 Huber MAE/RMSE: 0.213646 / 0.320153
MSE right/strong MAE: 0.249182 / 0.598862
Huber right/strong MAE: 0.276358 / 0.575495
MSE std ratio: 0.656937
Huber std ratio: 0.705915
MSE direction error: 16.46%
Huber direction error: 17.44%
```

Huber improved overall MAE slightly, made the zero-baseline comparison barely positive, improved strong-turn MAE, and increased prediction variance. It also worsened RMSE, right-turn MAE, and direction error.

### Verdict

Verdict: H2, valid experiment with no meaningful improvement.

Do not run another loss variant in this task. Recommended next single-variable experiment: a slightly stronger CNN architecture on the same fixed Local V3 split.

### Git Safety

The Huber checkpoint, generated metrics JSON files, generated screenshots, generated Local V3 CSV manifests, raw simulator datasets, and model checkpoints remained ignored by Git. No simulator control code was added.

## Day 27: EXP-009 Slightly Stronger CNN Architecture

### Goal

Run exactly one controlled architecture experiment on the fixed Local V3 split: replace the compact baseline `SteeringModel` with `cnn_v2` / `SteeringModelV2` while keeping baseline preprocessing, MSE loss, AdamW, learning rate, epochs, batch size, seed, and train-only augmentation unchanged.

### What Was Added

- Added `SteeringModelV2`, a slightly stronger single-frame CNN with BatchNorm2d, ELU activations, a deeper convolution stack, adaptive pooling, and a wider MLP head.
- Added model selection through `--model-arch baseline` and `--model-arch cnn_v2`.
- Preserved `baseline` as the default model architecture for backward compatibility.
- Added checkpoint metadata for `model_arch`, `model_class`, `model_architecture`, and parameter count.
- Updated evaluator and inference loading to read model architecture from checkpoint metadata, with old metadata-free checkpoints defaulting to baseline.
- Added focused model-architecture tests for factory creation, forward shape, parameter count, checkpoint metadata, evaluator loading, and unsupported architecture errors.

### Training Result

```text
Interpreter: C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe
Device: CPU
Train rows: 10657
Validation rows: 4163
Preprocessing: baseline
Loss: MSELoss
Architecture: cnn_v2 / SteeringModelV2
Epochs: 15
Batch size: 32
Seed: 42
Parameters: 726103
Observed command wall time: 634.1 seconds
Best epoch: 5
Best validation loss: 0.098543
Final training loss: 0.127928
Final validation loss: 0.119668
Final training MAE: 0.256503
Final validation MAE: 0.229572
Checkpoint: models/steering_model_local_v3_cnn_v2.pt
```

### Session C2 Evaluation Result

```text
Rows evaluated: 4163
MAE: 0.217054
RMSE: 0.313915
Zero-steering baseline MAE: 0.214081
MAE improvement over zero baseline: -1.39%
Near-zero MAE: 0.136335
Left MAE: 0.285110
Right MAE: 0.261968
Strong-turn MAE: 0.612222
Prediction std: 0.208329
Actual std: 0.347744
Prediction/actual std ratio: 0.599089
Incorrect direction rate: 19.03%
```

### Controlled Comparison

```text
Local V3 baseline MAE/RMSE: 0.215618 / 0.316627
Local V3 cnn_v2 MAE/RMSE: 0.217054 / 0.313915
Baseline right/strong MAE: 0.249182 / 0.598862
cnn_v2 right/strong MAE: 0.261968 / 0.612222
Baseline std ratio: 0.656937
cnn_v2 std ratio: 0.599089
Baseline direction error: 16.46%
cnn_v2 direction error: 19.03%
```

The stronger CNN improved RMSE slightly but worsened overall MAE, right MAE, strong-turn MAE, prediction variance compression, zero-baseline comparison, and direction error.

### Verdict

Verdict: A2, valid experiment with no meaningful improvement.

Do not run another architecture variant against Session C2 in this task. Recommended next single step: collect an independent Session E test set before further model-selection work.

### Git Safety

The cnn_v2 checkpoint, generated metrics JSON files, generated screenshots, generated Local V3 CSV manifests, raw simulator datasets, and model checkpoints remained ignored by Git. No simulator control code was added.

## Day 28: Session E Independent Test Set Preparation

### Goal

Prepare the workflow for an independent Session E test set after repeated Session C2 model-selection experiments.

Session E is intended to be a frozen independent test set. It must not be used for training, validation, hyperparameter tuning, crop selection, loss selection, architecture selection, or repeated model selection.

### Folder Preparation

Prepared the target folder:

```text
data/processed/simulator_v2/session_e_independent_test/
data/processed/simulator_v2/session_e_independent_test/IMG/
```

Exact Windows folder for recording:

```text
C:\Users\tarik\OneDrive\Ekler\Desktop\darkdrive-ai-simulation\data\processed\simulator_v2\session_e_independent_test
```

The Udacity simulator recording window should select `session_e_independent_test` directly. It should not select `simulator_v2`.

### Data Status

```text
driving_log.csv exists: no
IMG file count: 0
```

Session E recording is pending.

### Validation / Training / Evaluation

No Session E validation was run because no data exists yet.

No model training was run.

No model evaluation was run.

No fake `driving_log.csv` was created.

### Documentation

Added `docs/session-e-independent-test-plan.md` with:

- frozen-test-set rule
- target folder
- simulator recording instruction
- collection guidance
- target distribution ranges
- explicit prohibited uses
- current pending-recording status

Updated the experiment ledger to add `EXP-010-session-e-independent-test-set-prep`.

### Git Safety

Session E raw simulator data remains ignored by Git. No raw images, raw `driving_log.csv`, generated datasets, checkpoints, screenshots, or metrics JSON files were staged.

## Day 29: Session E Independent Test Validation

### Goal

Validate the newly recorded `session_e_independent_test` dataset as a candidate frozen independent test set. Do not train models, evaluate checkpoints, or compare model variants on Session E.

### Source

```text
data/processed/simulator_v2/session_e_independent_test/driving_log.csv
data/processed/simulator_v2/session_e_independent_test/IMG/
```

The CSV is headerless Udacity format with center, left, right, steering, throttle, brake, and speed columns. Image paths are absolute Windows paths pointing to the Session E `IMG/` folder.

### Validation Result

```text
CSV rows: 6379
Total image files: 19137
Center / left / right files: 6379 / 6379 / 6379
Missing center / left / right images: 0 / 0 / 0
Corrupt images: 0
Duplicate CSV rows: 0
Duplicate image references: 0
Exact duplicate image files by MD5: 0
Invalid steering labels: 0
Out-of-range steering labels: 0
Official validator result: PASS
```

### Distribution

```text
Steering min / max / mean / std: -1.000000 / 1.000000 / 0.000864 / 0.315431
Near-zero steering: 46.59%
Left steering: 26.09%
Right steering: 27.32%
Strong turns: 9.72%
Throttle min / mean / max: 0.000000 / 0.936395 / 1.000000
Brake min / mean / max: 0.000000 / 0.023379 / 1.000000
Speed min / mean / max: 0.000038 / 28.194715 / 30.509890
```

### Temporal Checks

```text
Medium steering runs, abs>=0.25: 675
Sustained medium runs, length>=5: 38
Sustained left/right medium runs: 22 / 16
Strong steering runs, abs>=0.5: 131
Sustained strong runs, length>=5: 23
Sustained left/right strong runs: 12 / 11
Long near-zero runs, length>=30: 3
Longest near-zero run: 41 frames
Stationary rows, speed<=0.1: 87
Timestamp parse failures: 0
Non-positive timestamp deltas: 0
Gaps greater than 0.50s: 4
Largest timestamp gap: 46.718s
```

The timestamp gaps look like recording pauses or interruptions. They did not produce missing images, malformed rows, or duplicate frames.

### Verdict

Verdict: E2, valid but not ideal.

Session E is technically clean and left/right balanced, but it is not frozen as the final independent test set because near-zero steering is slightly high at 46.59% and strong-turn coverage is low at 9.72%.

### Decision

No training was run.

No model evaluation was run.

Session E should not be used for training, validation, hyperparameter tuning, crop selection, loss selection, architecture selection, or repeated model selection.

Recommended next data step: record a Session E2 candidate with less straight-only driving and at least 15% strong-turn coverage while keeping smooth representative driving and balanced left/right steering.

### Git Safety

Raw Session E images, raw `driving_log.csv`, generated screenshots, model checkpoints, and metrics JSON files remain ignored by Git.
