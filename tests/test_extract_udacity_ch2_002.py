from __future__ import annotations

import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

from scripts.extract_udacity_ch2_002 import (
    UnsafeArchiveError,
    extract_dataset,
    inspect_archive,
    safe_extract,
    verify_existing_extraction,
)


class UdacityCh2002ExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_tar(
        self,
        members: list[tuple[tarfile.TarInfo, bytes | None]],
        name: str = "fixture.tar.gz",
    ) -> Path:
        archive_path = self.root / name
        with tarfile.open(archive_path, "w:gz") as archive:
            for member, content in members:
                archive.addfile(member, io.BytesIO(content) if content is not None else None)
        return archive_path

    @staticmethod
    def regular(name: str, content: bytes) -> tuple[tarfile.TarInfo, bytes]:
        member = tarfile.TarInfo(name)
        member.size = len(content)
        return member, content

    def test_normal_regular_file_extraction_and_reporting(self) -> None:
        archive_path = self.write_tar(
            [self.regular("HMB_1.bag", b"ROSBAG"), self.regular("HMB.txt", b"notes")]
        )
        output_dir = self.root / "extracted"

        result = safe_extract(archive_path, output_dir)

        self.assertEqual((output_dir / "HMB_1.bag").read_bytes(), b"ROSBAG")
        self.assertEqual(result["archive_member_count"], 2)
        self.assertEqual(result["extracted_file_count"], 2)
        self.assertEqual(result["extracted_total_bytes"], 11)
        self.assertTrue(result["size_and_count_verified"])

    def test_parent_traversal_is_rejected_before_writing(self) -> None:
        archive_path = self.write_tar([self.regular("../escaped.txt", b"unsafe")])
        with self.assertRaises(UnsafeArchiveError):
            safe_extract(archive_path, self.root / "extracted")
        self.assertFalse((self.root / "escaped.txt").exists())

    def test_absolute_path_is_rejected(self) -> None:
        archive_path = self.write_tar([self.regular("/absolute.txt", b"unsafe")])
        with self.assertRaises(UnsafeArchiveError):
            inspect_archive(archive_path, self.root / "extracted")

    def test_symbolic_link_is_rejected(self) -> None:
        member = tarfile.TarInfo("link")
        member.type = tarfile.SYMTYPE
        member.linkname = "target"
        archive_path = self.write_tar([(member, None)])
        with self.assertRaisesRegex(UnsafeArchiveError, "symbolic link"):
            safe_extract(archive_path, self.root / "extracted")

    def test_hard_link_is_rejected(self) -> None:
        member = tarfile.TarInfo("link")
        member.type = tarfile.LNKTYPE
        member.linkname = "target"
        archive_path = self.write_tar([(member, None)])
        with self.assertRaisesRegex(UnsafeArchiveError, "hard link"):
            safe_extract(archive_path, self.root / "extracted")

    def test_duplicate_destination_collision_is_rejected(self) -> None:
        archive_path = self.write_tar(
            [self.regular("same.txt", b"one"), self.regular("same.txt", b"two")]
        )
        with self.assertRaisesRegex(UnsafeArchiveError, "Duplicate"):
            safe_extract(archive_path, self.root / "extracted")

    def test_file_directory_collision_is_rejected(self) -> None:
        archive_path = self.write_tar(
            [self.regular("path", b"file"), self.regular("path/child", b"child")]
        )
        with self.assertRaisesRegex(UnsafeArchiveError, "collision"):
            safe_extract(archive_path, self.root / "extracted")

    def test_existing_output_is_protected_and_force_replaces_it(self) -> None:
        archive_path = self.write_tar([self.regular("new.txt", b"new")])
        output_dir = self.root / "extracted"
        output_dir.mkdir()
        (output_dir / "old.txt").write_bytes(b"keep")

        with self.assertRaises(FileExistsError):
            safe_extract(archive_path, output_dir)
        self.assertEqual((output_dir / "old.txt").read_bytes(), b"keep")

        safe_extract(archive_path, output_dir, force=True)
        self.assertFalse((output_dir / "old.txt").exists())
        self.assertEqual((output_dir / "new.txt").read_bytes(), b"new")

    def test_metadata_contains_verified_sizes_and_counts(self) -> None:
        archive_path = self.write_tar([self.regular("nested/data.bag", b"12345")])
        output_dir = self.root / "extracted"
        metadata_path = self.root / "metadata" / "extraction_metadata.json"

        metadata = extract_dataset(archive_path, output_dir, metadata_path)
        written = json.loads(metadata_path.read_text(encoding="utf-8"))

        self.assertEqual(metadata["expected_extracted_bytes"], 5)
        self.assertEqual(written["extracted_total_bytes"], 5)
        self.assertEqual(written["extracted_file_count"], 1)
        self.assertTrue(written["size_and_count_verified"])

    def test_existing_extraction_can_be_verified_without_overwrite(self) -> None:
        archive_path = self.write_tar([self.regular("HMB_1.bag", b"ROSBAG")])
        output_dir = self.root / "extracted"
        output_dir.mkdir()
        extracted_file = output_dir / "HMB_1.bag"
        extracted_file.write_bytes(b"ROSBAG")
        original_mtime = extracted_file.stat().st_mtime_ns

        result = verify_existing_extraction(archive_path, output_dir)

        self.assertTrue(result["existing_output_verified"])
        self.assertEqual(result["extracted_file_count"], 1)
        self.assertEqual(extracted_file.read_bytes(), b"ROSBAG")
        self.assertEqual(extracted_file.stat().st_mtime_ns, original_mtime)

    def test_existing_extraction_size_mismatch_is_rejected(self) -> None:
        archive_path = self.write_tar([self.regular("HMB_1.bag", b"ROSBAG")])
        output_dir = self.root / "extracted"
        output_dir.mkdir()
        (output_dir / "HMB_1.bag").write_bytes(b"short")

        with self.assertRaisesRegex(OSError, "size_mismatch"):
            verify_existing_extraction(archive_path, output_dir)


if __name__ == "__main__":
    unittest.main()
