# Model Release Checklist

DarkDrive models must not be connected to simulator control until this checklist passes.

Current release status: not approved for simulator control.

## Dataset Quality Gate

- [x] Simulator dataset exists.
- [x] Dataset validation passes.
- [x] Center images found.
- [x] Left images found.
- [x] Right images found.
- [x] Steering labels are numeric.
- [x] Steering distribution has been analyzed.
- [x] Dataset includes documented recovery driving.
- [x] Dataset includes documented curve-focused driving.
- [x] Final training dataset near-zero concentration is acceptable.
- [x] Validation split is by session, lap, or track segment.
- [ ] Low-speed parked frames are reviewed or filtered.

## Evaluation Gate

- [x] Offline evaluation script runs.
- [x] MAE is reported.
- [x] RMSE is reported.
- [x] Prediction-vs-actual plot is generated.
- [x] Prediction sample grid is generated.
- [x] Evaluation includes zero-steering baseline comparison in the official report.
- [x] Evaluation includes held-out session results.
- [x] Evaluation includes left/right/strong-turn metrics in the local v2 report.
- [ ] Evaluation includes recovery-case metrics for a release candidate.
- [x] Evaluation has been repeated with at least two random seeds or fixed held-out sessions.

## Prediction Stability Gate

- [ ] Frame-to-frame steering delta is measured.
- [ ] Steering sign flip rate is measured on straight sections.
- [ ] Steering oscillation is reviewed on a validation video sequence.
- [ ] Prediction smoothing is evaluated offline.
- [ ] Smoothing lag is measured on curve entry.
- [ ] No obvious steering oscillation remains.

## Minimum Candidate Thresholds

These are initial research thresholds, not final safety claims.

- MAE should improve by at least 25% over the zero-steering baseline.
- RMSE should improve by at least 30% over the zero-steering baseline.
- Prediction standard deviation should not be severely compressed relative to actual steering.
- Non-zero steering sign accuracy should remain above 90%.
- Sharp-turn and recovery errors should be reviewed separately.

The v1 model met the RMSE improvement target but did not meet the MAE improvement target. The local v2 model underperformed v1 historically and is not a release candidate. Local V2's Session C2 score is not treated as an independent holdout result because Session C2 contributed to the Local V2 training dataset. The local v3 model completed session-aware evaluation on Session C2, but did not beat the zero-steering MAE baseline. EXP-007 road-focused crop preprocessing was valid but did not materially improve Local V3. EXP-008 Huber loss made the zero-baseline comparison barely positive, but right MAE, RMSE, and direction error regressed. EXP-009 `cnn_v2` improved RMSE slightly, but MAE, right MAE, strong-turn MAE, std ratio, zero-baseline comparison, and direction error regressed. Session E validation is E2, valid but not ideal, and is not frozen as the final independent test set.

## Simulator-Control Gate

Simulator control is blocked until:

- [ ] Dataset quality verified.
- [ ] Evaluation complete.
- [ ] Prediction stability acceptable.
- [ ] No obvious steering oscillation.
- [ ] Release notes identify the exact checkpoint and dataset.
- [ ] The implementation remains simulation-only.

## Current Decision

Do not treat the current model as released or run it unattended. EXP-021 permits only a supervised low-throttle simulator diagnostic after the live dry-run and emergency-stop checks pass.

Current dataset progress:

- Local V3 train/validation manifests are built and validated.
- Local V3 training near-zero concentration is 28.72%.
- Local V3 validation uses complete `session_c2_right_recovery` holdout.
- Local V3 leakage checks found 0 source-session, image-path, filename, and CSV-row overlap.
- Local V3 model training completed with explicit manifests.
- Local V3 Session C2 MAE/RMSE: 0.215618 / 0.316627.
- Local V3 right MAE: 0.249182.
- Local V3 strong-turn MAE: 0.598862.
- Local V3 prediction/actual std ratio: 0.656937.
- Local V3 release verdict: R2, valid offline experiment, not promoted.
- EXP-007 road crop checkpoint: `models/steering_model_local_v3_crop_v1.pt`.
- EXP-007 Session C2 MAE/RMSE: 0.215280 / 0.307111.
- EXP-007 right MAE: 0.249969.
- EXP-007 strong-turn MAE: 0.574012.
- EXP-007 prediction/actual std ratio: 0.670205.
- EXP-007 zero-baseline improvement: -0.56%.
- EXP-007 verdict: P2, valid experiment with no meaningful improvement.
- EXP-008 Huber checkpoint: `models/steering_model_local_v3_huber.pt`.
- EXP-008 Session C2 MAE/RMSE: 0.213646 / 0.320153.
- EXP-008 right MAE: 0.276358.
- EXP-008 strong-turn MAE: 0.575495.
- EXP-008 prediction/actual std ratio: 0.705915.
- EXP-008 zero-baseline improvement: 0.20%.
- EXP-008 direction error: 17.44%.
- EXP-008 verdict: H2, valid experiment with no meaningful improvement.
- EXP-009 cnn_v2 checkpoint: `models/steering_model_local_v3_cnn_v2.pt`.
- EXP-009 Session C2 MAE/RMSE: 0.217054 / 0.313915.
- EXP-009 right MAE: 0.261968.
- EXP-009 strong-turn MAE: 0.612222.
- EXP-009 prediction/actual std ratio: 0.599089.
- EXP-009 zero-baseline improvement: -1.39%.
- EXP-009 direction error: 19.03%.
- EXP-009 verdict: A2, valid experiment with no meaningful improvement.
- Session E candidate rows/images: 6379 rows / 19137 images.
- Session E missing/corrupt images: 0 / 0.
- Session E near-zero / left / right / strong: 46.59% / 26.09% / 27.32% / 9.72%.
- Session E verdict: E2, valid but not ideal.
- Session E freeze decision: not frozen as the final independent test set.
- Session E2 target folder: `data/processed/simulator_v2/session_e2_independent_test/`.
- Session E2 recording status: pending.
- Session E2 target: 5000-7000 rows, near-zero 30%-42%, left/right both above 22%, strong turns at least 15%.

Blocking issues:

- Local v2 underperformed v1 historically on MAE and RMSE.
- Local V2 Session C2 metrics are contaminated historical context, not clean holdout evidence.
- Local V3 did not beat the zero-steering MAE baseline on Session C2.
- EXP-007 did not beat the zero-steering MAE baseline on Session C2.
- EXP-007 right MAE regressed slightly versus the Local V3 baseline.
- EXP-008 right MAE and direction error regressed versus the Local V3 baseline.
- EXP-008 zero-baseline improvement is too small for release consideration.
- EXP-009 cnn_v2 regressed MAE, right MAE, strong-turn MAE, std ratio, zero-baseline improvement, and direction error versus the Local V3 baseline.
- EXP-014 External Mix V1 improved strong-turn MAE and std ratio but regressed overall MAE, RMSE, right MAE, zero-baseline comparison, and direction error versus Local V3.
- EXP-019 Kaggle Jungle Mix V1 improved RMSE, right/strong-turn MAE, std ratio, and direction error, but overall MAE and zero-baseline comparison regressed slightly.
- Kaggle licensing is unresolved, so the EXP-019 checkpoint cannot be released or publicly promoted.
- Local V3 strong-turn error remains high.
- The Session C2 holdout has now been used for multiple model-selection decisions; further tuning should wait for an independent Session E test set.
- Current Session E candidate is too straight-heavy and has too little strong-turn coverage for final frozen-test status.
- Session E2 has not been recorded or validated yet.
- Temporal prediction stability has not been measured.
- No current checkpoint has passed release gates.

## External Dataset Gate

- [x] External Udacity-format source has recorded provenance and SHA-256.
- [x] External archive extraction was zip-slip protected and structure verified.
- [x] External image references and steering labels were validated.
- [x] External Mix V1 candidate was built and passed automated M1 integrity, cap, balance, and forbidden-session gates.
- [x] External Mix V1 balancing policy was reviewed for EXP-014.
- [x] External data was explicitly used in one controlled offline experiment.
- [x] EXP-014 used the fixed baseline configuration and complete Session C2 validation manifest without leakage.
- [x] Better external sources were scored by label quality, distribution potential, access, domain, conversion, and license risk.
- [x] Kaggle Udacity archive is acquired with provenance and SHA-256.
- [x] Every Kaggle track passed schema and image-integrity validation.
- [x] Kaggle tracks received separate distribution verdicts: jungle K1, `make` K2.
- [x] A center-only jungle candidate manifest is built and passed J1 integrity/provenance checks.
- [x] Kaggle Jungle Mix V1 is built and passed KM1 integrity, preservation, balance, and exclusion checks.
- [x] Kaggle Jungle Mix V1 received controlled local research training approval for EXP-019.
- [x] EXP-019 used the fixed baseline configuration and complete Session C2 manifest without leakage.
- [ ] Kaggle dataset-specific license/terms are resolved.
- [ ] EXP-019 is evaluated on a future frozen independent Session E2 test set.
- [ ] An external-data checkpoint passes model-promotion gates.

The source retains X2 status: 60.74% near-zero steering and 0.55% strong turns. EXP-014 trained the ignored 13,657-row External Mix V1 candidate once and received EM2, valid experiment with no meaningful improvement. Session C2 MAE/RMSE were 0.216895/0.319567; strong-turn MAE improved, but overall MAE, RMSE, right MAE, zero-baseline comparison, and direction error regressed versus Local V3. That checkpoint remains unpromoted and was not used for the later EXP-027 simulator run.

EXP-016 manually ingested and validated the Kaggle source; EXP-017/018 built J1/KM1 candidates. EXP-019 then trained the mix once. Its KJM3 result improved RMSE, right/strong-turn error, variance ratio, and direction error, but overall MAE and zero-baseline comparison regressed slightly. Session C2 is repeatedly reused, licensing is unresolved, the checkpoint is not promoted, and no release/control gate changes.

## Udacity CH2_002 Gate

- [x] Archive size and SHA-256 verified.
- [x] TAR structure received A1 safety verdict.
- [x] Five ROS1 bags are readable with 0 skipped messages.
- [x] Center/left/right cameras decode as 640 x 480 JPEG/BGR8.
- [x] Measured steering-wheel angle and radian unit are identified from the ROS schema.
- [x] Camera/steering synchronization received S1 in every bag.
- [x] A 500-frame ignored sample passed image, provenance, raw-steering, and timestamp validation.
- [ ] Dataset license and redistribution terms are resolved.
- [ ] Full conversion receives separate approval and full-output validation.
- [ ] Any simulator target mapping from physical radians is documented and validated.
- [ ] Real-world domain data receives a separate training and evaluation protocol.

EXP-020 verdict C2A1 is a conversion-research result only. It does not promote any checkpoint, satisfy an independent Session E2 model test, authorize training, or change the current no-control release decision.

## Closed-Loop Diagnostic Gate

- [x] Correct Behavioral Cloning simulator executable and EIO4 protocol identified.
- [x] Checkpoint loads before the server binds.
- [x] Checkpoint architecture and preprocessing metadata are reused.
- [x] Steering is finite-checked, clipped, and smoothed.
- [x] Default throttle is limited to 0.10.
- [x] Dry-run cannot emit non-zero steering or throttle.
- [x] Missing/corrupt frames, non-finite predictions, and repeated failures command zero throttle.
- [x] Ctrl+C and an emergency-stop file have neutral-command shutdown paths.
- [x] Runtime CSV/JSON artifacts are ignored.
- [x] Local real-checkpoint self-test and server bind passed.
- [x] Live Unity dry-run receives and logs center-camera telemetry with UC1.
- [x] Bounded max-runtime shutdown sends neutral control in the connected Unity session.
- [x] One supervised 20-second active diagnostic completed without an operational inference failure.
- [ ] Temporal stability and oscillation metrics are reviewed afterward.

The diagnostic gate does not promote KJM3, resolve Kaggle licensing, prove a lap, certify safety, or approve real-world autonomous operation.
