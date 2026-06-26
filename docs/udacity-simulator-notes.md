# Udacity Simulator Notes

## Local Simulator Path

The local simulator folder is:

```text
C:\Users\tarik\Downloads\win_sys_int\win_sys_int
```

This simulator is external to the project and must not be copied into the repository. Do not commit simulator executables, simulator assets, generated simulator data, images, CSV logs, or trained model files.

## Read-Only Inspection Result

Observed executable:

```text
C:\Users\tarik\Downloads\win_sys_int\win_sys_int\sys_int.exe
```

Observed Unity data folder:

```text
C:\Users\tarik\Downloads\win_sys_int\win_sys_int\sys_int_Data
```

Observed metadata/assets include:

- `app.info` with Udacity/self-driving-car-nanodegree metadata.
- `StreamingAssets/parkingLot.ply`
- `StreamingAssets/Simon2.ply`

The folder name `win_sys_int`, the executable name `sys_int.exe`, and the asset names strongly suggest this is the Udacity System Integration simulator, not the Term 1 behavior cloning simulator.

## Data Recording Support Check

During file inspection, no obvious recording/export files or folders were found for:

- `driving_log.csv`
- `IMG/`
- behavior cloning recording
- camera frame export

This does not prove the simulator cannot record data, but it means we should not assume it supports the behavior cloning dataset workflow.

## How to Launch Manually

Launch manually from Windows Explorer by opening:

```text
C:\Users\tarik\Downloads\win_sys_int\win_sys_int\sys_int.exe
```

Do not launch it from repository scripts. The project stores only documentation, validation scripts, and training code.

## How to Identify Behavior Cloning Recording Support

A behavior cloning training simulator should usually provide a way to:

- Select an output or recording folder.
- Drive manually in training mode.
- Export camera frames into an `IMG/` folder.
- Export a `driving_log.csv` file.

Expected behavior cloning dataset structure, if supported:

```text
data/processed/simulator/
|-- IMG/
`-- driving_log.csv
```

If this local simulator does not create `IMG` frames and `driving_log.csv`, use it only for visual/manual testing and switch data collection to another simulator later.
