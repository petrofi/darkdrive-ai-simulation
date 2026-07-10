from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import build_kaggle_jungle_candidate_manifest as builder


class KaggleJungleCandidateManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.kaggle_root = self.base / "download" / "extracted"
        self.output_dir = self.base / "output"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def default_rows() -> list[tuple[str, str, str, float, float, float, float]]:
        return [
            ("center_z.jpg", "left_z.jpg", "right_z.jpg", 0.0, 0.2, 0.0, 10.0),
            ("center_a.jpg", "left_a.jpg", "right_a.jpg", -0.6, 0.3, 0.0, 11.0),
            ("center_m.jpg", "left_m.jpg", "right_m.jpg", 0.6, 0.4, 0.0, 12.0),
            ("center_b.jpg", "left_b.jpg", "right_b.jpg", 0.2, 0.5, 0.0, 13.0),
        ]

    def write_track(
        self,
        name: str = builder.DEFAULT_TRACK_NAME,
        *,
        parent: Path | None = None,
        rows: list[tuple[str, str, str, float, float, float, float]] | None = None,
        missing_images: set[str] | None = None,
    ) -> Path:
        rows = rows or self.default_rows()
        missing_images = missing_images or set()
        parent = parent or (self.kaggle_root / "nested" / "archive")
        track_root = parent / name
        images_dir = track_root / "IMG"
        images_dir.mkdir(parents=True)
        for row in rows:
            for filename in row[:3]:
                if filename not in missing_images:
                    Image.new("RGB", (8, 6), color=(20, 40, 60)).save(images_dir / filename)

        with (track_root / "driving_log.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.writer(handle)
            for center, left, right, steering, throttle, brake, speed in rows:
                writer.writerow(
                    [
                        rf"C:\producer\jungle\IMG\{center}",
                        rf"C:\producer\jungle\IMG\{left}",
                        rf"C:\producer\jungle\IMG\{right}",
                        steering,
                        throttle,
                        brake,
                        speed,
                    ]
                )
        return track_root

    def build(self, *, force: bool = False, corrupt_check: bool = False) -> dict:
        return builder.build_candidate_manifest(
            self.kaggle_root,
            self.output_dir,
            force=force,
            check_corrupt_images=corrupt_check,
        )

    def test_recursively_discovers_jungle_track(self) -> None:
        expected = self.write_track()

        discovered = builder.discover_track_root(
            self.kaggle_root, builder.DEFAULT_TRACK_NAME
        )

        self.assertEqual(discovered, expected.resolve())

    def test_ambiguous_jungle_track_roots_fail(self) -> None:
        self.write_track(parent=self.kaggle_root / "one")
        self.write_track(parent=self.kaggle_root / "two")

        with self.assertRaisesRegex(ValueError, "Ambiguous track"):
            builder.discover_track_root(self.kaggle_root, builder.DEFAULT_TRACK_NAME)

    def test_make_track_is_excluded(self) -> None:
        self.write_track()
        self.write_track(
            builder.EXCLUDED_TRACK_NAME,
            parent=self.kaggle_root / "another_nested_folder",
        )

        summary = self.build()
        manifest = pd.read_csv(self.output_dir / "manifest.csv")

        self.assertEqual(summary["metrics"]["make_rows_included"], 0)
        self.assertEqual(set(manifest["source_track"]), {builder.DEFAULT_TRACK_NAME})
        self.assertNotIn("make", " ".join(manifest["source_track"]).lower())

    def test_output_contains_center_camera_only(self) -> None:
        self.write_track()

        self.build()
        manifest = pd.read_csv(self.output_dir / "manifest.csv")

        self.assertEqual(set(manifest["camera"]), {"center"})
        self.assertTrue(manifest["image_path"].map(lambda value: "center_" in value).all())
        self.assertFalse(manifest["image_path"].map(lambda value: "left_" in value).any())
        self.assertFalse(manifest["image_path"].map(lambda value: "right_" in value).any())

    def test_producer_windows_paths_resolve_and_are_preserved(self) -> None:
        self.write_track()

        self.build()
        manifest = pd.read_csv(self.output_dir / "manifest.csv")

        self.assertTrue(Path(manifest.loc[0, "image_path"]).is_file())
        self.assertEqual(
            manifest.loc[0, "original_center_path"],
            r"C:\producer\jungle\IMG\center_z.jpg",
        )
        self.assertEqual(
            manifest.loc[0, "original_left_path"],
            r"C:\producer\jungle\IMG\left_z.jpg",
        )

    def test_missing_center_image_fails_before_writing(self) -> None:
        self.write_track(missing_images={"center_z.jpg"})

        with self.assertRaisesRegex(FileNotFoundError, "missing center image"):
            self.build()

        self.assertFalse((self.output_dir / "manifest.csv").exists())

    def test_unsupported_csv_schema_fails(self) -> None:
        track_root = self.write_track()
        (track_root / "driving_log.csv").write_text(
            "foo,bar\nvalue,0.1\n", encoding="utf-8"
        )

        with self.assertRaisesRegex(ValueError, "Unsupported jungle CSV schema"):
            self.build()

    def test_duplicate_center_image_path_is_rejected(self) -> None:
        rows = self.default_rows()
        rows[1] = (
            rows[0][0],
            rows[1][1],
            rows[1][2],
            rows[1][3],
            rows[1][4],
            rows[1][5],
            rows[1][6],
        )
        self.write_track(rows=rows)

        with self.assertRaisesRegex(ValueError, "duplicate center image path"):
            self.build()

    def test_required_metadata_columns_and_values_exist(self) -> None:
        self.write_track()

        summary = self.build()
        manifest = pd.read_csv(self.output_dir / "manifest.csv")
        distribution = pd.read_csv(self.output_dir / "source_distribution.csv")

        self.assertEqual(list(manifest.columns), builder.OUTPUT_COLUMNS)
        self.assertEqual(set(manifest["source_dataset"]), {builder.DATASET_ID})
        self.assertEqual(set(manifest["source_track"]), {builder.DEFAULT_TRACK_NAME})
        self.assertTrue(manifest["is_external"].all())
        self.assertEqual(manifest["source_row_index"].tolist(), [1, 2, 3, 4])
        self.assertEqual(int(distribution.loc[0, "rows"]), 4)
        self.assertEqual(summary["candidate_verdict"], "J1")

    def test_output_order_is_source_order_and_deterministic(self) -> None:
        self.write_track()

        self.build()
        first_manifest = (self.output_dir / "manifest.csv").read_bytes()
        first_summary = (self.output_dir / "dataset_summary.json").read_bytes()
        first_names = [
            Path(value).name
            for value in pd.read_csv(self.output_dir / "manifest.csv")["image_path"]
        ]
        self.build(force=True)

        self.assertEqual(first_names, ["center_z.jpg", "center_a.jpg", "center_m.jpg", "center_b.jpg"])
        self.assertEqual(first_manifest, (self.output_dir / "manifest.csv").read_bytes())
        self.assertEqual(first_summary, (self.output_dir / "dataset_summary.json").read_bytes())

    def test_existing_outputs_require_force(self) -> None:
        self.write_track()
        self.build()

        with self.assertRaisesRegex(FileExistsError, "without --force"):
            self.build()

        self.assertEqual(self.build(force=True)["metrics"]["total_manifest_rows"], 4)

    def test_cli_argument_parsing(self) -> None:
        defaults = builder.parse_args([])
        custom = builder.parse_args(
            [
                "--kaggle-root",
                "custom-input",
                "--output-dir",
                "custom-output",
                "--track-name",
                builder.DEFAULT_TRACK_NAME,
                "--force",
            ]
        )

        self.assertEqual(defaults.track_name, builder.DEFAULT_TRACK_NAME)
        self.assertFalse(defaults.force)
        self.assertEqual(custom.kaggle_root, "custom-input")
        self.assertEqual(custom.output_dir, "custom-output")
        self.assertTrue(custom.force)

    def test_dataset_summary_is_valid_json(self) -> None:
        self.write_track()

        self.build()
        summary = json.loads((self.output_dir / "dataset_summary.json").read_text())

        self.assertFalse(summary["training_authorized"])
        self.assertEqual(summary["excluded_track"], builder.EXCLUDED_TRACK_NAME)
        self.assertEqual(summary["metrics"]["forbidden_internal_session_rows"], 0)


if __name__ == "__main__":
    unittest.main()
