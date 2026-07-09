from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.training.train_behavior_cloning import DrivingDataset  # noqa: E402
from src.utils.image_preprocessing import (  # noqa: E402
    BASELINE_PROFILE,
    MODEL_INPUT_HEIGHT,
    MODEL_INPUT_WIDTH,
    ROAD_CROP_V1_BOUNDS,
    ROAD_CROP_V1_PROFILE,
    apply_crop_profile,
    preprocess_image_array,
    preprocess_image_for_model,
    resolve_preprocessing_profile,
)


class ImagePreprocessingTests(unittest.TestCase):
    def make_image(self) -> np.ndarray:
        values = np.arange(160 * 320 * 3, dtype=np.uint32).reshape(160, 320, 3)
        return (values % 255).astype(np.uint8)

    def test_baseline_output_shape(self) -> None:
        image = self.make_image()
        output = preprocess_image_array(image, BASELINE_PROFILE)

        self.assertEqual(output.shape, (MODEL_INPUT_HEIGHT, MODEL_INPUT_WIDTH, 3))

    def test_road_crop_v1_output_shape(self) -> None:
        image = self.make_image()
        output = preprocess_image_array(image, ROAD_CROP_V1_PROFILE)

        self.assertEqual(output.shape, (MODEL_INPUT_HEIGHT, MODEL_INPUT_WIDTH, 3))

    def test_road_crop_v1_uses_exact_deterministic_boundaries(self) -> None:
        image = self.make_image()
        cropped = apply_crop_profile(image, ROAD_CROP_V1_PROFILE)
        expected = image[
            ROAD_CROP_V1_BOUNDS.y_min : ROAD_CROP_V1_BOUNDS.y_max,
            ROAD_CROP_V1_BOUNDS.x_min :,
        ]

        np.testing.assert_array_equal(cropped, expected)

    def test_invalid_profile_raises_clear_error(self) -> None:
        image = self.make_image()

        with self.assertRaisesRegex(ValueError, "Unsupported preprocessing profile"):
            preprocess_image_array(image, "not_a_profile")

    def test_training_dataset_matches_shared_preprocessing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image_path = root / "center.jpg"
            csv_path = root / "driving_log.csv"
            rgb = self.make_image()
            Image.fromarray(rgb).save(image_path)

            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["image_path", "steering", "throttle", "brake", "speed"])
                writer.writerow([str(image_path), 0.25, 1.0, 0.0, 10.0])

            dataset = DrivingDataset(
                csv_path,
                data_frame=None,
                augment=False,
                preprocessing_profile=ROAD_CROP_V1_PROFILE,
            )
            tensor, steering = dataset[0]
            bgr = cv2.imread(str(image_path))
            expected = torch.from_numpy(
                preprocess_image_for_model(
                    bgr,
                    ROAD_CROP_V1_PROFILE,
                    color_order="BGR",
                )
            )

            self.assertTrue(torch.allclose(tensor, expected))
            self.assertAlmostEqual(float(steering.item()), 0.25)

    def test_validation_preprocessing_is_deterministic_without_augmentation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image_path = root / "center.jpg"
            csv_path = root / "driving_log.csv"
            Image.fromarray(self.make_image()).save(image_path)

            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["image_path", "steering", "throttle", "brake", "speed"])
                writer.writerow([str(image_path), -0.4, 1.0, 0.0, 10.0])

            dataset = DrivingDataset(
                csv_path,
                augment=False,
                preprocessing_profile=ROAD_CROP_V1_PROFILE,
            )
            first, _ = dataset[0]
            second, _ = dataset[0]

            self.assertTrue(torch.equal(first, second))

    def test_old_checkpoint_without_metadata_defaults_to_baseline(self) -> None:
        checkpoint = {"model_state_dict": {}}

        self.assertEqual(resolve_preprocessing_profile("checkpoint", checkpoint), BASELINE_PROFILE)

    def test_checkpoint_metadata_selects_road_crop_v1(self) -> None:
        checkpoint = {"preprocessing": {"profile": ROAD_CROP_V1_PROFILE}}

        self.assertEqual(resolve_preprocessing_profile("checkpoint", checkpoint), ROAD_CROP_V1_PROFILE)


if __name__ == "__main__":
    unittest.main()
