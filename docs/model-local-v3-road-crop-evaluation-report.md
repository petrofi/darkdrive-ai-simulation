# Local V3 Road Crop Evaluation Report

This report documents EXP-007 - Road-Focused Crop Preprocessing. The work is simulation-only. No simulator control, websocket driving loop, autonomous mode, real vehicle control, or public-road claim was added.

## Hypothesis

The first Local V3 model compressed steering magnitude and under-predicted medium and strong turns. A deterministic road-focused crop might reduce upper-frame background influence while preserving road geometry, lane boundaries, and curve information.

## Crop Definition

Preprocessing profile: `road_crop_v1`.

Source simulator frames are 320x160 RGB after loading. The crop is applied before resizing:

| Field | Value |
| --- | ---: |
| `x_min` | 0 |
| `x_max` | full source width |
| `y_min` | 55 |
| `y_max` | 150, exclusive |
| Crop height | 95 pixels |
| Resize target | 160x80 |
| Pixel scaling | unchanged, `[0, 1]` |

`baseline` remains the previous behavior: resize the full frame to 160x80 with no crop.

## Controlled Variables

Only the preprocessing profile changed.

| Variable | Value |
| --- | --- |
| Train CSV | `data/processed/local_v3_training/train.csv` |
| Validation CSV | `data/processed/local_v3_training/validation.csv` |
| Architecture | `SteeringModel` |
| Parameters | 188219 |
| Loss | MSE |
| Optimizer | AdamW |
| Learning rate | 0.001 |
| Weight decay | 0.0001 |
| Epochs | 15 |
| Batch size | 32 |
| Seed | 42 |
| Augmentation | Existing training-only flip, brightness/contrast, shadow |
| Validation augmentation | Off |
| Device | CPU |

No Huber loss, weighted loss, CNN change, side-camera correction labels, simulator control, or repeated crop tuning was added.

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

## Implementation

Added shared preprocessing support in `src/utils/image_preprocessing.py` and wired it into:

- `src/training/train_behavior_cloning.py`
- `scripts/evaluate_steering_model.py`
- `src/inference/predict_steering.py`

Training accepts `--preprocessing-profile baseline` and `--preprocessing-profile road_crop_v1`.

Evaluation and inference default to `--preprocessing-profile checkpoint`, which reads checkpoint metadata where present. Old checkpoints without preprocessing metadata default to `baseline`.

The EXP-007 checkpoint stores:

- `preprocessing_profile: road_crop_v1`
- crop bounds `x=[0, full width)`, `y=[55, 150)`
- target input size 160x80
- pixel scale `[0, 1]`

## Tests

Validation run:

```powershell
C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe -m py_compile .\src\utils\image_preprocessing.py .\src\training\train_behavior_cloning.py .\scripts\evaluate_steering_model.py .\src\inference\predict_steering.py
C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe -m unittest discover -s tests
```

Result: `25 tests`, all passed.

Covered behavior includes:

- baseline output shape
- `road_crop_v1` output shape
- exact deterministic crop boundaries
- invalid profile handling
- shared dataset/preprocessing consistency
- deterministic validation preprocessing without augmentation
- old checkpoint metadata fallback to `baseline`
- checkpoint metadata selection of `road_crop_v1`
- horizontal flip steering sign negation
- explicit session-aware manifest isolation

## Training Command

Interpreter:

```text
C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe
```

Command:

```powershell
& 'C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe' .\src\training\train_behavior_cloning.py --csv data\processed\local_v3_training\train.csv --train-csv data\processed\local_v3_training\train.csv --validation-csv data\processed\local_v3_training\validation.csv --format simple --epochs 15 --batch-size 32 --lr 0.001 --loss mse --device cpu --seed 42 --preprocessing-profile road_crop_v1 --output models\steering_model_local_v3_crop_v1.pt --chart-output screenshots\training_loss_local_v3_crop_v1.png
```

## Training Results

| Metric | Value |
| --- | ---: |
| Training duration | 409.065 seconds |
| Best epoch | 5 |
| Best validation loss | 0.094317 |
| Final training loss | 0.119376 |
| Final validation loss | 0.107179 |
| Final training MAE | 0.245646 |
| Final validation MAE | 0.209884 |
| Checkpoint | `models/steering_model_local_v3_crop_v1.pt` |

The checkpoint and training chart are generated local artifacts and remain ignored by Git.

## Session C2 Evaluation

Evaluation command:

```powershell
& 'C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe' .\scripts\evaluate_steering_model.py --model models\steering_model_local_v3_crop_v1.pt --csv data\processed\local_v3_training\train.csv --validation-csv data\processed\local_v3_training\validation.csv --format simple --batch-size 64 --device cpu --seed 42 --metrics-json C:\tmp\darkdrive_exp007_crop_v1_metrics.json
```

The evaluator used `road_crop_v1` from checkpoint metadata.

| Metric | Value |
| --- | ---: |
| Sample count | 4163 |
| Overall MAE | 0.215280 |
| Overall RMSE | 0.307111 |
| Zero-steering baseline MAE | 0.214081 |
| Improvement over zero baseline | -0.001199 |
| Improvement over zero baseline | -0.56% |
| Near-zero MAE | 0.151936 |
| Near-zero count | 1720 |
| Left MAE | 0.269212 |
| Left count | 1258 |
| Right MAE | 0.249969 |
| Right count | 1185 |
| Strong-turn MAE | 0.574012 |
| Strong-turn count | 620 |
| Prediction mean | -0.026623 |
| Prediction std | 0.233060 |
| Actual mean | -0.017837 |
| Actual std | 0.347744 |
| Prediction/actual std ratio | 0.670205 |
| Signed bias, prediction minus actual | -0.008786 |
| Incorrect direction rate, abs(actual) > 0.05 | 16.00% |

Steering magnitude bins:

| abs(actual) bin | Count | MAE |
| --- | ---: | ---: |
| 0.00-0.05 | 1720 | 0.151936 |
| 0.05-0.25 | 1134 | 0.134900 |
| 0.25-0.50 | 689 | 0.182899 |
| 0.50-1.00 | 620 | 0.574012 |

## Controlled Comparison

Both rows use the same Local V3 train manifest, complete Session C2 validation manifest, architecture, optimizer, loss, learning rate, epochs, batch size, seed, and training-only augmentation. The intended difference is preprocessing.

| Model | Preprocessing | MAE | RMSE | Right MAE | Strong-Turn MAE | Std Ratio | Zero-Baseline Improvement |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `steering_model_local_v3.pt` | `baseline` | 0.215618 | 0.316627 | 0.249182 | 0.598862 | 0.656937 | -0.72% |
| `steering_model_local_v3_crop_v1.pt` | `road_crop_v1` | 0.215280 | 0.307111 | 0.249969 | 0.574012 | 0.670205 | -0.56% |

Interpretation:

- Overall MAE improved by only 0.000338.
- RMSE improved by 0.009516.
- Strong-turn MAE improved by 0.024850.
- Prediction/actual std ratio improved from 0.656937 to 0.670205.
- Right MAE regressed slightly from 0.249182 to 0.249969.
- Near-zero MAE regressed from 0.139037 to 0.151936.
- The model still did not beat the zero-steering MAE baseline.

## Historical Comparison Caveats

V1 and Local V2 are historical context only, not the primary controlled benchmark for EXP-007.

| Model | Context | MAE | RMSE | Caveat |
| --- | --- | ---: | ---: | --- |
| `steering_model_sim_v1.pt` | Older Dataset v1 workflow | 0.225056 on Session C2 | 0.332471 on Session C2 | Older workflow and data composition |
| `steering_model_local_v2.pt` | Merged Local V2 workflow | 0.193998 on Session C2 | 0.267838 on Session C2 | Session C2 contributed to Local V2 training data, so this is not an independent holdout result |

Local V2's Session C2 score is not considered an independent holdout result because Session C2 contributed to the Local V2 training dataset.

## Verdict

Verdict: **P2) Valid experiment, no meaningful improvement**.

Reasons:

- The preprocessing pipeline works and checkpoint metadata is reproducible.
- No split leakage was detected.
- Overall MAE improved only trivially versus Local V3 baseline.
- The crop model still performs worse than the zero-steering MAE baseline.
- Right MAE regressed slightly.
- Prediction variance and strong-turn error improved but remain far from promotion thresholds.

No simulator control should be implemented from this result.

## Next Recommendation

Do not run another crop variant against Session C2 in this task.

Recommended next single-variable experiment: Huber loss on the same fixed Local V3 split, using baseline preprocessing unless a separate plan explicitly chooses otherwise.
