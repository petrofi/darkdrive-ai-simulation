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
from urllib.parse import parse_qs, urlencode
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
PROTOCOL_DEBUG_EVENT_LIMIT = 100
MAX_UNITY_COMPAT_MESSAGE_CHARS = 2_000_000
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


class ProtocolDiagnostics:
    """Thread-safe, bounded Socket.IO diagnostics without payload contents."""

    COUNTER_NAMES = (
        "engineio_connections",
        "socketio_connections",
        "raw_events_received",
        "telemetry_events_received",
        "unknown_events_received",
        "steer_events_sent",
        "connect_failures",
        "namespace_failures",
    )
    COMPAT_COUNTER_NAMES = (
        "engineio_compat_connections",
        "compat_messages_received",
        "compat_socketio_events_parsed",
        "compat_telemetry_events",
        "compat_unknown_events",
        "compat_malformed_messages",
        "compat_steer_events_sent",
        "implicit_namespace_connections",
    )

    def __init__(
        self,
        enabled: bool = False,
        *,
        event_log_limit: int = PROTOCOL_DEBUG_EVENT_LIMIT,
    ) -> None:
        if event_log_limit < 0:
            raise ValueError("event_log_limit must be non-negative")
        self.enabled = enabled
        self.event_log_limit = event_log_limit
        self._counters = {
            name: 0 for name in (*self.COUNTER_NAMES, *self.COMPAT_COUNTER_NAMES)
        }
        self.protocol_backend = "standard_socketio"
        self.unity_compat_mode = False
        self._eio_versions: set[str] = set()
        self._transports: set[str] = set()
        self._successful_transports: set[str] = set()
        self._namespaces: set[str] = set()
        self._last_query_string = ""
        self._last_disconnect_reason: str | None = None
        self._transport_failures = 0
        self._event_logs_written = 0
        self._event_limit_reported = False
        self._compat_successful_telemetry = 0
        self._compat_steer_failures = 0
        self._compat_logs_written = 0
        self._compat_log_limit_reported = False
        self._protocol_logs_written = 0
        self._protocol_log_limit_reported = False
        self._lock = threading.Lock()

    def configure_backend(self, backend: str, unity_compat_mode: bool) -> None:
        with self._lock:
            self.protocol_backend = backend
            self.unity_compat_mode = unity_compat_mode

    def _debug(self, message: str) -> None:
        if self.enabled:
            print(f"[protocol-debug] {message}", flush=True)

    def _bounded_protocol_debug(self, message: str) -> None:
        should_log = False
        report_limit = False
        with self._lock:
            if self.enabled and self._protocol_logs_written < self.event_log_limit:
                self._protocol_logs_written += 1
                should_log = True
            elif self.enabled and not self._protocol_log_limit_reported:
                self._protocol_log_limit_reported = True
                report_limit = True
        if should_log:
            self._debug(message)
        elif report_limit:
            self._debug(
                f"protocol logger limit reached ({self.event_log_limit}); further lines suppressed"
            )

    @staticmethod
    def _request_metadata(environ: dict[str, Any]) -> tuple[str, str, str]:
        raw_query = str(environ.get("QUERY_STRING", ""))
        query = parse_qs(raw_query, keep_blank_values=True)
        eio = query.get("EIO", [""])[0]
        transport = query.get("transport", [""])[0]
        sid = query.get("sid", [""])[0]
        safe_query = urlencode(
            [(key, value) for key in ("EIO", "transport", "sid") for value in query.get(key, [])]
        )
        return eio, transport, safe_query or "(none)"

    def record_request(self, environ: dict[str, Any]) -> None:
        eio, transport, safe_query = self._request_metadata(environ)
        with self._lock:
            if eio:
                self._eio_versions.add(eio)
            if transport:
                self._transports.add(transport)
            self._last_query_string = safe_query
        self._bounded_protocol_debug(
            f"request method={environ.get('REQUEST_METHOD', '')} "
            f"path={environ.get('PATH_INFO', '')} query_string={safe_query} "
            f"EIO={eio or '(missing)'} transport={transport or '(missing)'}"
        )

    def record_request_result(self, status: str, transport: str) -> None:
        try:
            status_code = int(status.split(" ", 1)[0])
        except (ValueError, IndexError):
            status_code = 500
        with self._lock:
            if status_code < 400:
                if transport:
                    self._successful_transports.add(transport)
                return
            self._transport_failures += 1
            self._counters["connect_failures"] += 1
        self._debug(f"request_failure status={status} transport={transport or '(missing)'}")

    def record_engineio_connect(self, eio_sid: str, environ: dict[str, Any]) -> None:
        eio, transport, safe_query = self._request_metadata(environ)
        with self._lock:
            self._counters["engineio_connections"] += 1
            if eio:
                self._eio_versions.add(eio)
            if transport:
                self._transports.add(transport)
                self._successful_transports.add(transport)
            self._last_query_string = safe_query
        self._debug(
            f"engineio_connect sid={eio_sid} query_string={safe_query} "
            f"EIO={eio or '(missing)'} transport={transport or '(missing)'}"
        )

    def record_namespace_connect(self, namespace: str, sid: str | None, success: bool) -> None:
        namespace = namespace or "/"
        with self._lock:
            self._namespaces.add(namespace)
            if success:
                self._counters["socketio_connections"] += 1
            else:
                self._counters["connect_failures"] += 1
                self._counters["namespace_failures"] += 1
        outcome = "connected" if success else "failed"
        self._debug(f"socketio_namespace {outcome} namespace={namespace} sid={sid or '(none)'}")

    @staticmethod
    def payload_summary(payload: Any) -> str:
        payload_type = type(payload).__name__
        if not isinstance(payload, dict):
            return f"payload_type={payload_type}"
        all_keys = sorted(str(key) for key in payload.keys())
        keys = [key[:64] for key in all_keys[:30]]
        image_present = "image" in payload
        image = payload.get("image")
        image_length = len(image) if isinstance(image, (str, bytes)) else None
        return (
            f"payload_type={payload_type} dict_keys={keys} "
            f"dict_key_count={len(all_keys)} "
            f"image_present={str(image_present).lower()} "
            f"image_string_length={image_length if image_length is not None else '(not-string)'}"
        )

    @staticmethod
    def compat_payload_summary(payload: Any) -> str:
        try:
            payload_length: int | None = len(payload)
        except TypeError:
            payload_length = None
        return (
            f"{ProtocolDiagnostics.payload_summary(payload)} "
            f"payload_length={payload_length if payload_length is not None else '(unknown)'}"
        )

    def _bounded_compat_debug(self, message: str) -> None:
        should_log = False
        report_limit = False
        with self._lock:
            if self.enabled and self._compat_logs_written < self.event_log_limit:
                self._compat_logs_written += 1
                should_log = True
            elif self.enabled and not self._compat_log_limit_reported:
                self._compat_log_limit_reported = True
                report_limit = True
        if should_log:
            self._debug(message)
        elif report_limit:
            self._debug(
                f"compat log limit reached ({self.event_log_limit}); further messages suppressed"
            )

    def record_compat_connection(
        self,
        eio_sid: str,
        environ: dict[str, Any],
    ) -> None:
        eio, transport, safe_query = self._request_metadata(environ)
        with self._lock:
            self._counters["engineio_compat_connections"] += 1
            self._counters["implicit_namespace_connections"] += 1
            self._namespaces.add("/")
            if eio:
                self._eio_versions.add(eio)
            if transport:
                self._transports.add(transport)
                self._successful_transports.add(transport)
            self._last_query_string = safe_query
        self._debug(
            f"unity_compat_connect sid={eio_sid} namespace=/ implicit=true "
            f"query_string={safe_query} EIO={eio or '(missing)'} "
            f"transport={transport or '(missing)'}"
        )

    def record_compat_message(self, sid: str, message: Any) -> None:
        with self._lock:
            self._counters["compat_messages_received"] += 1
        try:
            message_length: int | str = len(message)
        except TypeError:
            message_length = "(unknown)"
        self._bounded_compat_debug(
            f"unity_compat_message sid={sid} message_type={type(message).__name__} "
            f"message_length={message_length}"
        )

    def record_compat_malformed(self, sid: str, message: Any, reason: str) -> None:
        with self._lock:
            self._counters["compat_malformed_messages"] += 1
        try:
            message_length: int | str = len(message)
        except TypeError:
            message_length = "(unknown)"
        self._bounded_compat_debug(
            f"unity_compat_malformed sid={sid} reason={reason[:160]} "
            f"message_type={type(message).__name__} message_length={message_length}"
        )

    def record_compat_event(self, sid: str, event: str, payload: Any) -> bool:
        valid_telemetry = event == "telemetry" and isinstance(payload, dict)
        with self._lock:
            self._counters["compat_socketio_events_parsed"] += 1
            if valid_telemetry:
                self._counters["compat_telemetry_events"] += 1
            elif event == "telemetry":
                self._counters["compat_malformed_messages"] += 1
            else:
                self._counters["compat_unknown_events"] += 1
        self._bounded_compat_debug(
            f"unity_compat_event event={event[:160]} namespace=/ sid={sid} "
            f"{self.compat_payload_summary(payload)}"
        )
        return valid_telemetry

    def record_compat_telemetry_result(self, successful: bool) -> None:
        if successful:
            with self._lock:
                self._compat_successful_telemetry += 1

    def record_compat_steer_sent(self, sid: str, encoded: str) -> None:
        with self._lock:
            self._counters["compat_steer_events_sent"] += 1
        self._bounded_compat_debug(
            f"unity_compat_steer_sent sid={sid} socketio_packet_type=EVENT "
            f"encoded_length={len(encoded)}"
        )

    def record_compat_steer_failure(self, sid: str, exc: Exception) -> None:
        with self._lock:
            self._compat_steer_failures += 1
        self._debug(
            f"unity_compat_steer_failed sid={sid} "
            f"error={type(exc).__name__}:{str(exc)[:160]}"
        )

    def record_event(
        self,
        event: str,
        namespace: str,
        sid: str,
        payload: Any,
        *,
        telemetry: bool,
    ) -> None:
        should_log = False
        report_limit = False
        with self._lock:
            self._counters["raw_events_received"] += 1
            counter = "telemetry_events_received" if telemetry else "unknown_events_received"
            self._counters[counter] += 1
            self._namespaces.add(namespace or "/")
            if self.enabled and self._event_logs_written < self.event_log_limit:
                self._event_logs_written += 1
                should_log = True
            elif self.enabled and not self._event_limit_reported:
                self._event_limit_reported = True
                report_limit = True
        if should_log:
            self._debug(
                f"event={event} namespace={namespace or '/'} sid={sid} "
                f"{self.payload_summary(payload)}"
            )
        elif report_limit:
            self._debug(f"event log limit reached ({self.event_log_limit}); further events suppressed")

    def record_steer_sent(self, sid: str, steering: float, throttle: float) -> None:
        with self._lock:
            self._counters["steer_events_sent"] += 1
        self._debug(
            f"steer_sent namespace=/ sid={sid} steering={steering:g} throttle={throttle:g}"
        )

    def record_disconnect(self, eio_sid: str, reason: Any) -> None:
        reason_text = str(reason) if reason is not None else "(none)"
        with self._lock:
            self._last_disconnect_reason = reason_text[:200]
        self._debug(f"engineio_disconnect sid={eio_sid} reason={reason_text[:200]}")

    def _verdict(self) -> tuple[str, str]:
        counters = self._counters
        if counters["telemetry_events_received"]:
            return "P1", "telemetry received"
        if any(version != "4" for version in self._eio_versions):
            return "P3", "Engine.IO version mismatch or missing EIO4 request"
        if counters["namespace_failures"] or any(ns != "/" for ns in self._namespaces):
            return "P4", "namespace mismatch"
        if counters["unknown_events_received"]:
            return "P4", "event-name or payload-contract mismatch"
        if self._transport_failures:
            return "P5", "transport or handshake failure"
        if counters["socketio_connections"]:
            return "P2", "Socket.IO connected but telemetry was not emitted"
        return "P6", "no complete Socket.IO namespace connection observed"

    def _unity_compat_verdict(self) -> tuple[str, str]:
        counters = self._counters
        if self._compat_steer_failures and not counters["compat_steer_events_sent"]:
            return "UC5", "outgoing steer framing or emission failed"
        if self._compat_successful_telemetry:
            return "UC1", "Unity compatibility telemetry confirmed"
        if counters["compat_telemetry_events"]:
            return "UC4", "telemetry parsed but image or inference failed"
        if counters["compat_messages_received"]:
            return "UC3", "messages received but framing or payload was unsupported"
        if counters["engineio_compat_connections"]:
            return "UC2", "Engine.IO connected but compatibility parser received no messages"
        return "UC6", "Unity compatibility result unresolved"

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            standard_verdict, standard_explanation = self._verdict()
            compat_verdict, compat_explanation = self._unity_compat_verdict()
            verdict = compat_verdict if self.unity_compat_mode else standard_verdict
            explanation = (
                compat_explanation if self.unity_compat_mode else standard_explanation
            )
            eio_versions = sorted(self._eio_versions)
            transports = sorted(self._transports)
            namespaces = sorted(self._namespaces)
            negotiated_transport = (
                "websocket"
                if "websocket" in self._successful_transports
                else "polling" if "polling" in self._successful_transports else None
            )
            return {
                "protocol_debug": self.enabled,
                "protocol_backend": self.protocol_backend,
                "unity_compat_mode": self.unity_compat_mode,
                **self._counters,
                "requested_eio_version": eio_versions[0] if len(eio_versions) == 1 else None,
                "requested_eio_versions": eio_versions,
                "negotiated_transport": negotiated_transport,
                "requested_transports": transports,
                "namespace": namespaces[0] if len(namespaces) == 1 else None,
                "namespaces_observed": namespaces,
                "last_query_string": self._last_query_string,
                "last_disconnect_reason": self._last_disconnect_reason,
                "transport_failures": self._transport_failures,
                "compat_successful_telemetry": self._compat_successful_telemetry,
                "compat_steer_failures": self._compat_steer_failures,
                "unity_compat_verdict": compat_verdict if self.unity_compat_mode else None,
                "final_protocol_verdict": verdict,
                "protocol_diagnostic_verdict": verdict,
                "protocol_verdict": verdict,
                "protocol_verdict_explanation": explanation,
            }


class ProtocolSafeLogger:
    """Logger facade that keeps protocol logs useful without packet contents."""

    def __init__(self, diagnostics: ProtocolDiagnostics, component: str) -> None:
        self.diagnostics = diagnostics
        self.component = component

    @staticmethod
    def _safe_argument(value: Any) -> str:
        text = str(value)
        if len(text) > 160:
            return f"<{type(value).__name__} length={len(text)}>"
        return text.replace("\r", "\\r").replace("\n", "\\n")

    def _log(self, level: str, message: Any, *args: Any, **kwargs: Any) -> None:
        del kwargs
        template = str(message)
        if " data %s" in template.lower() and args:
            data = args[-1]
            prefix_template = template.rsplit(" data %s", 1)[0]
            prefix_args = tuple(self._safe_argument(value) for value in args[:-1])
            try:
                rendered = prefix_template % prefix_args
            except (TypeError, ValueError):
                rendered = prefix_template
            rendered = f"{rendered} data=<redacted> data_length={len(str(data))}"
        else:
            safe_args = tuple(self._safe_argument(value) for value in args)
            try:
                rendered = template % safe_args if safe_args else template
            except (TypeError, ValueError):
                rendered = f"{template} args={list(safe_args)}"
        self.diagnostics._bounded_protocol_debug(
            f"{self.component} level={level} message={rendered[:500]}"
        )

    def debug(self, message: Any, *args: Any, **kwargs: Any) -> None:
        self._log("debug", message, *args, **kwargs)

    def info(self, message: Any, *args: Any, **kwargs: Any) -> None:
        self._log("info", message, *args, **kwargs)

    def warning(self, message: Any, *args: Any, **kwargs: Any) -> None:
        self._log("warning", message, *args, **kwargs)

    warn = warning

    def error(self, message: Any, *args: Any, **kwargs: Any) -> None:
        self._log("error", message, *args, **kwargs)

    def exception(self, message: Any, *args: Any, **kwargs: Any) -> None:
        self._log("exception", message, *args, **kwargs)


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
        protocol_diagnostics: ProtocolDiagnostics | None = None,
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
        self.protocol_diagnostics = protocol_diagnostics or ProtocolDiagnostics()
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
            **self.protocol_diagnostics.snapshot(),
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

    def send_neutral(self, sid: str) -> tuple[float, float]:
        return self._send_control(sid, 0.0, 0.0)

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
    def format_value(value: float) -> str:
        if value == 0:
            return "0"
        return f"{value:.8f}"

    return {
        "steering_angle": format_value(steering),
        "throttle": format_value(throttle),
    }


class UnityCompatProtocolError(ValueError):
    pass


def parse_unity_socketio_event(message: Any) -> tuple[str, Any]:
    """Parse only the two observed Socket.IO EVENT framing forms."""
    if not isinstance(message, str):
        raise UnityCompatProtocolError("message must be text")
    if len(message) > MAX_UNITY_COMPAT_MESSAGE_CHARS:
        raise UnityCompatProtocolError("message exceeds compatibility size limit")
    if message.startswith("42"):
        socketio_message = message[1:]
    elif message.startswith("2"):
        socketio_message = message
    else:
        raise UnityCompatProtocolError("unsupported Socket.IO packet type")
    if not socketio_message.startswith("2["):
        raise UnityCompatProtocolError("unsupported Socket.IO EVENT framing")
    try:
        decoded = json.loads(socketio_message[1:])
    except json.JSONDecodeError as exc:
        raise UnityCompatProtocolError("malformed Socket.IO EVENT JSON") from exc
    if not isinstance(decoded, list) or len(decoded) != 2:
        raise UnityCompatProtocolError("Socket.IO EVENT must contain event and payload")
    event, payload = decoded
    if not isinstance(event, str) or not event:
        raise UnityCompatProtocolError("Socket.IO event name must be non-empty text")
    return event, payload


def encode_unity_socketio_event(event: str, payload: dict[str, str]) -> str:
    if not isinstance(event, str) or not event:
        raise ValueError("Socket.IO event name must be non-empty text")
    return "2" + json.dumps([event, payload], separators=(",", ":"))


class ProtocolDebugWSGIMiddleware:
    def __init__(self, app: Any, diagnostics: ProtocolDiagnostics) -> None:
        self.app = app
        self.diagnostics = diagnostics

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> Any:
        self.diagnostics.record_request(environ)
        _, transport, _ = self.diagnostics._request_metadata(environ)

        def diagnostic_start_response(
            status: str,
            headers: list[tuple[str, str]],
            exc_info: Any = None,
        ) -> Any:
            self.diagnostics.record_request_result(status, transport)
            return start_response(status, headers, exc_info)

        return self.app(environ, diagnostic_start_response)


def build_socketio_app(driver: ClosedLoopDriver, protocol_debug: bool = False) -> tuple[Any, Any]:
    try:
        import socketio
    except ImportError as exc:
        raise RuntimeError(
            "Simulator dependencies are missing; install requirements-simulator.txt"
        ) from exc

    diagnostics = driver.telemetry_logger.protocol_diagnostics
    diagnostics.enabled = protocol_debug
    diagnostics.configure_backend("standard_socketio", False)

    class DiagnosticSocketIOServer(socketio.Server):
        def _handle_eio_connect(self, eio_sid: str, environ: dict[str, Any]) -> Any:
            diagnostics.record_engineio_connect(eio_sid, environ)
            return super()._handle_eio_connect(eio_sid, environ)

        def _handle_connect(self, eio_sid: str, namespace: str | None, data: Any) -> Any:
            resolved_namespace = namespace or "/"
            try:
                return super()._handle_connect(eio_sid, namespace, data)
            finally:
                sid = self.manager.sid_from_eio_sid(eio_sid, resolved_namespace)
                success = bool(sid and self.manager.is_connected(sid, resolved_namespace))
                diagnostics.record_namespace_connect(resolved_namespace, sid, success)

        def _handle_eio_disconnect(self, eio_sid: str, reason: Any) -> Any:
            diagnostics.record_disconnect(eio_sid, reason)
            return super()._handle_eio_disconnect(eio_sid, reason)

    socketio_logger: Any = False
    engineio_logger: Any = False
    if protocol_debug:
        socketio_logger = ProtocolSafeLogger(diagnostics, "socketio")
        engineio_logger = ProtocolSafeLogger(diagnostics, "engineio")

    sio = DiagnosticSocketIOServer(
        async_mode="threading",
        cors_allowed_origins=[],
        logger=socketio_logger,
        engineio_logger=engineio_logger,
        namespaces="*" if protocol_debug else None,
    )
    def emit_control(sid: str, steering: float, throttle: float) -> None:
        sio.emit(
            "steer",
            data=socketio_control_payload(steering, throttle),
            to=sid,
            namespace="/",
        )
        diagnostics.record_steer_sent(sid, steering, throttle)

    driver.set_control_emitter(emit_control)

    @sio.on("connect", namespace="/")
    def connect(sid: str, environ: dict[str, Any], auth: Any = None) -> bool:
        del auth
        if protocol_debug:
            _, _, safe_query = diagnostics._request_metadata(environ)
            diagnostics._debug(f"connect_handler namespace=/ sid={sid} query_string={safe_query}")
        try:
            steering, throttle = driver.on_connect(sid)
        except Exception as exc:
            driver.connected_sids.discard(sid)
            diagnostics._debug(
                f"initial_neutral failed namespace=/ sid={sid} "
                f"error={type(exc).__name__}:{str(exc)[:160]}"
            )
            return False
        diagnostics._debug(
            f"initial_neutral success namespace=/ sid={sid} steering={steering:g} throttle={throttle:g}"
        )
        return True

    @sio.on("telemetry", namespace="/")
    def telemetry(sid: str, data: Any) -> None:
        diagnostics.record_event("telemetry", "/", sid, data, telemetry=True)
        driver.handle_telemetry(sid, data)

    @sio.on("disconnect", namespace="/")
    def disconnect(sid: str, reason: str | None = None) -> None:
        diagnostics._debug(f"disconnect_handler namespace=/ sid={sid} reason={reason or '(none)'}")
        driver.on_disconnect(sid)

    if protocol_debug:
        @sio.on("connect", namespace="*")
        def connect_other(
            namespace: str,
            sid: str,
            environ: dict[str, Any],
            auth: Any = None,
        ) -> bool:
            del environ, auth
            diagnostics._debug(f"connect_handler alternate_namespace={namespace} sid={sid}")
            return True

        @sio.on("disconnect", namespace="*")
        def disconnect_other(namespace: str, sid: str, reason: Any = None) -> None:
            diagnostics._debug(
                f"disconnect_handler alternate_namespace={namespace} sid={sid} "
                f"reason={reason or '(none)'}"
            )

        @sio.on("*", namespace="/")
        def unknown_default(event: str, sid: str, *data: Any) -> None:
            payload = data[0] if len(data) == 1 else list(data)
            diagnostics.record_event(event, "/", sid, payload, telemetry=False)

        @sio.on("*", namespace="*")
        def unknown_other(event: str, namespace: str, sid: str, *data: Any) -> None:
            payload = data[0] if len(data) == 1 else list(data)
            diagnostics.record_event(event, namespace, sid, payload, telemetry=False)

    app: Any = socketio.WSGIApp(sio)
    if protocol_debug:
        app = ProtocolDebugWSGIMiddleware(app, diagnostics)
    return sio, app


def build_unity_compat_engineio_app(
    driver: ClosedLoopDriver,
    protocol_debug: bool = False,
) -> tuple[Any, Any]:
    try:
        import engineio
    except ImportError as exc:
        raise RuntimeError(
            "Simulator dependencies are missing; install requirements-simulator.txt"
        ) from exc

    diagnostics = driver.telemetry_logger.protocol_diagnostics
    diagnostics.enabled = protocol_debug
    diagnostics.configure_backend("unity_engineio_compat", True)
    engineio_logger: Any = (
        ProtocolSafeLogger(diagnostics, "engineio") if protocol_debug else False
    )
    eio = engineio.Server(
        async_mode="threading",
        cors_allowed_origins=[],
        logger=engineio_logger,
    )

    def emit_control(sid: str, steering: float, throttle: float) -> None:
        encoded = encode_unity_socketio_event(
            "steer",
            socketio_control_payload(steering, throttle),
        )
        try:
            eio.send(sid, encoded)
        except Exception as exc:
            diagnostics.record_compat_steer_failure(sid, exc)
            raise
        diagnostics.record_compat_steer_sent(sid, encoded)

    def send_safe_neutral(sid: str) -> None:
        try:
            driver.send_neutral(sid)
        except Exception:
            driver.request_emergency_stop("control_emit_failure")

    driver.set_control_emitter(emit_control)

    @eio.on("connect")
    def connect(sid: str, environ: dict[str, Any]) -> bool:
        diagnostics.record_compat_connection(sid, environ)
        try:
            steering, throttle = driver.on_connect(sid)
        except Exception as exc:
            driver.connected_sids.discard(sid)
            diagnostics._debug(
                f"unity_compat_initial_neutral failed sid={sid} "
                f"error={type(exc).__name__}:{str(exc)[:160]}"
            )
            return False
        diagnostics._debug(
            f"unity_compat_initial_neutral success sid={sid} "
            f"steering={steering:g} throttle={throttle:g}"
        )
        return True

    @eio.on("message")
    def message(sid: str, raw_message: Any) -> None:
        diagnostics.record_compat_message(sid, raw_message)
        try:
            event, payload = parse_unity_socketio_event(raw_message)
        except UnityCompatProtocolError as exc:
            diagnostics.record_compat_malformed(sid, raw_message, str(exc))
            send_safe_neutral(sid)
            return

        valid_telemetry = diagnostics.record_compat_event(sid, event, payload)
        if event != "telemetry" or not valid_telemetry:
            send_safe_neutral(sid)
            return

        row = driver.handle_telemetry(sid, payload)
        diagnostics.record_compat_telemetry_result(row.get("error_state") == "ok")

    @eio.on("disconnect")
    def disconnect(sid: str, reason: Any = None) -> None:
        try:
            driver.send_neutral(sid)
        except Exception:
            pass
        diagnostics.record_disconnect(sid, reason)
        driver.on_disconnect(sid)

    app: Any = engineio.WSGIApp(eio, engineio_path="socket.io")
    if protocol_debug:
        app = ProtocolDebugWSGIMiddleware(app, diagnostics)
    return eio, app


def run_socketio_server(
    driver: ClosedLoopDriver,
    host: str,
    port: int,
    *,
    emergency_stop_file: Path,
    max_runtime_seconds: float | None,
    protocol_debug: bool = False,
    unity_compat_mode: bool = False,
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

    if unity_compat_mode:
        _, app = build_unity_compat_engineio_app(
            driver,
            protocol_debug=protocol_debug,
        )
    else:
        _, app = build_socketio_app(driver, protocol_debug=protocol_debug)
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
