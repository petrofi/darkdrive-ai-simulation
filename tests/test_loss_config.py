from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

import torch
from PIL import Image
from torch import nn

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.training.train_behavior_cloning import (  # noqa: E402
    HUBER_BETA,
    LOSS_HUBER,
    LOSS_MSE,
    DrivingDataset,
    loss_metadata,
    make_loss_function,
    train,
)
from src.utils.image_preprocessing import BASELINE_PROFILE  # noqa: E402


class LossConfigTests(unittest.TestCase):
    def make_manifest(self, root: Path, name: str, steerings: list[float]) -> Path:
        images_dir = root / name / "IMG"
        images_dir.mkdir(parents=True)
        csv_path = root / name / "driving_log.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "image_path",
                    "steering",
                    "throttle",
                    "brake",
                    "speed",
                    "source_dataset",
                    "source_session",
                ]
            )
            for index, steering in enumerate(steerings):
                image_path = images_dir / f"center_{index:04d}.jpg"
                Image.new("RGB", (16, 8), color=(index * 40 % 255, 80, 120)).save(image_path)
                writer.writerow(
                    [
                        str(image_path),
                        steering,
                        1.0,
                        0.0,
                        12.0,
                        "test_simulator",
                        name,
                    ]
                )
        return csv_path

    def test_default_loss_is_mse(self) -> None:
        loss_function = make_loss_function()

        self.assertIsInstance(loss_function, nn.MSELoss)
        self.assertEqual(loss_metadata(LOSS_MSE)["pytorch_loss"], "MSELoss")

    def test_huber_loss_uses_smooth_l1_with_fixed_beta(self) -> None:
        loss_function = make_loss_function(LOSS_HUBER)

        self.assertIsInstance(loss_function, nn.SmoothL1Loss)
        self.assertEqual(loss_metadata(LOSS_HUBER)["beta"], HUBER_BETA)
        self.assertEqual(loss_metadata(LOSS_HUBER)["delta"], HUBER_BETA)
        self.assertAlmostEqual(float(loss_function.beta), HUBER_BETA)

    def test_unsupported_loss_fails_clearly(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported regression loss"):
            make_loss_function("mae")

    def test_huber_metadata_is_stored_in_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            train_csv = self.make_manifest(root, "train_session", [0.0, 0.2, -0.3])
            validation_csv = self.make_manifest(root, "validation_session", [0.1, -0.2])
            output_path = root / "huber.pt"
            chart_path = root / "huber.png"

            success = train(
                csv_path=train_csv,
                dataset_format="simple",
                train_csv_path=train_csv,
                validation_csv_path=validation_csv,
                epochs=1,
                batch_size=2,
                output_path=output_path,
                chart_output=chart_path,
                learning_rate=0.001,
                loss_name=LOSS_HUBER,
                preprocessing_profile=BASELINE_PROFILE,
                device_name="cpu",
                seed=42,
            )

            self.assertTrue(success)
            checkpoint = torch.load(output_path, map_location="cpu", weights_only=True)
            self.assertEqual(checkpoint["loss"]["name"], LOSS_HUBER)
            self.assertEqual(checkpoint["loss"]["beta"], HUBER_BETA)
            self.assertEqual(checkpoint["training_args"]["loss"], LOSS_HUBER)
            self.assertEqual(checkpoint["training_args"]["loss_beta"], HUBER_BETA)
            self.assertEqual(checkpoint["training_args"]["loss_delta"], HUBER_BETA)
            self.assertEqual(checkpoint["training_args"]["preprocessing_profile"], BASELINE_PROFILE)

    def test_driving_dataset_defaults_to_baseline_preprocessing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            csv_path = self.make_manifest(root, "baseline_session", [0.0])
            dataset = DrivingDataset(csv_path)

            self.assertEqual(dataset.preprocessing_profile, BASELINE_PROFILE)


if __name__ == "__main__":
    unittest.main()
