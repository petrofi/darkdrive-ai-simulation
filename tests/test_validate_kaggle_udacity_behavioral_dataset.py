from __future__ import annotations

import csv
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_kaggle_udacity_behavioral_dataset import (  # noqa: E402
    CandidateCsv,
    UnsafeArchiveError,
    discover_candidates,
    read_candidate_csv,
    safe_extract,
    validate_candidate,
)


class KaggleUdacityValidatorTests(unittest.TestCase):
    def make_image(self, path: Path, color: int = 80) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (8, 8), color=(color, 40, 120)).save(path)

    def candidate(self, root: Path, csv_path: Path) -> CandidateCsv:
        return CandidateCsv(csv_path, root, [root / "IMG"])

    def make_headered_track(self, root: Path, *, missing_image: bool = False) -> Path:
        csv_path = root / "records.csv"
        root.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["center_image", "steering_angle", "throttle", "reverse", "speed"],
            )
            writer.writeheader()
            for index, steering in enumerate([-0.8, -0.3, -0.1, 0.0, 0.1, 0.3, 0.8]):
                name = f"frame_{index}.jpg"
                if not (missing_image and index == 6):
                    self.make_image(root / "IMG" / name, 30 + index)
                writer.writerow(
                    {
                        "center_image": f"IMG/{name}",
                        "steering_angle": steering,
                        "throttle": 0.5,
                        "reverse": 0,
                        "speed": 10 + index,
                    }
                )
        return csv_path

    def make_headerless_track(self, root: Path) -> Path:
        csv_path = root / "driving_log.csv"
        root.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            for index, steering in enumerate([-0.7, -0.2, 0.0, 0.2, 0.7]):
                names = {
                    camera: f"{camera}_{index}.jpg" for camera in ("center", "left", "right")
                }
                for offset, name in enumerate(names.values()):
                    self.make_image(root / "IMG" / name, 50 + index + offset)
                writer.writerow(
                    [
                        f"C:/old/path/IMG/{names['center']}",
                        f"C:/old/path/IMG/{names['left']}",
                        f"C:/old/path/IMG/{names['right']}",
                        steering,
                        0.8,
                        0.0,
                        15.0,
                    ]
                )
        return csv_path

    def test_headered_alternate_schema_detection(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "track"
            csv_path = self.make_headered_track(root)
            data, schema = read_candidate_csv(csv_path)
            self.assertTrue(schema.header_present)
            self.assertEqual(schema.mapping["center"], "center_image")
            self.assertEqual(schema.mapping["steering"], "steering_angle")
            self.assertEqual(schema.mapping["reverse"], "reverse")
            self.assertEqual(len(data), 7)

    def test_headerless_udacity_schema_and_windows_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "track"
            csv_path = self.make_headerless_track(root)
            report = validate_candidate(self.candidate(root, csv_path), check_corrupt_images=False)
            self.assertFalse(report["schema"]["header_present"])
            self.assertEqual(report["metrics"]["csv_rows"], 5)
            self.assertEqual(report["metrics"]["missing_image_references"], 0)
            self.assertEqual(report["metrics"]["center_image_count"], 5)
            self.assertEqual(report["metrics"]["left_image_count"], 5)
            self.assertEqual(report["metrics"]["right_image_count"], 5)

    def test_missing_steering_column_is_k3(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "track"
            root.mkdir(parents=True)
            self.make_image(root / "IMG" / "frame.jpg")
            csv_path = root / "records.csv"
            csv_path.write_text("image_path,throttle\nIMG/frame.jpg,0.5\n", encoding="utf-8")
            report = validate_candidate(self.candidate(root, csv_path), check_corrupt_images=False)
            self.assertEqual(report["verdict"], "K3")
            self.assertIn("steering", report["schema"]["missing_required_fields"])

    def test_missing_image_is_detected_as_k3(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "track"
            csv_path = self.make_headered_track(root, missing_image=True)
            report = validate_candidate(self.candidate(root, csv_path), check_corrupt_images=False)
            self.assertEqual(report["metrics"]["missing_image_references"], 1)
            self.assertEqual(report["verdict"], "K3")

    def test_distribution_and_k1_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "track"
            csv_path = self.make_headered_track(root)
            report = validate_candidate(self.candidate(root, csv_path), check_corrupt_images=False)
            metrics = report["metrics"]
            self.assertAlmostEqual(metrics["near_zero_pct"], 100 / 7)
            self.assertEqual(metrics["left_count"], 3)
            self.assertEqual(metrics["right_count"], 3)
            self.assertEqual(metrics["strong_turn_count"], 2)
            self.assertEqual(report["verdict"], "K1")

    def test_weak_straight_heavy_track_is_k2(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "track"
            root.mkdir(parents=True)
            csv_path = root / "records.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["image", "steering"])
                for index, steering in enumerate([0.0] * 8 + [-0.1, 0.1]):
                    name = f"frame_{index}.jpg"
                    self.make_image(root / name, 60 + index)
                    writer.writerow([name, steering])
            report = validate_candidate(self.candidate(root, csv_path), check_corrupt_images=False)
            self.assertEqual(report["verdict"], "K2")
            self.assertEqual(report["metrics"]["near_zero_pct"], 80.0)

    def test_recursive_multi_track_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            extracted = Path(temp) / "extracted"
            first = extracted / "nested" / "track_a"
            second = extracted / "track_b"
            self.make_headerless_track(first)
            self.make_headered_track(second)
            candidates = discover_candidates(extracted)
            self.assertEqual(len(candidates), 2)
            self.assertEqual({candidate.root.name for candidate in candidates}, {"track_a", "track_b"})

    def test_safe_extraction_rejects_zip_slip(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / "bad.zip"
            with zipfile.ZipFile(archive, "w") as handle:
                handle.writestr("../escape.txt", "blocked")
            with self.assertRaises(UnsafeArchiveError):
                safe_extract(archive, root / "out")
            self.assertFalse((root / "escape.txt").exists())


if __name__ == "__main__":
    unittest.main()
