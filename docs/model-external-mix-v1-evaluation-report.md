# External Mix V1 Model Evaluation Report

This report documents EXP-014, a simulation-only controlled training experiment. No real vehicle control, websocket driving loop, closed-loop simulator control, or autonomous-driving claim was added.

## Hypothesis

A capped, direction-balanced subset of the public Udacity behavioral-cloning dataset may add visual diversity to Local V3 while preserving enough curve-rich internal data to improve offline steering prediction on the complete Session C2 validation manifest.

## Controlled Variable

Only the training manifest changed:

| Field | Local V3 baseline | EXP-014 External Mix V1 |
| --- | --- | --- |
| Training CSV | `data/processed/local_v3_training/train.csv` | `data/processed/external_mix_v1_training/train.csv` |
| Training rows | 10,657 | 13,657 |
| External rows | 0 | 3,000, or 21.97% |

Both runs used the same complete Session C2 validation manifest, baseline full-frame preprocessing, baseline `SteeringModel`, MSE loss, AdamW optimizer, learning rate, weight decay, epochs, batch size, seed, training-only augmentation, validation policy, and CPU device.

The experiment did not use `road_crop_v1`, Huber/SmoothL1Loss, `cnn_v2`, side-camera steering offsets, Session E, Session E2, or validation rows for training.

## External Subset

External Mix V1 preserves all 10,657 Local V3 training rows and adds a deterministic center-camera-only subset of `udacity_behavioral_cloning_public`:

- Seed: 42
- Near-zero: 750 rows
- Left: 1,125 rows
- Right: 1,125 rows
- Strong turns: all 44 available external strong-turn rows
- Oversampling: none
- Side-camera steering offsets: none

The complete 13,657-row training candidate is 27.91% near-zero, 36.22% left, 35.87% right, and 21.55% strong turns. The source external dataset remains weak on strong turns: only 0.55% before sampling and 1.47% in the selected subset.

## Input And Leakage Validation

| Check | Result |
| --- | ---: |
| Training rows | 13,657 |
| Internal / external rows | 10,657 / 3,000 |
| Validation rows | 4,163 |
| Validation source | `session_c2_right_recovery` only |
| Missing training / validation images | 0 / 0 |
| Duplicate training / validation image paths | 0 / 0 |
| Invalid or out-of-range labels | 0 |
| Training/validation image-path overlap | 0 |
| Training/validation source-session overlap | 0 |
| Session C2 training rows | 0 |
| Session E/E2 training rows | 0 |

Session C2 is a repeatedly used validation holdout, not an untouched final test set. Session E was not frozen, and Session E2 was not used.

## Pre-Training Tests

The exact trainer and evaluator compiled successfully. The complete repository test suite passed 57 tests before training.

## Training Configuration

| Variable | Value |
| --- | --- |
| Interpreter | `C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe` |
| Training CSV | `data/processed/external_mix_v1_training/train.csv` |
| Validation CSV | `data/processed/local_v3_training/validation.csv` |
| Dataset format | `simple` |
| Architecture | `baseline` / `SteeringModel` |
| Parameters | 188,219 |
| Preprocessing | `baseline`, full frame resized to 160x80 |
| Loss | `MSELoss` |
| Optimizer | AdamW |
| Learning rate | 0.001 |
| Weight decay | 0.0001 |
| Epochs | 15 |
| Batch size | 32 |
| Seed | 42 |
| Training augmentation | Existing flip, brightness/contrast, and shadow pipeline enabled |
| Validation augmentation | Disabled |
| Device | CPU |

Exact command:

```powershell
& 'C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe' src/training/train_behavior_cloning.py --train-csv data/processed/external_mix_v1_training/train.csv --validation-csv data/processed/local_v3_training/validation.csv --format simple --epochs 15 --batch-size 32 --lr 0.001 --weight-decay 0.0001 --seed 42 --loss mse --preprocessing-profile baseline --model-arch baseline --augment --device cpu --output models/steering_model_external_mix_v1.pt --chart-output screenshots/training_loss_external_mix_v1.png
```

Exactly one training command was run.

## Training Results

| Metric | Value |
| --- | ---: |
| Wall-clock duration | 616.520 seconds |
| Best epoch | 3 |
| Best validation loss | 0.102123 |
| Final training loss | 0.089346 |
| Final validation loss | 0.106086 |
| Final training MAE | 0.205349 |
| Final validation MAE | 0.218132 |
| Checkpoint | `models/steering_model_external_mix_v1.pt` |
| Loss chart | `screenshots/training_loss_external_mix_v1.png` |

The saved checkpoint contains the best epoch-3 state, not the final epoch-15 state. All recorded training and validation loss/MAE values were finite. No source rows were skipped, the validation set was non-empty, and the checkpoint was written without replacing an existing model.

## Session C2 Evaluation

The new checkpoint was evaluated once against the explicit validation manifest, using its stored baseline architecture and preprocessing metadata.

```powershell
& 'C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe' scripts/evaluate_steering_model.py --model models/steering_model_external_mix_v1.pt --csv data/processed/local_v3_training/validation.csv --validation-csv data/processed/local_v3_training/validation.csv --format simple --batch-size 64 --device cpu --seed 42 --preprocessing-profile checkpoint --model-arch checkpoint --metrics-json screenshots/evaluation_metrics_external_mix_v1.json
```

| Metric | Value |
| --- | ---: |
| Sample count | 4,163 |
| Overall MAE | 0.216895 |
| Overall RMSE | 0.319567 |
| Zero-steering baseline MAE | 0.214081 |
| Improvement over zero baseline | -0.002813 / -1.31% |
| Near-zero MAE / count | 0.137197 / 1,720 |
| Left MAE / count | 0.293121 / 1,258 |
| Right MAE / count | 0.251651 / 1,185 |
| Strong-turn MAE / count | 0.579000 / 620 |
| Prediction mean / std | 0.024110 / 0.243616 |
| Actual mean / std | -0.017837 / 0.347744 |
| Prediction/actual std ratio | 0.700562 |
| Signed bias, prediction minus actual | 0.041946 |
| Incorrect direction | 418 / 2,443, or 17.11% |

MAE by steering-magnitude bin:

| `abs(actual)` bin | Count | MAE |
| --- | ---: | ---: |
| 0.00-0.05 | 1,720 | 0.137197 |
| 0.05-0.25 | 1,134 | 0.143292 |
| 0.25-0.50 | 689 | 0.211146 |
| 0.50-1.00 | 620 | 0.579000 |

The prediction standard deviation and 0.700562 variance ratio do not indicate a near-zero prediction collapse. The evaluation remained an offline frame-level test and provides no evidence of closed-loop stability.

## Primary Controlled Comparison

| Model | Training Data | Rows | MAE | RMSE | Right MAE | Strong-Turn MAE | Std Ratio | Zero-Baseline Improvement | Direction Error |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `steering_model_local_v3.pt` | Local V3 | 10,657 | 0.215618 | 0.316627 | 0.249182 | 0.598862 | 0.656937 | -0.72% | 16.46% |
| `steering_model_external_mix_v1.pt` | External Mix V1 | 13,657 | 0.216895 | 0.319567 | 0.251651 | 0.579000 | 0.700562 | -1.31% | 17.11% |

Compared with the Local V3 baseline:

- Overall MAE regressed by 0.001277.
- RMSE regressed by 0.002940.
- Right MAE regressed by 0.002469.
- Direction error regressed by 0.65 percentage points.
- Zero-baseline comparison worsened by 0.59 percentage points.
- Strong-turn MAE improved by 0.019862.
- Prediction/actual standard-deviation ratio improved by 0.043625.

The external mix improved two curve-magnitude indicators but did not improve the primary error measures. It still performed worse than the zero-steering MAE baseline.

## Secondary Context

These rows are context only because each changed a different variable from the primary controlled comparison.

| Model | Changed variable | MAE | RMSE | Right MAE | Strong-Turn MAE | Std Ratio | Zero-Baseline Improvement | Direction Error |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Local V3 `crop_v1` | Preprocessing | 0.215280 | 0.307111 | 0.249969 | 0.574012 | 0.670205 | -0.56% | 16.00% |
| Local V3 Huber | Loss | 0.213646 | 0.320153 | 0.276358 | 0.575495 | 0.705915 | 0.20% | 17.44% |
| Local V3 `cnn_v2` | Architecture | 0.217054 | 0.313915 | 0.261968 | 0.612222 | 0.599089 | -1.39% | 19.03% |

Local V2 reported MAE/RMSE of 0.193998/0.267838 on Session C2, but that result is contaminated non-holdout context because Session C2 contributed to Local V2 training. It is not the primary benchmark.

## Limitations

- Session C2 has now influenced the Local V3 baseline, crop, loss, architecture, and external-data decisions; further tuning against it risks selection overfitting.
- The external source contributes only 44 strong-turn rows and remains weak in strong-turn diversity.
- A single seeded run cannot estimate training variance.
- Frame-level offline metrics do not establish temporal stability or closed-loop simulator behavior.
- External licensing and usage terms remain relevant to any future public-release decision.

## Verdict

**EM2 — Valid experiment, no meaningful improvement.**

The workflow, checkpoint, metadata, leakage controls, and evaluation are valid. Strong-turn MAE and prediction variance improved, but overall MAE, RMSE, right MAE, zero-baseline comparison, and direction error regressed. The checkpoint is retained only as an ignored offline research artifact and is not promoted.

## Exact Next Recommendation

Collect and validate Session E2 as a genuinely independent test candidate before any further model-selection experiment. Do not adjust the external sample or run another variant against Session C2 in this experiment chain.

No simulator control was implemented.
