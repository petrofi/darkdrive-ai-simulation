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

Status: first session-aware model experiment, EXP-007 road-focused crop, EXP-008 Huber loss, and EXP-009 `cnn_v2` architecture are complete and not promoted. Dataset v2 now has validated Session C2 right-recovery data and Session D curve-focused data. Local Dataset v2 improved aggregate distribution but the trained local v2 model underperformed v1 historically. Local V2's Session C2 score is historical context only because Session C2 contributed to Local V2 training data. Local V3 provides explicit session-aware train and validation manifests, with Session C2 held out completely for validation. The first Local V3 model and road-crop variant failed to beat the zero-steering MAE baseline. Huber loss barely beat the zero baseline on MAE, but RMSE, right MAE, and direction error regressed. `cnn_v2` improved RMSE slightly but regressed MAE, right MAE, strong-turn MAE, prediction variance, zero-baseline comparison, and direction error. Session E was recorded and validated as E2, valid but not ideal, so it is not frozen as the final independent test set. Session E2 folder preparation is complete and recording is pending.

Actions:

- Preserve validated Dataset v1 and Sessions A/B/C2/D.
- Use Dataset v1, Session A, Session B, and Session D for Local V3 training.
- Keep Session C2 as the complete-session validation holdout.
- Use Session D for sustained curve and strong-turn coverage.
- Downsample near-zero-heavy v1/A/B rows.
- Downsample Session D softer-left rows to avoid left dominance.
- Treat the explicit Local V3 session-aware validation split as used for multiple model-selection decisions.
- Review Local V3 strong-turn and right-recovery failure samples before any further model changes.
- Record a Session E2 candidate and validate it before further model-selection work.
- Keep left/right camera correction as a separate future experiment.

Metrics:

- Steering histogram.
- Left/right/zero distribution.
- Speed distribution.
- MAE and RMSE.
- Zero-baseline comparison.
- Prediction variance vs actual variance.
- Qualitative review of prediction samples.

Exit criteria:

- Near-zero steering no longer dominates the Local V3 training set. Met by Local V3 train at 28.72%.
- Recovery and curve behavior are visibly present. Session D supplies curve/strong-turn coverage; Session C2 is held out for right-recovery validation.
- The same baseline CNN improves materially over both v1 and local v2 without architecture changes. Not met by the first Local V3 run.
- Session-aware validation is reported, not only a random row split. Met for Local V3.

First Local V3 result:

- Session C2 MAE/RMSE: 0.215618 / 0.316627.
- Right MAE: 0.249182.
- Strong-turn MAE: 0.598862.
- Prediction/actual std ratio: 0.656937.
- Verdict: R2, valid offline experiment, not promoted.

EXP-007 road-focused crop result:

- Crop: `road_crop_v1`, y=[55,150) before resize.
- Session C2 MAE/RMSE: 0.215280 / 0.307111.
- Right MAE: 0.249969.
- Strong-turn MAE: 0.574012.
- Prediction/actual std ratio: 0.670205.
- Zero-baseline improvement: -0.56%.
- Verdict: P2, valid experiment with no meaningful improvement.

EXP-008 Huber loss result:

- Loss: `SmoothL1Loss(beta=1.0)`.
- Preprocessing: `baseline`.
- Session C2 MAE/RMSE: 0.213646 / 0.320153.
- Right MAE: 0.276358.
- Strong-turn MAE: 0.575495.
- Prediction/actual std ratio: 0.705915.
- Zero-baseline improvement: 0.20%.
- Direction error: 17.44%.
- Verdict: H2, valid experiment with no meaningful improvement.

EXP-009 `cnn_v2` architecture result:

- Architecture: `SteeringModelV2`, 726103 parameters, BatchNorm2d + ELU convolution stack.
- Preprocessing: `baseline`.
- Loss: `MSELoss`.
- Session C2 MAE/RMSE: 0.217054 / 0.313915.
- Right MAE: 0.261968.
- Strong-turn MAE: 0.612222.
- Prediction/actual std ratio: 0.599089.
- Zero-baseline improvement: -1.39%.
- Direction error: 19.03%.
- Verdict: A2, valid experiment with no meaningful improvement.

Session E independent test validation:

- Target folder: `data/processed/simulator_v2/session_e_independent_test/`.
- Rows/images: 6379 rows and 19137 images.
- Missing/corrupt images: 0 / 0.
- Near-zero / left / right / strong: 46.59% / 26.09% / 27.32% / 9.72%.
- Verdict: E2, valid but not ideal.
- Freeze decision: not frozen as the final independent test set.
- No training or model evaluation was run on Session E.
- Next data step: record a Session E2 candidate with less straight-only driving and at least 15% strong-turn coverage.

Session E2 independent test preparation:

- Target folder: `data/processed/simulator_v2/session_e2_independent_test/`.
- `IMG/` subfolder is prepared.
- Recording is pending.
- No validation, training, or model evaluation has been run for Session E2.
- Target: 5000-7000 rows, near-zero 30%-42%, left/right both above 22%, and strong turns at least 15%.

## Research Iteration 3: Better CNN

Goal: improve visual feature learning after proving the dataset is stronger.

Candidate changes:

- NVIDIA Behavioral Cloning Network style crop and convolution stack.
- Image normalization with dataset mean/std.
- Optional batch normalization.
- ResNet18 transfer learning only if the dataset becomes large enough.
- EfficientNet-lite only after a strong lightweight baseline exists.

Recent result: a standalone road crop was tested in EXP-007 and did not materially improve Local V3. Do not run another crop variant against Session C2 without a new experimental plan and a future untouched test session.

Recent loss result: Huber/SmoothL1Loss was tested in EXP-008 and did not materially improve Local V3 because right MAE and direction error regressed. Do not run another loss variant against Session C2 in the same experiment chain.

Recent architecture result: `cnn_v2` was tested in EXP-009 and did not materially improve Local V3. It improved RMSE slightly but worsened MAE, right MAE, strong-turn MAE, prediction variance compression, zero-baseline comparison, and direction error. Do not run another architecture variant against Session C2 in the same experiment chain.

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

## External Dataset Governance Update

`udacity_behavioral_cloning_public` completed controlled ingestion with X2 verdict. It is clean structurally (8,036 rows, 24,108 images, 0 missing/corrupt references, valid labels, and recorded SHA-256), but it is not ready for direct use because 60.74% of steering labels are near zero and only 0.55% are strong turns.

External Mix V1 now exists as an ignored M1 candidate for human review. It preserves all 10,657 Local V3 training rows and adds 3,000 deterministic center-camera external rows: 750 near-zero, 1,125 left, and 1,125 right, including all 44 available strong turns. The final 13,657 rows are 27.91% near-zero, 36.22% left, 35.87% right, and 21.55% strong turns; external data is 21.97% of the candidate. Integrity and forbidden-session checks passed.

Next external-data step: review the M1 candidate. If approved, run exactly one controlled offline Local V3 baseline versus External Mix V1 experiment. This does not change evaluation-independence requirements or the simulation-only control gate. No external-data model has been trained yet.
