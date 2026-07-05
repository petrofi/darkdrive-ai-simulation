from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.training.train_behavior_cloning import (  # noqa: E402
    DrivingDataset,
    augment_training_image,
    prepare_training_frames,
    split_data_frame,
    validate_explicit_split,
)


class SessionAwareTrainingTests(unittest.TestCase):
    def make_manifest(
        self,
        root: Path,
        name: str,
        steerings: list[float],
        *,
        source_session: str,
        shared_image: Path | None = None,
    ) -> Path:
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
                image_path = shared_image or (images_dir / f"center_{index:04d}.jpg")
                if not image_path.exists():
                    Image.new("RGB", (12, 8), color=(index * 25 % 255, 60, 90)).save(image_path)
                writer.writerow(
                    [
                        str(image_path),
                        steering,
                        1.0,
                        0.0,
                        12.0,
                        "test_simulator",
                        source_session,
                    ]
                )
        return csv_path

    def test_explicit_manifests_load_without_random_split(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            train_csv = self.make_manifest(root, "train", [0.0, -0.2, 0.4], source_session="train_s")
            validation_csv = self.make_manifest(
                root,
                "validation",
                [0.1, -0.6],
                source_session="validation_s",
            )

            frames = prepare_training_frames(
                csv_path=root / "unused.csv",
                dataset_format="simple",
                images_dir=None,
                validation_split=0.2,
                seed=42,
                train_csv_path=train_csv,
                validation_csv_path=validation_csv,
            )

            self.assertIsNotNone(frames)
            assert frames is not None
            self.assertTrue(frames.explicit_manifests)
            self.assertEqual(len(frames.training_data), 3)
            self.assertEqual(len(frames.validation_data), 2)
            self.assertEqual(frames.training_validation.source_sessions, ["train_s"])
            self.assertEqual(frames.validation_validation.source_sessions, ["validation_s"])

    def test_only_one_explicit_manifest_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            train_csv = self.make_manifest(root, "train", [0.0], source_session="train_s")
            frames = prepare_training_frames(
                csv_path=root / "unused.csv",
                dataset_format="simple",
                images_dir=None,
                validation_split=0.2,
                seed=42,
                train_csv_path=train_csv,
                validation_csv_path=None,
            )

            self.assertIsNone(frames)

    def test_explicit_split_detects_image_and_session_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shared_image = root / "shared.jpg"
            Image.new("RGB", (12, 8), color=(10, 20, 30)).save(shared_image)
            train_csv = self.make_manifest(
                root,
                "train",
                [0.2],
                source_session="same_session",
                shared_image=shared_image,
            )
            validation_csv = self.make_manifest(
                root,
                "validation",
                [-0.2],
                source_session="same_session",
                shared_image=shared_image,
            )

            frames = prepare_training_frames(
                csv_path=root / "unused.csv",
                dataset_format="simple",
                images_dir=None,
                validation_split=0.2,
                seed=42,
                train_csv_path=train_csv,
                validation_csv_path=validation_csv,
            )
            self.assertIsNone(frames)

    def test_validation_dataset_has_augmentation_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            train_csv = self.make_manifest(root, "train", [0.0, 0.2], source_session="train_s")
            validation_csv = self.make_manifest(
                root,
                "validation",
                [-0.2],
                source_session="validation_s",
            )
            frames = prepare_training_frames(
                csv_path=root / "unused.csv",
                dataset_format="simple",
                images_dir=None,
                validation_split=0.2,
                seed=42,
                train_csv_path=train_csv,
                validation_csv_path=validation_csv,
            )
            assert frames is not None
            training_dataset = DrivingDataset(train_csv, data_frame=frames.training_data, augment=True)
            validation_dataset = DrivingDataset(
                validation_csv,
                data_frame=frames.validation_data,
                augment=False,
            )
            self.assertTrue(training_dataset.augment)
            self.assertFalse(validation_dataset.augment)

    def test_horizontal_flip_negates_steering(self) -> None:
        image = np.ones((8, 12, 3), dtype=np.uint8) * 128
        np.random.seed(1)
        _, steering = augment_training_image(image, 0.35)
        self.assertLess(steering, 0.0)
        self.assertAlmostEqual(steering, -0.35)

    def test_random_split_is_deterministic_for_backward_compatibility(self) -> None:
        import pandas as pd

        data = pd.DataFrame({"image_path": list(range(10)), "steering": np.linspace(-1, 1, 10)})
        first_train, first_validation = split_data_frame(data, 0.2, 42)
        second_train, second_validation = split_data_frame(data, 0.2, 42)
        self.assertEqual(first_train["image_path"].tolist(), second_train["image_path"].tolist())
        self.assertEqual(
            first_validation["image_path"].tolist(),
            second_validation["image_path"].tolist(),
        )

    def test_validate_explicit_split_allows_missing_source_session_column(self) -> None:
        import pandas as pd

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            train_image = root / "train.jpg"
            validation_image = root / "validation.jpg"
            Image.new("RGB", (12, 8)).save(train_image)
            Image.new("RGB", (12, 8)).save(validation_image)
            train = pd.DataFrame({"image_path": [str(train_image)], "steering": [0.1]})
            validation = pd.DataFrame({"image_path": [str(validation_image)], "steering": [-0.1]})
            check = validate_explicit_split(train, validation, root / "train.csv", root / "val.csv", None, "simple")
            self.assertEqual(check["overlapping_image_path_count"], 0)
            self.assertEqual(check["overlapping_source_session_count"], 0)


if __name__ == "__main__":
    unittest.main()
