from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_local_v3_training_dataset import (  # noqa: E402
    SessionSpec,
    build,
    distribution_metrics,
)


class LocalV3BuilderTests(unittest.TestCase):
    def make_session(
        self,
        root: Path,
        name: str,
        steerings: list[float],
        *,
        duplicate_center: bool = False,
        missing_last_center: bool = False,
    ) -> SessionSpec:
        session_dir = root / name
        images_dir = session_dir / "IMG"
        images_dir.mkdir(parents=True)
        csv_path = session_dir / "driving_log.csv"

        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            for index, steering in enumerate(steerings):
                image_index = 0 if duplicate_center and index == 1 else index
                center_name = f"center_{image_index:04d}.jpg"
                left_name = f"left_{index:04d}.jpg"
                right_name = f"right_{index:04d}.jpg"

                for image_name in [center_name, left_name, right_name]:
                    if missing_last_center and index == len(steerings) - 1 and image_name == center_name:
                        continue
                    image_path = images_dir / image_name
                    if not image_path.exists():
                        Image.new("RGB", (8, 8), color=(index * 20 % 255, 40, 80)).save(image_path)

                writer.writerow(
                    [
                        f"C:/old_capture/IMG/{center_name}",
                        f"C:/old_capture/IMG/{left_name}",
                        f"C:/old_capture/IMG/{right_name}",
                        steering,
                        1.0,
                        0.0,
                        10.0 + index,
                    ]
                )

        return SessionSpec(name, csv_path, images_dir, "test_simulator")

    def build_args(
        self,
        output_dir: Path,
        train_sessions: list[SessionSpec],
        validation_sessions: list[SessionSpec],
    ) -> argparse.Namespace:
        return argparse.Namespace(
            output_dir=str(output_dir),
            train_session=train_sessions,
            validation_session=validation_sessions,
            seed=42,
            max_normal_near_zero_ratio=0.30,
            curve_session_name="session_d_curve_focused",
            curve_left_to_right_ratio=0.85,
            skip_corrupt_check=True,
            no_source_distribution_csv=False,
        )

    def test_build_is_deterministic_and_preserves_session_holdout(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            v1 = self.make_session(root, "v1", [0.0, 0.0, -0.2, 0.2, -0.7, 0.7])
            curve = self.make_session(
                root,
                "session_d_curve_focused",
                [0.0, -0.2, -0.3, -0.6, -0.8, 0.2, 0.6],
            )
            holdout = self.make_session(root, "session_c2_right_recovery", [0.0, -0.2, 0.2, 0.7])

            first_output = root / "out1"
            second_output = root / "out2"
            args_one = self.build_args(first_output, [v1, curve], [holdout])
            args_two = self.build_args(second_output, [v1, curve], [holdout])

            self.assertTrue(build(args_one))
            self.assertTrue(build(args_two))

            first_train = (first_output / "train.csv").read_text(encoding="utf-8")
            second_train = (second_output / "train.csv").read_text(encoding="utf-8")
            self.assertEqual(first_train, second_train)

            train = pd.read_csv(first_output / "train.csv")
            validation = pd.read_csv(first_output / "validation.csv")
            self.assertEqual(set(train["source_session"]), {"v1", "session_d_curve_focused"})
            self.assertEqual(set(validation["source_session"]), {"session_c2_right_recovery"})
            self.assertFalse(set(train["image_path"]) & set(validation["image_path"]))

            summary = json.loads((first_output / "dataset_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["leakage_checks"]["overlapping_source_session_count"], 0)
            self.assertEqual(summary["leakage_checks"]["overlapping_image_path_count"], 0)
            self.assertEqual(summary["leakage_checks"]["session_c2_rows_in_training"], 0)

    def test_missing_image_fails_the_build(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            train = self.make_session(root, "v1", [0.0, 0.2], missing_last_center=True)
            holdout = self.make_session(root, "session_c2_right_recovery", [0.0, 0.2])
            args = self.build_args(root / "out", [train], [holdout])

            self.assertFalse(build(args))
            self.assertFalse((root / "out" / "train.csv").exists())

    def test_duplicate_path_detection(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            session = self.make_session(root, "v1", [0.2, 0.4], duplicate_center=True)
            holdout = self.make_session(root, "session_c2_right_recovery", [0.0, -0.2])
            args = self.build_args(root / "out", [session], [holdout])

            self.assertTrue(build(args))
            summary = json.loads((root / "out" / "dataset_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["splits"]["train"]["duplicate_image_paths"], 1)

    def test_distribution_metrics_bucket_counts(self) -> None:
        data = pd.DataFrame(
            {
                "image_path": [__file__] * 5,
                "steering": [0.0, -0.1, 0.2, -0.6, 0.8],
                "throttle": [1.0] * 5,
                "brake": [0.0] * 5,
                "speed": [10.0] * 5,
                "source_dataset": ["test"] * 5,
                "source_session": ["fixture"] * 5,
            }
        )

        metrics = distribution_metrics(data, check_corrupt_images=False)
        self.assertEqual(metrics["near_zero_count"], 1)
        self.assertEqual(metrics["left_count"], 2)
        self.assertEqual(metrics["right_count"], 2)
        self.assertEqual(metrics["strong_turn_count"], 2)
        self.assertAlmostEqual(metrics["near_zero_pct"], 20.0)


if __name__ == "__main__":
    unittest.main()
