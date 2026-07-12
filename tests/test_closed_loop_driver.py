from __future__ import annotations

import base64
import csv
import io
import json
import math
import tempfile
import threading
import unittest
import urllib.parse
import urllib.request
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
    UnityCompatProtocolError,
    build_socketio_app,
    build_unity_compat_engineio_app,
    clip_steering,
    decode_telemetry_image,
    frame_to_tensor,
    encode_unity_socketio_event,
    parse_unity_socketio_event,
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
        self.assertEqual(diagnostics.snapshot()["protocol_backend"], "standard_socketio")
        self.assertFalse(diagnostics.snapshot()["unity_compat_mode"])
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


class UnityCompatibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def make_driver(
        self,
        *,
        protocol_debug: bool = False,
        event_log_limit: int = 100,
    ) -> tuple[ClosedLoopDriver, TelemetrySessionLogger, ProtocolDiagnostics]:
        runtime = FakeRuntime([0.4])
        diagnostics = ProtocolDiagnostics(
            enabled=protocol_debug,
            event_log_limit=event_log_limit,
        )
        logger = TelemetrySessionLogger(
            self.root,
            runtime.model_name,
            runtime.device_name,
            True,
            session_id="unity_compat",
            protocol_diagnostics=diagnostics,
        )
        driver = ClosedLoopDriver(runtime, DriverConfig(dry_run=True), logger)
        return driver, logger, diagnostics

    @staticmethod
    def environ() -> dict[str, str]:
        return {
            "QUERY_STRING": "EIO=4&transport=websocket",
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/socket.io/",
        }

    def build_with_capture(
        self,
        *,
        protocol_debug: bool = False,
        event_log_limit: int = 100,
    ) -> tuple[
        ClosedLoopDriver,
        TelemetrySessionLogger,
        ProtocolDiagnostics,
        object,
        list[tuple[str, str]],
    ]:
        driver, logger, diagnostics = self.make_driver(
            protocol_debug=protocol_debug,
            event_log_limit=event_log_limit,
        )
        eio, _ = build_unity_compat_engineio_app(
            driver,
            protocol_debug=protocol_debug,
        )
        emitted: list[tuple[str, str]] = []
        eio.send = lambda sid, data: emitted.append((sid, data))
        return driver, logger, diagnostics, eio, emitted

    def test_cli_unity_compat_mode_is_opt_in(self) -> None:
        self.assertFalse(parse_args([]).unity_compat_mode)
        self.assertTrue(parse_args(["--unity-compat-mode"]).unity_compat_mode)

    def test_verified_callback_and_wire_framing_are_parsed(self) -> None:
        payload = {"image": "abc", "speed": "0"}
        self.assertEqual(
            parse_unity_socketio_event('2["telemetry",{"image":"abc","speed":"0"}]'),
            ("telemetry", payload),
        )
        self.assertEqual(
            parse_unity_socketio_event('42["telemetry",{"image":"abc","speed":"0"}]'),
            ("telemetry", payload),
        )

    def test_malformed_json_and_wrong_packet_type_are_rejected(self) -> None:
        for message in ('2["telemetry",', '3["telemetry",{}]', '40'):
            with self.subTest(message=message):
                with self.assertRaises(UnityCompatProtocolError):
                    parse_unity_socketio_event(message)

    def test_connect_registers_engineio_sid_and_sends_one_neutral(self) -> None:
        driver, _, diagnostics, eio, emitted = self.build_with_capture()
        self.assertTrue(eio.handlers["connect"]("engine-sid", self.environ()))
        self.assertIn("engine-sid", driver.connected_sids)
        self.assertEqual(
            emitted,
            [
                (
                    "engine-sid",
                    '2["steer",{"steering_angle":"0","throttle":"0"}]',
                )
            ],
        )
        snapshot = diagnostics.snapshot()
        self.assertEqual(snapshot["protocol_backend"], "unity_engineio_compat")
        self.assertTrue(snapshot["unity_compat_mode"])
        self.assertEqual(snapshot["engineio_compat_connections"], 1)
        self.assertEqual(snapshot["implicit_namespace_connections"], 1)
        self.assertEqual(snapshot["compat_steer_events_sent"], 1)
        self.assertEqual(snapshot["unity_compat_verdict"], "UC2")
        driver.close()

    def test_standard_backend_still_rejects_event_without_namespace_connect(self) -> None:
        driver, _, _ = self.make_driver()
        sio, _ = build_socketio_app(driver)
        sio._handle_eio_connect("engine-sid", self.environ())
        sio._handle_eio_message(
            "engine-sid",
            encode_unity_socketio_event(
                "telemetry",
                {"image": image_payload(), "speed": "1"},
            ),
        )
        self.assertEqual(driver.frame_index, 0)
        self.assertNotIn("engine-sid", driver.connected_sids)
        driver.close()

    def test_initial_compat_steer_failure_rejects_connection_with_uc5(self) -> None:
        driver, _, diagnostics = self.make_driver()
        eio, _ = build_unity_compat_engineio_app(driver)

        def fail_send(sid: str, data: str) -> None:
            del sid, data
            raise OSError("closed")

        eio.send = fail_send
        self.assertFalse(eio.handlers["connect"]("engine-sid", self.environ()))
        self.assertNotIn("engine-sid", driver.connected_sids)
        snapshot = diagnostics.snapshot()
        self.assertEqual(snapshot["compat_steer_events_sent"], 0)
        self.assertEqual(snapshot["compat_steer_failures"], 1)
        self.assertEqual(snapshot["unity_compat_verdict"], "UC5")
        driver.close()

    def test_compat_telemetry_reaches_driver_once_and_stays_neutral(self) -> None:
        driver, _, diagnostics, eio, emitted = self.build_with_capture()
        eio.handlers["connect"]("engine-sid", self.environ())
        emitted.clear()
        packet = encode_unity_socketio_event(
            "telemetry",
            {"image": image_payload(), "speed": "3"},
        )
        eio.handlers["message"]("engine-sid", packet)
        self.assertEqual(driver.frame_index, 1)
        self.assertEqual(emitted[-1][0], "engine-sid")
        self.assertEqual(
            parse_unity_socketio_event(emitted[-1][1]),
            ("steer", {"steering_angle": "0", "throttle": "0"}),
        )
        snapshot = diagnostics.snapshot()
        self.assertEqual(snapshot["compat_messages_received"], 1)
        self.assertEqual(snapshot["compat_socketio_events_parsed"], 1)
        self.assertEqual(snapshot["compat_telemetry_events"], 1)
        self.assertEqual(snapshot["telemetry_events_received"], 0)
        self.assertEqual(snapshot["compat_successful_telemetry"], 1)
        self.assertEqual(snapshot["unity_compat_verdict"], "UC1")
        driver.close()

    def test_unknown_and_non_dictionary_telemetry_are_safe(self) -> None:
        driver, _, diagnostics, eio, emitted = self.build_with_capture()
        eio.handlers["connect"]("engine-sid", self.environ())
        emitted.clear()
        eio.handlers["message"]("engine-sid", '2["manual",[1,2]]')
        eio.handlers["message"]("engine-sid", '2["telemetry",["not-a-dict"]]')
        snapshot = diagnostics.snapshot()
        self.assertEqual(snapshot["compat_unknown_events"], 1)
        self.assertEqual(snapshot["compat_malformed_messages"], 1)
        self.assertEqual(snapshot["compat_telemetry_events"], 0)
        self.assertEqual(driver.frame_index, 0)
        self.assertEqual(len(emitted), 2)
        for _, encoded in emitted:
            self.assertEqual(
                parse_unity_socketio_event(encoded),
                ("steer", {"steering_angle": "0", "throttle": "0"}),
            )
        self.assertEqual(snapshot["unity_compat_verdict"], "UC3")
        driver.close()

    def test_malformed_message_is_bounded_and_never_prints_image(self) -> None:
        driver, _, diagnostics, eio, _ = self.build_with_capture(
            protocol_debug=True,
            event_log_limit=2,
        )
        image = "private-base64" * 100
        output = io.StringIO()
        with redirect_stdout(output):
            eio.handlers["connect"]("engine-sid", self.environ())
            eio.handlers["message"](
                "engine-sid",
                f'2["telemetry",{{"image":"{image}"}}',
            )
        rendered = output.getvalue()
        self.assertNotIn(image, rendered)
        self.assertIn("message_length=", rendered)
        self.assertEqual(diagnostics.snapshot()["compat_malformed_messages"], 1)
        driver.close()

    def test_bad_image_produces_uc4_and_zero_control(self) -> None:
        driver, _, diagnostics, eio, emitted = self.build_with_capture()
        eio.handlers["connect"]("engine-sid", self.environ())
        emitted.clear()
        eio.handlers["message"](
            "engine-sid",
            '2["telemetry",{"image":"not-base64","speed":"0"}]',
        )
        self.assertEqual(len(emitted), 1)
        self.assertEqual(
            parse_unity_socketio_event(emitted[0][1]),
            ("steer", {"steering_angle": "0", "throttle": "0"}),
        )
        snapshot = diagnostics.snapshot()
        self.assertEqual(snapshot["compat_telemetry_events"], 1)
        self.assertEqual(snapshot["compat_successful_telemetry"], 0)
        self.assertEqual(snapshot["unity_compat_verdict"], "UC4")
        driver.close()

    def test_disconnect_sends_neutral_and_clears_driver_state(self) -> None:
        driver, _, diagnostics, eio, emitted = self.build_with_capture()
        eio.handlers["connect"]("engine-sid", self.environ())
        emitted.clear()
        driver.previous_steering = 0.5
        eio.handlers["disconnect"]("engine-sid", "client disconnect")
        self.assertEqual(len(emitted), 1)
        self.assertNotIn("engine-sid", driver.connected_sids)
        self.assertIsNone(driver.previous_steering)
        self.assertEqual(driver.telemetry_logger.disconnect_count, 1)
        self.assertEqual(
            diagnostics.snapshot()["last_disconnect_reason"],
            "client disconnect",
        )
        driver.close()

    def test_summary_contains_compatibility_fields_and_uc1(self) -> None:
        driver, logger, _, eio, _ = self.build_with_capture()
        eio.handlers["connect"]("engine-sid", self.environ())
        eio.handlers["message"](
            "engine-sid",
            encode_unity_socketio_event(
                "telemetry",
                {"image": image_payload(), "speed": "1"},
            ),
        )
        summary = driver.close()
        self.assertEqual(summary["final_protocol_verdict"], "UC1")
        self.assertEqual(summary["protocol_diagnostic_verdict"], "UC1")
        self.assertEqual(summary["engineio_compat_connections"], 1)
        self.assertEqual(summary["compat_telemetry_events"], 1)
        written = json.loads(logger.summary_path.read_text(encoding="utf-8"))
        self.assertEqual(written["unity_compat_verdict"], "UC1")

    def test_engineio_wraps_callback_and_outgoing_socketio_event_correctly(self) -> None:
        from werkzeug.serving import make_server

        driver, _, diagnostics = self.make_driver()
        _, app = build_unity_compat_engineio_app(driver)
        server = make_server("127.0.0.1", 0, app, threaded=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def request(url: str, data: bytes | None = None) -> str:
            http_request = urllib.request.Request(
                url,
                data=data,
                method="POST" if data is not None else "GET",
            )
            if data is not None:
                http_request.add_header("Content-Type", "text/plain;charset=UTF-8")
            with urllib.request.urlopen(http_request, timeout=3) as response:
                return response.read().decode("utf-8")

        try:
            base = (
                f"http://127.0.0.1:{server.server_port}/socket.io/"
                "?EIO=4&transport=polling"
            )
            opened = request(base)
            packets = opened.split("\x1e")
            open_packet = next(packet for packet in packets if packet.startswith("0"))
            sid = json.loads(open_packet[1:])["sid"]
            self.assertIn(
                '42["steer",{"steering_angle":"0","throttle":"0"}]',
                packets,
            )
            session_url = base + "&sid=" + urllib.parse.quote(sid)
            wire_packet = "4" + encode_unity_socketio_event(
                "telemetry",
                {"image": image_payload(), "speed": "2"},
            )
            self.assertEqual(request(session_url, wire_packet.encode("utf-8")), "OK")
            response_packets = request(session_url).split("\x1e")
            self.assertIn(
                '42["steer",{"steering_angle":"0","throttle":"0"}]',
                response_packets,
            )
            request(session_url, b"1")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
            summary = driver.close()

        self.assertEqual(summary["total_frames"], 1)
        self.assertEqual(summary["successful_predictions"], 1)
        self.assertEqual(summary["compat_messages_received"], 1)
        self.assertEqual(summary["compat_telemetry_events"], 1)
        self.assertEqual(summary["unity_compat_verdict"], "UC1")


if __name__ == "__main__":
    unittest.main()
