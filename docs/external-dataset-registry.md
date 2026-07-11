# External Dataset Registry

This registry records the provenance and governance state of external datasets before they can be proposed for a DarkDrive simulator experiment. Registry inclusion does not authorize training, evaluation, data mixing, or simulator control.

## udacity_behavioral_cloning_public

- Dataset ID: `udacity_behavioral_cloning_public`
- Source URL: <https://d17h27t6h515a5.cloudfront.net/topher/2016/December/584f6edd_data/data.zip>
- Source type: public Udacity-format behavioral-cloning simulator dataset.
- Intended use: external simulator training-data candidate for controlled future experiments.
- Current source status: X2 validated on 2026-07-09; valid but unsuitable for direct unbalanced use. External Mix V1 passed M1 candidate checks and was used once in the controlled EXP-014 offline experiment.

Verified ingestion record:

- Downloaded archive: 333,137,665 bytes.
- SHA-256: `7ca6aba7f72df475de32959b3b7a5a825b345c94307e715639dc2a13eb61dd0c`.
- Extracted dataset root: `data/external/udacity_behavioral_cloning_public/extracted/data/`.
- Structure: headered seven-column `driving_log.csv` and `IMG/` directory.
- Validation: 8,036 CSV rows, 24,108 images, 0 missing image references, 0 corrupt images, and 0 invalid or out-of-range steering labels.
- X2 rationale: 60.74% near-zero steering and 0.55% strong-turn steering make the unbalanced source unsuitable for direct augmentation.

External Mix V1 candidate record:

- Output: `data/processed/external_mix_v1_training/` (ignored).
- Policy: seed 42, center camera only, no side-camera offsets or oversampling, at most 25% external data in the final candidate, and at most 25% near-zero rows in the external subset.
- Composition: all 10,657 Local V3 training rows plus 3,000 external rows; 21.97% external share.
- External subset: 750 near-zero, 1,125 left, 1,125 right, and all 44 available strong-turn rows.
- Combined distribution: 27.91% near-zero, 36.22% left, 35.87% right, and 21.55% strong turns.
- Validation: 0 missing/corrupt images, duplicate rows/paths, invalid labels, or forbidden training sessions.
- Candidate-build verdict: M1, candidate ready for review. No training or model evaluation was run during the build task.

EXP-014 controlled-use record:

- Training: exactly one 15-epoch CPU run using the baseline `SteeringModel`, MSE, AdamW, learning rate 0.001, batch 32, and seed 42.
- Validation: complete 4,163-row `session_c2_right_recovery` manifest, with 0 train/validation path or source-session overlap.
- Results: MAE 0.216895, RMSE 0.319567, right MAE 0.251651, strong-turn MAE 0.579000, std ratio 0.700562, zero-baseline comparison -1.31%, and direction error 17.11%.
- Verdict: EM2, valid experiment with no meaningful improvement.
- Promotion: no; checkpoint retained only as an ignored offline artifact.
- Control status: no simulator control was implemented or authorized.

Governance notes:

- External data must not be mixed with internal data without a documented experiment.
- License and usage terms must be reviewed before any public release claim.
- Use is limited to local research until licensing is clarified.
- A SHA-256 checksum must be recorded for each downloaded archive.
- The raw ZIP, extracted data, raw `driving_log.csv`, generated reports, and generated manifests remain ignored by Git.
- A valid result only makes the dataset eligible for a future reviewed experiment; it never authorizes training automatically.

## Better External Candidate Scout

EXP-015 scored five initially un-ingested sources in `docs/external-dataset-candidate-registry.md`:

- `kaggle_udacity_behavioral_cloning_lake_jungle`: originally 4/5; now 5/5 after EXP-016 found one K1 track, EXP-017 built its J1 manifest, and EXP-018 built a KM1 mix candidate.
- `donkeycar_tubs_public`: 3/5, Kaggle tub source requiring access, conversion, scale, and license review.
- `donkeycar_autorope_datasets`: 3/5, DonkeyCar 4.x Git LFS tubs requiring conversion and license clarification.
- `carla_generated_future`: 3/5, future controlled-generation pipeline rather than an immediate download.
- `comma2k19_real_world`: 2/5, real-highway research/domain-adaptation source with high conversion cost.

The other four entries remain candidate records only.

## kaggle_udacity_behavioral_cloning_lake_jungle

- Dataset ID: `kaggle_udacity_behavioral_cloning_lake_jungle`
- Source URL: <https://www.kaggle.com/datasets/andy8744/udacity-self-driving-car-behavioural-cloning>
- Access: manually downloaded and extracted by the human, then relocated from the repository root to ignored external storage.
- ZIP: 294,399,633 bytes.
- SHA-256: `b8bde91d71b4fca7639962eb24374e519cf01dec48650b026079e46ccf74ceba`.
- Extracted files/bytes: 22,004 / 294,206,140.
- Schema: two headerless Udacity tracks with center/left/right, steering, throttle, brake, speed, and local `IMG/` folders.
- License: unresolved; no license/README/terms file was found in the archive.

Track verdicts:

- `self_driving_car_dataset_jungle`: K1, strong external candidate. 3,404 rows, 10,212 images, 47.00% near-zero, 25.88% left, 27.12% right, and 26.38% strong turns.
- `self_driving_car_dataset_make`: K2, valid but weak. 3,930 rows, 11,790 images, 80.41% near-zero, 16.87% left, 2.72% right, and 1.88% strong turns.
- Both tracks have 0 missing/corrupt images, duplicate rows/paths/filenames, invalid labels, or out-of-range labels.

Candidate manifest record:

- Output: `data/processed/external/kaggle_jungle_candidate/` (ignored).
- Policy: all 3,404 jungle rows retained in source order; center camera only; no side-camera offsets; original center/left/right references preserved as provenance.
- Validation: 0 missing/corrupt images, duplicate rows/paths/filenames, invalid/out-of-range labels, `make` rows, or Session C2/E/E2 rows.
- Distribution: 47.00% near-zero, 25.88% left, 27.12% right, and 26.38% strong turns; exact match to EXP-016 validation metadata.
- Controls: throttle, brake, and speed preserved for every row.
- Verdict: J1, jungle candidate manifest ready for review.

Kaggle Jungle Mix V1 candidate record:

- Output: `data/processed/kaggle_jungle_mix_v1_training/` (ignored).
- Policy: retain all 10,657 Local V3 training rows and all 3,404 Jungle rows in source order; no sampling, shuffling, image copying, side-camera offsets, or Local V3 manifest modification.
- Composition: 14,061 rows and 24.21% external.
- Distribution: 33.15% near-zero, 33.45% left, 33.40% right, and 27.00% strong turns.
- Validation: 0 missing/corrupt images, duplicate rows/paths/filenames, invalid/out-of-range labels, `make` rows, Session C2/E/E2 rows, or non-center rows.
- Preservation: all Local V3 and Jungle rows and source order retained exactly.
- Verdict: KM1, Kaggle Jungle Mix V1 candidate ready for review.

EXP-019 controlled-use record:

- Training: exactly one 15-epoch CPU run using baseline `SteeringModel`, baseline preprocessing, MSE, AdamW, learning rate 0.001, weight decay 0.0001, batch 32, and seed 42.
- Validation: complete 4,163-row `session_c2_right_recovery` manifest, with 0 train/validation image-path or source-session overlap.
- Results: MAE 0.216064, RMSE 0.309429, right MAE 0.242521, strong-turn MAE 0.559137, std ratio 0.711011, zero-baseline comparison -0.93%, and direction error 16.17%.
- Controlled comparison: RMSE, right/strong-turn MAE, std ratio, and direction error improved versus Local V3; overall MAE and zero-baseline comparison regressed slightly.
- Verdict: KJM3, useful offline improvement.
- Promotion/release: no; checkpoint retained only as an ignored local research artifact because Session C2 is repeatedly reused and Kaggle licensing is unresolved.
- Control status: no simulator control was implemented or authorized.

Status: one controlled local experiment completed, but the checkpoint is not approved for release or promotion. The K2 `make` track and prior straight-heavy external Udacity source remain excluded. Independent Session E2 evaluation and license resolution remain open gates.

## udacity_ch2_002

- Dataset ID: `udacity_ch2_002`.
- Source type: real-world Udacity Challenge 2 ROS1 driving records.
- Archive: `data/external/udacity_ch2_002/raw/Ch2_002.tar.gz`, 4,716,005,956 bytes.
- SHA-256: `E7FB718AA2646F40FAF9E194E715551FFCEDCD729FA1C5CA2F428E197098743D`.
- Archive verdict: A1, six regular members and no unsafe paths, links, collisions, or special files.
- Bags: five ROS1 v2.0 files, all readable, 6,985,240 total messages, 0 skipped.
- Camera: center/left/right `sensor_msgs/msg/CompressedImage`, 640 x 480 JPEG/BGR8, successful decoding.
- Steering: `/vehicle/steering_report.steering_wheel_angle`, measured steering-wheel angle in documented radians, not a normalized simulator command.
- Synchronization: S1 for every bag and camera; center global match 33,808/33,808, median 4.995 ms, p95 9.519 ms.
- Sample: 500 ignored center-camera rows, 500 readable images, 0 missing/unreadable/duplicates/invalid raw steering values.
- Phase-A verdict: C2A1, strong full-conversion candidate.
- License and redistribution: unresolved; local offline research only.
- Domain: `real_world_offline_dataset`, not equivalent to simulator data.
- Governance: C2A1 does not authorize full conversion, normalization, mixing, training, checkpoint evaluation, release, or control.

Exact next external-data step: a separate full-conversion and normalization-governance task that preserves raw steering radians and resolves licensing before any training proposal.
