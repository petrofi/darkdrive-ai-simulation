# Model Analysis V1

DarkDrive has reached a valid first behavior cloning baseline, but the current model should be treated as an offline research checkpoint only. It is not ready for simulator control.

## Scope

This review analyzes the current simulator dataset, trained checkpoint, CNN architecture, and offline evaluation results. It does not implement simulator control, websocket steering, or autonomous mode.

## Evidence Used

| Area | Current value |
| --- | --- |
| Dataset rows | 3706 driving samples |
| Simulator images | 11118 images, 3706 each for center, left, and right cameras |
| Dataset validation | PASS |
| Training split | 2965 train rows, 741 validation rows |
| Best validation loss | 0.060776 |
| Evaluation MAE | 0.174045 |
| Evaluation RMSE | 0.246529 |
| Model | Compact PyTorch CNN in `src/models/steering_model.py` |
| Current camera usage | Center camera only |

## Dataset Distribution

The steering distribution is heavily concentrated around zero.

| Statistic | Value |
| --- | ---: |
| Steering min | -1.000000 |
| Steering max | 1.000000 |
| Steering mean | -0.013526 |
| Steering median | 0.000000 |
| Steering std | 0.350406 |
| 25th percentile | 0.000000 |
| 75th percentile | 0.000000 |

The p25, median, and p75 all being exactly zero is the most important dataset warning sign. The model sees a large amount of "go straight" behavior compared with corrective behavior.

## Steering Balance

| Steering region | Count | Percent |
| --- | ---: | ---: |
| Strong left, steering <= -0.50 | 311 | 8.39% |
| Medium left, -0.50 to -0.20 | 262 | 7.07% |
| Gentle left, -0.20 to -0.05 | 252 | 6.80% |
| Near zero, abs <= 0.05 | 2054 | 55.42% |
| Gentle right, 0.05 to 0.20 | 272 | 7.34% |
| Medium right, 0.20 to 0.50 | 315 | 8.50% |
| Strong right, steering >= 0.50 | 240 | 6.48% |

Directional balance is better than expected once near-zero steering is excluded:

| Direction | Count | Percent |
| --- | ---: | ---: |
| Left, steering < -0.05 | 825 | 22.26% |
| Right, steering > 0.05 | 827 | 22.32% |
| Near zero, abs <= 0.05 | 2054 | 55.42% |

Left and right turns are represented almost equally by count. However, both are underrepresented relative to straight driving, and the dataset does not prove that recovery behavior is represented.

## Zero Steering Concentration

| Threshold | Count | Percent |
| --- | ---: | ---: |
| abs steering <= 0.01 | 1913 | 51.62% |
| abs steering <= 0.03 | 1971 | 53.18% |
| abs steering <= 0.05 | 2054 | 55.42% |
| abs steering <= 0.10 | 2236 | 60.33% |
| abs steering <= 0.20 | 2578 | 69.56% |

Judgment: yes, steering is centered too much around zero for a robust first driving model. More than half of all labels are effectively straight-line labels.

## Training Behavior

| Epoch | Train loss | Validation loss | Train MAE | Validation MAE |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 0.126273 | 0.116218 | 0.2124 | 0.2091 |
| 2 | 0.117344 | 0.110330 | 0.2178 | 0.2050 |
| 3 | 0.104476 | 0.100918 | 0.2093 | 0.2067 |
| 4 | 0.097639 | 0.105082 | 0.2027 | 0.2255 |
| 5 | 0.094116 | 0.081245 | 0.1981 | 0.1892 |
| 6 | 0.087725 | 0.086247 | 0.1920 | 0.1863 |
| 7 | 0.080917 | 0.074878 | 0.1854 | 0.1804 |
| 8 | 0.081457 | 0.075929 | 0.1874 | 0.1801 |
| 9 | 0.073821 | 0.075710 | 0.1772 | 0.1812 |
| 10 | 0.068089 | 0.060776 | 0.1716 | 0.1740 |

The best validation loss occurs at the final epoch, so the run does not show a clear plateau. The model may benefit from more training, but more epochs alone are unlikely to fix the dataset bias.

## Evaluation Behavior

| Metric | Value |
| --- | ---: |
| Validation rows evaluated | 741 |
| MAE | 0.174045 |
| RMSE | 0.246529 |
| Zero-steering baseline MAE | 0.193285 |
| Zero-steering baseline RMSE | 0.350208 |
| MAE improvement over zero baseline | 9.95% |
| RMSE improvement over zero baseline | 29.60% |
| Prediction mean | -0.023701 |
| Actual mean | -0.023525 |
| Prediction std | 0.272862 |
| Actual std | 0.349416 |
| Prediction/actual correlation | 0.712008 |
| Sign accuracy when abs(actual) > 0.05 | 89.29% |
| Mean abs(prediction) / abs(actual), abs(actual) > 0.05 | 0.888031 |

The model learns real steering signal: correlation is positive and sign accuracy is high on non-trivial steering labels. However, the model only improves MAE over always predicting zero by about 10%, and predicted steering has lower variance than actual steering. That suggests conservative steering and likely under-response in sharper situations.

## Underfitting Assessment

Judgment: partial underfitting is likely.

Evidence:

- Best validation loss occurred at epoch 10, the final epoch.
- Training and validation losses are still moving downward.
- Prediction variance is compressed relative to true label variance.
- The model beats the zero baseline by only 9.95% MAE.
- The architecture is compact and uses aggressive adaptive pooling, which may discard spatial detail.

This is not catastrophic underfitting. The model clearly learned some steering signal. But it is not yet a strong behavior cloning model.

## Overfitting Assessment

Judgment: no strong evidence of classic overfitting yet.

Evidence:

- Training loss and validation loss stay close.
- Validation loss is sometimes lower than training loss, which is plausible because augmentation is enabled for training but disabled for validation.
- There is no widening train-validation gap across epochs.

Important caveat: the current validation split is a random row split. Adjacent simulator frames are highly correlated, so train and validation may contain near-duplicate temporal neighbors. This can make validation look better than true generalization. Future evaluation should split by lap, session, or track segment.

## Dataset Balance Assessment

Judgment: directionally balanced, but not behaviorally balanced.

The left and right counts outside near-zero steering are almost identical. That is good. The problem is not simple left/right count asymmetry. The problem is that straight driving dominates the label distribution, recovery situations are not explicitly represented, and temporal adjacent-frame leakage may inflate evaluation confidence.

## Left and Right Turn Representation

Judgment: left and right turns are present, but not sufficient for robust simulator driving.

Positive signs:

- Left non-zero count: 825.
- Right non-zero count: 827.
- Steering reaches full range from -1.0 to 1.0.

Weaknesses:

- Near-zero steering is 55.42% of the dataset.
- Strong right turns are lower than strong left turns: 240 right vs 311 left.
- No documented recovery-driving sessions exist.
- Current training ignores left and right camera images.

## Critical Risk Before Closed Loop

The current model was evaluated offline. Offline MAE/RMSE does not prove closed-loop stability. A behavior cloning model can look acceptable offline and still drift off track because its own predictions create states that are missing from the dataset.

Current release decision: do not connect this model to simulator control yet.

