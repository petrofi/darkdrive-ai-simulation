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
