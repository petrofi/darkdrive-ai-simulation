# External Dataset Source Notes

## DonkeyCar

DonkeyCar is promising because its tub format records camera images with steering/angle and throttle-style controls. This is conceptually close to behavior cloning, and DarkDrive already has `scripts/convert_donkey_tub_to_darkdrive.py` for supported JSON/catalog variants.

The sources are not directly interchangeable with DarkDrive:

- `autorope/donkey_datasets` states that its tubs use DonkeyCar 4.x format and Git LFS.
- Kaggle tubs may use different tub generations or metadata layouts.
- Steering sign and numeric scale must be verified rather than assumed.
- Real RC track imagery differs from the Udacity simulator.
- Each tub needs its own missing-image, duplicate, distribution, and provenance report.
- The reviewed public repository did not expose a clear dataset license file.

Do not use DonkeyCar data directly without conversion and steering-scale validation.

Sources:

- <https://www.kaggle.com/datasets/vanmil/donkeycar-tubs>
- <https://github.com/autorope/donkey_datasets>
- <https://docs.donkeycar.com/guide/deep_learning/dataset_pretrained_models/>

## comma2k19

comma2k19 is a large real-world driving source with road-facing video, CAN, GNSS, IMU, and pose data. Its repository documents steering angle and car speed in processed CAN logs, but it is designed primarily for pose estimation and mapping research.

It is not suitable for immediate DarkDrive simulator training because:

- the download is about 100 GB
- the domain is real California highway commuting
- labels and video frames require time alignment
- steering is reported in physical degrees rather than DarkDrive's normalized simulator convention
- highway data is unlikely to target the recovery and strong-turn gaps identified by External Mix V1
- Windows filesystems require a documented extraction workaround for route names containing `|`

Treat comma2k19 as a future domain-adaptation or representation-learning research source, not direct augmentation.

Source: <https://github.com/commaai/comma2k19>

## CARLA

CARLA is the strongest future route for deliberately generating balanced synthetic data. A separate pipeline could synchronize RGB frames with steering, throttle, brake, speed, route, weather, and recovery-scenario metadata while targeting left/right and strong-turn coverage.

It is not a quick external-download step:

- current CARLA guidance describes a heavy modern CPU/GPU/RAM setup
- simulator installation and version selection are separate engineering work
- an exporter, schema, scenario plan, and validator must be designed
- CARLA-to-Udacity visual domain differences must be measured
- synthetic scenario balance can still become unrealistic if collection is poorly designed

CARLA-specific code is MIT, CARLA assets are CC-BY, and Unreal Engine/third-party terms also apply. Installation or data generation was intentionally not attempted in this task.

Sources:

- <https://github.com/carla-simulator/carla>
- <https://github.com/carla-simulator/imitation-learning>
