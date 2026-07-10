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

from scripts.build_external_mix_v1_training_dataset import (  # noqa: E402
    OUTPUT_COLUMNS,
    build,
    parse_args,
)
from scripts.validate_external_mix_v1_training_dataset import validate  # noqa: E402


class ExternalMixV1BuilderTests(unittest.TestCase):
    def make_image(self, path: Path, color: int) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (8, 8), color=(color % 255, 40, 90)).save(path)

    def make_local_manifest(
        self,
        root: Path,
        *,
        forbidden_session: str | None = None,
        duplicate_path: bool = False,
    ) -> Path:
        csv_path = root / "local" / "train.csv"
        csv_path.parent.mkdir(parents=True)
        steerings = [0.0, -0.2, 0.2, -0.7, 0.7, -0.4, 0.4, 0.01]
        rows = []
        for index, steering in enumerate(steerings):
            image_index = 0 if duplicate_path and index == 1 else index
            image_path = root / "local" / "IMG" / f"local_{image_index:03d}.jpg"
            if not image_path.exists():
                self.make_image(image_path, index * 20)
            rows.append(
                {
                    "image_path": str(image_path),
                    "steering": steering,
                    "throttle": 0.8,
                    "brake": 0.0,
                    "speed": 20.0 + index,
                    "source_dataset": "fixture_local",
                    "source_session": forbidden_session or "session_a_normal",
                }
            )
        pd.DataFrame(rows).to_csv(csv_path, index=False)
        return csv_path

    def make_external_dataset(
        self,
        root: Path,
        *,
        missing_index: int | None = None,
        duplicate_path: bool = False,
    ) -> Path:
        external_root = root / "external"
        images_dir = external_root / "IMG"
        images_dir.mkdir(parents=True)
        csv_path = external_root / "driving_log.csv"
        steerings = [
            0.0,
            0.01,
            -0.02,
            0.03,
            -0.04,
            0.05,
            -0.1,
            -0.2,
            -0.3,
            -0.6,
            -0.8,
            0.1,
            0.2,
            0.3,
            0.6,
            0.8,
        ]
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["center", "left", "right", "steering", "throttle", "brake", "speed"])
            for index, steering in enumerate(steerings):
                image_index = 0 if duplicate_path and index == 1 else index
                name = f"center_{image_index:03d}.jpg"
                if index != missing_index and not (images_dir / name).exists():
                    self.make_image(images_dir / name, index * 13)
                writer.writerow(
                    [
                        f"IMG/{name}",
                        f"IMG/left_{index:03d}.jpg",
                        f"IMG/right_{index:03d}.jpg",
                        steering,
                        0.9,
                        0.0,
                        25.0,
                    ]
                )
        return external_root

    def build_args(
        self,
        local_csv: Path,
        external_root: Path,
        output_dir: Path,
        *,
        seed: int = 42,
        target: int = 8,
        near_zero_cap: float = 0.25,
        max_ratio: float = 0.50,
        force: bool = False,
    ) -> argparse.Namespace:
        return argparse.Namespace(
            local_train_csv=str(local_csv),
            external_root=str(external_root),
            output_dir=str(output_dir),
            seed=seed,
            external_target_rows=target,
            external_near_zero_cap_ratio=near_zero_cap,
            max_external_final_ratio=max_ratio,
            force=force,
        )

    def make_fixture(self, root: Path) -> tuple[Path, Path]:
        return self.make_local_manifest(root), self.make_external_dataset(root)

    def test_sampling_is_deterministic_for_seed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            local_csv, external_root = self.make_fixture(root)
            build(self.build_args(local_csv, external_root, root / "out1"))
            build(self.build_args(local_csv, external_root, root / "out2"))
            self.assertEqual(
                (root / "out1" / "train.csv").read_bytes(),
                (root / "out2" / "train.csv").read_bytes(),
            )
            self.assertEqual(
                (root / "out1" / "external_subset_report.csv").read_bytes(),
                (root / "out2" / "external_subset_report.csv").read_bytes(),
            )

    def test_all_local_v3_rows_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            local_csv, external_root = self.make_fixture(root)
            build(self.build_args(local_csv, external_root, root / "out"))
            source = pd.read_csv(local_csv)
            candidate = pd.read_csv(root / "out" / "train.csv")
            internal = candidate[candidate["is_external"] == False]  # noqa: E712
            self.assertEqual(len(internal), len(source))
            self.assertEqual(set(internal["source_path"]), set(source["image_path"]))
            self.assertEqual(set(internal["source_dataset"]), {"internal_local_v3"})

    def test_external_rows_are_capped_by_final_ratio(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            local_csv, external_root = self.make_fixture(root)
            build(
                self.build_args(
                    local_csv, external_root, root / "out", target=16, max_ratio=0.25
                )
            )
            candidate = pd.read_csv(root / "out" / "train.csv")
            external_count = int(candidate["is_external"].sum())
            self.assertLessEqual(external_count / len(candidate), 0.25)
            self.assertEqual(external_count, 2)

    def test_external_near_zero_cap_is_respected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            local_csv, external_root = self.make_fixture(root)
            build(self.build_args(local_csv, external_root, root / "out"))
            candidate = pd.read_csv(root / "out" / "train.csv")
            external = candidate[candidate["is_external"]]
            near_zero_ratio = (external["steering"].abs() <= 0.05).mean()
            self.assertLessEqual(near_zero_ratio, 0.25)

    def test_external_left_right_selection_is_balanced(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            local_csv, external_root = self.make_fixture(root)
            build(self.build_args(local_csv, external_root, root / "out"))
            candidate = pd.read_csv(root / "out" / "train.csv")
            external = candidate[candidate["is_external"]]
            left = int((external["steering"] < -0.05).sum())
            right = int((external["steering"] > 0.05).sum())
            self.assertLessEqual(abs(left - right), 1)
            self.assertEqual(int((external["steering"].abs() >= 0.5).sum()), 4)

    def test_forbidden_sessions_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            local_csv = self.make_local_manifest(root, forbidden_session="session_c2_right_recovery")
            external_root = self.make_external_dataset(root)
            with self.assertRaisesRegex(ValueError, "Forbidden training session"):
                build(self.build_args(local_csv, external_root, root / "out"))

    def test_missing_external_images_fail_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            local_csv = self.make_local_manifest(root)
            external_root = self.make_external_dataset(root, missing_index=15)
            with self.assertRaisesRegex(FileNotFoundError, "missing image"):
                build(self.build_args(local_csv, external_root, root / "out"))

    def test_duplicate_image_paths_are_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            local_csv = self.make_local_manifest(root)
            external_root = self.make_external_dataset(root, duplicate_path=True)
            with self.assertRaisesRegex(ValueError, "duplicate image path"):
                build(self.build_args(local_csv, external_root, root / "out"))

    def test_required_metadata_columns_are_written(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            local_csv, external_root = self.make_fixture(root)
            build(self.build_args(local_csv, external_root, root / "out"))
            candidate = pd.read_csv(root / "out" / "train.csv")
            self.assertEqual(list(candidate.columns), OUTPUT_COLUMNS)
            external = candidate[candidate["is_external"]]
            self.assertEqual(set(external["source_dataset"]), {"udacity_behavioral_cloning_public"})
            self.assertEqual(set(external["source_session"]), {"external_udacity_public"})
            self.assertTrue(external["source_row_index"].notna().all())

    def test_output_summary_and_reports_are_written(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            local_csv, external_root = self.make_fixture(root)
            build(self.build_args(local_csv, external_root, root / "out"))
            for filename in (
                "train.csv",
                "dataset_summary.json",
                "source_distribution.csv",
                "external_subset_report.csv",
            ):
                self.assertTrue((root / "out" / filename).is_file())
            summary = json.loads((root / "out" / "dataset_summary.json").read_text(encoding="utf-8"))
            self.assertFalse(summary["training_performed"])
            self.assertEqual(summary["sampling_strategy"]["effective_external_rows"], 8)

    def test_overwrite_protection_requires_force(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            local_csv, external_root = self.make_fixture(root)
            args = self.build_args(local_csv, external_root, root / "out")
            build(args)
            with self.assertRaisesRegex(FileExistsError, "without --force"):
                build(args)
            args.force = True
            build(args)

    def test_cli_argument_parsing(self) -> None:
        args = parse_args(
            [
                "--local-train-csv",
                "local.csv",
                "--external-root",
                "external",
                "--output-dir",
                "output",
                "--seed",
                "7",
                "--external-target-rows",
                "123",
                "--external-near-zero-cap-ratio",
                "0.2",
                "--max-external-final-ratio",
                "0.3",
                "--force",
            ]
        )
        self.assertEqual(args.seed, 7)
        self.assertEqual(args.external_target_rows, 123)
        self.assertAlmostEqual(args.external_near_zero_cap_ratio, 0.2)
        self.assertAlmostEqual(args.max_external_final_ratio, 0.3)
        self.assertTrue(args.force)

    def test_independent_validator_reports_duplicate_path_as_m3(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            local_csv, external_root = self.make_fixture(root)
            build(self.build_args(local_csv, external_root, root / "out"))
            candidate_path = root / "out" / "train.csv"
            candidate = pd.read_csv(candidate_path)
            candidate.loc[1, "image_path"] = candidate.loc[0, "image_path"]
            candidate.to_csv(candidate_path, index=False)
            report = validate(
                candidate_path,
                local_csv,
                external_near_zero_cap_ratio=0.25,
                max_external_final_ratio=0.50,
                check_corrupt_images=False,
            )
            self.assertEqual(report["verdict"], "M3")
            self.assertEqual(report["metrics"]["duplicate_image_paths"], 1)


if __name__ == "__main__":
    unittest.main()
