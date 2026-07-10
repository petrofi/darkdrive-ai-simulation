# External Dataset Candidate Registry

This registry scores possible future DarkDrive data sources before any download, conversion, merge, training, or checkpoint evaluation. Registry inclusion does not approve a dataset for training.

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
| 4 | `kaggle_udacity_behavioral_cloning_lake_jungle` | Best next access target; manually download, then extract and validate every track before any manifest work. |
| 3 | `donkeycar_tubs_public` | Potential image/control source, but Kaggle access, tub conversion, steering scale, domain, and license require review. |
| 3 | `donkeycar_autorope_datasets` | Public Git LFS tub repository with known DonkeyCar 4.x format; conversion and license review required. |
| 3 | `carla_generated_future` | Best controlled generation route later, but too heavy for the current external-download task. |
| 2 | `comma2k19_real_world` | Valuable domain-adaptation research source, not an immediate simulator behavior-cloning dataset. |

No candidate receives score 5 because none is both immediately accessible and already verified for licensing, steering distribution, image integrity, and DarkDrive-compatible controls.

## `kaggle_udacity_behavioral_cloning_lake_jungle`

| Field | Assessment |
| --- | --- |
| Dataset ID | `kaggle_udacity_behavioral_cloning_lake_jungle` |
| Source name | Kaggle: Udacity Self Driving Car - Behavioural Cloning |
| Source URL | <https://www.kaggle.com/datasets/andy8744/udacity-self-driving-car-behavioural-cloning> |
| Access method | Kaggle browser or Kaggle CLI; credentials required for CLI download |
| Expected format | Reported simulator camera images and CSV-style driving metadata; possible lake/jungle track folders; not locally verified |
| Expected labels | Steering angle and camera paths; throttle/brake/speed availability must be inspected after download |
| License/terms status | Dataset-specific license was not visible through the unauthenticated review; unresolved until the Kaggle data card is reviewed by the human downloader |
| Domain similarity | High: Udacity simulator behavior cloning is closest to DarkDrive's current image/steering pipeline |
| Expected steering-label quality | Promising, but label schema, scale, duplication, and synchronization are unverified |
| Expected curve/strong-turn usefulness | Potentially useful if multiple tracks add curves; actual distribution is unknown and may still be straight-heavy |
| Download difficulty | Medium: Kaggle account/API credentials required; no CLI or credentials were available on 2026-07-10 |
| Conversion difficulty | Low to medium if Udacity-style; higher if multiple schemas or nested tracks differ |
| Direct training suitability | No. Each track requires checksum, safe extraction, schema detection, image validation, distribution review, and a future mix decision |
| Risk notes | Unverified license, unknown distribution, possible multiple roots, possible near-zero dominance, and unavailable access |
| Priority score | 4 |

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

The Kaggle Udacity source is the best next practical access target, but score 4 rather than 5 reflects missing credentials, unverified license terms, and unknown per-track steering distributions. No dataset should enter a training manifest until its actual files, labels, provenance, license notes, and distribution pass review.
