# External Dataset Candidate Registry

This registry scores possible and ingested DarkDrive data sources before any conversion, merge, training, or checkpoint evaluation decision. Registry inclusion or validation does not approve a dataset for training.

## Selection Principle

The next dataset should not be selected by size. It should be selected by steering-label quality and distribution.

Useful data must provide camera-image references and steering labels, preferably with throttle, brake, and speed. It must also add meaningful non-zero, left, right, curve, or recovery behavior. A large source dominated by straight driving can weaken the training signal even when its files are technically valid.

Priority scores:

- 5: best immediate candidate
- 4: promising but needs credentials or conversion
- 3: useful later
- 2: research-only or high conversion risk
- 1: unsuitable for current DarkDrive training

## Priority Summary

| Priority | Dataset ID | Immediate decision |
| ---: | --- | --- |
| 5 | `kaggle_udacity_behavioral_cloning_lake_jungle` | Manually ingested and validated; the jungle-only center manifest passed J1, while `make` remains excluded. Review before any controlled mix. |
| 3 | `donkeycar_tubs_public` | Potential image/control source, but Kaggle access, tub conversion, steering scale, domain, and license require review. |
| 3 | `donkeycar_autorope_datasets` | Public Git LFS tub repository with known DonkeyCar 4.x format; conversion and license review required. |
| 3 | `carla_generated_future` | Best controlled generation route later, but too heavy for the current external-download task. |
| 2 | `comma2k19_real_world` | Valuable domain-adaptation research source, not an immediate simulator behavior-cloning dataset. |

The Kaggle source remains score 5 because it contains a verified K1 track and a J1 candidate manifest. Training approval, controlled mix design, human review, and license resolution remain separate gates.

## `kaggle_udacity_behavioral_cloning_lake_jungle`

| Field | Assessment |
| --- | --- |
| Dataset ID | `kaggle_udacity_behavioral_cloning_lake_jungle` |
| Source name | Kaggle: Udacity Self Driving Car - Behavioural Cloning |
| Source URL | <https://www.kaggle.com/datasets/andy8744/udacity-self-driving-car-behavioural-cloning> |
| Access method | Manually downloaded from Kaggle; ZIP checksummed and stored under ignored external data |
| Expected format | Actual format: two headerless Udacity tracks with center/left/right, steering, throttle, brake, speed, and `IMG/` |
| Expected labels | Verified steering, throttle, brake, and speed for every row in both tracks |
| License/terms status | Unresolved: no license/README/terms file exists in the archive; Kaggle data-card terms require human review |
| Domain similarity | High: Udacity simulator behavior cloning is closest to DarkDrive's current image/steering pipeline |
| Expected steering-label quality | Structurally valid in both tracks; jungle distribution is strong, `make` distribution is weak |
| Expected curve/strong-turn usefulness | Jungle: 26.38% strong turns with balanced directions; `make`: only 1.88% strong and 2.72% right |
| Download difficulty | Completed manually; ZIP is 294,399,633 bytes with recorded SHA-256 |
| Conversion difficulty | Low; EXP-017 normalized producer Windows paths into a center-camera manifest while preserving original references |
| Direct training suitability | No. The jungle manifest is J1 for review only; `make` must not be used wholesale |
| Risk notes | License unresolved; manual extraction safety cannot be verified retroactively; tracks have sharply different quality |
| Priority score | 5 |

Actual validation result:

- `self_driving_car_dataset_jungle`: K1, 3,404 rows, 10,212 images, 47.00% near-zero, 25.88% left, 27.12% right, 26.38% strong turns.
- `self_driving_car_dataset_make`: K2, 3,930 rows, 11,790 images, 80.41% near-zero, 16.87% left, 2.72% right, 1.88% strong turns.
- Both tracks: 0 missing/corrupt images, duplicate rows/paths/filenames, invalid labels, or out-of-range labels.

EXP-017 candidate result:

- `data/processed/external/kaggle_jungle_candidate/` contains ignored manifest, summary, and source-distribution outputs.
- 3,404 center-camera jungle rows; `make` rows: 0; Session C2/E/E2 rows: 0.
- 0 missing/corrupt images, duplicate rows/paths/filenames, or invalid/out-of-range labels.
- Distribution matches EXP-016 exactly. Verdict J1, ready for review; no training or Local V3 merge was performed.

## `donkeycar_tubs_public`

| Field | Assessment |
| --- | --- |
| Dataset ID | `donkeycar_tubs_public` |
| Source name | Kaggle: Donkeycar Tubs |
| Source URL | <https://www.kaggle.com/datasets/vanmil/donkeycar-tubs> |
| Access method | Kaggle browser or CLI |
| Expected format | DonkeyCar tub records/catalogs plus images; exact version is not locally verified |
| Expected labels | Typically image, steering/angle, and throttle; speed may be absent |
| License/terms status | Unverified; the unauthenticated Kaggle page did not expose a dataset-specific license |
| Domain similarity | Medium-low: control-learning format is relevant, but RC/simulator camera domain and geometry may differ |
| Expected steering-label quality | Potentially useful after mapping and scale validation |
| Expected curve/strong-turn usefulness | Unknown until each tub is profiled; racing/track tubs may contain turns but can be one-sided or recovery-poor |
| Download difficulty | Medium: Kaggle access required |
| Conversion difficulty | Medium-high: tub version, catalog schema, image references, and steering range must be detected |
| Direct training suitability | No. Use the converter only after steering sign/range and source provenance are verified |
| Risk notes | License uncertainty, domain gap, unknown tub versions, unknown distribution, and steering scale mismatch |
| Priority score | 3 |

## `donkeycar_autorope_datasets`

| Field | Assessment |
| --- | --- |
| Dataset ID | `donkeycar_autorope_datasets` |
| Source name | `autorope/donkey_datasets` |
| Source URL | <https://github.com/autorope/donkey_datasets> |
| Access method | Public Git repository using Git LFS for large files |
| Expected format | Repository states all tub data is DonkeyCar 4.x format |
| Expected labels | DonkeyCar tub image plus user/pilot steering and throttle fields; inspect manifests/catalogs per tub |
| License/terms status | No dataset license file was visible in the reviewed repository; clarification is required before use beyond local research |
| Domain similarity | Medium-low: behavior-cloning controls are relevant, but the repository's visible datasets are real DonkeyCar tracks, not DarkDrive's Udacity simulator |
| Expected steering-label quality | Potentially useful, with converter support already present in DarkDrive; scale/sign still require validation |
| Expected curve/strong-turn usefulness | Likely track-dependent and unknown until individual tubs are profiled |
| Download difficulty | Medium: Git LFS is required and binary size can be substantial |
| Conversion difficulty | Medium: DarkDrive has a tub converter, but tub-specific schema and steering-scale checks remain mandatory |
| Direct training suitability | No. Convert and validate one named tub first; never mix the repository wholesale |
| Risk notes | No visible dataset license, Git LFS dependency, real RC domain gap, and unknown per-tub distribution |
| Priority score | 3 |

## `comma2k19_real_world`

| Field | Assessment |
| --- | --- |
| Dataset ID | `comma2k19_real_world` |
| Source name | comma.ai comma2k19 |
| Source URL | <https://github.com/commaai/comma2k19> |
| Access method | Official Academic Torrents download linked by the repository; about 100 GB in roughly 10 GB chunks |
| Expected format | HEVC road video, raw/processed logs, CAN, GNSS, IMU, and pose arrays |
| Expected labels | CAN steering angle in degrees and vehicle speed are documented; image/control time alignment requires conversion |
| License/terms status | Repository declares MIT; dataset citation and data-use terms still require confirmation before reuse |
| Domain similarity | Low: real California highway commute data differs substantially from the Udacity simulator |
| Expected steering-label quality | Sensor-rich but not a ready per-frame DarkDrive steering manifest |
| Expected curve/strong-turn usefulness | Likely weak for DarkDrive recovery/strong-turn needs because the source is primarily highway commuting |
| Download difficulty | Very high: about 100 GB and Windows filename workarounds are documented |
| Conversion difficulty | Very high: video decoding, CAN alignment, degree-to-model steering mapping, calibration, and domain-gap analysis |
| Direct training suitability | No. Research/domain-adaptation candidate only |
| Risk notes | Real-world domain, highway bias, large size, complex synchronization, safety-sensitive interpretation, and non-comparable steering scale |
| Priority score | 2 |

## `carla_generated_future`

| Field | Assessment |
| --- | --- |
| Dataset ID | `carla_generated_future` |
| Source name | CARLA Simulator controlled data generation |
| Source URL | <https://github.com/carla-simulator/carla> |
| Access method | Separate CARLA installation and scripted collection task; not a dataset download in this task |
| Expected format | User-defined RGB sensors and synchronized steer/throttle/brake/speed controls |
| Expected labels | Can be generated directly and deterministically from simulator controls |
| License/terms status | CARLA code is MIT, CARLA assets are CC-BY, and Unreal Engine/third-party terms also apply |
| Domain similarity | Medium-high for simulator research, but visually different from the Udacity simulator |
| Expected steering-label quality | High if collection is designed with synchronized controls, provenance, and recovery scenarios |
| Expected curve/strong-turn usefulness | High potential because routes and label distribution can be deliberately controlled |
| Download difficulty | High: current CARLA guidance describes substantial CPU/GPU/RAM requirements |
| Conversion difficulty | High initially; a dedicated exporter and validation pipeline must be designed |
| Direct training suitability | Not yet. Suitable only after a separate controlled collection and conversion project |
| Risk notes | Heavy setup, domain shift, simulator-version complexity, and risk of synthetic scenario bias |
| Priority score | 3 |

## Governance Decision

The Kaggle Udacity source completed access, per-track validation, and a jungle-only J1 candidate build. Its score 5 reflects verified K1 steering coverage, not training approval. License terms remain unresolved, `make` remains excluded, and the next governed action is human manifest review followed by a separately specified controlled mix candidate. No dataset should enter training until provenance, license notes, composition, leakage, and distribution gates pass review.
