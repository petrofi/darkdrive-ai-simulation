from __future__ import annotations

import base64
import csv
import io
import json
import math
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from src.simulator.closed_loop_driver import (
    ClosedLoopDriver,
    DriverConfig,
    ModelRuntime,
    PredictionResult,
    ProtocolDiagnostics,
    ProtocolSafeLogger,
    TelemetrySessionLogger,
    build_socketio_app,
    clip_steering,
    decode_telemetry_image,
    frame_to_tensor,
    smooth_steering,
    socketio_control_payload,
)
from scripts.run_closed_loop_simulator import parse_args


class FakeRuntime:
    model_name = "fake.pt"
    device_name = "cpu"
    preprocessing_profile = "baseline"

    def __init__(self, predictions: list[float] | None = None) -> None:
        self.predictions = predictions or [0.25]
        self.calls = 0

    def predict_rgb(self, image_rgb: np.ndarray) -> PredictionResult:
        del image_rgb
        index = min(self.calls, len(self.predictions) - 1)
        self.calls += 1
        return PredictionResult(self.predictions[index], 2.5)


def image_payload(width: int = 320, height: int = 160) -> str:
    image = Image.new("RGB", (width, height), color=(20, 80, 120))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


class ClosedLoopDriverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.emitted: list[tuple[str, float, float]] = []

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def make_driver(
        self,
        *,
        predictions: list[float] | None = None,
        dry_run: bool = False,
        failure_threshold: int = 3,
    ) -> tuple[ClosedLoopDriver, TelemetrySessionLogger]:
        runtime = FakeRuntime(predictions)
        config = DriverConfig(
            throttle=0.10,
            max_steering=0.8,
            steering_smoothing=0.5,
            dry_run=dry_run,
            failure_threshold=failure_threshold,
        )
        logger = TelemetrySessionLogger(
            self.root,
            runtime.model_name,
            runtime.device_name,
            dry_run,
            session_id="fixture",
        )
        driver = ClosedLoopDriver(
            runtime,
            config,
            logger,
            lambda sid, steering, throttle: self.emitted.append(
                (sid, steering, throttle)
            ),
        )
        driver.on_connect("simulator")
        self.emitted.clear()
        return driver, logger

    def test_checkpoint_loading_failure_prevents_runtime(self) -> None:
        with self.assertRaises(FileNotFoundError):
            ModelRuntime.load(self.root / "missing.pt")

    def test_image_decoding(self) -> None:
        decoded = decode_telemetry_image(image_payload())
        self.assertEqual(decoded.shape, (160, 320, 3))
        self.assertEqual(decoded.dtype, np.uint8)

    def test_preprocessing_shape(self) -> None:
        decoded = decode_telemetry_image(image_payload())
        tensor = frame_to_tensor(decoded, "baseline", torch.device("cpu"))
        self.assertEqual(tuple(tensor.shape), (1, 3, 80, 160))

    def test_steering_clipping(self) -> None:
        self.assertEqual(clip_steering(2.0, 0.8), 0.8)
        self.assertEqual(clip_steering(-2.0, 0.8), -0.8)

    def test_smoothing_behavior(self) -> None:
        self.assertEqual(smooth_steering(None, 0.5, 0.25), 0.5)
        self.assertAlmostEqual(smooth_steering(0.5, -0.5, 0.25), 0.25)

    def test_nan_and_inf_predictions_are_rejected(self) -> None:
        for value in (math.nan, math.inf):
            with self.subTest(value=value):
                self.emitted.clear()
                session = f"nonfinite_{'nan' if math.isnan(value) else 'inf'}"
                runtime = FakeRuntime([value])
                logger = TelemetrySessionLogger(
                    self.root, "fake.pt", "cpu", False, session_id=session
                )
                driver = ClosedLoopDriver(
                    runtime,
                    DriverConfig(),
                    logger,
                    lambda sid, steering, throttle: self.emitted.append(
                        (sid, steering, throttle)
                    ),
                )
                driver.on_connect("simulator")
                self.emitted.clear()
                row = driver.handle_telemetry(
                    "simulator", {"image": image_payload(), "speed": "10"}
                )
                self.assertNotEqual(row["error_state"], "ok")
                self.assertEqual(self.emitted[-1][1:], (0.0, 0.0))
                driver.close()

    def test_corrupt_frame_sends_zero_throttle(self) -> None:
        driver, _ = self.make_driver()
        row = driver.handle_telemetry(
            "simulator", {"image": "not-base64", "speed": "4"}
        )
        self.assertNotEqual(row["error_state"], "ok")
        self.assertEqual(self.emitted[-1], ("simulator", 0.0, 0.0))
        driver.close()

    def test_dry_run_sends_no_active_control(self) -> None:
        driver, _ = self.make_driver(predictions=[0.6], dry_run=True)
        row = driver.handle_telemetry(
            "simulator", {"image": image_payload(), "speed": "5"}
        )
        self.assertEqual(row["error_state"], "ok")
        self.assertEqual(self.emitted[-1], ("simulator", 0.0, 0.0))
        driver.close()

    def test_emergency_stop_produces_zero_throttle(self) -> None:
        driver, _ = self.make_driver(predictions=[0.4])
        driver.request_emergency_stop("test")
        self.assertTrue(driver.emergency.active)
        self.assertEqual(self.emitted[-1], ("simulator", 0.0, 0.0))
        row = driver.handle_telemetry(
            "simulator", {"image": image_payload(), "speed": "5"}
        )
        self.assertEqual(row["throttle_command"], 0.0)
        driver.close()

    def test_repeated_failures_latch_emergency_stop(self) -> None:
        driver, _ = self.make_driver(failure_threshold=2)
        for _ in range(2):
            driver.handle_telemetry("simulator", {"image": "bad"})
        self.assertTrue(driver.emergency.active)
        self.assertEqual(driver.emergency.reason, "repeated_inference_failure")
        driver.close()

    def test_control_emit_failure_is_logged_and_latches_stop(self) -> None:
        driver, _ = self.make_driver(predictions=[0.2])

        def fail_emit(sid: str, steering: float, throttle: float) -> None:
            del sid, steering, throttle
            raise OSError("socket closed")

        driver.set_control_emitter(fail_emit)
        row = driver.handle_telemetry(
            "simulator", {"image": image_payload(), "speed": "4"}
        )
        self.assertTrue(str(row["error_state"]).startswith("control_emit_failure"))
        self.assertEqual(row["throttle_command"], 0.0)
        self.assertTrue(driver.emergency.active)
        self.assertEqual(driver.emergency.reason, "control_emit_failure")
        driver.close()

    def test_telemetry_session_summary(self) -> None:
        driver, logger = self.make_driver(predictions=[0.2, -0.2])
        driver.handle_telemetry("simulator", {"image": image_payload(), "speed": "7"})
        driver.handle_telemetry("simulator", {"image": image_payload(), "speed": "8"})
        summary = driver.close()
        self.assertEqual(summary["total_frames"], 2)
        self.assertEqual(summary["successful_predictions"], 2)
        self.assertEqual(summary["failed_frames"], 0)
        self.assertIsNotNone(summary["average_inference_latency_ms"])
        self.assertEqual(summary["protocol_verdict"], "P6")
        self.assertEqual(summary["telemetry_events_received"], 0)
        written = json.loads(logger.summary_path.read_text(encoding="utf-8"))
        self.assertEqual(written["total_frames"], 2)
        with logger.csv_path.open(encoding="utf-8", newline="") as handle:
            self.assertEqual(len(list(csv.DictReader(handle))), 2)

    def test_clean_disconnect_is_counted_and_idempotent(self) -> None:
        driver, _ = self.make_driver()
        driver.on_disconnect("simulator")
        driver.on_disconnect("simulator")
        summary = driver.close()
        self.assertEqual(summary["disconnect_count"], 2)
        self.assertNotIn("simulator", driver.connected_sids)


class ProtocolDiagnosticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def make_driver(
        self,
        diagnostics: ProtocolDiagnostics,
        *,
        dry_run: bool = True,
    ) -> tuple[ClosedLoopDriver, TelemetrySessionLogger]:
        runtime = FakeRuntime([0.4])
        logger = TelemetrySessionLogger(
            self.root,
            runtime.model_name,
            runtime.device_name,
            dry_run,
            session_id="protocol",
            protocol_diagnostics=diagnostics,
        )
        driver = ClosedLoopDriver(
            runtime,
            DriverConfig(dry_run=dry_run),
            logger,
        )
        return driver, logger

    def test_cli_protocol_debug_flag_defaults_false_and_can_be_enabled(self) -> None:
        self.assertFalse(parse_args([]).protocol_debug)
        self.assertTrue(parse_args(["--protocol-debug"]).protocol_debug)

    def test_protocol_counters_and_eio4_verdict(self) -> None:
        diagnostics = ProtocolDiagnostics()
        environ = {
            "QUERY_STRING": "EIO=4&transport=websocket&token=do-not-log",
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/socket.io/",
        }
        diagnostics.record_request(environ)
        diagnostics.record_engineio_connect("eio-1", environ)
        diagnostics.record_namespace_connect("/", "sio-1", True)
        diagnostics.record_event(
            "telemetry", "/", "sio-1", {"image": "abc", "speed": "0"}, telemetry=True
        )
        diagnostics.record_steer_sent("sio-1", 0.0, 0.0)
        snapshot = diagnostics.snapshot()
        self.assertEqual(snapshot["engineio_connections"], 1)
        self.assertEqual(snapshot["socketio_connections"], 1)
        self.assertEqual(snapshot["raw_events_received"], 1)
        self.assertEqual(snapshot["telemetry_events_received"], 1)
        self.assertEqual(snapshot["unknown_events_received"], 0)
        self.assertEqual(snapshot["steer_events_sent"], 1)
        self.assertEqual(snapshot["protocol_verdict"], "P1")
        self.assertEqual(snapshot["protocol_diagnostic_verdict"], "P1")
        self.assertEqual(snapshot["requested_eio_version"], "4")
        self.assertEqual(snapshot["negotiated_transport"], "websocket")
        self.assertEqual(snapshot["namespace"], "/")
        self.assertNotIn("token", str(snapshot["last_query_string"]))

    def test_eio3_is_reported_as_protocol_mismatch(self) -> None:
        diagnostics = ProtocolDiagnostics()
        diagnostics.record_request({"QUERY_STRING": "EIO=3&transport=websocket"})
        self.assertEqual(diagnostics.snapshot()["protocol_verdict"], "P3")

    def test_failed_websocket_request_is_not_reported_as_negotiated(self) -> None:
        diagnostics = ProtocolDiagnostics()
        diagnostics.record_request({"QUERY_STRING": "EIO=4&transport=polling"})
        diagnostics.record_request_result("200 OK", "polling")
        diagnostics.record_request({"QUERY_STRING": "EIO=4&transport=websocket"})
        diagnostics.record_request_result("400 BAD REQUEST", "websocket")
        snapshot = diagnostics.snapshot()
        self.assertEqual(snapshot["negotiated_transport"], "polling")
        self.assertEqual(snapshot["transport_failures"], 1)
        self.assertEqual(snapshot["protocol_verdict"], "P5")

    def test_payload_debug_is_bounded_and_never_prints_image(self) -> None:
        diagnostics = ProtocolDiagnostics(enabled=True, event_log_limit=1)
        image = "secret-base64-value" * 100
        output = io.StringIO()
        with redirect_stdout(output):
            diagnostics.record_event(
                "manual", "/alternate", "sid", {"image": image, "speed": "4"}, telemetry=False
            )
            diagnostics.record_event("second", "/", "sid", "value", telemetry=False)
        rendered = output.getvalue()
        self.assertIn("event=manual", rendered)
        self.assertIn("namespace=/alternate", rendered)
        self.assertIn(f"image_string_length={len(image)}", rendered)
        self.assertIn("dict_keys=['image', 'speed']", rendered)
        self.assertNotIn(image, rendered)
        self.assertIn("further events suppressed", rendered)
        snapshot = diagnostics.snapshot()
        self.assertEqual(snapshot["unknown_events_received"], 2)
        self.assertEqual(snapshot["protocol_verdict"], "P4")

    def test_engineio_logger_redacts_packet_data(self) -> None:
        diagnostics = ProtocolDiagnostics(enabled=True)
        logger = ProtocolSafeLogger(diagnostics, "engineio")
        image = "private-image-data" * 100
        output = io.StringIO()
        with redirect_stdout(output):
            logger.info(
                "%s: Received packet %s data %s",
                "sid",
                "MESSAGE",
                f'42["telemetry",{{"image":"{image}"}}]',
            )
        rendered = output.getvalue()
        self.assertIn("data=<redacted>", rendered)
        self.assertIn("data_length=", rendered)
        self.assertNotIn(image, rendered)

    def test_explicit_default_namespace_and_initial_neutral_payload(self) -> None:
        diagnostics = ProtocolDiagnostics(enabled=True)
        driver, _ = self.make_driver(diagnostics)
        sio, _ = build_socketio_app(driver, protocol_debug=True)
        emitted: list[tuple[str, dict[str, str], str, str]] = []

        def capture_emit(
            event: str,
            data: dict[str, str],
            *,
            to: str,
            namespace: str,
        ) -> None:
            emitted.append((event, data, to, namespace))

        sio.emit = capture_emit
        connect_handler = sio.handlers["/"]["connect"]
        self.assertTrue(
            connect_handler(
                "simulator-sid",
                {"QUERY_STRING": "EIO=4&transport=websocket"},
                None,
            )
        )
        self.assertEqual(
            emitted,
            [("steer", {"steering_angle": "0", "throttle": "0"}, "simulator-sid", "/")],
        )
        self.assertIn("telemetry", sio.handlers["/"])
        self.assertIn("disconnect", sio.handlers["/"])
        self.assertIn("*", sio.handlers["/"])
        driver.close()

    def test_telemetry_handler_wins_over_catch_all(self) -> None:
        diagnostics = ProtocolDiagnostics()
        driver, _ = self.make_driver(diagnostics)
        sio, _ = build_socketio_app(driver, protocol_debug=True)
        sio.emit = lambda *args, **kwargs: None
        sio.handlers["/"]["telemetry"](
            "simulator-sid", {"image": image_payload(), "speed": "3"}
        )
        snapshot = diagnostics.snapshot()
        self.assertEqual(snapshot["raw_events_received"], 1)
        self.assertEqual(snapshot["telemetry_events_received"], 1)
        self.assertEqual(snapshot["unknown_events_received"], 0)
        driver.close()

    def test_initial_neutral_failure_rejects_connection(self) -> None:
        diagnostics = ProtocolDiagnostics()
        driver, _ = self.make_driver(diagnostics)
        sio, _ = build_socketio_app(driver, protocol_debug=True)

        def fail_emit(*args: object, **kwargs: object) -> None:
            del args, kwargs
            raise OSError("closed")

        sio.emit = fail_emit
        connected = sio.handlers["/"]["connect"](
            "failed-sid", {"QUERY_STRING": "EIO=4&transport=websocket"}, None
        )
        self.assertFalse(connected)
        self.assertNotIn("failed-sid", driver.connected_sids)
        self.assertEqual(diagnostics.snapshot()["steer_events_sent"], 0)
        driver.close()

    def test_normal_mode_has_no_catch_all_or_debug_output(self) -> None:
        diagnostics = ProtocolDiagnostics(enabled=True)
        driver, _ = self.make_driver(diagnostics)
        output = io.StringIO()
        with redirect_stdout(output):
            sio, _ = build_socketio_app(driver, protocol_debug=False)
        self.assertFalse(diagnostics.enabled)
        self.assertNotIn("*", sio.handlers.get("/", {}))
        self.assertEqual(output.getvalue(), "")
        driver.close()

    def test_summary_contains_protocol_failure_fields(self) -> None:
        diagnostics = ProtocolDiagnostics()
        diagnostics.record_namespace_connect("/wrong", None, False)
        driver, logger = self.make_driver(diagnostics)
        summary = driver.close()
        self.assertEqual(summary["connect_failures"], 1)
        self.assertEqual(summary["namespace_failures"], 1)
        self.assertEqual(summary["protocol_verdict"], "P4")
        written = json.loads(logger.summary_path.read_text(encoding="utf-8"))
        self.assertEqual(written["namespaces_observed"], ["/wrong"])

    def test_zero_control_payload_uses_exact_simulator_strings(self) -> None:
        self.assertEqual(
            socketio_control_payload(0.0, -0.0),
            {"steering_angle": "0", "throttle": "0"},
        )


if __name__ == "__main__":
    unittest.main()
