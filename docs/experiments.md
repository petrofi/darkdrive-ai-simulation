# Experiments

This file is the experiment tracking ledger for DarkDrive AI Simulation.

## Required Experiment Fields

Each future experiment must record:

- Experiment ID
- Dataset
- Epochs
- Learning Rate
- Architecture
- Validation Loss
- MAE
- RMSE
- Observations
- Next Action

## Experiment Table

| Experiment ID | Dataset | Epochs | Learning Rate | Architecture | Validation Loss | MAE | RMSE | Observations | Next Action |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | --- | --- |
| EXP-001-baseline-sim-v1 | `data/processed/simulator/driving_log.csv`, 3706 samples, center camera only | 10 | 0.001 | Compact PyTorch CNN, ELU, dropout | 0.060776 | 0.174045 | 0.246529 | Learned real steering signal, but labels are 55.42% near zero and MAE improves only 9.95% over zero baseline. | Collect balanced recovery dataset before simulator control. |
| EXP-002-merged-dataset-bc-v1 | Local Udacity simulator data + external behavior cloning dataset | 15 planned | 0.001 initial | Same as EXP-001 | TBD | TBD | TBD | Goal: reduce always-zero steering bias and improve turning prediction. Record rows, near-zero percentage, validation loss, MAE, RMSE, and notes. | Build merged dataset with `scripts/build_merged_training_dataset.py`, then train `steering_model_merged_v1.pt`. |
| EXP-003-local-simulator-v2-recovery | `data/processed/local_v2_training/driving_log.csv`, 8647 samples, center camera only, Dataset v1 + Sessions A/B/C2 | 15 | 0.001 | Same as EXP-001 | 0.092040 | 0.211307 | 0.303382 | Dataset distribution improved: near-zero 34.99%, right steering 29.73%, strong turns 18.53%. Model underperformed v1 and under-predicted right/strong turns. | Do not release. Collect Session D curve-focused data before another local v2 training run. |
| EXP-004-session-d-curve-focused-data | `data/processed/simulator_v2/session_d_curve_focused/driving_log.csv`, 7721 rows, 23163 images | N/A | N/A | Dataset collection and validation only | N/A | N/A | N/A | Hypothesis: sustained curve data will address steering magnitude under-prediction. Distribution: 22.00% near-zero, 47.07% left, 30.93% right, 24.83% strong turns, 0 missing/corrupt images. Temporal analysis found 210 sustained medium steering runs and 80 sustained strong steering runs. Verdict: strong curve-focused session, left-heavy but useful. | Include in Local V3 plan with Session C2; do not train until the dataset build and session-aware split are reviewed. |
| EXP-005-local-v3-session-aware-dataset-build | Train: `data/processed/local_v3_training/train.csv`, 10657 rows, center camera only; validation: complete `session_c2_right_recovery`, 4163 rows | N/A | N/A | Dataset build and validation only | N/A | N/A | N/A | Hypothesis: a session-aware V3 split can reduce near-zero bias, preserve strong turns, and avoid random adjacent-frame leakage. Train distribution: 28.72% near-zero, 35.86% left, 35.41% right, 27.20% strong turns. Leakage checks: 0 source-session, image-path, filename, and CSV-row overlap. Verdict: A, ready for session-aware training. | Extend training/evaluation CLIs to accept explicit train/validation CSV files, then train `steering_model_local_v3.pt`. |
| EXP-006-local-v3-session-aware-training | Train: `data/processed/local_v3_training/train.csv`, 10657 rows; validation: complete `session_c2_right_recovery`, 4163 rows | 15 | 0.001 | Same compact PyTorch CNN as EXP-001/003, 188219 parameters | 0.100252 | 0.215618 | 0.316627 | Explicit split training worked, but the model did not beat the zero-steering baseline. Strong-turn MAE was 0.598862, right MAE was 0.249182, prediction std was 0.228446 versus actual std 0.347744, and MAE was 0.72% worse than the zero-steering baseline. Local V2's lower Session C2 score is historical context only because Session C2 contributed to Local V2 training. Verdict: R2, valid offline experiment, not promoted. | Do not release. Review prediction samples and test preprocessing/loss/architecture changes as separate fixed-split experiments. |
| EXP-007-road-focused-crop-preprocessing | Train: `data/processed/local_v3_training/train.csv`, 10657 rows; validation: complete `session_c2_right_recovery`, 4163 rows; preprocessing `road_crop_v1` y=[55,150) before resize | 15 | 0.001 | Same compact PyTorch CNN as EXP-006, 188219 parameters | 0.094317 | 0.215280 | 0.307111 | One-variable preprocessing experiment. RMSE, strong-turn MAE, direction error, and std ratio improved, but MAE improved only 0.000338, right MAE regressed slightly to 0.249969, near-zero MAE regressed to 0.151936, and the model still missed the zero-steering baseline by 0.56%. Verdict: P2, valid experiment with no meaningful improvement. | Do not release and do not run another crop variant against Session C2. Next single-variable experiment: Huber loss on the same fixed split. |
| EXP-008-huber-loss-smoothl1 | Train: `data/processed/local_v3_training/train.csv`, 10657 rows; validation: complete `session_c2_right_recovery`, 4163 rows; baseline preprocessing; SmoothL1Loss beta=1.0 | 15 | 0.001 | Same compact PyTorch CNN as EXP-006, 188219 parameters | 0.049741 | 0.213646 | 0.320153 | One-variable loss experiment. MAE improved slightly, zero-baseline improvement became +0.20%, strong-turn MAE improved to 0.575495, and std ratio improved to 0.705915. However RMSE worsened, right MAE regressed materially to 0.276358, and direction error regressed to 17.44%. Verdict: H2, valid experiment with no meaningful improvement. | Do not release and do not run another loss variant. Next single-variable experiment: slightly stronger CNN architecture on the same fixed split. |
| EXP-009-slightly-stronger-cnn-architecture | Train: `data/processed/local_v3_training/train.csv`, 10657 rows; validation: complete `session_c2_right_recovery`, 4163 rows; baseline preprocessing; MSE loss | 15 | 0.001 | `cnn_v2` / `SteeringModelV2`, 726103 parameters, BatchNorm2d + ELU conv stack | 0.098543 | 0.217054 | 0.313915 | One-variable architecture experiment. RMSE improved slightly, but MAE regressed, right MAE regressed to 0.261968, strong-turn MAE regressed to 0.612222, std ratio fell to 0.599089, zero-baseline comparison worsened to -1.39%, and direction error regressed to 19.03%. Verdict: A2, valid experiment with no meaningful improvement. | Do not release and do not run another architecture variant against Session C2 in this task. Next single step: collect an independent Session E test set before further model-selection work. |
| EXP-010-session-e-independent-test-set-validation | `data/processed/simulator_v2/session_e_independent_test/`, 6379 rows, 19137 images, intended frozen independent test session | N/A | N/A | Dataset validation only | N/A | N/A | N/A | Session E validates technically: 0 missing/corrupt images, 0 duplicate rows, balanced left/right steering at 26.09% / 27.32%, and PASS validator result. Distribution is not ideal for a final frozen test set: near-zero is 46.59% and strong turns are 9.72%. Verdict: E2, valid but not ideal. No training or model evaluation was run. | Do not freeze this recording as the final independent test set. Re-record a Session E2 candidate with less straight-only driving and at least 15% strong-turn coverage. |
| EXP-011-session-e2-independent-test-set-prep | Target: `data/processed/simulator_v2/session_e2_independent_test/`, intended replacement candidate for Session E | N/A | N/A | Dataset preparation only | N/A | N/A | N/A | Session E2 folder and `IMG/` subfolder prepared. Recording is pending; no `driving_log.csv` or images exist yet. Session E2 must not be used for training, validation, tuning, crop/loss/architecture selection, or repeated model selection. No validation, training, or model evaluation was run. | Human must record Session E2 in the Udacity simulator by selecting `session_e2_independent_test` directly. Target 5000-7000 rows, near-zero 30%-42%, left/right both above 22%, and strong turns at least 15%. |
| EXP-012-external-udacity-dataset-ingestion | Public Udacity-format source, 8,036 rows and 24,108 images; raw and manifests ignored | N/A | N/A | Download, extraction, and validation only | N/A | N/A | N/A | Archive SHA-256 recorded; all center/left/right references resolved; 0 missing/corrupt images, duplicates, and invalid/out-of-range labels. Verdict X2 because near-zero steering is 60.74% and strong turns are only 0.55%. No training or model evaluation was run. | Build an External Mix V1 training candidate for review with explicit balancing; do not train it yet. |
| EXP-013-external-mix-v1-training-candidate | Local V3 train, 10,657 rows, plus a deterministic 3,000-row center-camera subset of `udacity_behavioral_cloning_public`; generated candidate ignored | N/A | N/A | Dataset build and validation only | N/A | N/A | N/A | Hypothesis: a capped external subset can add visual diversity without destroying Local V3 curve strength. External cap strategy: seed 42, at most 25% of final rows, external near-zero at most 25%, balanced left/right, strong turns retained first. Final 13,657-row distribution: 27.91% near-zero, 36.22% left, 35.87% right, and 21.55% strong turns. Integrity checks found 0 missing/corrupt images, duplicate rows/paths, invalid labels, or forbidden sessions. Verdict M1, ready for human review. No training or model evaluation was run during this build task. | Completed as the one-run EXP-014 controlled training experiment; the resulting EM2 checkpoint was not promoted. |
| EXP-014-external-mix-v1-training | External Mix V1 train, 13,657 rows, versus complete 4,163-row Session C2 validation manifest | 15 | 0.001 | Baseline `SteeringModel`, 188,219 parameters | 0.102123 best | 0.216895 | 0.319567 | One-variable design: only training data changed from Local V3 to External Mix V1. Baseline preprocessing, MSE, AdamW, batch 32, seed 42, CPU, and augmentation policy stayed fixed. External data was capped at 3,000 rows / 21.97%. Right MAE 0.251651, strong-turn MAE 0.579000, std ratio 0.700562, zero-baseline comparison -1.31%, direction error 17.11%. Verdict EM2: valid, no meaningful improvement. | Do not promote or tune again on Session C2. Collect and validate Session E2 as an independent test candidate. |
| EXP-015-better-external-dataset-scout | Five documented external-source candidates; no data downloaded or merged | N/A | N/A | Dataset governance and access research only | N/A | N/A | N/A | Previous external data was structurally valid but straight-heavy, and EXP-014 returned EM2. Candidate scoring prioritized steering-label/distribution quality over size. Kaggle Udacity scored 4/5 as the best next access target; Kaggle CLI and credentials were unavailable, so download, extraction, validation, training, and evaluation were not performed. | Human manually downloads the Kaggle archive to the documented ignored folder, records SHA-256, then reruns multi-track extraction and validation. |
| EXP-016-kaggle-udacity-dataset-validation | Manually downloaded Kaggle Udacity ZIP; two extracted tracks, raw/generated artifacts ignored | N/A | N/A | Multi-track dataset validation only | N/A | N/A | N/A | ZIP SHA-256 recorded. Jungle: 3,404 rows/10,212 images, 47.00% near-zero, 25.88% left, 27.12% right, 26.38% strong, K1. `make`: 3,930 rows/11,790 images, 80.41% near-zero, 16.87% left, 2.72% right, 1.88% strong, K2. Both tracks have 0 missing/corrupt images, duplicates, or invalid labels. No training/evaluation/merge. | Build and review a jungle-only candidate manifest in a later task; keep `make` excluded by default and do not train yet. |
| EXP-017-kaggle-jungle-candidate-manifest | Complete `self_driving_car_dataset_jungle`, 3,404 center-camera rows; generated outputs ignored under `data/processed/external/kaggle_jungle_candidate/` | N/A | N/A | Dataset manifest build and validation only | N/A | N/A | N/A | All source rows retained in order with original camera references as provenance. Full center-image scan and manifest checks found 0 missing/corrupt images, duplicate rows/paths/filenames, invalid labels, `make` rows, or Session C2/E/E2 rows. Distribution exactly preserves EXP-016: 47.00% near-zero, 25.88% left, 27.12% right, 26.38% strong. Verdict J1, ready for review. No training, evaluation, or Local V3 merge. | Review the manifest, then design a controlled Kaggle Jungle Mix V1 candidate in a later task; resolve licensing and keep `make` excluded. |
| EXP-018-kaggle-jungle-mix-v1-training-candidate | All 10,657 Local V3 training rows plus all 3,404 Kaggle Jungle center-camera rows; ignored output `data/processed/kaggle_jungle_mix_v1_training/` | N/A | N/A | Dataset mix build and validation only | N/A | N/A | N/A | Hypothesis: the strong Jungle distribution can add external visual diversity without diluting Local V3 curve strength. Final 14,061 rows are 24.21% external, 33.15% near-zero, 33.45% left, 33.40% right, and 27.00% strong. All source rows/order preserved; 0 missing/corrupt images, duplicate paths, invalid labels, `make` rows, or Session C2/E/E2 rows. Verdict KM1. No training or checkpoint evaluation. | Human reviews the mix and unresolved license gate before one later controlled training experiment. |
| EXP-019-kaggle-jungle-mix-v1-training | Kaggle Jungle Mix V1 train, 14,061 rows, versus complete 4,163-row Session C2 validation manifest | 15 | 0.001 | Baseline `SteeringModel`, 188,219 parameters | 0.095746 best | 0.216064 | 0.309429 | One-variable data experiment: baseline/MSE/AdamW/weight decay/batch/seed/CPU/augmentation fixed. Right MAE 0.242521, strong-turn MAE 0.559137, std ratio 0.711011, zero-baseline comparison -0.93%, direction error 16.17%. Versus Local V3, RMSE, right/strong MAE, std ratio, and direction error improved; MAE and zero-baseline comparison regressed slightly. Verdict KJM3, useful offline improvement. Licensing unresolved; checkpoint not promoted. | Collect and validate Session E2 before further model-selection or Kaggle-training decisions. |
| EXP-020-udacity-ch2-002-phase-a-ingestion | `udacity_ch2_002`, five ROS1 bags, bounded 500-frame sample | N/A | N/A | Archive, bag, semantics, and synchronization inspection only | N/A | N/A | N/A | A1 archive; 5/5 bags and 6,985,240 messages readable; measured steering-wheel radians; S1 camera/steering sync; 500/500 sample images readable. Verdict C2A1. No full conversion, training, or evaluation. | Run a separately governed full-conversion and normalization task; do not train yet. |
| EXP-021-closed-loop-simulator-demo-v1 | Live Udacity Behavioral Cloning center-camera telemetry with ignored KJM3 checkpoint | N/A | N/A | EIO4 Socket.IO + baseline SteeringModel inference runtime | N/A | N/A | N/A | Implemented checkpoint-aware center-camera inference, clipping, EMA smoothing, low throttle, dry-run neutral commands, emergency stop, reconnect handling, and CSV/JSON telemetry. Local self-test: finite -0.110780 prediction at 4.886 ms CPU. Server bind test passed. Live Unity telemetry and movement not yet tested. | Human runs live dry-run, verifies emergency stop and logs, then performs at most one supervised 60-second active diagnostic. |
| EXP-025-simulator-protocol-diagnostics | Established Unity TCP connection with zero telemetry frames; no dataset used | N/A | N/A | EIO4 Socket.IO protocol diagnostics only | N/A | N/A | N/A | Added bounded, image-redacting Engine.IO/Socket.IO diagnostics, explicit `/` handlers, protocol counters, and P1-P6 verdicts. No Unity session, inference experiment, training, checkpoint change, or active control was run. | Repair `C:\venvs\darkdrive-sim`, run the documented 20-30 second dry-run, and inspect the protocol log plus ignored JSON summary. |
| EXP-022-left-right-camera-correction | Planned: Local V3 plus side-camera correction | TBD | 0.001 initial | Same as EXP-001 | TBD | TBD | TBD | Test correction magnitude around 0.15 to 0.25 after verifying steering sign convention. | Compare against Local V3 center-only result after a fresh independent test set is available. |
| EXP-023-nvidia-bc-cnn | Planned: fixed Local V3 split | TBD | TBD | NVIDIA Behavioral Cloning style CNN | TBD | TBD | TBD | Architecture comparison after data improvement and a fresh independent test set. | Compare against same-data compact CNN. |
| EXP-024-temporal-stability | Planned: held-out validation videos | TBD | TBD | Best single-frame model plus smoothing/frame stacking candidate | TBD | TBD | TBD | Measure oscillation, steering delta, and lag. | Decide if model can enter simulator-only closed-loop test. |

## Experiment Template

Copy this row for new experiments:

| Experiment ID | Dataset | Epochs | Learning Rate | Architecture | Validation Loss | MAE | RMSE | Observations | Next Action |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | --- | --- |
| EXP-YYYY-NN-name | Dataset path, sample count, camera usage, split policy | 0 | 0.000 | Architecture name | 0.000000 | 0.000000 | 0.000000 | Key result and failure mode. | Keep, reject, or run next experiment. |

## Recommended Extra Metadata

The required table is the minimum. For research-grade comparison, also record:

- Date.
- Git commit hash.
- Random seed.
- Batch size.
- Weight decay.
- Loss function.
- Augmentation settings.
- Image size.
- Crop policy.
- Validation split method.
- Checkpoint path.
- Training chart path.
- Prediction plot path.
- Dataset analysis plot paths.

## Experiment Rules

- Do not compare architectures using different validation splits.
- Do not compare data strategies without naming the dataset version.
- Do not report validation loss without MAE and RMSE.
- Do not treat offline evaluation as proof of simulator driving readiness.
- Keep generated checkpoints out of Git unless a deliberate model-release policy is added later.
- Prefer one major change per experiment.

## Baseline Interpretation

EXP-001 is a valid baseline, not a release model.

Reasons:

- It uses real simulator data.
- It has validated images and labels.
- It has offline MAE/RMSE.
- It does not have recovery-heavy training data.
- It does not have session-level validation.
- It does not have temporal stability evaluation.

## EXP-020 - Udacity CH2_002 Phase-A Ingestion

Status: complete, C2A1.

Changed factor: ingest and inspect one external real-world ROS1 archive without full conversion or training.

- Archive: 4,716,005,956 bytes; SHA-256 matched `E7FB718AA2646F40FAF9E194E715551FFCEDCD729FA1C5CA2F428E197098743D`.
- TAR: A1, 6 regular members and 6,236,839,127 extracted bytes.
- Bags: 5/5 ROS1 v2.0 readable; 6,985,240 messages; 0 skipped.
- Camera: center/left/right 640 x 480 compressed JPEG streams decode successfully.
- Steering: measured `/vehicle/steering_report.steering_wheel_angle` in documented radians; no simulator normalization.
- Synchronization: S1 in all bag/camera pairs; center global match 100%, median 4.995 ms, p95 9.519 ms.
- Sample: 500 center frames, 500 readable, 0 missing/unreadable/duplicates/invalid raw steering.
- Verdict: C2A1, strong full-conversion candidate only.
- Training/evaluation: none; no dataset merge, checkpoint comparison, or control implementation.
- License/domain: unresolved license; real-world offline data, not simulator data.

Next step: run a separate full conversion and normalization-governance task before any training proposal.

## EXP-021 - Closed-Loop Simulator Demo V1

Status: implementation and local dry-run preparation complete; live Unity diagnostic pending.

- Protocol: installed simulator assembly verified as EIO4 WebSocket on port 4567 with `telemetry` and `steer` events.
- Model: ignored KJM3 baseline checkpoint, loaded once in eval/inference mode.
- Preprocessing: checkpoint-selected baseline RGB 160 x 80 pipeline.
- Controls: throttle 0.10 default, steering clip 1.0, EMA alpha 0.35.
- Safety: neutral on frame/model/control failure, repeated-failure latch, dry-run neutral-only, Ctrl+C and stop-file emergency shutdown.
- Telemetry: ignored per-frame CSV and JSON session summary.
- Tests: 13 focused runtime tests; complete suite 116 tests after final update.
- Local self-test: finite raw steering -0.110780, 4.886 ms CPU inference, neutral command only.
- Server bind: EIO4 runtime bound and stopped cleanly under a one-second dry-run limit.
- Active driving: not tested; no lap claim.

Next step: human starts Unity Autonomous mode and completes dry-run acceptance before any supervised active command.

## EXP-025 - Simulator Protocol Diagnostics

Status: implementation and local tests complete; live Unity evidence pending.

Failure reproduced from existing artifacts: TCP established on port 4567 while the latest telemetry CSV remained header-only and all frame counters stayed at zero. This proves no inference attempt occurred and keeps the issue at the simulator integration layer.

- Changed factor: protocol visibility only.
- Protocol: Unity assembly declares EIO4; current package metadata is Socket.IO 5.16.3 and Engine.IO 4.13.3.
- Diagnostics: redacted low-level loggers, query/EIO/transport/SID lifecycle, explicit `/` events, alternate namespace/event capture, eight counters, and P1-P6 verdict.
- Safety: dry-run command only; initial and subsequent controls remain neutral; no active test was performed.
- Data/model: no dataset, training, evaluation, checkpoint update, or promotion.
- Environment limitation: `C:\venvs\darkdrive-sim` cannot currently launch because its recorded base Python executable is missing.

Next step: repair the target environment, run the exact documented dry-run for 20-30 seconds with Unity Autonomous Mode, then classify the result using P1-P6 from the protocol log and ignored summary.
