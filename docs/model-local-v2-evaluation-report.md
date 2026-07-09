# Local V2 Model Evaluation Report

This report documents the offline training and evaluation of the local Dataset v2 behavior-cloning model.

## Scope

The model is a simulation-only steering predictor. It is not real vehicle control code, and closed-loop simulator control was not implemented in this task.

## Architecture

Model: `src.models.steering_model.SteeringModel`

Architecture summary:

- Compact PyTorch CNN.
- RGB image input resized to 160x80.
- Five convolution blocks with ELU activations.
- Adaptive average pooling.
- Fully connected steering regressor with dropout.
- One continuous steering output.

## Training Command

```powershell
python src/training/train_behavior_cloning.py --csv data/processed/local_v2_training/driving_log.csv --format simple --images-dir data/processed/local_v2_training --epochs 15 --batch-size 32 --seed 42 --output models/steering_model_local_v2.pt --chart-output screenshots/training_loss_local_v2.png
```

## Training Settings

| Setting | Value |
| --- | --- |
| Dataset | `data/processed/local_v2_training/driving_log.csv` |
| Format | `simple` |
| Usable rows | 8647 |
| Training rows | 6918 |
| Validation rows | 1729 |
| Validation split | 20%, deterministic random row split |
| Epochs | 15 |
| Batch size | 32 |
| Learning rate | 0.001 |
| Weight decay | 0.0001 |
| Loss | MSE |
| Random seed | 42 |
| Device | CPU |
| Augmentation | On: horizontal flip with steering sign flip, brightness/contrast, shadow |
| Checkpoint | `models/steering_model_local_v2.pt` |
| Training chart | `screenshots/training_loss_local_v2.png` |

## Training Results

| Metric | Value |
| --- | ---: |
| Best epoch | 15 |
| Best validation loss | 0.092040 |
| Final training loss | 0.080739 |
| Final validation loss | 0.092040 |
| Final training MAE | 0.1948 |
| Final validation MAE | 0.2113 |

The best checkpoint was saved based on validation loss.

## Evaluation Command

```powershell
python scripts/evaluate_steering_model.py --model models/steering_model_local_v2.pt --csv data/processed/local_v2_training/driving_log.csv --images-dir data/processed/local_v2_training --format simple --batch-size 64 --validation-split 0.2 --device auto --seed 42
```

## Evaluation Results

| Metric | Value |
| --- | ---: |
| Rows evaluated | 1729 |
| MAE | 0.211307 |
| RMSE | 0.303382 |
| Zero-steering baseline MAE | 0.261022 |
| MAE improvement over zero baseline | 0.049715 |
| MAE improvement over zero baseline | 19.05% |
| Prediction mean | -0.047240 |
| Prediction std | 0.292377 |
| Actual steering mean | -0.021182 |
| Actual steering std | 0.401228 |

Generated evaluation artifacts:

```text
screenshots/prediction_vs_actual_local_v2.png
screenshots/prediction_samples_local_v2.png
```

## Segment Error Analysis

| Segment | Samples | MAE | RMSE | Actual mean | Prediction mean |
| --- | ---: | ---: | ---: | ---: | ---: |
| Near-zero, `abs <= 0.05` | 576 | 0.137285 | 0.180750 | 0.000422 | -0.048094 |
| Left, `< -0.05` | 613 | 0.240932 | 0.336345 | -0.396553 | -0.263215 |
| Right, `> 0.05` | 540 | 0.256633 | 0.362533 | 0.381889 | 0.198843 |
| Strong turns, `abs >= 0.5` | 348 | 0.469480 | 0.554691 | -0.064504 | -0.069259 |

The model under-predicts turn magnitude. Right-steering and strong-turn errors are too high for a release candidate.

## Source/Session Metrics

Note: `session_c2_right_recovery` contributed to the Local V2 training dataset. Metrics for that session in this report are not independent holdout metrics; they are historical random-split diagnostics only.

| Source/session | Samples | MAE | RMSE |
| --- | ---: | ---: | ---: |
| `local_simulator_v1` | 568 | 0.198192 | 0.275037 |
| `local_simulator_v2` | 1161 | 0.217723 | 0.316325 |
| `v1` | 568 | 0.198192 | 0.275037 |
| `session_a_normal` | 351 | 0.237513 | 0.371981 |
| `session_b_new_training` | 166 | 0.176902 | 0.228539 |
| `session_c2_right_recovery` | 644 | 0.217460 | 0.302509 |

## Comparison Against V1

Recorded Dataset v1/model v1 metrics:

| Metric | V1 | Local V2 |
| --- | ---: | ---: |
| Best validation loss | 0.060776 | 0.092040 |
| MAE | 0.174045 | 0.211307 |
| RMSE | 0.246529 | 0.303382 |

The local v2 model did not improve over v1. The dataset distribution improved, but the trained model's offline error worsened.

## Leakage Consideration

The current training/evaluation pipeline uses a deterministic random row split. Adjacent simulator frames may appear across train and validation sets, which can make validation optimistic. Even with that limitation, the local v2 model underperforms v1, so it should not be promoted.

## Release Recommendation

Final verdict: **R1) Not ready**.

Reasons:

- MAE and RMSE are worse than v1.
- Best validation loss is worse than v1.
- Right-turn and strong-turn prediction errors remain high.
- The model under-predicts steering magnitude.
- Closed-loop simulator control is not implemented and should not be added from this result.

Recommended next step: collect Session D curve-focused data.
