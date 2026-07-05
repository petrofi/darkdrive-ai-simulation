# Local V3 Model Evaluation Report

This report documents the first Local V3 session-aware training run and Session C2 holdout evaluation. The work is simulation-only. No simulator control, websocket driving loop, autonomous mode, or real vehicle control was added.

## Experiment Objective

Hypothesis: training on the session-aware Local V3 manifest should improve steering magnitude, right-steering, and strong-turn prediction compared with Local V2, while evaluating on a complete Session C2 holdout with no adjacent-frame random split leakage.

Result: the pipeline worked, but the model result did not improve over Local V2 on the fair Session C2 holdout.

Release verdict: **R2) Valid offline experiment, not promoted**.

## Python Environment

`python` was not available on PATH in this Codex PowerShell session. Training and evaluation used the project virtual environment:

```text
C:\Users\tarik\OneDrive\Ekler\Desktop\darkdrive-ai-simulation\.venv\Scripts\python.exe
```

Verified packages:

| Package | Version |
| --- | --- |
| Python | 3.13.14 |
| pip | 26.1.2 |
| PyTorch | 2.12.0+cpu |
| OpenCV | 4.13.0 |
| pandas | 3.0.3 |
| NumPy | 2.4.6 |

Device used: CPU.

## Code Changes

Trainer changes:

- Added `--train-csv` and `--validation-csv` explicit manifest support.
- Kept the existing single `--csv` random-split workflow for backward compatibility.
- Explicit mode fails if only one manifest is supplied.
- Explicit mode validates missing images, invalid labels, empty manifests, image-path overlap, and `source_session` overlap before training.
- Validation rows are never augmented.
- Checkpoints now include explicit manifest paths, row counts, source-session lists, seed, batch size, learning rate, augmentation setting, architecture name, parameter count, best epoch, and best validation loss.

Evaluator changes:

- Added `--validation-csv` explicit evaluation mode with no random split.
- Added overall MAE/RMSE, zero-baseline MAE, subgroup metrics, steering-bin metrics, prediction/actual standard deviations, signed bias, direction error, and `source_session` aggregation.
- Added ignored JSON metrics output support.
- Added Local V3 artifact naming so fair comparisons do not overwrite each other.

## Dataset Split

Training manifest:

```text
data/processed/local_v3_training/train.csv
```

Validation manifest:

```text
data/processed/local_v3_training/validation.csv
```

Training rows: 10657.

Training source sessions:

- `v1`: 2360 rows.
- `session_a_normal`: 1460 rows.
- `session_b_new_training`: 720 rows.
- `session_d_curve_focused`: 6117 rows.

Validation rows: 4163.

Validation source session:

- `session_c2_right_recovery`: 4163 rows.

Strict split checks:

| Check | Result |
| --- | ---: |
| Train/validation image-path overlap | 0 |
| Train/validation `source_session` overlap | 0 |
| Missing images | 0 |
| Invalid steering labels | 0 |
| Validation augmentation | Disabled |

## Model Architecture

Model: `src.models.steering_model.SteeringModel`.

| Property | Value |
| --- | --- |
| Input image size | 160x80 RGB |
| Trainable parameters | 188219 |
| Convolution stack | 5 conv layers: 24, 36, 48, 64, 64 channels |
| Activations | ELU |
| Pooling | Adaptive average pooling to 2x4 |
| Regressor | Dropout MLP: 512 -> 100 -> 50 -> 10 -> 1 |
| Output activation | None |
| Output clipping | None |

The model was intentionally not replaced. This isolates the effect of the Local V3 data and explicit split before testing a new architecture.

Likely under-prediction causes remain:

- MSE regression rewards conservative predictions near the conditional mean.
- The compact CNN may discard spatial detail through aggressive downsampling and adaptive pooling.
- Center-camera-only data lacks side-camera recovery labels.
- Session C2 has right-recovery behavior that may not be sufficiently matched by the V3 training distribution.

## Training Configuration

Command:

```powershell
.\.venv\Scripts\python.exe src/training/train_behavior_cloning.py --train-csv data/processed/local_v3_training/train.csv --validation-csv data/processed/local_v3_training/validation.csv --format simple --epochs 15 --batch-size 32 --seed 42 --output models/steering_model_local_v3.pt --chart-output screenshots/training_loss_local_v3.png
```

| Setting | Value |
| --- | --- |
| Epochs | 15 |
| Batch size | 32 |
| Learning rate | 0.001 |
| Weight decay | 0.0001 |
| Loss | MSE |
| Augmentation | On for training only |
| Validation augmentation | Off |
| Seed | 42 |
| Device | CPU |
| Training duration | 432.77 seconds |
| Checkpoint | `models/steering_model_local_v3.pt` |
| Loss chart | `screenshots/training_loss_local_v3.png` |

The checkpoint and chart are generated local artifacts and remain ignored by Git.

## Training Results

| Metric | Value |
| --- | ---: |
| Best epoch | 3 |
| Best validation loss | 0.100252 |
| Final training loss | 0.111446 |
| Final validation loss | 0.113804 |
| Final training MAE | 0.238593 |
| Final validation MAE | 0.221872 |

Validation loss improved through epoch 3, then fluctuated and ended worse than the best checkpoint. The saved checkpoint uses the best validation-loss weights from epoch 3.

## Session C2 Evaluation

Primary evaluation command:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_steering_model.py --model models/steering_model_local_v3.pt --csv data/processed/local_v3_training/validation.csv --validation-csv data/processed/local_v3_training/validation.csv --format simple --batch-size 64 --device cpu --seed 42 --metrics-json screenshots/evaluation_metrics_local_v3.json
```

Overall result on the complete Session C2 validation holdout:

| Metric | Value |
| --- | ---: |
| Rows evaluated | 4163 |
| MAE | 0.215618 |
| RMSE | 0.316627 |
| Zero-steering baseline MAE | 0.214081 |
| MAE improvement over zero baseline | -0.001536 |
| MAE improvement over zero baseline | -0.72% |
| Prediction mean | -0.000800 |
| Prediction std | 0.228446 |
| Actual mean | -0.017837 |
| Actual std | 0.347744 |
| Prediction/actual std ratio | 0.656937 |
| Signed bias, mean prediction minus actual | 0.017037 |
| Incorrect direction, abs(actual) > 0.05 | 16.46% |

Subgroup metrics:

| Segment | Count | MAE | RMSE |
| --- | ---: | ---: | ---: |
| Near-zero, `abs <= 0.05` | 1720 | 0.139037 | 0.177763 |
| Left, `< -0.05` | 1258 | 0.288706 | 0.415585 |
| Right, `> 0.05` | 1185 | 0.249182 | 0.350682 |
| Strong turns, `abs >= 0.5` | 620 | 0.598862 | 0.681756 |

Steering magnitude bins:

| abs(actual) bin | Count | MAE |
| --- | ---: | ---: |
| 0.00-0.05 | 1720 | 0.139037 |
| 0.05-0.25 | 1134 | 0.130846 |
| 0.25-0.50 | 689 | 0.201450 |
| 0.50-1.00 | 620 | 0.598862 |

Source-session metrics:

| Source session | Count | MAE | RMSE |
| --- | ---: | ---: | ---: |
| `session_c2_right_recovery` | 4163 | 0.215618 | 0.316627 |

## Fair Session C2 Comparison

All three checkpoints were evaluated on the exact same Local V3 Session C2 validation manifest.

| Model | MAE | RMSE | Near-zero MAE | Left MAE | Right MAE | Strong-turn MAE | Prediction std | Direction error | Verdict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `steering_model_sim_v1.pt` | 0.225056 | 0.332471 | 0.146287 | 0.284477 | 0.276305 | 0.615606 | 0.234684 | 19.85% | Worse than Local V2 and Local V3 on C2 |
| `steering_model_local_v2.pt` | 0.193998 | 0.267838 | 0.146422 | 0.233108 | 0.221535 | 0.444943 | 0.267542 | 12.03% | Best C2 holdout result |
| `steering_model_local_v3.pt` | 0.215618 | 0.316627 | 0.139037 | 0.288706 | 0.249182 | 0.598862 | 0.228446 | 16.46% | Valid but not promoted |

Interpretation:

- Local V3 improves over v1 on C2 MAE/RMSE, but only modestly.
- Local V3 is worse than Local V2 on C2 MAE, RMSE, left MAE, right MAE, strong-turn MAE, prediction std, and direction error.
- Local V3 has the best near-zero MAE, but that is not the core failure mode.
- Local V3 does not beat the zero-steering baseline on Session C2.
- Prediction standard deviation remains compressed at 65.69% of actual steering std.

## Historical Comparison Limitation

The earlier v1 and Local V2 headline metrics came from different random split conditions:

| Model | Historical MAE | Historical RMSE | Historical validation loss |
| --- | ---: | ---: | ---: |
| V1 | 0.174045 | 0.246529 | 0.060776 |
| Local V2 | 0.211307 | 0.303382 | 0.092040 |
| Local V3 | 0.215618 on Session C2 | 0.316627 on Session C2 | 0.100252 |

Those historical numbers are not perfectly apples-to-apples with Local V3 because Local V3 uses a complete held-out session. The fair comparison is the Session C2 table above.

## Release Verdict

Verdict: **R2) Valid offline experiment, not promoted**.

Reasons:

- Explicit session-aware training and evaluation work correctly.
- The complete Session C2 holdout evaluation is valid and leakage-safe.
- Local V3 does not improve over Local V2 on the fair Session C2 holdout.
- Local V3 does not beat the zero-steering baseline on MAE.
- Strong-turn error is high at 0.598862.
- Prediction variance remains compressed.
- Temporal stability has not been measured.

Simulator control remains blocked.

## Generated Artifacts

Ignored model and evaluation artifacts:

```text
models/steering_model_local_v3.pt
screenshots/training_loss_local_v3.png
screenshots/prediction_vs_actual_local_v3.png
screenshots/prediction_samples_local_v3.png
screenshots/error_by_steering_bin_local_v3.png
screenshots/evaluation_metrics_local_v3.json
screenshots/evaluation_metrics_sim_v1_on_local_v3.json
screenshots/evaluation_metrics_local_v2_on_local_v3.json
```

## Next Recommendation

Do not tune repeatedly on Session C2. Treat Session C2 as validation.

Recommended next task:

1. Review Local V3 prediction samples and strong-turn failures.
2. Add image crop/normalization or a slightly stronger architecture as a separate controlled experiment on the same fixed Local V3 split.
3. Consider a Huber-loss run only as a clearly separate experiment.
4. Collect a new untouched Session E later for final testing.
