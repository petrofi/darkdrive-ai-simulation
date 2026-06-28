# Dataset Collection Strategy V1

The highest impact next step is not a larger CNN. The highest impact next step is a better simulator dataset with explicit recovery and off-center examples.

## Recommendation Summary

| Question | Recommendation |
| --- | --- |
| How many more frames? | Add 8000 to 12000 more center-labeled driving samples. With three cameras, this produces 24000 to 36000 additional image files. |
| Add recovery driving? | Yes. This is mandatory before simulator control. |
| Add intentional off-center driving? | Yes, but only as controlled recovery sequences. |
| Use left/right camera correction? | Yes, as a separate experiment after verifying steering sign convention. |
| Add more sharp turns? | Yes. Oversample curves and strong corrections without deleting all straight driving. |

## Target Dataset Size

Current dataset:

- 3706 driving samples.
- 11118 images.
- 3706 images per camera.

Next useful target:

- 12000 to 16000 total driving samples.
- This requires about 8000 to 12000 additional center-labeled samples.
- With center, left, and right cameras, this means about 24000 to 36000 additional image files.

This target is large enough to reduce the dominance of the first recording session while still being realistic for a local simulator workflow.

## Target Label Distribution

The current dataset has 55.42% near-zero steering labels using abs(steering) <= 0.05. The next dataset should aim for a lower straight-driving concentration.

Suggested target:

| Region | Target share |
| --- | ---: |
| Near zero, abs steering <= 0.05 | 30% to 40% |
| Gentle left/right | 20% to 30% combined |
| Medium left/right | 20% to 30% combined |
| Strong left/right and recovery corrections | 15% to 25% combined |

Do not force a perfectly uniform distribution. Real driving has many straight frames. The goal is to avoid a model that treats "go straight" as the safest default for almost every image.

## Recovery Driving

Recommendation: add recovery driving.

Reason:

Behavior cloning suffers when the model drifts into states not present in the training data. If all examples are clean centered driving, the model has no supervised examples for returning from the lane edge back to center.

Collect examples where:

- The car is slightly left of lane center and steering corrects right.
- The car is slightly right of lane center and steering corrects left.
- The car enters a curve late and recovers smoothly.
- The car approaches lane boundaries and returns without abrupt oscillation.

Recovery data should be recorded intentionally and labeled by human steering behavior. Do not simply include bad driving without correction.

## Off-Center Driving

Recommendation: intentionally record off-center driving as recovery sequences.

Reason:

The future closed-loop model will make mistakes. It must learn what recovery looks like from images that are not perfectly centered.

Rules:

- Off-center samples must include a clear corrective steering label.
- Avoid long segments of drifting away from the lane center.
- Record both left-offset and right-offset recovery.
- Keep recovery speed moderate so steering labels are stable.

## Left/Right Camera Correction

Recommendation: use left and right camera images as a controlled augmentation experiment.

Reason:

The dataset already contains 3706 left and 3706 right camera images, but the current baseline uses only center images. Camera correction can turn existing side-camera images into recovery-like examples.

Initial correction plan:

- Left camera image: add a positive steering correction if positive means steering right in the simulator.
- Right camera image: add a negative steering correction if positive means steering right in the simulator.
- Start with a correction magnitude around 0.15 to 0.25.
- Verify the steering sign convention visually before training.
- Track this as a separate experiment, not as an invisible change to the baseline.

Risk:

The correction value is a hyperparameter. Too small gives weak recovery training. Too large teaches overcorrection and oscillation.

## Sharp Turns

Recommendation: collect more sharp turns and curve exits.

Reason:

Sharp steering labels exist, but strong turns are still a minority:

- Strong left: 311 samples, 8.39%.
- Strong right: 240 samples, 6.48%.

The current model predicts with lower variance than the actual labels, so it may understeer in sharper situations. Add more curve-heavy laps and recovery corrections around curves.

Collection guidance:

- Record multiple clean laps through curves.
- Include curve entry, apex, and exit frames.
- Add both directions when the simulator/track allows it.
- Avoid collecting only full-lock steering at very low speed.

## Session Strategy

Collect data in named sessions instead of one large anonymous log.

Recommended sessions:

| Session | Purpose | Approx. samples |
| --- | --- | ---: |
| S01 | Clean centered lap, baseline consistency | 1500 to 2500 |
| S02 | Left-offset recovery | 1500 to 2500 |
| S03 | Right-offset recovery | 1500 to 2500 |
| S04 | Curve-heavy driving | 1500 to 2500 |
| S05 | Mixed validation lap, not used for training | 1000 to 2000 |

The validation session should be held out by session, not randomly mixed row-by-row.

## Quality Rules

Before using the next dataset for training:

- Validate all image paths.
- Count center, left, and right images.
- Remove parked or near-stationary frames unless they serve a specific purpose.
- Report steering distribution.
- Report speed distribution.
- Report left/right/near-zero balance.
- Save sample frame grids.
- Split validation by session or lap.

## Highest Impact Next Dataset Experiment

Train the same current CNN on a better dataset before changing architecture. This isolates the effect of data quality.

Experiment name:

```text
EXP-002-balanced-recovery-dataset
```

Success criteria:

- Near-zero steering reduced below 40%.
- Evaluation split held out by session.
- MAE improves by at least 25% over the zero-steering baseline.
- Prediction standard deviation moves closer to actual steering standard deviation.
- Qualitative prediction samples show reasonable behavior on recovery images.

