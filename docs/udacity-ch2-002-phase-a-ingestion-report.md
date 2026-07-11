# Udacity CH2_002 Phase-A Ingestion Report

## Dataset Purpose

EXP-020 evaluates `udacity_ch2_002` as a local, offline, real-world driving-data source. Phase A verifies the archive, ROS1 bag readability, camera and steering semantics, and timestamp synchronization. It does not authorize a full conversion, training, checkpoint evaluation, simulator control, or real-vehicle control.

## Repository And Storage Status

- Branch before work: `main`.
- Starting commit: `06a4cf9 feat: evaluate kaggle jungle mix v1 training experiment`.
- Starting synchronization: `origin/main...HEAD = 0 0`.
- Starting worktree: clean, with no staged generated data or models.
- Project location: OneDrive, under `C:\Users\tarik\OneDrive\Ekler\Desktop\darkdrive-ai-simulation`.
- Available C: space: 301,933,543,424 bytes, or 281.20 GiB.
- Archive size: 4,716,005,956 bytes, or about 4.39 GiB.
- Expected additional extracted data: 6,236,839,127 bytes, or about 5.81 GiB.
- At least 20 GB free: yes.

The existing broad data-directory ignore rules protected the archive and generated output. Explicit `*.bag`, `*.tar`, `*.tar.gz`, and `*.torrent` rules were added as defense in depth. No `git add -f` was used.

## Archive Verification

- Full path: `C:\Users\tarik\OneDrive\Ekler\Desktop\darkdrive-ai-simulation\data\external\udacity_ch2_002\raw\Ch2_002.tar.gz`.
- Exact size: 4,716,005,956 bytes.
- Modification time: 2026-07-11 21:33:28.5450424 +03:00.
- Calculated SHA-256: `E7FB718AA2646F40FAF9E194E715551FFCEDCD729FA1C5CA2F428E197098743D`.
- Recorded SHA-256: `E7FB718AA2646F40FAF9E194E715551FFCEDCD729FA1C5CA2F428E197098743D`.
- Hash comparison: exact match.

## TAR Safety Inspection

| Member | Type | Uncompressed bytes |
| --- | --- | ---: |
| `HMB_2.bag` | Regular file | 3,009,938,927 |
| `HMB.txt` | Regular file | 2,839 |
| `HMB_1.bag` | Regular file | 704,510,416 |
| `HMB_4.bag` | Regular file | 347,674,885 |
| `HMB_6.bag` | Regular file | 1,343,721,081 |
| `HMB_5.bag` | Regular file | 830,990,979 |

- Members: 6.
- Expected extracted bytes: 6,236,839,127.
- Duplicate member names: 0.
- Absolute paths: 0.
- Parent-traversal paths: 0.
- Symbolic links: 0.
- Hard links: 0.
- Device, FIFO, or unsupported special members: 0.
- TAR result: **A1 - archive structure safe**.

## Extraction Result

`scripts/extract_udacity_ch2_002.py` validates every member before writing, rejects absolute and traversal paths, rejects all links and special members, detects duplicate/file-directory collisions, refuses silent overwrite, extracts to a temporary sibling directory, verifies file count and bytes, and supports explicit `--force` replacement only after the replacement extraction succeeds.

A complete extraction already existed when the real run reached the output target. The default mode correctly refused to overwrite it. The explicit non-mutating `--verify-existing` mode then compared every extracted relative name and byte size with the TAR metadata and wrote ignored extraction metadata.

- Verified files: 6.
- Verified bytes: 6,236,839,127.
- Bag files: `HMB_1.bag`, `HMB_2.bag`, `HMB_4.bag`, `HMB_5.bag`, `HMB_6.bag`.
- Metadata/text file: `HMB.txt`.
- Missing, extra, or size-mismatched files: 0.
- Existing extracted files overwritten: 0.
- Original TAR deleted or modified: no.
- Verification result: pass.

Generated metadata remains ignored at `data/external/udacity_ch2_002/metadata/extraction_metadata.json`.

## Python And ROSBAG Environment

The Windows `py` launcher referenced a missing Python 3.13 installation, and the project `.venv` was tied to that missing base interpreter. No global Python installation was changed. A separate ignored environment was created at `data/external/udacity_ch2_002/tooling_venv` from the bundled Python 3.12.13 runtime.

Directly required packages:

- `rosbags==0.11.3`
- `opencv-python==5.0.0.93`
- `numpy==2.5.1`
- `pandas==3.0.3`
- `torch==2.13.0`
- `torchvision==0.28.0`
- `pillow==12.3.0`
- `matplotlib==3.11.0`

Installed transitive/runtime packages and exact versions:

- `apsw==3.53.3.1`, `contourpy==1.3.3`, `cycler==0.12.1`, `filelock==3.29.7`, `fonttools==4.63.0`
- `fsspec==2026.6.0`, `Jinja2==3.1.6`, `kiwisolver==1.5.0`, `lz4==4.4.5`, `MarkupSafe==3.0.3`
- `mpmath==1.3.0`, `networkx==3.6.1`, `packaging==26.2`, `pyparsing==3.3.2`, `python-dateutil==2.9.0.post0`
- `ruamel.yaml==0.19.1`, `setuptools==83.0.0`, `six==1.17.0`, `sympy==1.14.0`, `typing_extensions==4.16.0`
- `tzdata==2026.3`, `zstandard==0.25.0`, `pip==25.0.1`

WSL reports default version 2 but no Linux distribution is installed. No full ROS Desktop installation was attempted. All bag work used the pure-Python `rosbags` reader on Windows.

## Extracted Bag Inventory

Every file starts with `#ROSBAG V2.0\n` and is a ROS1 bag.

| Bag | Size | Format | Duration | Messages | Read Status |
| --- | ---: | --- | ---: | ---: | --- |
| `HMB_1.bag` | 704,510,416 | ROS1 v2.0 | 221.212 s | 910,943 | Readable, 0 skipped |
| `HMB_2.bag` | 3,009,938,927 | ROS1 v2.0 | 791.022 s | 3,257,956 | Readable, 0 skipped |
| `HMB_4.bag` | 347,674,885 | ROS1 v2.0 | 99.792 s | 410,816 | Readable, 0 skipped |
| `HMB_5.bag` | 830,990,979 | ROS1 v2.0 | 212.875 s | 876,603 | Readable, 0 skipped |
| `HMB_6.bag` | 1,343,721,081 | ROS1 v2.0 | 371.241 s | 1,528,922 | Readable, 0 skipped |

All bags expose 39 connections and the same 36 unique topic/type pairs. Total indexed messages: 6,985,240. Generated inventory remains ignored at `data/external/udacity_ch2_002/metadata/bag_inventory.json`.

## Topic Inventory

Counts below are global across all five bags. Frequency is the observed per-bag range.

| Topic | Message type | Messages | Approx. Hz |
| --- | --- | ---: | ---: |
| `/can_bus_dbw/can_rx` | `dataspeed_can_msgs/msg/CanMessageStamped` | 1,202,993 | 709.23-709.34 |
| `/center_camera/camera_info` | `sensor_msgs/msg/CameraInfo` | 33,808 | 20.00 |
| `/center_camera/image_color/compressed` | `sensor_msgs/msg/CompressedImage` | 33,808 | 20.00 |
| `/diagnostics` | `diagnostic_msgs/msg/DiagnosticArray` | 6,685 | 3.93-3.96 |
| `/ecef` | `geometry_msgs/msg/PointStamped` | 678,406 | 400.00 |
| `/fix` | `sensor_msgs/msg/NavSatFix` | 678,400 | 400.00-400.01 |
| `/imu/data` | `sensor_msgs/msg/Imu` | 678,397 | 400.00-400.01 |
| `/left_camera/camera_info` | `sensor_msgs/msg/CameraInfo` | 33,805 | 20.00 |
| `/left_camera/image_color/compressed` | `sensor_msgs/msg/CompressedImage` | 33,805 | 20.00 |
| `/pressure` | `sensor_msgs/msg/FluidPressure` | 84,800 | 50.00 |
| `/right_camera/camera_info` | `sensor_msgs/msg/CameraInfo` | 33,783 | 19.93-20.00 |
| `/right_camera/image_color/compressed` | `sensor_msgs/msg/CompressedImage` | 33,783 | 19.93-20.00 |
| `/time_reference` | `sensor_msgs/msg/TimeReference` | 2,055,505 | 1211.99-1212.00 |
| `/vehicle/brake_info_report` | `dbw_mkz_msgs/msg/BrakeInfoReport` | 84,800 | 50.00 |
| `/vehicle/brake_report` | `dbw_mkz_msgs/msg/BrakeReport` | 84,665 | 49.92 |
| `/vehicle/dbw_enabled` | `std_msgs/msg/Bool` | 5 | one per bag |
| `/vehicle/filtered_accel` | `std_msgs/msg/Float64` | 84,657 | 49.92 |
| `/vehicle/fuel_level_report` | `dbw_mkz_msgs/msg/FuelLevelReport` | 17,027 | 10.00-10.20 |
| `/vehicle/gear_report` | `dbw_mkz_msgs/msg/GearReport` | 33,864 | 19.97 |
| `/vehicle/gps/fix` | `sensor_msgs/msg/NavSatFix` | 1,695 | 1.00 |
| `/vehicle/gps/time` | `sensor_msgs/msg/TimeReference` | 1,695 | 1.00 |
| `/vehicle/gps/vel` | `geometry_msgs/msg/TwistStamped` | 1,695 | 1.00 |
| `/vehicle/imu/data_raw` | `sensor_msgs/msg/Imu` | 169,190 | 99.75-99.76 |
| `/vehicle/joint_states` | `sensor_msgs/msg/JointState` | 254,253 | 149.91-149.92 |
| `/vehicle/misc_1_report` | `dbw_mkz_msgs/msg/Misc1Report` | 33,865 | 19.97 |
| `/vehicle/sonar_cloud` | `sensor_msgs/msg/PointCloud2` | 8,475 | 4.97-5.05 |
| `/vehicle/steering_report` | `dbw_mkz_msgs/msg/SteeringReport` | 84,656 | 49.92 |
| `/vehicle/surround_report` | `dbw_mkz_msgs/msg/SurroundReport` | 8,475 | 4.97-5.05 |
| `/vehicle/suspension_report` | `dbw_mkz_msgs/msg/SuspensionReport` | 84,809 | 50.00-50.01 |
| `/vehicle/throttle_info_report` | `dbw_mkz_msgs/msg/ThrottleInfoReport` | 169,601 | 100.00 |
| `/vehicle/throttle_report` | `dbw_mkz_msgs/msg/ThrottleReport` | 84,663 | 49.92 |
| `/vehicle/tire_pressure_report` | `dbw_mkz_msgs/msg/TirePressureReport` | 3,390 | 2.00 |
| `/vehicle/twist_controller/parameter_descriptions` | `dynamic_reconfigure/msg/ConfigDescription` | 5 | one per bag |
| `/vehicle/twist_controller/parameter_updates` | `dynamic_reconfigure/msg/Config` | 5 | one per bag |
| `/vehicle/wheel_speed_report` | `dbw_mkz_msgs/msg/WheelSpeedReport` | 169,595 | 100.00 |
| `/velodyne_packets` | `velodyne_msgs/msg/VelodyneScan` | 16,177 | 9.54 |

Speed candidates include `/vehicle/steering_report.speed`, `/vehicle/wheel_speed_report`, `/vehicle/gps/vel`, and other velocity/twist schemas. Throttle/brake candidates include the corresponding info/report topics. No control field was mapped into a DarkDrive training schema in Phase A.

## HMB Metadata File

`HMB.txt` is 2,839 bytes, 20 lines, and ASCII/UTF-8 compatible. It describes lighting, road, traffic, curve, elevation, and divided-highway conditions for HMB_1 through HMB_6. It states that HMB_3 is the test dataset and is not included in this archive. It also describes center-camera extraction for HMB_3 release data. It does not define a simulator steering conversion or normalization rule.

## Camera Topic Assessment

The three payload topics are unambiguous compressed-image streams:

- `/center_camera/image_color/compressed`
- `/left_camera/image_color/compressed`
- `/right_camera/image_color/compressed`

Across every bag and camera topic, the inspected messages are `sensor_msgs/msg/CompressedImage`, format `bgr8; jpeg compressed bgr8`, and decode successfully as 640 x 480 x 3 images. Both bag record timestamps and ROS header timestamps are present. The center topic was selected for the bounded sample because its name and `HMB.txt` usage establish it as the forward center camera.

## Steering Topic Assessment

The only plausible root steering topic is `/vehicle/steering_report`, type `dbw_mkz_msgs/msg/SteeringReport`. Complete root fields are:

`header`, `steering_wheel_angle`, `steering_wheel_angle_cmd`, `steering_wheel_torque`, `speed`, `enabled`, `override`, `driver`, `fault_wdc`, `fault_bus1`, `fault_bus2`, `fault_calibration`, `fault_connector`.

The message definition records `float32 steering_wheel_angle # rad` and separately exposes `steering_wheel_angle_cmd`. Therefore `steering_wheel_angle` is classified with high confidence as a measured physical steering-wheel angle in radians, not a desired command, front-wheel angle, curvature, yaw signal, or normalized simulator control.

| Bag | Bounded samples | Min rad | Max rad | Mean rad | Std rad |
| --- | ---: | ---: | ---: | ---: | ---: |
| `HMB_1.bag` | 5,520 | -0.340339 | 0.136136 | -0.022914 | 0.080942 |
| `HMB_2.bag` | 9,871 | -1.244420 | 1.902409 | -0.004576 | 0.300140 |
| `HMB_4.bag` | 4,979 | -0.363028 | 0.539307 | 0.030054 | 0.240892 |
| `HMB_5.bag` | 5,313 | -2.050762 | 1.165880 | -0.001235 | 0.460182 |
| `HMB_6.bag` | 9,265 | -0.171042 | 0.108210 | -0.022984 | 0.046775 |

The signal is bidirectional in every bag. No arbitrary conversion to `[-1, 1]` was defined or applied.

## Timestamp Synchronization Results

Method: for every camera bag timestamp, select the nearest steering bag timestamp within the same bag. A frame is matched when the absolute delta is at most 100 ms. Metrics use bag record timestamps; header timestamps remain available as provenance.

| Bag | Camera Topic | Steering Topic | Match Rate | Median Delta | P95 Delta | Verdict |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `HMB_1.bag` | center compressed | steering report | 100.00% | 4.924 ms | 9.466 ms | S1 |
| `HMB_2.bag` | center compressed | steering report | 100.00% | 5.005 ms | 9.520 ms | S1 |
| `HMB_4.bag` | center compressed | steering report | 100.00% | 5.043 ms | 9.609 ms | S1 |
| `HMB_5.bag` | center compressed | steering report | 100.00% | 4.982 ms | 9.476 ms | S1 |
| `HMB_6.bag` | center compressed | steering report | 100.00% | 5.010 ms | 9.550 ms | S1 |

Center-camera global result: 33,808/33,808 frames matched, median 4.995 ms, p90 9.015 ms, p95 9.519 ms, maximum 12.202 ms, S1. Left-camera global result: 33,805/33,805 matched, median 5.023 ms, p95 9.506 ms, maximum 10.232 ms, S1. Right-camera global result: 33,783/33,783 matched, median 4.977 ms, p95 9.527 ms, maximum 11.404 ms, S1.

Center and steering streams contain 0 duplicate timestamps, 0 non-monotonic timestamps, and 0 major gaps under the documented 10x-median-or-1-second rule. Center/steering coverage overlap is 100% except HMB_4 at 99.949%; nearest-neighbor coverage still matches every center frame within 12.203 ms.

## Sample Conversion

The sample conditions were all met, so `scripts/convert_udacity_ch2_002_sample.py` exported exactly 500 deterministic center-camera frames: 100 evenly spaced frames from each bag. Output remains ignored at `data/processed/external/udacity_ch2_002_sample/`.

- Manifest rows / image files: 500 / 500.
- Readable images: 500.
- Missing / unreadable / duplicate image paths: 0 / 0 / 0.
- Invalid raw steering values: 0.
- Bag distribution: 100 rows from each of the five bags.
- Timestamp delta: min 0.040 ms, median 5.072 ms, p90 9.072 ms, p95 9.429 ms, max 12.202 ms.
- Sample steering radians: min -2.047271, max 1.685988, mean -0.003271, std 0.279929.
- `source_dataset`: `udacity_ch2_002`.
- `is_external`: `true`.
- `domain`: `real_world_offline_dataset`.
- Steering scale: physical steering-wheel angle in radians; no simulator normalization.

No full dataset conversion or visual sample grid was produced.

## Phase-A Verdict

**C2A1 - Strong full-conversion candidate.**

Supporting evidence:

- The checksummed A1 archive is valid.
- All five ROS1 bags are readable with zero skipped messages.
- Center, left, and right JPEG camera streams are identified and decode successfully.
- The measured steering-wheel angle field and radian unit are documented by the source message schema.
- Camera/steering synchronization is consistently S1.
- The 500-frame bounded sample conversion passed all integrity checks.

C2A1 authorizes only a separately reviewed full-conversion task. It does not authorize training, normalization, data mixing, checkpoint evaluation, release, simulator control, or real-world control.

## Domain And License Caveat

This is real-world vehicle data and is not equivalent to Udacity simulator data. Camera appearance, vehicle geometry, steering ratio, road conditions, sensor calibration, and measured steering-wheel radians differ from DarkDrive's simulator command labels. A future conversion must preserve raw units and make any model-target mapping an explicit, evidenced governance decision.

Archive-specific license and redistribution terms remain unresolved. Raw bags, extracted files, metadata, sample images, and sample manifests are local-only ignored artifacts and must not be committed or redistributed.

## Training Decision

No full conversion was performed. No research model was trained. No checkpoint was evaluated. No simulator control was implemented. No real-vehicle control code was created. No autonomous-driving readiness claim is made.

## Code And Tests

- Added `scripts/extract_udacity_ch2_002.py`.
- Added `scripts/inspect_udacity_ch2_002_bags.py`.
- Added `scripts/convert_udacity_ch2_002_sample.py`.
- Added synthetic TAR safety and sample-helper tests.
- All three scripts passed `py_compile`.
- Complete repository result: 103 tests passed.

## Exact Recommended Next Step

Run a separate full conversion and normalization-governance task. Preserve `steering_wheel_angle` in radians, define the full manifest and split policy, validate every exported image and synchronization match, resolve license/redistribution constraints, and do not train until the converted real-world dataset receives a separate approval.
