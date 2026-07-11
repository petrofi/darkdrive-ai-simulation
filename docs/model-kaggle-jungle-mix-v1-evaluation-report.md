# Kaggle Jungle Mix V1 Model Evaluation Report

## Experiment

EXP-019 tests one hypothesis: adding the complete reviewed Kaggle Jungle center-camera candidate to Local V3 can improve curve and right-turn behavior without changing the baseline model or evaluation split.

The only intended variable is training data:

| Field | Local V3 baseline | EXP-019 |
| --- | --- | --- |
| Training CSV | `data/processed/local_v3_training/train.csv` | `data/processed/kaggle_jungle_mix_v1_training/train.csv` |
| Training rows | 10,657 | 14,061 |
| Kaggle Jungle rows | 0 | 3,404 |
| External share | 0% | 24.21% |

Both runs use the complete 4,163-row Session C2 validation manifest, baseline full-frame preprocessing, baseline `SteeringModel`, MSE loss, AdamW, learning rate 0.001, weight decay 0.0001, 15 epochs, batch size 32, seed 42, training-only augmentation, no validation augmentation, and CPU.

No road crop, Huber/SmoothL1 loss, `cnn_v2`, side-camera correction, Kaggle `make`, previous external Udacity data, Session E, Session E2, or validation rows were used for training.

## Kaggle Jungle Source And License Caveat

The external component is the complete 3,404-row `self_driving_car_dataset_jungle` center-camera manifest. It is 47.00% near-zero, 25.88% left, 27.12% right, and 26.38% strong turns. The K2 `self_driving_car_dataset_make` track is excluded.

Kaggle dataset-specific licensing remains unresolved. This experiment is local offline research only. The checkpoint is not approved for release, redistribution, commercial use, or a public training/deployment claim.

## Input And Leakage Verification

- Training rows: 14,061, including 10,657 Local V3 and 3,404 Jungle rows.
- Validation rows: 4,163, all `session_c2_right_recovery`.
- Missing/duplicate-path/invalid-label counts: 0 for both manifests.
- Train/validation image-path overlap: 0.
- Train/validation source-session overlap: 0.
- Session C2/E/E2 rows in training: 0.
- Kaggle `make` rows in training: 0.
- Training camera distribution: 14,061 center rows.

Session C2 has already influenced multiple model-selection decisions. It is a controlled comparison holdout, not a final independent benchmark.

## Exact Training Command

Interpreter:

```text
C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe
```

Command:

```powershell
& 'C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe' src\training\train_behavior_cloning.py --train-csv data\processed\kaggle_jungle_mix_v1_training\train.csv --validation-csv data\processed\local_v3_training\validation.csv --format simple --epochs 15 --batch-size 32 --lr 0.001 --weight-decay 0.0001 --loss mse --preprocessing-profile baseline --model-arch baseline --device cpu --num-workers 0 --seed 42 --augment --output models\steering_model_kaggle_jungle_mix_v1.pt --chart-output screenshots\training_loss_kaggle_jungle_mix_v1.png
```

Exactly one EXP-019 training run was executed.

## Training Configuration

| Field | Value |
| --- | --- |
| Architecture | `baseline` / `SteeringModel` |
| Parameters | 188,219 |
| Preprocessing | `baseline`, full frame resized to 160x80 |
| Loss | MSE / `MSELoss` |
| Optimizer | AdamW |
| Learning rate / weight decay | 0.001 / 0.0001 |
| Epochs / batch size | 15 / 32 |
| Seed | 42 |
| Device / workers | CPU / 0 |
| Training augmentation | Enabled |
| Validation augmentation | Disabled |
| Training sessions | `v1`, `session_a_normal`, `session_b_new_training`, `session_d_curve_focused`, `external_kaggle_jungle` |
| Validation session | `session_c2_right_recovery` |

## Training Results

| Metric | Value |
| --- | ---: |
| Duration | 493.691 seconds |
| Best epoch | 5 |
| Best validation loss | 0.095746 |
| Final training loss | 0.106595 |
| Final validation loss | 0.107738 |
| Final training MAE | 0.235268 |
| Final validation MAE | 0.222954 |
| Checkpoint | `models/steering_model_kaggle_jungle_mix_v1.pt` |
| Checkpoint size | 762,312 bytes |

The checkpoint stores the explicit manifests, baseline model/preprocessing metadata, MSE configuration, optimizer hyperparameters, seed, source sessions, row counts, best epoch/loss, parameter count, and complete 15-epoch history. No loss or MAE became NaN or infinite. The best epoch state was saved.

## Session C2 Evaluation

The checkpoint was evaluated once using its stored model and preprocessing metadata on `data/processed/local_v3_training/validation.csv`.

| Metric | Value |
| --- | ---: |
| Samples | 4,163 |
| MAE | 0.216064 |
| RMSE | 0.309429 |
| Zero-steering baseline MAE | 0.214081 |
| Improvement over zero baseline | -0.001982 / -0.93% |
| Near-zero MAE / count | 0.155438 / 1,720 |
| Left MAE / count | 0.274032 / 1,258 |
| Right MAE / count | 0.242521 / 1,185 |
| Strong-turn MAE / count | 0.559137 / 620 |
| Prediction mean / std | -0.015018 / 0.247250 |
| Actual mean / std | -0.017837 / 0.347744 |
| Prediction/actual std ratio | 0.711011 |
| Signed bias, prediction minus actual | 0.002819 |
| Incorrect direction | 395 / 2,443 / 16.17% |

Steering-magnitude bins:

| Absolute steering bin | Count | MAE | RMSE |
| --- | ---: | ---: | ---: |
| 0.00-0.05 | 1,720 | 0.155438 | 0.196378 |
| 0.05-0.25 | 1,134 | 0.141441 | 0.175075 |
| 0.25-0.50 | 689 | 0.181510 | 0.237161 |
| 0.50-1.00 | 620 | 0.559137 | 0.646016 |

Prediction variance remains compressed relative to actual steering, but the 0.711011 ratio is higher than the Local V3 baseline. Predictions neither collapsed near zero nor saturated near -1 or 1.

## Controlled Comparison

| Model | Training Data | Rows | MAE | RMSE | Right MAE | Strong-Turn MAE | Std Ratio | Zero-Baseline Improvement | Direction Error |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `steering_model_local_v3.pt` | Local V3 | 10,657 | 0.215618 | 0.316627 | 0.249182 | 0.598862 | 0.656937 | -0.72% | 16.46% |
| `steering_model_kaggle_jungle_mix_v1.pt` | Kaggle Jungle Mix V1 | 14,061 | 0.216064 | 0.309429 | 0.242521 | 0.559137 | 0.711011 | -0.93% | 16.17% |

Compared with Local V3:

- MAE regressed by 0.000446, about 0.21%.
- RMSE improved by 0.007198, about 2.27%.
- Right MAE improved by 0.006661, about 2.67%.
- Strong-turn MAE improved by 0.039724, about 6.63%.
- Prediction/actual std ratio improved by 0.054074.
- Direction error improved by 0.29 percentage points, with seven fewer wrong-direction predictions.
- Zero-baseline comparison regressed by 0.21 percentage points and remains negative.
- Near-zero MAE regressed from 0.139037 to 0.155438; left MAE improved from 0.288706 to 0.274032.

The result is mixed but useful: five of the seven primary KJM3 criteria improved, including the curve/right-turn targets, while overall MAE and the zero-baseline comparison regressed slightly.

## Secondary Context

| Model | Change | MAE | RMSE | Right MAE | Strong MAE | Std Ratio | Zero Improvement | Direction Error |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Local V3 `crop_v1` | Preprocessing | 0.215280 | 0.307111 | 0.249969 | 0.574012 | 0.670205 | -0.56% | 16.00% |
| Local V3 Huber | Loss | 0.213646 | 0.320153 | 0.276358 | 0.575495 | 0.705915 | +0.20% | 17.44% |
| Local V3 `cnn_v2` | Architecture | 0.217054 | 0.313915 | 0.261968 | 0.612222 | 0.599089 | -1.39% | 19.03% |
| External Mix V1 | Prior data mix | 0.216895 | 0.319567 | 0.251651 | 0.579000 | 0.700562 | -1.31% | 17.11% |

These are secondary context, not the primary benchmark. Local V2 reported lower Session C2 error historically, but that comparison is contaminated because Session C2 contributed to Local V2 training.

## Limitations

- Session C2 is repeatedly reused and is not a final independent test set.
- One seeded run does not measure training variance.
- Overall MAE still fails to beat the zero-steering baseline.
- Near-zero error regressed and steering variance remains compressed.
- Kaggle licensing remains unresolved, blocking release or redistribution.
- No temporal stability or closed-loop simulator behavior was measured.

## Verdict

**KJM3 — Useful Kaggle Jungle improvement.**

The workflow is valid and leakage-free. RMSE, right MAE, strong-turn MAE, prediction variance, and direction error improved without changing the baseline configuration. The slight MAE and zero-baseline regressions prevent KJM4 and prevent model promotion.

The checkpoint is retained only as an ignored local offline research artifact. It is not promoted or released.

## Exact Next Recommendation

Collect and validate Session E2 as the independent test candidate before making any further model-selection or Kaggle-training decision.

No simulator control was implemented.
