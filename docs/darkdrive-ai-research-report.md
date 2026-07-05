# DarkDrive AI Research Report

## Current Maturity Level

DarkDrive is at Simulator Training Baseline maturity with a session-aware Local V3 evaluation workflow.

The project has moved beyond infrastructure. It has real simulator data, trained behavior cloning checkpoints, validated Dataset v2 sessions, and offline evaluation. It has not reached simulator-driving readiness.

Research verdict: accept the pipeline, v1 baseline, Local V2 checkpoint, and Local V3 session-aware workflow as valid offline research artifacts. Reject the current Local V3 model as a release/control candidate because it did not beat Local V2 on the fair Session C2 holdout.

## Current Strengths

- OpenCV lane detection works.
- Simulator data collection works.
- Dataset validation works.
- Real Udacity-style simulator data exists.
- Dataset v2 now includes validated recovery and curve-focused sessions.
- Training pipeline is functional and now supports explicit train/validation manifests.
- Evaluation pipeline is functional and now supports complete-session validation manifests.
- The model learns real steering signal.
- Repository safety boundaries are clear.
- Checkpoints and generated datasets are not committed.

## Current Weaknesses

- The original Dataset v1 is too centered around zero steering.
- The local Dataset v2 model underperformed v1 despite improved aggregate label balance.
- The first Local V3 model did not improve over Local V2 on the fair Session C2 holdout.
- Local V3 strong-turn MAE is high at 0.598862.
- Local V3 prediction variance remains compressed: prediction/actual std ratio 0.656937.
- Current model uses only the center camera.
- Older v1 and Local V2 headline evaluations used random row-based splits, which may leak adjacent-frame similarity.
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
- Candidate changes: crop/normalization, Huber loss, or a slightly stronger behavior-cloning CNN.
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

## Recommended Commit Message

```text
docs: add ML research analysis and release gates
```
