"""Simulation-only closed-loop runtime for the Udacity behavior-cloning simulator."""

from __future__ import annotations

import base64
import csv
import io
import json
import math
import os
import statistics
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

import numpy as np
import torch
from PIL import Image, UnidentifiedImageError

from src.inference.predict_steering import load_checkpoint
from src.models.steering_model import make_steering_model, resolve_model_arch
from src.utils.image_preprocessing import (
    MODEL_INPUT_HEIGHT,
    MODEL_INPUT_WIDTH,
    preprocess_image_for_model,
    resolve_preprocessing_profile,
)


DEFAULT_CHECKPOINT = Path("models/steering_model_kaggle_jungle_mix_v1.pt")
DEFAULT_LOG_DIR = Path("runtime_logs/closed_loop_v1")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 4567
DEFAULT_THROTTLE = 0.10
DEFAULT_MAX_STEERING = 1.0
DEFAULT_SMOOTHING_ALPHA = 0.35
DEFAULT_FAILURE_THRESHOLD = 3
MIN_FRAME_WIDTH = 160
MIN_FRAME_HEIGHT = 80
MAX_FRAME_PIXELS = 4096 * 4096
TELEMETRY_COLUMNS = (
    "timestamp",
    "simulator_speed",
    "raw_steering_prediction",
    "smoothed_steering_command",
    "throttle_command",
    "inference_latency_ms",
    "frame_processing_latency_ms",
    "model",
    "device",
    "frame_index",
    "error_state",
    "dry_run",
)


class InferenceRuntime(Protocol):
    model_name: str
    device_name: str
    preprocessing_profile: str

    def predict_rgb(self, image_rgb: np.ndarray) -> "PredictionResult": ...


@dataclass(frozen=True)
class PredictionResult:
    steering: float
    inference_latency_ms: float


@dataclass(frozen=True)
class DriverConfig:
    throttle: float = DEFAULT_THROTTLE
    max_steering: float = DEFAULT_MAX_STEERING
    steering_smoothing: float = DEFAULT_SMOOTHING_ALPHA
    dry_run: bool = False
    failure_threshold: int = DEFAULT_FAILURE_THRESHOLD

    def __post_init__(self) -> None:
        if not math.isfinite(self.throttle) or not 0.0 <= self.throttle <= 1.0:
            raise ValueError("throttle must be finite and in [0, 1]")
        if not math.isfinite(self.max_steering) or not 0.0 < self.max_steering <= 1.0:
            raise ValueError("max_steering must be finite and in (0, 1]")
        if not math.isfinite(self.steering_smoothing) or not 0.0 < self.steering_smoothing <= 1.0:
            raise ValueError("steering_smoothing must be finite and in (0, 1]")
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")


def resolve_device(device_name: str) -> torch.device:
    if device_name == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device_name == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available")
    if device_name not in {"cpu", "cuda"}:
        raise ValueError(f"Unsupported device: {device_name}")
    return torch.device(device_name)


def clip_steering(value: float, max_steering: float) -> float:
    if not math.isfinite(value):
        raise ValueError("steering value must be finite")
    if not math.isfinite(max_steering) or max_steering <= 0:
        raise ValueError("max_steering must be finite and positive")
    return max(-max_steering, min(max_steering, value))


def smooth_steering(previous: float | None, current: float, alpha: float) -> float:
    if not 0.0 < alpha <= 1.0:
        raise ValueError("smoothing alpha must be in (0, 1]")
    if previous is None:
        return current
    return alpha * current + (1.0 - alpha) * previous


def decode_telemetry_image(payload: str | bytes) -> np.ndarray:
    if isinstance(payload, bytes):
        encoded = payload.strip()
    elif isinstance(payload, str):
        text = payload.strip()
        if text.startswith("data:"):
            separator = text.find(",")
            if separator < 0:
                raise ValueError("Malformed image data URI")
            text = text[separator + 1 :]
        encoded = text.encode("ascii", errors="strict")
    else:
        raise ValueError("Telemetry image must be base64 text or bytes")
    if not encoded:
        raise ValueError("Telemetry image is empty")
    try:
        image_bytes = base64.b64decode(encoded, validate=True)
        with Image.open(io.BytesIO(image_bytes)) as image:
            image.load()
            image_rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    except (ValueError, OSError, UnidentifiedImageError) as exc:
        raise ValueError("Could not decode telemetry image") from exc
    validate_frame_shape(image_rgb)
    return image_rgb


def validate_frame_shape(image_rgb: np.ndarray) -> None:
    if image_rgb.ndim != 3 or image_rgb.shape[2] != 3:
        raise ValueError(f"Expected an H x W x 3 frame, got {image_rgb.shape}")
    height, width = image_rgb.shape[:2]
    if width < MIN_FRAME_WIDTH or height < MIN_FRAME_HEIGHT:
        raise ValueError(f"Frame is too small: {width}x{height}")
    if width * height > MAX_FRAME_PIXELS:
        raise ValueError(f"Frame is too large: {width}x{height}")


def frame_to_tensor(
    image_rgb: np.ndarray,
    preprocessing_profile: str,
    device: torch.device,
) -> torch.Tensor:
    validate_frame_shape(image_rgb)
    image_array = preprocess_image_for_model(
        image_rgb,
        preprocessing_profile,
        color_order="RGB",
    )
    expected = (3, MODEL_INPUT_HEIGHT, MODEL_INPUT_WIDTH)
    if image_array.shape != expected:
        raise ValueError(f"Preprocessing returned {image_array.shape}; expected {expected}")
    return torch.from_numpy(image_array).unsqueeze(0).to(device)


class ModelRuntime:
    def __init__(
        self,
        model: torch.nn.Module,
        device: torch.device,
        preprocessing_profile: str,
        model_name: str,
        model_arch: str,
    ) -> None:
        self.model = model
        self.device = device
        self.preprocessing_profile = preprocessing_profile
        self.model_name = model_name
        self.model_arch = model_arch
        self.device_name = str(device)

    @classmethod
    def load(cls, checkpoint_path: Path, device_name: str = "cpu") -> "ModelRuntime":
        checkpoint_path = checkpoint_path.resolve()
        if not checkpoint_path.is_file():
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
        device = resolve_device(device_name)
        try:
            checkpoint = load_checkpoint(checkpoint_path)
            model_arch = resolve_model_arch("checkpoint", checkpoint)
            preprocessing_profile = resolve_preprocessing_profile("checkpoint", checkpoint)
            state_dict = (
                checkpoint.get("model_state_dict", checkpoint)
                if isinstance(checkpoint, dict)
                else checkpoint
            )
            model = make_steering_model(model_arch)
            model.load_state_dict(state_dict)
            model.to(device)
            model.eval()
        except Exception as exc:
            raise RuntimeError(f"Could not load simulator checkpoint: {checkpoint_path}") from exc
        return cls(model, device, preprocessing_profile, checkpoint_path.name, model_arch)

    def predict_rgb(self, image_rgb: np.ndarray) -> PredictionResult:
        image_tensor = frame_to_tensor(image_rgb, self.preprocessing_profile, self.device)
        started = time.perf_counter()
        with torch.inference_mode():
            steering = float(self.model(image_tensor).item())
        latency_ms = (time.perf_counter() - started) * 1000
        if not math.isfinite(steering):
            raise ValueError("Model returned a non-finite steering prediction")
        return PredictionResult(steering=steering, inference_latency_ms=latency_ms)


def _percentile(values: list[float], percent: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percent / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


class TelemetrySessionLogger:
    def __init__(
        self,
        log_dir: Path,
        model_name: str,
        device_name: str,
        dry_run: bool,
        *,
        session_id: str | None = None,
    ) -> None:
        self.log_dir = log_dir.resolve()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id or datetime.now(timezone.utc).strftime(
            "%Y%m%dT%H%M%S_%fZ"
        )
        self.csv_path = self.log_dir / f"session_{self.session_id}.csv"
        self.summary_path = self.log_dir / f"session_{self.session_id}_summary.json"
        self.model_name = model_name
        self.device_name = device_name
        self.dry_run = dry_run
        self.started_monotonic = time.monotonic()
        self.total_frames = 0
        self.successful_predictions = 0
        self.failed_frames = 0
        self.disconnect_count = 0
        self.inference_latencies: list[float] = []
        self.steering_commands: list[float] = []
        self._lock = threading.Lock()
        self._closed = False
        self._handle = self.csv_path.open("x", encoding="utf-8", newline="")
        self._writer = csv.DictWriter(
            self._handle,
            fieldnames=TELEMETRY_COLUMNS,
            lineterminator="\n",
        )
        self._writer.writeheader()
        self._handle.flush()

    def record(self, row: dict[str, object], *, successful: bool) -> None:
        with self._lock:
            if self._closed:
                return
            self._writer.writerow({column: row.get(column, "") for column in TELEMETRY_COLUMNS})
            self._handle.flush()
            self.total_frames += 1
            if successful:
                self.successful_predictions += 1
                latency = row.get("inference_latency_ms")
                steering = row.get("smoothed_steering_command")
                if isinstance(latency, (int, float)) and math.isfinite(float(latency)):
                    self.inference_latencies.append(float(latency))
                if isinstance(steering, (int, float)) and math.isfinite(float(steering)):
                    self.steering_commands.append(float(steering))
            else:
                self.failed_frames += 1

    def mark_disconnect(self) -> None:
        with self._lock:
            self.disconnect_count += 1

    def summary(self, emergency_stop: bool, emergency_reason: str | None) -> dict[str, object]:
        runtime = time.monotonic() - self.started_monotonic
        steering = self.steering_commands
        inference = self.inference_latencies
        return {
            "session_id": self.session_id,
            "model": self.model_name,
            "device": self.device_name,
            "dry_run": self.dry_run,
            "total_frames": self.total_frames,
            "successful_predictions": self.successful_predictions,
            "failed_frames": self.failed_frames,
            "average_inference_latency_ms": statistics.fmean(inference) if inference else None,
            "p95_inference_latency_ms": _percentile(inference, 95),
            "steering_mean": statistics.fmean(steering) if steering else None,
            "steering_standard_deviation": statistics.pstdev(steering) if steering else None,
            "steering_minimum": min(steering) if steering else None,
            "steering_maximum": max(steering) if steering else None,
            "total_runtime_seconds": runtime,
            "disconnect_count": self.disconnect_count,
            "emergency_stop": emergency_stop,
            "emergency_stop_reason": emergency_reason,
            "telemetry_csv": str(self.csv_path),
        }

    def close(self, emergency_stop: bool, emergency_reason: str | None) -> dict[str, object]:
        with self._lock:
            if not self._closed:
                self._handle.flush()
                self._handle.close()
                self._closed = True
        summary = self.summary(emergency_stop, emergency_reason)
        self.summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return summary


class EmergencyStopState:
    def __init__(self) -> None:
        self._event = threading.Event()
        self._reason: str | None = None
        self._lock = threading.Lock()

    @property
    def active(self) -> bool:
        return self._event.is_set()

    @property
    def reason(self) -> str | None:
        return self._reason

    def trigger(self, reason: str) -> bool:
        with self._lock:
            if self._event.is_set():
                return False
            self._reason = reason
            self._event.set()
            return True


ControlEmitter = Callable[[str, float, float], None]


class ClosedLoopDriver:
    def __init__(
        self,
        inference_runtime: InferenceRuntime,
        config: DriverConfig,
        telemetry_logger: TelemetrySessionLogger,
        control_emitter: ControlEmitter | None = None,
    ) -> None:
        self.inference_runtime = inference_runtime
        self.config = config
        self.telemetry_logger = telemetry_logger
        self.control_emitter = control_emitter
        self.emergency = EmergencyStopState()
        self.connected_sids: set[str] = set()
        self.frame_index = 0
        self.previous_steering: float | None = None
        self.consecutive_failures = 0
        self.shutdown_callback: Callable[[], None] | None = None
        self._close_lock = threading.Lock()
        self._closed = False

    def set_control_emitter(self, emitter: ControlEmitter) -> None:
        self.control_emitter = emitter

    def set_shutdown_callback(self, callback: Callable[[], None]) -> None:
        self.shutdown_callback = callback

    def _send_control(self, sid: str, steering: float, throttle: float) -> tuple[float, float]:
        steering = clip_steering(steering, self.config.max_steering)
        throttle = max(0.0, min(1.0, throttle)) if math.isfinite(throttle) else 0.0
        if self.config.dry_run or self.emergency.active:
            steering = 0.0
            throttle = 0.0
        if self.control_emitter is not None:
            self.control_emitter(sid, steering, throttle)
        return steering, throttle

    def send_neutral_to_all(self) -> None:
        for sid in tuple(self.connected_sids):
            try:
                self._send_control(sid, 0.0, 0.0)
            except Exception:
                pass

    def request_emergency_stop(self, reason: str) -> None:
        first_trigger = self.emergency.trigger(reason)
        self.send_neutral_to_all()
        if first_trigger and self.shutdown_callback is not None:
            threading.Thread(target=self.shutdown_callback, daemon=True).start()

    def on_connect(self, sid: str) -> tuple[float, float]:
        self.connected_sids.add(sid)
        self.previous_steering = None
        self.consecutive_failures = 0
        return self._send_control(sid, 0.0, 0.0)

    def on_disconnect(self, sid: str) -> None:
        self.connected_sids.discard(sid)
        self.previous_steering = None
        self.telemetry_logger.mark_disconnect()

    @staticmethod
    def _speed(data: dict[str, Any]) -> float | None:
        try:
            speed = float(data.get("speed", ""))
        except (TypeError, ValueError):
            return None
        return speed if math.isfinite(speed) else None

    def handle_telemetry(self, sid: str, data: dict[str, Any] | None) -> dict[str, object]:
        frame_started = time.perf_counter()
        self.frame_index += 1
        raw_prediction: float | None = None
        smoothed_command = 0.0
        throttle_command = 0.0
        inference_latency: float | None = None
        error_state = "ok"
        successful = False
        speed = self._speed(data or {})

        try:
            if self.emergency.active:
                raise RuntimeError(f"emergency_stop:{self.emergency.reason}")
            if not isinstance(data, dict):
                raise ValueError("Telemetry payload is missing")
            image_rgb = decode_telemetry_image(data.get("image", ""))
            prediction = self.inference_runtime.predict_rgb(image_rgb)
            raw_prediction = prediction.steering
            inference_latency = prediction.inference_latency_ms
            if not math.isfinite(raw_prediction):
                raise ValueError("Model returned a non-finite steering prediction")
            bounded = clip_steering(raw_prediction, self.config.max_steering)
            smoothed_command = smooth_steering(
                self.previous_steering,
                bounded,
                self.config.steering_smoothing,
            )
            smoothed_command = clip_steering(smoothed_command, self.config.max_steering)
            self.previous_steering = smoothed_command
            throttle_command = self.config.throttle
            self.consecutive_failures = 0
            successful = True
        except Exception as exc:
            error_state = f"{type(exc).__name__}:{exc}"
            self.consecutive_failures += 1
            self.previous_steering = None
            smoothed_command = 0.0
            throttle_command = 0.0

        control_failure = False
        try:
            steering_sent, throttle_sent = self._send_control(
                sid, smoothed_command, throttle_command
            )
        except Exception as exc:
            steering_sent, throttle_sent = 0.0, 0.0
            successful = False
            control_failure = True
            error_state = f"control_emit_failure:{type(exc).__name__}:{exc}"
        frame_latency = (time.perf_counter() - frame_started) * 1000
        row: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "simulator_speed": speed if speed is not None else "",
            "raw_steering_prediction": raw_prediction if raw_prediction is not None else "",
            "smoothed_steering_command": steering_sent,
            "throttle_command": throttle_sent,
            "inference_latency_ms": inference_latency if inference_latency is not None else "",
            "frame_processing_latency_ms": frame_latency,
            "model": self.inference_runtime.model_name,
            "device": self.inference_runtime.device_name,
            "frame_index": self.frame_index,
            "error_state": error_state,
            "dry_run": self.config.dry_run,
        }
        self.telemetry_logger.record(row, successful=successful)
        if control_failure:
            self.request_emergency_stop("control_emit_failure")
        if self.consecutive_failures >= self.config.failure_threshold:
            self.request_emergency_stop("repeated_inference_failure")
        return row

    def close(self) -> dict[str, object]:
        with self._close_lock:
            if self._closed:
                return self.telemetry_logger.summary(
                    self.emergency.active, self.emergency.reason
                )
            self.send_neutral_to_all()
            self._closed = True
            return self.telemetry_logger.close(
                self.emergency.active, self.emergency.reason
            )


def socketio_control_payload(steering: float, throttle: float) -> dict[str, str]:
    return {
        "steering_angle": f"{steering:.8f}",
        "throttle": f"{throttle:.8f}",
    }


def build_socketio_app(driver: ClosedLoopDriver) -> tuple[Any, Any]:
    try:
        import socketio
    except ImportError as exc:
        raise RuntimeError(
            "Simulator dependencies are missing; install requirements-simulator.txt"
        ) from exc

    sio = socketio.Server(
        async_mode="threading",
        cors_allowed_origins=[],
        logger=False,
        engineio_logger=False,
    )
    driver.set_control_emitter(
        lambda sid, steering, throttle: sio.emit(
            "steer",
            data=socketio_control_payload(steering, throttle),
            to=sid,
        )
    )

    @sio.event
    def connect(sid: str, environ: dict[str, Any], auth: Any = None) -> bool:
        del environ, auth
        driver.on_connect(sid)
        return True

    @sio.on("telemetry")
    def telemetry(sid: str, data: dict[str, Any] | None) -> None:
        driver.handle_telemetry(sid, data)

    @sio.event
    def disconnect(sid: str, reason: str | None = None) -> None:
        del reason
        driver.on_disconnect(sid)

    return sio, socketio.WSGIApp(sio)


def run_socketio_server(
    driver: ClosedLoopDriver,
    host: str,
    port: int,
    *,
    emergency_stop_file: Path,
    max_runtime_seconds: float | None,
) -> dict[str, object]:
    try:
        from werkzeug.serving import make_server
    except ImportError as exc:
        raise RuntimeError(
            "Werkzeug is missing; install requirements-simulator.txt"
        ) from exc
    if not 1 <= port <= 65535:
        raise ValueError("port must be in [1, 65535]")
    if max_runtime_seconds is not None and max_runtime_seconds <= 0:
        raise ValueError("max_runtime_seconds must be positive")
    emergency_stop_file = emergency_stop_file.resolve()
    emergency_stop_file.parent.mkdir(parents=True, exist_ok=True)
    if emergency_stop_file.exists():
        raise FileExistsError(
            f"Emergency-stop file already exists; remove it before startup: {emergency_stop_file}"
        )

    _, app = build_socketio_app(driver)
    server = make_server(host, port, app, threaded=True)
    driver.set_shutdown_callback(server.shutdown)
    monitor_stop = threading.Event()
    started = time.monotonic()

    def monitor() -> None:
        while not monitor_stop.wait(0.1):
            if emergency_stop_file.exists():
                driver.request_emergency_stop("emergency_stop_file")
                return
            if (
                max_runtime_seconds is not None
                and time.monotonic() - started >= max_runtime_seconds
            ):
                driver.request_emergency_stop("max_runtime")
                return

    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        driver.request_emergency_stop("keyboard_interrupt")
    finally:
        monitor_stop.set()
        driver.send_neutral_to_all()
        server.server_close()
        monitor_thread.join(timeout=1.0)
    return driver.close()


def run_self_test(
    inference_runtime: InferenceRuntime,
    config: DriverConfig,
    log_dir: Path,
    image_path: Path,
) -> tuple[dict[str, object], dict[str, object]]:
    if not image_path.is_file():
        raise FileNotFoundError(f"Self-test image not found: {image_path}")
    logger = TelemetrySessionLogger(
        log_dir,
        inference_runtime.model_name,
        inference_runtime.device_name,
        True,
    )
    emitted: list[tuple[str, float, float]] = []
    safe_config = DriverConfig(
        throttle=config.throttle,
        max_steering=config.max_steering,
        steering_smoothing=config.steering_smoothing,
        dry_run=True,
        failure_threshold=config.failure_threshold,
    )
    driver = ClosedLoopDriver(
        inference_runtime,
        safe_config,
        logger,
        lambda sid, steering, throttle: emitted.append((sid, steering, throttle)),
    )
    try:
        driver.on_connect("self-test")
        payload = base64.b64encode(image_path.read_bytes()).decode("ascii")
        row = driver.handle_telemetry(
            "self-test", {"image": payload, "speed": "0"}
        )
        if row["error_state"] != "ok":
            raise RuntimeError(f"Self-test inference failed: {row['error_state']}")
        if any(steering != 0.0 or throttle != 0.0 for _, steering, throttle in emitted):
            raise RuntimeError("Self-test dry-run attempted an active control command")
    finally:
        summary = driver.close()
    return row, summary


def default_emergency_stop_file(log_dir: Path) -> Path:
    return log_dir / "EMERGENCY_STOP"


def protocol_environment() -> dict[str, object]:
    return {
        "socketio_protocol": "EIO4",
        "telemetry_event": "telemetry",
        "control_event": "steer",
        "host_default": DEFAULT_HOST,
        "port_default": DEFAULT_PORT,
        "process_id": os.getpid(),
    }
