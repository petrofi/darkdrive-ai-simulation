from __future__ import annotations

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

import build_kaggle_jungle_mix_v1_training_dataset as builder


class KaggleJungleMixV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.images = self.root / "images"
        self.images.mkdir()
        self.local_csv = self.root / "local_train.csv"
        self.jungle_csv = self.root / "jungle_manifest.csv"
        self.output_dir = self.root / "output"
        self.local = self.write_local()
        self.jungle = self.write_jungle()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def image_path(self, name: str) -> str:
        path = self.images / name
        if not path.exists():
            Image.new("RGB", (8, 6), color=(30, 60, 90)).save(path)
        return str(path.resolve())

    def write_local(self, *, forbidden_session: str | None = None) -> pd.DataFrame:
        steering = [0.0, 0.0, -0.8, -0.6, -0.3, -0.2, 0.2, 0.3, 0.6, 0.8]
        rows = []
        for index, value in enumerate(steering):
            session = "local_a" if index < 5 else "local_d"
            if forbidden_session is not None and index == 0:
                session = forbidden_session
            rows.append(
                {
                    "image_path": self.image_path(f"local_{index:02d}.jpg"),
                    "steering": value,
                    "throttle": 0.4,
                    "brake": 0.0,
                    "speed": 12.0 + index,
                    "source_dataset": "local_simulator_v2",
                    "source_session": session,
                }
            )
        data = pd.DataFrame(rows)
        data.to_csv(self.local_csv, index=False)
        self.local = data
        return data

    def write_jungle(
        self,
        *,
        track: str = builder.KAGGLE_JUNGLE_TRACK,
        first_image_path: str | None = None,
    ) -> pd.DataFrame:
        steering = [0.0, 0.0, -0.7, 0.7]
        rows = []
        for index, value in enumerate(steering):
            image_path = (
                first_image_path
                if index == 0 and first_image_path is not None
                else self.image_path(f"jungle_{index:02d}.jpg")
            )
            rows.append(
                {
                    "image_path": image_path,
                    "steering": value,
                    "throttle": 0.7,
                    "brake": 0.0,
                    "speed": 15.0 + index,
                    "source_dataset": builder.KAGGLE_DATASET_ID,
                    "source_track": track,
                    "source_row_index": index + 1,
                    "camera": "center",
                    "is_external": True,
                    "original_center_path": rf"C:\producer\jungle\IMG\jungle_{index:02d}.jpg",
                    "original_left_path": rf"C:\producer\jungle\IMG\left_{index:02d}.jpg",
                    "original_right_path": rf"C:\producer\jungle\IMG\right_{index:02d}.jpg",
                }
            )
        data = pd.DataFrame(rows)
        data.to_csv(self.jungle_csv, index=False)
        self.jungle = data
        return data

    def build(self, *, force: bool = False) -> dict:
        return builder.build_candidate(
            self.local_csv,
            self.jungle_csv,
            self.output_dir,
            force=force,
            check_corrupt_images=False,
        )

    def test_all_local_v3_rows_are_preserved_in_order(self) -> None:
        summary = self.build()
        output = pd.read_csv(self.output_dir / "train.csv")
        local_output = output[~output["is_external"]].reset_index(drop=True)

        self.assertEqual(len(local_output), len(self.local))
        self.assertEqual(local_output["image_path"].tolist(), self.local["image_path"].tolist())
        self.assertEqual(local_output["steering"].tolist(), self.local["steering"].tolist())
        self.assertEqual(
            local_output["source_session"].tolist(), self.local["source_session"].tolist()
        )
        self.assertTrue(summary["preservation_checks"]["all_local_v3_rows_preserved"])

    def test_all_kaggle_jungle_rows_are_preserved_in_order(self) -> None:
        summary = self.build()
        output = pd.read_csv(self.output_dir / "train.csv")
        external = output[output["is_external"]].reset_index(drop=True)

        self.assertEqual(len(external), len(self.jungle))
        self.assertEqual(external["image_path"].tolist(), self.jungle["image_path"].tolist())
        self.assertEqual(external["source_row_index"].tolist(), [1, 2, 3, 4])
        self.assertEqual(set(external["source_track"]), {builder.KAGGLE_JUNGLE_TRACK})
        self.assertTrue(summary["preservation_checks"]["all_kaggle_jungle_rows_preserved"])

    def test_make_rows_are_rejected(self) -> None:
        self.write_jungle(track=builder.KAGGLE_MAKE_TRACK)

        with self.assertRaisesRegex(ValueError, "make-track"):
            self.build()

    def test_forbidden_sessions_are_rejected(self) -> None:
        for session in (
            "session_c2_right_recovery",
            "session_e_independent_test",
            "session_e2_independent_test",
        ):
            with self.subTest(session=session):
                self.write_local(forbidden_session=session)
                with self.assertRaisesRegex(ValueError, "forbidden Session C2/E/E2"):
                    self.build()

    def test_missing_image_path_fails_clearly(self) -> None:
        data = pd.read_csv(self.local_csv)
        data.loc[0, "image_path"] = str(self.root / "missing.jpg")
        data.to_csv(self.local_csv, index=False)

        with self.assertRaisesRegex(FileNotFoundError, "missing image path"):
            self.build()

    def test_duplicate_image_paths_across_sources_are_detected(self) -> None:
        shared_path = self.local.loc[0, "image_path"]
        self.write_jungle(first_image_path=shared_path)

        with self.assertRaisesRegex(ValueError, "Combined candidate has 1 duplicate"):
            self.build()

    def test_metadata_columns_and_km1_verdict(self) -> None:
        summary = self.build()
        output = pd.read_csv(self.output_dir / "train.csv")

        self.assertEqual(list(output.columns), builder.OUTPUT_COLUMNS)
        self.assertEqual(summary["candidate_verdict"], "KM1")
        self.assertEqual(summary["metrics"]["local_v3_rows"], 10)
        self.assertEqual(summary["metrics"]["kaggle_jungle_rows"], 4)
        self.assertEqual(summary["metrics"]["make_rows_included"], 0)
        self.assertEqual(summary["metrics"]["forbidden_internal_session_rows"], 0)
        self.assertFalse(summary["training_authorized"])

    def test_source_distribution_is_written(self) -> None:
        self.build()
        distribution = pd.read_csv(self.output_dir / "source_distribution.csv")

        self.assertEqual(int(distribution["rows"].sum()), 14)
        self.assertEqual(set(distribution["is_external"]), {False, True})
        self.assertIn(builder.KAGGLE_SESSION_ID, set(distribution["source_session"]))

    def test_existing_outputs_require_force(self) -> None:
        self.build()

        with self.assertRaisesRegex(FileExistsError, "without --force"):
            self.build()

        self.assertEqual(self.build(force=True)["metrics"]["total_rows"], 14)

    def test_cli_argument_parsing(self) -> None:
        defaults = builder.parse_args([])
        custom = builder.parse_args(
            [
                "--local-train-csv",
                "local.csv",
                "--kaggle-jungle-manifest",
                "jungle.csv",
                "--output-dir",
                "out",
                "--force",
            ]
        )

        self.assertFalse(defaults.force)
        self.assertEqual(custom.local_train_csv, "local.csv")
        self.assertEqual(custom.kaggle_jungle_manifest, "jungle.csv")
        self.assertEqual(custom.output_dir, "out")
        self.assertTrue(custom.force)


if __name__ == "__main__":
    unittest.main()
