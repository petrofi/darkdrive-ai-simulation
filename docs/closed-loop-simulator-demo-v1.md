# Closed-Loop Simulator Demo V1

## Scope

EXP-021 adds a simulation-only closed-loop diagnostic for the installed Udacity Behavioral Cloning simulator. It receives the simulator's center-camera telemetry, runs the existing PyTorch KJM3 checkpoint, and can return bounded steering with a conservative constant throttle.

This is not real-vehicle control, a model release, autonomous-driving readiness, or a successful-lap claim.

## Installed Simulator Assessment

The correct Behavioral Cloning simulator is installed outside the repository at:

```text
C:\Users\tarik\Downloads\simulator-windows-64\Default Windows desktop 64-bit.exe
```

Read-only inspection of `Assembly-CSharp.dll` verified:

- WebSocket URL: `ws://127.0.0.1:4567/socket.io/?EIO=4&transport=websocket`.
- Incoming event: `telemetry`.
- Incoming fields include `speed` and base64 `image`.
- Outgoing event: `steer`.
- Outgoing fields: `steering_angle` and `throttle`.
- Autonomous scenes for the lake and mountain tracks are present.

The separate `win_sys_int/sys_int.exe` installation is the System Integration simulator and is not the target for this camera-to-steering runtime.

## Runtime Architecture

```text
Unity center camera
  -> EIO4 / Socket.IO telemetry
  -> validated base64 JPEG decode to RGB
  -> checkpoint-selected baseline preprocessing
  -> 1 x 3 x 80 x 160 tensor
  -> PyTorch SteeringModel inference_mode
  -> finite-value check
  -> symmetric steering clip
  -> EMA steering smoothing
  -> dry-run neutral command OR low-throttle steer command
  -> Socket.IO steer event
  -> ignored CSV telemetry and JSON session summary
```

Core runtime: `src/simulator/closed_loop_driver.py`.

CLI entry point: `scripts/run_closed_loop_simulator.py`.

Only the center-camera `image` telemetry field is used. Side-camera frames are not accepted or synthesized.

## Model And Preprocessing

- Checkpoint: `models/steering_model_kaggle_jungle_mix_v1.pt`.
- Checkpoint status: KJM3, useful offline improvement, not promoted.
- Architecture metadata: `baseline` / `SteeringModel`, 188,219 parameters.
- Preprocessing metadata: `baseline`, full RGB frame, resize to 160 x 80, CHW float pixels in `[0, 1]`.
- Device default: CPU.
- Model loading: once, before the server binds.
- Runtime mode: `eval()` plus `torch.inference_mode()`.

Model-load or state-dict failure prevents the Socket.IO server from starting.

## Installation Requirements

The simulator assembly explicitly uses EIO4. The runtime therefore uses the EIO4-compatible modern stack below rather than the incompatible legacy Socket.IO 1.x/eventlet examples:

- `python-socketio==5.16.3`
- `python-engineio==4.13.3`
- `simple-websocket==1.1.0`
- `Werkzeug==3.1.8`

Install project and simulator dependencies in an isolated Python environment:

```powershell
python -m pip install -r requirements.txt -r requirements-simulator.txt
```

No full ROS installation or global package modification is required.

## Safety Controls

- Default throttle is `0.10` and can only be configured in `[0, 1]`.
- Steering is clipped symmetrically to `--max-steering`, default `1.0`.
- EMA smoothing uses `alpha=0.35` for the newest prediction by default.
- Empty, malformed, corrupt, undersized, oversized, or non-RGB frames command neutral steering and zero throttle.
- NaN or infinite predictions command neutral steering and zero throttle.
- Three consecutive frame/inference failures latch an emergency stop and stop the server.
- Control-emission failure is logged, latches an emergency stop, and stops the server.
- Dry-run always emits `0.0` steering and `0.0` throttle even after successful inference.
- Ctrl+C sends a final neutral command to every connected simulator session when possible.
- Creating `runtime_logs/closed_loop_v1/EMERGENCY_STOP` sends neutral control and stops the server.
- A stale emergency-stop file prevents startup until a human removes it.
- `--max-runtime-seconds` provides a bounded first diagnostic.

These are simulator runtime controls, not physical safety certification.

## Telemetry Logging

Ignored per-frame CSV files are written under `runtime_logs/closed_loop_v1/` with:

- UTC timestamp
- simulator speed when available
- raw steering prediction
- smoothed steering command
- throttle command
- inference latency
- complete frame-processing latency
- model and device
- frame index
- error state
- dry-run state

The ignored JSON summary records total/successful/failed frames, average and p95 inference latency, steering mean/std/min/max, runtime, disconnect count, and emergency-stop status/reason.

## Protocol Diagnostic Mode

The first human integration attempt established a TCP connection to port 4567, but the newest CSV remained header-only and the summary reported zero total, successful, and failed frames. No inference was attempted. The checkpoint self-test still passes, so this is an Engine.IO/Socket.IO/Unity integration failure rather than a model-training failure.

Add `--protocol-debug` to enable bounded diagnostics. The mode:

- enables redacting Socket.IO and Engine.IO loggers;
- records Engine.IO requests, EIO version, requested transport, SID, namespace lifecycle, and disconnect reason;
- handles `connect`, `telemetry`, and `disconnect` explicitly on `/`;
- emits exactly one initial neutral `steer` event with string values `"0"` and `"0"`;
- catches otherwise unhandled events on the default and alternate namespaces;
- logs event name, namespace, SID, payload type, dictionary keys, image presence, and image string length only;
- limits event metadata output to 100 events and never prints complete image data.

The ignored JSON summary includes protocol counters and one verdict:

- `P1`: telemetry flow confirmed.
- `P2`: Socket.IO connected but telemetry absent.
- `P3`: Engine.IO/Socket.IO protocol mismatch.
- `P4`: namespace or event-name mismatch.
- `P5`: transport or handshake failure.
- `P6`: unresolved; additional Unity-side inspection required.

The installed Unity assembly declares `EIO=4`. Do not downgrade the current environment unless a live request explicitly proves `EIO=3`. If that occurs, preserve the EIO4 environment and plan an isolated `C:\venvs\darkdrive-sim-eio3` environment.

## Local Self-Test

Run this before opening Unity:

```powershell
python scripts/run_closed_loop_simulator.py --checkpoint models/steering_model_kaggle_jungle_mix_v1.pt --device cpu --dry-run --self-test-only --self-test-image data/samples/road_sample.jpg
```

Verified local result on 2026-07-11:

- Checkpoint loaded once.
- Architecture and preprocessing resolved to `baseline`.
- Input tensor contract: 1 x 3 x 80 x 160.
- Raw prediction: `-0.110780`, finite.
- CPU inference latency: `4.886 ms` for the recorded run.
- Emitted control: neutral steering and zero throttle.
- CSV and JSON runtime logging: pass.

## Human Dry-Run Command

The package metadata in `C:\venvs\darkdrive-sim` records Python 3.10.11, `python-socketio==5.16.3`, `python-engineio==4.13.3`, `simple-websocket==1.1.0`, and `Werkzeug==3.1.8`. WebSocket is supplied by `simple-websocket`; polling is built into Engine.IO; the server uses Werkzeug with Socket.IO threading mode.

The environment launcher currently points to a missing base interpreter at `C:\Users\tarik\AppData\Local\Programs\Python\Python310\python.exe`. Repair or recreate that environment before using this exact command. Ensure the stop file does not already exist, then start the diagnostic server first:

```powershell
& "C:\venvs\darkdrive-sim\Scripts\python.exe" `
  ".\scripts\run_closed_loop_simulator.py" `
  --checkpoint ".\models\steering_model_kaggle_jungle_mix_v1.pt" `
  --host 0.0.0.0 `
  --port 4567 `
  --device cpu `
  --throttle 0.10 `
  --max-steering 1.0 `
  --steering-smoothing 0.35 `
  --dry-run `
  --protocol-debug `
  --max-runtime-seconds 120
```

Then open `Default Windows desktop 64-bit.exe`, select the first track, enter Autonomous Mode, wait 20-30 seconds, and stop with Ctrl+C. Dry-run always returns neutral steering and zero throttle. Preserve the console protocol log and ignored JSON session summary for diagnosis.

Do not proceed to active control unless live dry-run confirms telemetry reception, successful frame decoding, finite predictions, runtime logs, clean disconnect, and emergency-stop behavior.

## Human Active Diagnostic Command

For the first supervised movement diagnostic only:

```powershell
python scripts/run_closed_loop_simulator.py --checkpoint models/steering_model_kaggle_jungle_mix_v1.pt --device cpu --throttle 0.10 --max-steering 1.0 --steering-smoothing 0.35 --max-runtime-seconds 60
```

Open the simulator in Autonomous mode, watch the vehicle continuously, and stop immediately with Ctrl+C if behavior is unstable.

Emergency-stop file command from another PowerShell window:

```powershell
New-Item -ItemType File -Force runtime_logs\closed_loop_v1\EMERGENCY_STOP
```

The first objective is telemetry, inference, command transmission, visible movement, emergency stop, and logging. It is not a full lap.

## Known Limitations

- Live Unity telemetry and active vehicle movement were not run automatically in this implementation task.
- KJM3 is not a promoted checkpoint and Kaggle licensing remains unresolved.
- Session C2 was reused for model selection; Session E2 remains pending.
- The model is single-frame and has no proven temporal stability.
- EMA smoothing is a simple runtime filter, not a learned temporal controller.
- Throttle is fixed; there is no speed controller, braking policy, collision detector, lane-departure detector, or recovery state machine.
- Runtime metrics do not prove safe autonomous driving or production readiness.

## First-Demo Acceptance Criteria

- Unity connects to `127.0.0.1:4567` over EIO4 WebSocket.
- Center-camera telemetry is received and decoded.
- Predictions are finite and logged with latency.
- Dry-run returns only neutral steering and zero throttle.
- Active diagnostic visibly transmits bounded steering and `0.10` throttle.
- Ctrl+C and the emergency-stop file produce zero throttle.
- Disconnect/reconnect does not crash the process.
- CSV and JSON session artifacts are generated and remain ignored.

Active simulator driving remains pending until a human completes these checks.
