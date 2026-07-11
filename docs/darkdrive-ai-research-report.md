# DarkDrive AI Research Report

## Current Maturity Level

DarkDrive is at Simulator Training Baseline maturity with a session-aware Local V3 evaluation workflow, one completed Local V3 preprocessing experiment, one completed Local V3 loss-function experiment, one completed Local V3 architecture experiment, and one completed External Mix V1 data-composition experiment.

The project has moved beyond infrastructure. It has real simulator data, trained behavior cloning checkpoints, validated Dataset v2 sessions, and offline evaluation. It has not reached simulator-driving readiness.

Research verdict: accept the pipeline, v1 baseline, Local V2 checkpoint, Local V3 session-aware workflow, EXP-007 road-crop experiment, EXP-008 Huber-loss experiment, EXP-009 `cnn_v2` architecture experiment, EXP-014 External Mix V1 experiment, and Session E validation as valid offline research artifacts. Reject the current Local V3-family and External Mix V1 checkpoints as release/control candidates. Local V3 baseline and EXP-007 did not beat the zero-steering MAE baseline on the Session C2 holdout. EXP-008 barely beat the zero baseline on MAE, but RMSE, right MAE, and direction error regressed. EXP-009 improved RMSE slightly, but MAE, right MAE, strong-turn MAE, prediction variance, zero-baseline comparison, and direction error regressed. EXP-014 improved strong-turn MAE and prediction variance but regressed overall MAE, RMSE, right MAE, zero-baseline comparison, and direction error. Session E validates technically but is E2, not frozen, because near-zero steering is slightly high and strong-turn coverage is low. Local V2's Session C2 score is historical context only because Session C2 contributed to Local V2 training data.

## Current Strengths

- OpenCV lane detection works.
- Simulator data collection works.
- Dataset validation works.
- Real Udacity-style simulator data exists.
- Dataset v2 now includes validated recovery and curve-focused sessions.
- Session E independent-test validation workflow exists.
- Training pipeline is functional and now supports explicit train/validation manifests.
- Evaluation pipeline is functional and now supports complete-session validation manifests.
- Training, evaluation, and inference now support checkpoint-aware preprocessing profiles.
- Training now supports configurable MSE versus Huber/SmoothL1 regression loss with checkpoint metadata.
- Training, evaluation, and inference now support checkpoint-aware model architecture selection.
- The model learns real steering signal.
- Repository safety boundaries are clear.
- Checkpoints and generated datasets are not committed.

## Current Weaknesses

- The original Dataset v1 is too centered around zero steering.
- The local Dataset v2 model underperformed v1 despite improved aggregate label balance.
- The first Local V3 model did not beat the zero-steering MAE baseline on the clean Session C2 holdout.
- EXP-007 road-focused crop preprocessing did not materially improve Local V3 and still missed the zero-steering baseline.
- EXP-008 Huber loss improved MAE only slightly and regressed RMSE, right MAE, and direction error.
- EXP-009 `cnn_v2` architecture did not materially improve Local V3 and regressed MAE, right MAE, strong-turn MAE, std ratio, zero-baseline comparison, and direction error.
- Session E is valid but not ideal: near-zero steering is 46.59% and strong turns are 9.72%, so it is not frozen as the final independent test set.
- Local V3 strong-turn MAE is high at 0.598862.
- EXP-007 strong-turn MAE improved to 0.574012 but remains high.
- EXP-008 strong-turn MAE improved to 0.575495 but remains high.
- EXP-009 strong-turn MAE regressed to 0.612222.
- Local V3 prediction variance remains compressed: prediction/actual std ratio 0.656937.
- EXP-007 prediction/actual std ratio improved only slightly to 0.670205.
- EXP-008 prediction/actual std ratio improved to 0.705915 but remains below the preferred 0.80 candidate range.
- EXP-009 prediction/actual std ratio regressed to 0.599089.
- Current model uses only the center camera.
- Older v1 and Local V2 headline evaluations used random row-based splits, which may leak adjacent-frame similarity.
- Local V2 Session C2 metrics are contaminated by Session C2 membership in the Local V2 training dataset.
- Local v2 MAE/RMSE are worse than v1: 0.211307 / 0.303382 versus 0.174045 / 0.246529.
- Local v2 prediction variance is lower than actual variance, suggesting conservative steering.
- Temporal stability and oscillation have not been measured.

## Biggest ML Bottleneck

The biggest bottleneck is dataset coverage and evaluation independence, not CNN size.

The immediate bottleneck is now model/data generalization beyond repeated Session C2 decisions. Local V3 solved the split-leakage problem, but baseline, crop, Huber, and `cnn_v2` experiments did not produce a convincing release candidate on Session C2.

## Highest Impact Next Experiment

Record and validate a better Session E2 candidate before further model-selection work.

Plan:

- Preserve the Local V3 train/validation split as historical research context.
- Do not tune repeatedly against Session C2.
- Do not use the current E2-verdict Session E recording for training, validation, tuning, or model selection.
- Record Session E2 with less straight-only driving and at least 15% strong-turn coverage.
- Keep any future side-camera correction or weighted-loss work as a separate tracked experiment.

This reduces the risk of overfitting experiment choices to Session C2.

## Estimated Chance Current Model Can Keep a Vehicle Inside a Lane

Estimated chance for sustained closed-loop lane keeping in the same simulator: low, around 25% to 40%.

It may handle some straight or gentle segments for short periods. It is likely to fail on recovery, long curves, sharp turns, or oscillation-prone sections because those cases are not yet proven by data or temporal evaluation.

This estimate is intentionally conservative because offline MAE/RMSE does not prove closed-loop stability.

## What Should Be Done Before Simulator Driving

- Collect a better recovery-heavy dataset.
- Reduce near-zero steering dominance.
- Add session-level validation.
- Evaluate left/right camera correction.
- Save official zero-baseline comparisons.
- Measure prediction stability over frame sequences.
- Review steering oscillation visually and numerically.
- Approve `docs/model-release-checklist.md`.

## Recommended Next Sprint

Sprint goal: restore evaluation independence before further model-selection work.

Deliverables:

- Session E2 collection and validation.
- Failure-sample review for Local V3-family checkpoints.
- Updated experiment table.
- Updated release checklist.
- Decision on whether future side-camera correction or weighted loss should be tested after an E1-quality independent test set is frozen.

Recent EXP-007 result: road-focused crop preprocessing was valid but not useful enough. Recent EXP-008 result: Huber loss was valid but not useful enough because right MAE and direction error regressed. Recent EXP-009 result: `cnn_v2` was valid but not useful enough because MAE, right MAE, strong-turn MAE, std ratio, zero-baseline comparison, and direction error regressed. Recent Session E result: valid but not ideal, not frozen. The next exact recommendation is to record a Session E2 candidate before further model-selection work.

## External Udacity Dataset Governance Result

The public Udacity-format source `udacity_behavioral_cloning_public` was downloaded and validated without training or evaluation. It contains 8,036 clean CSV rows and 24,108 images; all three camera references resolve, the image scan found no corruption, steering labels are valid, and the archive SHA-256 is recorded. The result is X2, not X1, because the distribution is strongly straight-heavy: 60.74% near-zero steering and 0.55% strong turns. It is therefore not suitable as direct unbalanced augmentation.

The generated normalized source manifest is ignored by Git. External Mix V1 was subsequently built as a separate ignored training candidate with documented balancing: all 10,657 Local V3 rows plus 3,000 deterministic center-camera external rows. The external subset is 25.00% near-zero, 37.50% left, 37.50% right, and 1.47% strong turns; all 44 available external strong-turn rows were retained. The final 13,657-row candidate is 27.91% near-zero, 36.22% left, 35.87% right, and 21.55% strong turns, with a 21.97% external share.

External Mix V1 passed automated integrity and governance validation with M1 verdict: 0 missing/corrupt images, duplicate rows/paths, invalid labels, or forbidden Session C2/E/E2 rows, and all Local V3 training rows were preserved.

EXP-014 then trained this candidate exactly once with the Local V3 baseline configuration. On the complete Session C2 manifest, External Mix V1 recorded MAE/RMSE 0.216895/0.319567 versus 0.215618/0.316627 for Local V3. Strong-turn MAE improved to 0.579000 and std ratio to 0.700562, while right MAE regressed to 0.251651, zero-baseline comparison worsened to -1.31%, and direction error rose to 17.11%. Verdict EM2: valid experiment, no meaningful improvement. The checkpoint is an ignored offline artifact and is not promoted.

The external source's weak strong-turn coverage remains a limitation. Because Session C2 has now been used repeatedly, the next single recommendation is to collect and validate Session E2 before further model selection. No simulator control was implemented.

## Better External Data Scout Result

EXP-015 reviewed five named sources without downloading them blindly. The Kaggle Udacity lake/jungle candidate ranked highest at priority 4/5 because its expected camera/steering simulator format is closest to DarkDrive, but no Kaggle CLI or credentials were available and its license, schemas, track contents, and steering distributions remain unverified.

DonkeyCar Kaggle/autorope tubs ranked 3/5 because they can provide image/steering/throttle-style records but need conversion, steering-scale checks, domain review, and license clarification. CARLA ranked 3/5 as a future controlled-generation route with heavy setup. comma2k19 ranked 2/5 because its roughly 100 GB real-highway video/CAN domain and conversion requirements do not target the immediate simulator recovery-data need.

EXP-016 subsequently completed the manual ingestion and multi-track validation. Jungle is K1 with 3,404 rows, 10,212 images, 47.00% near-zero, 25.88% left, 27.12% right, and 26.38% strong turns. The supplied `make` track is K2 with 3,930 rows, 11,790 images, 80.41% near-zero, 16.87% left, 2.72% right, and 1.88% strong turns. Both tracks have complete center/left/right images, no corruption, no duplicates, and valid controls.

The jungle track is genuinely better than the first external Udacity source for curve and strong-turn coverage. The source must not be used wholesale because `make` is weak, and archive licensing remains unresolved.

EXP-017 built a center-camera-only jungle candidate under ignored processed storage. It retains all 3,404 source rows in order, preserves original left/right references as provenance without using them for training labels, and exactly matches the EXP-016 distribution. Full manifest validation found 0 missing/corrupt images, duplicate rows/paths/filenames, invalid/out-of-range labels, `make` rows, or Session C2/E/E2 rows. Throttle, brake, and speed are available for every row. Verdict J1 means ready for human review, not training authorization.

EXP-018 built the controlled Kaggle Jungle Mix V1 candidate without modifying Local V3. It preserves all 10,657 Local V3 training rows and all 3,404 Jungle rows for 14,061 total and a 24.21% external share. Its 33.15% near-zero, 33.45% left, 33.40% right, and 27.00% strong-turn distribution keeps curve strength close to Local V3 while adding external visual diversity. It also avoids the prior external source's 0.55% strong-turn weakness.

Full validation found 0 missing/corrupt images, duplicate rows/paths/filenames, invalid/out-of-range labels, K2 `make` rows, Session C2/E/E2 rows, or non-center rows. Verdict KM1 made the mix ready for human review but did not itself authorize training. At the end of EXP-018 no Kaggle model had been trained or evaluated; Session E2 collection remained the separate model-selection priority because Session C2 had already been reused repeatedly.

EXP-019 subsequently trained Kaggle Jungle Mix V1 exactly once with the Local V3 baseline configuration. The 14,061-row training manifest and complete 4,163-row Session C2 validation manifest had 0 image-path or source-session overlap. Training took 493.691 seconds; best epoch/loss were 5/0.095746.

On Session C2, the new checkpoint recorded MAE/RMSE 0.216064/0.309429, right MAE 0.242521, strong-turn MAE 0.559137, std ratio 0.711011, zero-baseline comparison -0.93%, and direction error 16.17%. Compared with Local V3, RMSE, right/strong-turn MAE, std ratio, and direction error improved; MAE regressed by 0.000446 and zero-baseline comparison worsened by 0.21 percentage points. Verdict KJM3: useful offline Kaggle Jungle improvement, not a strong release candidate.

The checkpoint remains an ignored local research artifact. Kaggle licensing is unresolved, Session C2 is not an independent final benchmark, and no model is promoted or released. The next single step is Session E2 collection and validation; no further Kaggle tuning should occur before independent evaluation.

## Udacity CH2_002 Phase-A Result

EXP-020 ingested the real-world `udacity_ch2_002` archive for offline dataset research. Its SHA-256 matched, TAR structure was A1-safe, and all five ROS1 v2.0 bags were readable with 6,985,240 total messages and 0 skipped messages. The three 640 x 480 compressed camera streams decode successfully.

The source schema identifies `/vehicle/steering_report.steering_wheel_angle` as a measured steering-wheel angle in radians and exposes a separate command field. This resolves the raw signal semantics but does not define a DarkDrive simulator normalization. Every camera/steering pair received S1 synchronization; center-camera global matching was 33,808/33,808 with 4.995 ms median and 9.519 ms p95 absolute delta.

A bounded 500-frame center-camera sample retained raw radians and passed with 500 readable images and 0 missing files, unreadable images, duplicate paths, or invalid steering values. The C2A1 verdict means a separate full conversion is technically justified. It does not authorize training, mixing, checkpoint evaluation, release, or control. License/redistribution remains unresolved, and the real-world domain gap requires an explicit future policy.

Session E2 remains the highest-impact next model-evaluation task. The exact CH2_002 next step is a separate full-conversion and normalization-governance task.

## Closed-Loop Simulator Demo V1 Result

EXP-021 implemented the first simulation-only closed-loop integration around the ignored KJM3 checkpoint. The installed Behavioral Cloning Unity assembly verifies EIO4 WebSocket telemetry with base64 center-camera images and `steer` responses. The runtime reuses checkpoint architecture/preprocessing metadata, performs inference without gradients, clips and smooths steering, limits throttle to 0.10 by default, and records ignored telemetry and latency artifacts.

Runtime safety behavior includes neutral control for corrupt/missing frames and non-finite predictions, a repeated-failure latch, neutral-only dry-run, control-emission failure shutdown, Ctrl+C neutral control, an emergency-stop file, and an optional runtime limit. These are simulator diagnostics, not real-vehicle safety controls.

The KJM3 checkpoint passed a local stored-frame self-test with finite raw steering -0.110780 and 4.886 ms CPU inference. The EIO4 server also bound and stopped cleanly in a one-second dry-run with no simulator attached. Live Unity telemetry, vehicle movement, connected emergency-stop behavior, and a lap were not tested or claimed.

The exact next runtime step is a human live dry-run in Unity Autonomous mode. Only after telemetry, logs, disconnect handling, and emergency stop pass should one supervised 60-second active diagnostic be attempted. Session E2 remains the next model-selection priority, and KJM3 remains unpromoted.

## Recommended Commit Message

```text
docs: add ML research analysis and release gates
```
