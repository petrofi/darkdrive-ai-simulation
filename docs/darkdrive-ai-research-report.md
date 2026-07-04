# DarkDrive AI Research Report

## Current Maturity Level

DarkDrive is at Simulator Training Baseline maturity.

The project has moved beyond infrastructure. It has real simulator data, trained behavior cloning checkpoints, validated Dataset v2 sessions, and offline evaluation. It has not reached simulator-driving readiness.

Research verdict: accept the pipeline and v1 baseline as valid offline research, reject the current local v2 model as a control model.

## Current Strengths

- OpenCV lane detection works.
- Simulator data collection works.
- Dataset validation works.
- Real Udacity-style simulator data exists.
- Dataset v2 now includes validated recovery and curve-focused sessions.
- Training pipeline is functional.
- Evaluation pipeline is functional.
- The model learns real steering signal.
- Repository safety boundaries are clear.
- Checkpoints and generated datasets are not committed.

## Current Weaknesses

- The original Dataset v1 is too centered around zero steering.
- The local Dataset v2 model underperformed v1 despite improved aggregate label balance.
- Session D is left-heavy and must be balanced carefully in Local V3.
- Current model uses only the center camera.
- Validation split is random row-based, which may leak adjacent-frame similarity.
- Local v2 MAE/RMSE are worse than v1: 0.211307 / 0.303382 versus 0.174045 / 0.246529.
- Local v2 prediction variance is lower than actual variance, suggesting conservative steering.
- Temporal stability and oscillation have not been measured.

## Biggest ML Bottleneck

The biggest bottleneck is dataset coverage, not CNN size.

The immediate bottleneck is now converting the stronger raw sessions into a leak-resistant Local V3 dataset and evaluation protocol. Session C2 adds right-recovery coverage and Session D adds sustained curve/strong-turn coverage, but the next training run must avoid random adjacent-frame validation optimism.

## Highest Impact Next Experiment

Run the Local V3 training dataset build and evaluation plan after review.

Plan:

- Preserve all raw sessions.
- Include Session C2 and Session D.
- Downsample near-zero-heavy v1/A/B rows.
- Preserve `source_session` metadata.
- Hold out a complete session for validation where practical.
- Train the same current CNN first.
- Compare against both v1 and local v2 before changing architecture.

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

Sprint goal: improve the dataset before improving the model.

Deliverables:

- New balanced simulator dataset.
- Dataset analysis report.
- Session-level validation split.
- Retrained compact CNN baseline.
- Updated experiment table.
- Updated release checklist.
- Decision on whether NVIDIA-style CNN is justified.

## Recommended Commit Message

```text
docs: add ML research analysis and release gates
```
