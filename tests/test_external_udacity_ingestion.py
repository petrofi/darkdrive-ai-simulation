from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.download_external_udacity_dataset import (
    DEFAULT_URL,
    ensure_destination_available,
    parse_args as parse_download_args,
    sha256_file,
    write_download_metadata,
)
from scripts.extract_external_udacity_dataset import (
    UnsafeArchiveError,
    discover_dataset_root,
    extract_dataset,
    safe_extract,
)
from scripts.validate_external_udacity_dataset import validate_dataset, write_normalized_manifest


def tiny_jpeg() -> bytes:
    """A structurally sufficient JPEG fixture for the stdlib validator."""
    return b"\xff\xd8\xff\xe0JFIF\x00\x01\x02\x03\xff\xd9"


class ExternalUdacityIngestionTests(unittest.TestCase):
    def test_checksum_and_metadata_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            archive = root / "raw" / "data.zip"
            archive.parent.mkdir()
            archive.write_bytes(b"darkdrive-external-dataset")
            self.assertEqual(
                sha256_file(archive),
                "84663ba8c9be9f41cc4b442d05f44b9b7dba579d935eaa60c8d2fe6349d4648e",
            )
            metadata_path = write_download_metadata(
                archive.parent,
                {"dataset_id": "fixture", "sha256": sha256_file(archive), "file_size_bytes": archive.stat().st_size},
            )
            self.assertEqual(json.loads(metadata_path.read_text(encoding="utf-8"))["dataset_id"], "fixture")

    def test_existing_archive_is_not_overwritten_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "data.zip"
            destination.write_bytes(b"keep me")
            with self.assertRaises(FileExistsError):
                ensure_destination_available(destination, force=False)
            ensure_destination_available(destination, force=True)
            self.assertEqual(destination.read_bytes(), b"keep me")

    def test_download_url_argument_parsing(self) -> None:
        self.assertEqual(parse_download_args([]).url, DEFAULT_URL)
        self.assertEqual(
            parse_download_args(["--url", "https://example.test/data.zip", "--output-dir", "custom/raw"]).url,
            "https://example.test/data.zip",
        )

    def test_safe_extraction_and_nested_root_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            archive_path = root / "data.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("data/driving_log.csv", "center,left,right,steering,throttle,brake,speed\n")
                archive.writestr("data/IMG/center.jpg", tiny_jpeg())
            extraction_dir = root / "extracted"
            metadata = extract_dataset(archive_path, extraction_dir)
            self.assertEqual(metadata["extracted_file_count"], 2)
            self.assertTrue(metadata["has_driving_log_csv"])
            self.assertTrue(metadata["has_img_dir"])
            self.assertEqual(Path(str(metadata["detected_dataset_root"])), (extraction_dir / "data").resolve())

    def test_zip_slip_is_rejected_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            archive_path = root / "unsafe.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../escaped.txt", "unsafe")
            with self.assertRaises(UnsafeArchiveError):
                safe_extract(archive_path, root / "extracted")
            self.assertFalse((root / "escaped.txt").exists())

    def test_root_discovery_handles_missing_csv_and_img(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            missing_csv = root / "missing_csv"
            (missing_csv / "IMG").mkdir(parents=True)
            csv_discovery = discover_dataset_root(missing_csv)
            self.assertIsNone(csv_discovery.dataset_root)
            self.assertFalse(csv_discovery.has_driving_log_csv)
            self.assertTrue(csv_discovery.has_img_dir)

            missing_img = root / "missing_img"
            missing_img.mkdir()
            (missing_img / "driving_log.csv").write_text("", encoding="utf-8")
            img_discovery = discover_dataset_root(missing_img)
            self.assertIsNone(img_discovery.dataset_root)
            self.assertTrue(img_discovery.has_driving_log_csv)
            self.assertFalse(img_discovery.has_img_dir)

    def test_validation_supports_headerless_paths_and_creates_manifest_after_x1(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            dataset_root = root / "extracted" / "data"
            img_dir = dataset_root / "IMG"
            img_dir.mkdir(parents=True)
            rows: list[str] = []
            for row_index, steering in enumerate((-0.6, -0.2, 0.2, 0.6)):
                paths = []
                for camera in ("center", "left", "right"):
                    filename = f"{camera}_{row_index}.jpg"
                    (img_dir / filename).write_bytes(tiny_jpeg())
                    paths.append(f"IMG\\{filename}")
                rows.append(",".join([*paths, str(steering), "0.3", "0.0", "12.0"])
                )
            (dataset_root / "driving_log.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
            metadata_dir = root / "metadata"
            metadata_dir.mkdir()
            (metadata_dir / "download_metadata.json").write_text(
                json.dumps({"sha256": "a" * 64}), encoding="utf-8"
            )

            report = validate_dataset(dataset_root, metadata_dir)
            self.assertEqual(report["verdict"], "X1")
            self.assertEqual(report["metrics"]["missing_image_references"], 0)
            manifest = write_normalized_manifest(report, root / "manifest.csv")
            self.assertTrue(manifest["created"])
            self.assertEqual(manifest["manifest_rows"], 4)


if __name__ == "__main__":
    unittest.main()
