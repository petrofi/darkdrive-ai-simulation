from __future__ import annotations

import base64
import csv
import io
import json
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from src.simulator.closed_loop_driver import (
    ClosedLoopDriver,
    DriverConfig,
    ModelRuntime,
    PredictionResult,
    TelemetrySessionLogger,
    clip_steering,
    decode_telemetry_image,
    frame_to_tensor,
    smooth_steering,
)


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


if __name__ == "__main__":
    unittest.main()
