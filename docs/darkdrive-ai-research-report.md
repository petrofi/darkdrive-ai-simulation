# DarkDrive AI Research Report

## Current Maturity Level

DarkDrive is at Simulator Training Baseline maturity.

The project has moved beyond infrastructure. It has real simulator data, a trained behavior cloning model, and offline evaluation. It has not reached simulator-driving readiness.

Research verdict: accept as a baseline, reject as a control model.

## Current Strengths

- OpenCV lane detection works.
- Simulator data collection works.
- Dataset validation works.
- Real Udacity-style simulator data exists.
- Training pipeline is functional.
- Evaluation pipeline is functional.
- The model learns real steering signal.
- Repository safety boundaries are clear.
- Checkpoints and generated datasets are not committed.

## Current Weaknesses

- Dataset is too centered around zero steering.
- 55.42% of labels have abs(steering) <= 0.05.
- p25, median, and p75 steering are all exactly 0.0.
- Recovery driving is not documented.
- Off-center correction behavior is not documented.
- Current model uses only the center camera.
- Validation split is random row-based, which may leak adjacent-frame similarity.
- Offline MAE improves only 9.95% over always predicting zero.
- Prediction variance is lower than actual variance, suggesting conservative steering.
- Temporal stability and oscillation have not been measured.

## Biggest ML Bottleneck

The biggest bottleneck is dataset coverage, not CNN size.

The current dataset mostly teaches normal centered driving. A closed-loop model will inevitably drift into off-center states, and the current training data does not sufficiently teach recovery behavior. A larger model cannot reliably fix missing supervision.

## Highest Impact Next Experiment

Run `EXP-002-balanced-recovery-dataset`.

Plan:

- Collect 8000 to 12000 more center-labeled simulator samples.
- Include left-offset and right-offset recovery.
- Include curve-heavy sections.
- Hold out a full session for validation.
- Train the same current CNN first.
- Compare against EXP-001 before changing architecture.

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

