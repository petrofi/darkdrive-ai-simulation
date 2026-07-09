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

The v1 model met the RMSE improvement target but did not meet the MAE improvement target. The local v2 model underperformed v1 historically and is not a release candidate. Local V2's Session C2 score is not treated as an independent holdout result because Session C2 contributed to the Local V2 training dataset. The local v3 model completed session-aware evaluation on Session C2, but did not beat the zero-steering MAE baseline. EXP-007 road-focused crop preprocessing was valid but did not materially improve Local V3.

## Simulator-Control Gate

Simulator control is blocked until:

- [ ] Dataset quality verified.
- [ ] Evaluation complete.
- [ ] Prediction stability acceptable.
- [ ] No obvious steering oscillation.
- [ ] Release notes identify the exact checkpoint and dataset.
- [ ] The implementation remains simulation-only.

## Current Decision

Do not connect the current model to simulator control.

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

Blocking issues:

- Local v2 underperformed v1 historically on MAE and RMSE.
- Local V2 Session C2 metrics are contaminated historical context, not clean holdout evidence.
- Local V3 did not beat the zero-steering MAE baseline on Session C2.
- EXP-007 did not beat the zero-steering MAE baseline on Session C2.
- EXP-007 right MAE regressed slightly versus the Local V3 baseline.
- Local V3 strong-turn error remains high.
- Temporal prediction stability has not been measured.
- No current checkpoint has passed release gates.
