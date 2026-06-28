# Research Roadmap

DarkDrive is now in the Machine Learning Research phase. Infrastructure is good enough for baseline research. The next milestones should improve data quality, model quality, prediction stability, and only then simulator driving.

## Research Iteration 1: Current Baseline

Status: complete as an offline baseline.

Current baseline:

- 3706 simulator driving samples.
- 11118 simulator images.
- Validated Udacity-style dataset.
- Compact PyTorch CNN trained on center camera images.
- Best validation loss: 0.060776.
- Offline MAE: 0.174045.
- Offline RMSE: 0.246529.

Research verdict:

- The model has learned real steering signal.
- The dataset is directionally balanced but too concentrated around zero steering.
- Offline evaluation is useful, but not enough for closed-loop simulator control.
- Current model is not release-ready.

Exit criteria already met:

- Training pipeline works.
- Evaluation pipeline works.
- Dataset validation works.
- Results are documented.

## Research Iteration 2: Better Dataset

Goal: improve the data distribution before changing the architecture.

Actions:

- Collect 8000 to 12000 more center-labeled driving samples.
- Add recovery driving from left and right lane offsets.
- Add off-center correction sequences.
- Add more curve-heavy and sharp-turn samples.
- Use session-level or lap-level validation splits.
- Keep a clean held-out validation session.
- Test left/right camera correction as a separate experiment.

Metrics:

- Steering histogram.
- Left/right/zero distribution.
- Speed distribution.
- MAE and RMSE.
- Zero-baseline comparison.
- Prediction variance vs actual variance.
- Qualitative review of prediction samples.

Exit criteria:

- Near-zero steering no longer dominates the dataset.
- Recovery behavior is visibly present.
- The same baseline CNN improves materially without architecture changes.

## Research Iteration 3: Better CNN

Goal: improve visual feature learning after proving the dataset is stronger.

Candidate changes:

- NVIDIA Behavioral Cloning Network style crop and convolution stack.
- Improved image crop to remove sky/hood regions if present.
- Image normalization with dataset mean/std.
- Optional batch normalization.
- ResNet18 transfer learning only if the dataset becomes large enough.
- EfficientNet-lite only after a strong lightweight baseline exists.

Rules:

- Change one major factor at a time.
- Keep dataset and split fixed during architecture comparisons.
- Track every experiment in `docs/experiments.md`.
- Do not choose a larger architecture only because it is larger.

Exit criteria:

- Architecture improves validation metrics on the same held-out session.
- Prediction plots improve on curves and recovery samples.
- Model remains fast enough for future real-time simulator inference.

## Research Iteration 4: Prediction Smoothing

Goal: reduce unstable steering without hiding model failure.

Candidate techniques:

- Exponential moving average over predicted steering.
- Rate limiting on steering changes.
- Temporal frame stacking.
- Short-window temporal model after frame-level baseline is strong.
- Oscillation metrics on validation videos.

Required metrics:

- Frame-to-frame steering delta.
- Sign flip frequency on straight sections.
- Mean absolute steering jerk.
- Delay introduced by smoothing.
- Error on curve entry and recovery events.

Important warning:

Smoothing should not be used to cover up a weak model. It should be introduced only after the offline model makes directionally reasonable predictions.

## Research Iteration 5: Simulator Driving

Goal: connect the model to simulator-only closed-loop driving after release gates pass.

Prerequisites:

- Dataset quality verified.
- Offline evaluation complete.
- Held-out session results acceptable.
- Prediction stability acceptable.
- No obvious steering oscillation in offline video replay.
- Model release checklist approved.

Initial simulator-driving scope:

- Simulation only.
- No real vehicle control.
- No RC car control.
- No public road deployment.
- Record model predictions during driving for post-run analysis.

Exit criteria:

- Vehicle can remain in lane for short controlled simulator segments.
- Failure cases are recorded and categorized.
- New recovery data is collected from failures.

