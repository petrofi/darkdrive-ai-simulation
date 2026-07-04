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
- [ ] Final training dataset near-zero concentration is acceptable.
- [ ] Validation split is by session, lap, or track segment.
- [ ] Low-speed parked frames are reviewed or filtered.

## Evaluation Gate

- [x] Offline evaluation script runs.
- [x] MAE is reported.
- [x] RMSE is reported.
- [x] Prediction-vs-actual plot is generated.
- [x] Prediction sample grid is generated.
- [x] Evaluation includes zero-steering baseline comparison in the official report.
- [ ] Evaluation includes held-out session results.
- [x] Evaluation includes left/right/strong-turn metrics in the local v2 report.
- [ ] Evaluation includes recovery-case metrics for a release candidate.
- [ ] Evaluation has been repeated with at least two random seeds or fixed held-out sessions.

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

The v1 model met the RMSE improvement target but did not meet the MAE improvement target. The local v2 model underperformed v1 and is not a release candidate.

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

Blocking issues:

- Local v2 underperformed v1 on MAE and RMSE.
- Session-aware Local V3 validation has not been run.
- Temporal prediction stability has not been measured.
- No current checkpoint has passed release gates.
