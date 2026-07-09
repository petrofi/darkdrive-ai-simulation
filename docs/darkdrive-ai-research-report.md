# DarkDrive AI Research Report

## Current Maturity Level

DarkDrive is at Simulator Training Baseline maturity with a session-aware Local V3 evaluation workflow, one completed Local V3 preprocessing experiment, and one completed Local V3 loss-function experiment.

The project has moved beyond infrastructure. It has real simulator data, trained behavior cloning checkpoints, validated Dataset v2 sessions, and offline evaluation. It has not reached simulator-driving readiness.

Research verdict: accept the pipeline, v1 baseline, Local V2 checkpoint, Local V3 session-aware workflow, EXP-007 road-crop experiment, and EXP-008 Huber-loss experiment as valid offline research artifacts. Reject the current Local V3-family checkpoints as release/control candidates. Local V3 baseline and EXP-007 did not beat the zero-steering MAE baseline on the clean Session C2 holdout. EXP-008 barely beat the zero baseline on MAE, but RMSE, right MAE, and direction error regressed. Local V2's Session C2 score is historical context only because Session C2 contributed to Local V2 training data.

## Current Strengths

- OpenCV lane detection works.
- Simulator data collection works.
- Dataset validation works.
- Real Udacity-style simulator data exists.
- Dataset v2 now includes validated recovery and curve-focused sessions.
- Training pipeline is functional and now supports explicit train/validation manifests.
- Evaluation pipeline is functional and now supports complete-session validation manifests.
- Training, evaluation, and inference now support checkpoint-aware preprocessing profiles.
- Training now supports configurable MSE versus Huber/SmoothL1 regression loss with checkpoint metadata.
- The model learns real steering signal.
- Repository safety boundaries are clear.
- Checkpoints and generated datasets are not committed.

## Current Weaknesses

- The original Dataset v1 is too centered around zero steering.
- The local Dataset v2 model underperformed v1 despite improved aggregate label balance.
- The first Local V3 model did not beat the zero-steering MAE baseline on the clean Session C2 holdout.
- EXP-007 road-focused crop preprocessing did not materially improve Local V3 and still missed the zero-steering baseline.
- EXP-008 Huber loss improved MAE only slightly and regressed RMSE, right MAE, and direction error.
- Local V3 strong-turn MAE is high at 0.598862.
- EXP-007 strong-turn MAE improved to 0.574012 but remains high.
- EXP-008 strong-turn MAE improved to 0.575495 but remains high.
- Local V3 prediction variance remains compressed: prediction/actual std ratio 0.656937.
- EXP-007 prediction/actual std ratio improved only slightly to 0.670205.
- EXP-008 prediction/actual std ratio improved to 0.705915 but remains below the preferred 0.80 candidate range.
- Current model uses only the center camera.
- Older v1 and Local V2 headline evaluations used random row-based splits, which may leak adjacent-frame similarity.
- Local V2 Session C2 metrics are contaminated by Session C2 membership in the Local V2 training dataset.
- Local v2 MAE/RMSE are worse than v1: 0.211307 / 0.303382 versus 0.174045 / 0.246529.
- Local v2 prediction variance is lower than actual variance, suggesting conservative steering.
- Temporal stability and oscillation have not been measured.

## Biggest ML Bottleneck

The biggest bottleneck is dataset coverage, not CNN size.

The immediate bottleneck is now model/data generalization on the fixed Session C2 holdout. Local V3 solved the split-leakage problem, but the compact center-camera CNN still under-predicts steering magnitude and performs poorly on strong turns.

## Highest Impact Next Experiment

Review Local V3 strong-turn failures and run one controlled fixed-split model-quality experiment.

Plan:

- Preserve the Local V3 train/validation split.
- Do not tune repeatedly against Session C2.
- Compare one change at a time against the current Local V3 checkpoint.
- Candidate changes: a slightly stronger behavior-cloning CNN or normalization, tested one at a time.
- Keep side-camera correction as a separate tracked experiment.

This isolates the effect of data quality.

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

Sprint goal: improve model generalization on the fixed Local V3 split without changing multiple factors at once.

Deliverables:

- Failure-sample review for Local V3.
- One fixed-split training experiment with a single planned change.
- Updated experiment table.
- Updated release checklist.
- Decision on whether NVIDIA-style CNN is justified.

Recent EXP-007 result: road-focused crop preprocessing was valid but not useful enough. Recent EXP-008 result: Huber loss was valid but not useful enough because right MAE and direction error regressed. The next exact single-variable recommendation is a slightly stronger CNN architecture on the same fixed Local V3 split.

## Recommended Commit Message

```text
docs: add ML research analysis and release gates
```
