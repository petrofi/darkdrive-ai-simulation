# External Dataset Registry

This registry records the provenance and governance state of external datasets before they can be proposed for a DarkDrive simulator experiment. Registry inclusion does not authorize training, evaluation, data mixing, or simulator control.

## udacity_behavioral_cloning_public

- Dataset ID: `udacity_behavioral_cloning_public`
- Source URL: <https://d17h27t6h515a5.cloudfront.net/topher/2016/December/584f6edd_data/data.zip>
- Source type: public Udacity-format behavioral-cloning simulator dataset.
- Intended use: external simulator training-data candidate for controlled future experiments.
- Current status: X2 validated on 2026-07-09; valid but requires documented balancing before any future experiment. Not approved for training.

Verified ingestion record:

- Downloaded archive: 333,137,665 bytes.
- SHA-256: `7ca6aba7f72df475de32959b3b7a5a825b345c94307e715639dc2a13eb61dd0c`.
- Extracted dataset root: `data/external/udacity_behavioral_cloning_public/extracted/data/`.
- Structure: headered seven-column `driving_log.csv` and `IMG/` directory.
- Validation: 8,036 CSV rows, 24,108 images, 0 missing image references, 0 corrupt images, and 0 invalid or out-of-range steering labels.
- X2 rationale: 60.74% near-zero steering and 0.55% strong-turn steering make the unbalanced source unsuitable for direct augmentation.

Governance notes:

- External data must not be mixed with internal data without a documented experiment.
- License and usage terms must be reviewed before any public release claim.
- Use is limited to local research until licensing is clarified.
- A SHA-256 checksum must be recorded for each downloaded archive.
- The raw ZIP, extracted data, raw `driving_log.csv`, generated reports, and generated manifests remain ignored by Git.
- A valid result only makes the dataset eligible for a future reviewed experiment; it never authorizes training automatically.
