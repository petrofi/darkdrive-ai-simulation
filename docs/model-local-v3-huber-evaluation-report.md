# Local V3 Huber Loss Evaluation Report

This report documents EXP-008 - Huber Loss / SmoothL1Loss. The work is simulation-only. No simulator control, websocket driving loop, autonomous mode, real vehicle control, or public-road claim was added.

## Hypothesis

The baseline Local V3 model compresses steering magnitude and under-predicts medium and strong turns. MSE may over-penalize larger steering errors and encourage conservative predictions near the conditional mean. A Huber-style regression loss may improve robustness and reduce steering-magnitude compression.

## Controlled Variable

Only the regression loss changed:

| Field | Baseline Local V3 | EXP-008 |
| --- | --- | --- |
| Loss | `MSELoss` | `SmoothL1Loss` |
| Beta/delta | N/A | 1.0 |
| Preprocessing | `baseline` | `baseline` |

No crop, architecture change, optimizer change, learning-rate change, augmentation change, side-camera correction, or simulator control was added.

## Loss Implementation

`src/training/train_behavior_cloning.py` supports:

- `--loss mse`, the backward-compatible default.
- `--loss huber`, implemented as `torch.nn.SmoothL1Loss(beta=1.0)`.

Checkpoint metadata stores:

- loss name
- PyTorch loss class
- beta
- delta

Unsupported loss names fail with a clear `ValueError` in the training helper and are rejected by CLI choices.

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
| Architecture | `SteeringModel` |
| Parameters | 188219 |
| Optimizer | AdamW |
| Learning rate | 0.001 |
| Weight decay | 0.0001 |
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
C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe -m py_compile .\src\training\train_behavior_cloning.py .\scripts\evaluate_steering_model.py
C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe -m unittest discover -s tests
```

Result: `30 tests`, all passed.

Covered behavior includes:

- default loss is MSE
- `--loss huber` / `LOSS_HUBER` selects `SmoothL1Loss`
- unsupported loss names fail clearly
- Huber beta/delta is stored in checkpoint metadata
- explicit train/validation mode still avoids random splitting
- validation remains augmentation-free
- preprocessing defaults to `baseline`
- previous baseline paths remain backward-compatible

## Training Command

Interpreter:

```text
C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe
```

Command:

```powershell
& 'C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe' .\src\training\train_behavior_cloning.py --csv data\processed\local_v3_training\train.csv --train-csv data\processed\local_v3_training\train.csv --validation-csv data\processed\local_v3_training\validation.csv --format simple --epochs 15 --batch-size 32 --lr 0.001 --loss huber --preprocessing-profile baseline --device cpu --seed 42 --output models\steering_model_local_v3_huber.pt --chart-output screenshots\training_loss_local_v3_huber.png
```

## Training Results

| Metric | Value |
| --- | ---: |
| Training duration | 496.612 seconds |
| Best epoch | 7 |
| Best validation loss | 0.049741 |
| Final training loss | 0.056181 |
| Final validation loss | 0.052497 |
| Final training MAE | 0.238528 |
| Final validation MAE | 0.218696 |
| Checkpoint | `models/steering_model_local_v3_huber.pt` |

The checkpoint and training chart are generated local artifacts and remain ignored by Git.

## Session C2 Evaluation

Evaluation command:

```powershell
& 'C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe' .\scripts\evaluate_steering_model.py --model models\steering_model_local_v3_huber.pt --csv data\processed\local_v3_training\train.csv --validation-csv data\processed\local_v3_training\validation.csv --format simple --batch-size 64 --device cpu --seed 42 --metrics-json C:\tmp\darkdrive_exp008_huber_metrics.json
```

The evaluator used `baseline` preprocessing from checkpoint metadata.

| Metric | Value |
| --- | ---: |
| Sample count | 4163 |
| Overall MAE | 0.213646 |
| Overall RMSE | 0.320153 |
| Zero-steering baseline MAE | 0.214081 |
| Improvement over zero baseline | 0.000436 |
| Improvement over zero baseline | 0.20% |
| Near-zero MAE | 0.132261 |
| Near-zero count | 1720 |
| Left MAE | 0.265846 |
| Left count | 1258 |
| Right MAE | 0.276358 |
| Right count | 1185 |
| Strong-turn MAE | 0.575495 |
| Strong-turn count | 620 |
| Prediction mean | -0.029333 |
| Prediction std | 0.245478 |
| Actual mean | -0.017837 |
| Actual std | 0.347744 |
| Prediction/actual std ratio | 0.705915 |
| Signed bias, prediction minus actual | -0.011496 |
| Incorrect direction rate, abs(actual) > 0.05 | 17.44% |

Steering magnitude bins:

| abs(actual) bin | Count | MAE |
| --- | ---: | ---: |
| 0.00-0.05 | 1720 | 0.132261 |
| 0.05-0.25 | 1134 | 0.142138 |
| 0.25-0.50 | 689 | 0.208893 |
| 0.50-1.00 | 620 | 0.575495 |

## Controlled Comparison

Both rows use the same Local V3 train manifest, complete Session C2 validation manifest, baseline preprocessing, architecture, optimizer, learning rate, epochs, batch size, seed, and training-only augmentation. The intended difference is MSE versus Huber/SmoothL1Loss.

| Model | Loss | MAE | RMSE | Right MAE | Strong-Turn MAE | Std Ratio | Zero-Baseline Improvement | Direction Error |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `steering_model_local_v3.pt` | `MSELoss` | 0.215618 | 0.316627 | 0.249182 | 0.598862 | 0.656937 | -0.72% | 16.46% |
| `steering_model_local_v3_huber.pt` | `SmoothL1Loss(beta=1.0)` | 0.213646 | 0.320153 | 0.276358 | 0.575495 | 0.705915 | 0.20% | 17.44% |

Interpretation:

- Overall MAE improved by 0.001972.
- Zero-baseline improvement became slightly positive at 0.20%.
- Strong-turn MAE improved by 0.023367.
- Prediction/actual std ratio improved from 0.656937 to 0.705915.
- RMSE worsened by 0.003526.
- Right MAE regressed materially from 0.249182 to 0.276358.
- Direction error regressed from 16.46% to 17.44%.

## Secondary Historical Context

Road crop and Local V2 are secondary context only, not the primary controlled benchmark for EXP-008.

| Model | Context | MAE | RMSE | Caveat |
| --- | --- | ---: | ---: | --- |
| `steering_model_local_v3_crop_v1.pt` | EXP-007 preprocessing-only experiment | 0.215280 | 0.307111 | Uses different preprocessing, so not a loss-only comparison |
| `steering_model_local_v2.pt` | Merged Local V2 workflow | 0.193998 on Session C2 | 0.267838 on Session C2 | Session C2 contributed to Local V2 training data, so this is not an independent holdout result |

Local V2's Session C2 score is not considered an independent holdout result because Session C2 contributed to the Local V2 training dataset.

## Verdict

Verdict: **H2) Valid experiment, no meaningful improvement**.

Reasons:

- The Huber workflow is valid and reproducible.
- No split leakage was detected.
- Baseline preprocessing was used.
- MAE, strong-turn MAE, zero-baseline improvement, and prediction variance improved.
- RMSE, right MAE, and direction error regressed.
- The 0.20% zero-baseline improvement is too small to support release or simulator-control work.

No simulator control should be implemented from this result.

## Next Recommendation

Do not run another loss variant in this task.

Recommended next single-variable experiment: a slightly stronger CNN architecture on the same fixed Local V3 split, with baseline preprocessing and MSE or a deliberately chosen loss documented before training.
