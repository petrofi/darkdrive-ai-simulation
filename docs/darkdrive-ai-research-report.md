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

No archive was downloaded, no fake metrics were recorded, no data was merged, and no model was trained or evaluated. The external-data next step is manual download and multi-track validation of the named Kaggle candidate. The separate model-selection next step remains Session E2 collection because Session C2 has been reused repeatedly.

## Recommended Commit Message

```text
docs: add ML research analysis and release gates
```
