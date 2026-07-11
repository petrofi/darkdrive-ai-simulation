"""CLI entry point for the simulation-only DarkDrive closed-loop demo."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.simulator.closed_loop_driver import (
    DEFAULT_CHECKPOINT,
    DEFAULT_HOST,
    DEFAULT_LOG_DIR,
    DEFAULT_MAX_STEERING,
    DEFAULT_PORT,
    DEFAULT_SMOOTHING_ALPHA,
    DEFAULT_THROTTLE,
    ClosedLoopDriver,
    DriverConfig,
    ModelRuntime,
    ProtocolDiagnostics,
    TelemetrySessionLogger,
    default_emergency_stop_file,
    protocol_environment,
    run_self_test,
    run_socketio_server,
)


def project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the simulation-only DarkDrive closed-loop Socket.IO driver."
    )
    parser.add_argument("--checkpoint", default=str(DEFAULT_CHECKPOINT))
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--device", choices=("cpu", "cuda", "auto"), default="cpu")
    parser.add_argument("--throttle", type=float, default=DEFAULT_THROTTLE)
    parser.add_argument("--max-steering", type=float, default=DEFAULT_MAX_STEERING)
    parser.add_argument(
        "--steering-smoothing",
        type=float,
        default=DEFAULT_SMOOTHING_ALPHA,
        help="EMA weight for the newest prediction; 1.0 disables smoothing.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--protocol-debug",
        action="store_true",
        help="Enable bounded Engine.IO/Socket.IO lifecycle and event diagnostics.",
    )
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    parser.add_argument("--max-runtime-seconds", type=float, default=None)
    parser.add_argument(
        "--emergency-stop-file",
        default=None,
        help="Creating this file latches neutral steering and zero throttle, then stops the server.",
    )
    parser.add_argument(
        "--self-test-only",
        action="store_true",
        help="Load the checkpoint and run one stored frame without opening a server.",
    )
    parser.add_argument(
        "--self-test-image",
        default="data/samples/road_sample.jpg",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = DriverConfig(
            throttle=args.throttle,
            max_steering=args.max_steering,
            steering_smoothing=args.steering_smoothing,
            dry_run=args.dry_run,
        )
        checkpoint = project_path(args.checkpoint)
        log_dir = project_path(args.log_dir)
        runtime = ModelRuntime.load(checkpoint, args.device)
        print("DarkDrive Closed-Loop Simulator Demo V1")
        print("Simulation-only runtime. No real-vehicle control.")
        print(f"- Checkpoint: {checkpoint.resolve()}")
        print(f"- Architecture: {runtime.model_arch}")
        print(f"- Preprocessing: {runtime.preprocessing_profile}")
        print(f"- Device: {runtime.device_name}")
        print(f"- Protocol: {protocol_environment()['socketio_protocol']}")

        if args.self_test_only:
            row, summary = run_self_test(
                runtime,
                config,
                log_dir,
                project_path(args.self_test_image),
            )
            print("Local dry-run self-test passed")
            print(f"- Raw steering: {float(row['raw_steering_prediction']):.6f}")
            print(f"- Inference latency: {float(row['inference_latency_ms']):.3f} ms")
            print("- Control sent: neutral steering, zero throttle")
            print(f"- Summary: {summary['session_id']}")
            return 0

        diagnostics = ProtocolDiagnostics(enabled=args.protocol_debug)
        logger = TelemetrySessionLogger(
            log_dir,
            runtime.model_name,
            runtime.device_name,
            config.dry_run,
            protocol_diagnostics=diagnostics,
        )
        driver = ClosedLoopDriver(runtime, config, logger)
        stop_file = (
            project_path(args.emergency_stop_file)
            if args.emergency_stop_file
            else default_emergency_stop_file(log_dir)
        )
        print(f"- Listening: http://{args.host}:{args.port}")
        print(f"- Dry run: {config.dry_run}")
        print(f"- Protocol debug: {args.protocol_debug}")
        print(f"- Throttle: {config.throttle:.3f}")
        print(f"- Max steering: {config.max_steering:.3f}")
        print(f"- EMA newest-prediction weight: {config.steering_smoothing:.3f}")
        print(f"- Emergency-stop file: {stop_file.resolve()}")
        print("Stop with Ctrl+C or create the emergency-stop file.")
        summary = run_socketio_server(
            driver,
            args.host,
            args.port,
            emergency_stop_file=stop_file,
            max_runtime_seconds=args.max_runtime_seconds,
            protocol_debug=args.protocol_debug,
        )
        print("Closed-loop session ended")
        print(f"- Frames: {summary['total_frames']}")
        print(f"- Successful/failed: {summary['successful_predictions']}/{summary['failed_frames']}")
        print(f"- Emergency stop: {summary['emergency_stop']}")
        print(
            f"- Protocol: {summary['protocol_verdict']} "
            f"({summary['protocol_verdict_explanation']})"
        )
        print(f"- Summary: {logger.summary_path}")
        return 0
    except (FileNotFoundError, FileExistsError, RuntimeError, ValueError, OSError) as exc:
        print(f"Closed-loop simulator startup failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
