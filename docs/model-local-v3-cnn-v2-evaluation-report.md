# Local V3 CNN V2 Architecture Evaluation Report

This report documents EXP-009 - Slightly Stronger CNN Architecture. The work is simulation-only. No simulator control, websocket driving loop, autonomous mode, real vehicle control, or public-road claim was added.

## Hypothesis

The baseline Local V3 model compresses steering magnitude and under-predicts medium and strong turns. A slightly stronger single-frame CNN may learn richer curve geometry and improve steering magnitude without changing the dataset, preprocessing, loss, optimizer, or validation split.

## Architecture Review

Baseline `SteeringModel`:

- Input: RGB tensor shaped `[batch, 3, height, width]`, with the training pipeline using 80 x 160 images.
- Internal normalization: pixels from `[0, 1]` to `[-1, 1]`.
- Convolution stack: `3->24` 5x5 stride 2, `24->36` 5x5 stride 2, `36->48` 5x5 stride 2, `48->64` 3x3 stride 1, `64->64` 3x3 stride 1.
- Activations: ELU.
- Pooling: `AdaptiveAvgPool2d((2, 4))`.
- MLP head: flatten, dropout 0.2, `512->100->50->10->1`.
- Output: one unconstrained scalar steering value.
- Parameters: 188219.

## CNN V2 Definition

`cnn_v2` is implemented as `SteeringModelV2` in `src/models/steering_model.py`.

- Input contract: same RGB tensor and image size as baseline.
- Internal normalization: same `[0, 1]` to `[-1, 1]` centering as baseline.
- Convolution stack:
  - `3->32` 5x5 stride 2, BatchNorm2d, ELU
  - `32->48` 5x5 stride 2, BatchNorm2d, ELU
  - `48->64` 5x5 stride 2, BatchNorm2d, ELU
  - `64->96` 3x3 stride 1 padding 1, BatchNorm2d, ELU
  - `96->128` 3x3 stride 1 padding 1, BatchNorm2d, ELU
  - `128->128` 3x3 stride 1 padding 1, BatchNorm2d, ELU
- Pooling: `AdaptiveAvgPool2d((2, 4))`.
- MLP head: flatten, dropout 0.25, `1024->256->100->50->10->1`.
- Output: one unconstrained scalar steering value.
- Parameters: 726103.

The architecture remains lightweight enough for CPU-only offline training and stays within the requested 400k to 1.5M parameter range.

## Controlled Variable

Only the model architecture changed:

| Field | Local V3 Baseline | EXP-009 |
| --- | --- | --- |
| Architecture | `SteeringModel` | `SteeringModelV2` / `cnn_v2` |
| Parameters | 188219 | 726103 |
| Preprocessing | `baseline` | `baseline` |
| Loss | `MSELoss` | `MSELoss` |

No road crop, Huber loss, dataset change, split change, side-camera correction, temporal model, or simulator control was added.

## Model Selection Implementation

Training now supports:

- `--model-arch baseline`, the backward-compatible default.
- `--model-arch cnn_v2`, the new stronger CNN.

Checkpoint metadata stores:

- `model_arch`
- `model_class`
- `model_architecture`
- `parameter_count`

The evaluator and single-image inference path read `model_arch` from checkpoint metadata by default. Older checkpoints without `model_arch` safely default to the baseline architecture.

## Train And Validation Split

Training:

- Rows: 10657.
- Source sessions: `v1`, `session_a_normal`, `session_b_new_training`, `session_d_curve_focused`.

Validation:

- Rows: 4163.
- Source session: complete `session_c2_right_recovery`.

Leakage checks:

| Check | Result |
| --- | ---: |
| Source-session overlap | 0 |
| Image-path overlap | 0 |

Session C2 was not included in Local V3 training.

## Controlled Variables

| Variable | Value |
| --- | --- |
| Train CSV | `data/processed/local_v3_training/train.csv` |
| Validation CSV | `data/processed/local_v3_training/validation.csv` |
| Architecture | `cnn_v2` / `SteeringModelV2` |
| Parameters | 726103 |
| Optimizer | AdamW |
| Learning rate | 0.001 |
| Weight decay | 0.0001 |
| Loss | `MSELoss` |
| Epochs | 15 |
| Batch size | 32 |
| Seed | 42 |
| Augmentation | Existing training-only flip, brightness/contrast, shadow |
| Validation augmentation | Off |
| Preprocessing profile | `baseline` |
| Device | CPU |

## Tests

Validation run:

```powershell
C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe -m py_compile .\src\models\steering_model.py .\src\training\train_behavior_cloning.py .\scripts\evaluate_steering_model.py .\src\inference\predict_steering.py .\tests\test_model_architecture.py
C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe -m unittest discover -s tests
```

Result: `37 tests`, all passed.

Covered behavior includes:

- baseline model still instantiates
- `cnn_v2` model instantiates
- both architectures accept the same input shape and return `[batch, 1]`
- `cnn_v2` parameter count is larger than baseline and still lightweight
- unsupported model architectures fail clearly
- checkpoint metadata stores `model_arch`
- evaluator loads baseline and `cnn_v2` checkpoints
- explicit train/validation mode remains isolated
- default loss remains MSE
- preprocessing default remains baseline

## Training Command

Interpreter:

```text
C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe
```

Command:

```powershell
& 'C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe' .\src\training\train_behavior_cloning.py --csv data\processed\local_v3_training\train.csv --train-csv data\processed\local_v3_training\train.csv --validation-csv data\processed\local_v3_training\validation.csv --format simple --epochs 15 --batch-size 32 --lr 0.001 --loss mse --preprocessing-profile baseline --model-arch cnn_v2 --device cpu --seed 42 --output models\steering_model_local_v3_cnn_v2.pt --chart-output screenshots\training_loss_local_v3_cnn_v2.png
```

## Training Results

| Metric | Value |
| --- | ---: |
| Observed command wall time | 634.1 seconds |
| Best epoch | 5 |
| Best validation loss | 0.098543 |
| Final training loss | 0.127928 |
| Final validation loss | 0.119668 |
| Final training MAE | 0.256503 |
| Final validation MAE | 0.229572 |
| Checkpoint | `models/steering_model_local_v3_cnn_v2.pt` |

The checkpoint and generated charts are local artifacts and remain ignored by Git.

## Session C2 Evaluation

Evaluation command:

```powershell
& 'C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe' .\scripts\evaluate_steering_model.py --model models\steering_model_local_v3_cnn_v2.pt --csv data\processed\local_v3_training\train.csv --validation-csv data\processed\local_v3_training\validation.csv --format simple --batch-size 64 --device cpu --seed 42 --metrics-json C:\tmp\darkdrive_exp009_cnn_v2_metrics.json
```

The evaluator used `cnn_v2` architecture and `baseline` preprocessing from checkpoint metadata.

| Metric | Value |
| --- | ---: |
| Sample count | 4163 |
| Overall MAE | 0.217054 |
| Overall RMSE | 0.313915 |
| Zero-steering baseline MAE | 0.214081 |
| Improvement over zero baseline | -0.002973 |
| Improvement over zero baseline | -1.39% |
| Near-zero MAE | 0.136335 |
| Near-zero count | 1720 |
| Left MAE | 0.285110 |
| Left count | 1258 |
| Right MAE | 0.261968 |
| Right count | 1185 |
| Strong-turn MAE | 0.612222 |
| Strong-turn count | 620 |
| Prediction mean | -0.011571 |
| Prediction std | 0.208329 |
| Actual mean | -0.017837 |
| Actual std | 0.347744 |
| Prediction/actual std ratio | 0.599089 |
| Signed bias, prediction minus actual | 0.006266 |
| Incorrect direction rate, abs(actual) > 0.05 | 19.03% |

Steering magnitude bins:

| abs(actual) bin | Count | MAE |
| --- | ---: | ---: |
| 0.00-0.05 | 1720 | 0.136335 |
| 0.05-0.25 | 1134 | 0.130032 |
| 0.25-0.50 | 689 | 0.206193 |
| 0.50-1.00 | 620 | 0.612222 |

## Controlled Comparison

Both rows use the same Local V3 train manifest, complete Session C2 validation manifest, baseline preprocessing, MSE loss, AdamW optimizer, learning rate, epochs, batch size, seed, and training-only augmentation. The intended difference is baseline architecture versus `cnn_v2`.

| Model | Architecture | Params | MAE | RMSE | Right MAE | Strong-Turn MAE | Std Ratio | Zero-Baseline Improvement | Direction Error |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `steering_model_local_v3.pt` | `baseline` / `SteeringModel` | 188219 | 0.215618 | 0.316627 | 0.249182 | 0.598862 | 0.656937 | -0.72% | 16.46% |
| `steering_model_local_v3_cnn_v2.pt` | `cnn_v2` / `SteeringModelV2` | 726103 | 0.217054 | 0.313915 | 0.261968 | 0.612222 | 0.599089 | -1.39% | 19.03% |

Interpretation:

- RMSE improved by 0.002712.
- Overall MAE regressed by 0.001436.
- Right MAE regressed by 0.012786.
- Strong-turn MAE regressed by 0.013360.
- Prediction/actual std ratio dropped from 0.656937 to 0.599089, meaning steering magnitude compression worsened.
- Zero-baseline comparison worsened from -0.72% to -1.39%.
- Direction error regressed from 16.46% to 19.03%.

## Secondary Historical Context

Road crop, Huber, and Local V2 are secondary context only, not the primary controlled benchmark for EXP-009.

| Model | Context | MAE | RMSE | Caveat |
| --- | --- | ---: | ---: | --- |
| `steering_model_local_v3_crop_v1.pt` | EXP-007 preprocessing-only experiment | 0.215280 | 0.307111 | Uses different preprocessing, so not an architecture-only comparison |
| `steering_model_local_v3_huber.pt` | EXP-008 loss-only experiment | 0.213646 | 0.320153 | Uses different loss, so not an architecture-only comparison |
| `steering_model_local_v2.pt` | Merged Local V2 workflow | 0.193998 on Session C2 | 0.267838 on Session C2 | Session C2 contributed to Local V2 training data, so this is not an independent holdout result |

Local V2's Session C2 score is not considered an independent holdout result because Session C2 contributed to the Local V2 training dataset.

## Verdict

Verdict: **A2) Valid experiment, no meaningful improvement**.

Reasons:

- The model architecture implementation, metadata path, evaluator loading path, and inference loading path are valid.
- The run used the fixed Local V3 split with no source-session or image-path leakage.
- Baseline preprocessing and MSE loss were preserved.
- The checkpoint was written and evaluated successfully.
- RMSE improved slightly, but MAE, right MAE, strong-turn MAE, std ratio, zero-baseline improvement, and direction error all regressed.
- The stronger CNN did not solve steering-magnitude compression and is not a release/control candidate.

No simulator control should be implemented from this result.

## Next Recommendation

Do not run another architecture experiment against Session C2 in this task.

Recommended next single step: collect an independent Session E test set and freeze it before further model-selection work. The Local V3 Session C2 holdout has now been used for baseline, crop, Huber, and CNN architecture decisions, so continuing to tune against it risks overfitting experiment choices to that holdout.
