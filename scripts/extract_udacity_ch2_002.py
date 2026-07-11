"""Safely inspect and extract the Udacity Challenge 2 CH2_002 TAR archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


DATASET_ID = "udacity_ch2_002"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE = PROJECT_ROOT / "data/external/udacity_ch2_002/raw/Ch2_002.tar.gz"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data/external/udacity_ch2_002/extracted"
DEFAULT_METADATA = (
    PROJECT_ROOT / "data/external/udacity_ch2_002/metadata/extraction_metadata.json"
)
SCRIPT_VERSION = "1.0.0"


class UnsafeArchiveError(ValueError):
    """Raised when a TAR member cannot be extracted safely."""


def project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def normalized_member_path(member_name: str) -> PurePosixPath:
    normalized = member_name.replace("\\", "/")
    posix_path = PurePosixPath(normalized)
    windows_path = PureWindowsPath(member_name)
    if (
        not normalized
        or "\x00" in normalized
        or posix_path.is_absolute()
        or windows_path.is_absolute()
        or bool(windows_path.drive)
        or ".." in posix_path.parts
        or posix_path == PurePosixPath(".")
    ):
        raise UnsafeArchiveError(f"Unsafe archive member path: {member_name!r}")
    return posix_path


def member_type(member: tarfile.TarInfo) -> str:
    if member.isfile():
        return "regular_file"
    if member.isdir():
        return "directory"
    if member.issym():
        return "symbolic_link"
    if member.islnk():
        return "hard_link"
    if member.ischr():
        return "character_device"
    if member.isblk():
        return "block_device"
    if member.isfifo():
        return "fifo"
    return "unsupported_special"


def _destination_key(path: Path) -> str:
    return os.path.normcase(str(path.resolve())).casefold()


def inspect_members(
    members: list[tarfile.TarInfo], extraction_dir: Path
) -> tuple[list[dict[str, Any]], int, int]:
    extraction_root = extraction_dir.resolve()
    destinations: dict[str, tuple[Path, str]] = {}
    inventory: list[dict[str, Any]] = []
    expected_files = 0
    expected_bytes = 0

    for member in members:
        relative = normalized_member_path(member.name)
        kind = member_type(member)
        if kind not in {"regular_file", "directory"}:
            raise UnsafeArchiveError(
                f"Refusing {kind.replace('_', ' ')} member: {member.name!r}"
            )

        destination = (extraction_root / Path(*relative.parts)).resolve()
        try:
            destination.relative_to(extraction_root)
        except ValueError as exc:
            raise UnsafeArchiveError(
                f"Archive member escapes extraction root: {member.name!r}"
            ) from exc

        key = _destination_key(destination)
        if key in destinations:
            raise UnsafeArchiveError(
                f"Duplicate archive member destination: {member.name!r}"
            )
        destinations[key] = (destination, kind)
        if member.isfile():
            expected_files += 1
            expected_bytes += member.size
        inventory.append(
            {
                "name": member.name,
                "type": kind,
                "size_bytes": member.size,
                "mtime": datetime.fromtimestamp(member.mtime, timezone.utc).isoformat(),
            }
        )

    for destination, kind in destinations.values():
        for parent in destination.parents:
            parent_entry = destinations.get(_destination_key(parent))
            if parent_entry and parent_entry[1] == "regular_file":
                raise UnsafeArchiveError(
                    f"Archive path collision: file {parent_entry[0]} is a parent of {destination}"
                )
            if parent == extraction_root:
                break
        if kind == "regular_file":
            prefix = _destination_key(destination) + os.sep.casefold()
            if any(other_key.startswith(prefix) for other_key in destinations if other_key != _destination_key(destination)):
                raise UnsafeArchiveError(
                    f"Archive path collision: file {destination} also acts as a directory"
                )

    return inventory, expected_files, expected_bytes


def inspect_archive(archive_path: Path, extraction_dir: Path) -> dict[str, Any]:
    if not archive_path.is_file():
        raise FileNotFoundError(f"Input archive not found: {archive_path}")
    try:
        with tarfile.open(archive_path, mode="r:*") as archive:
            members = archive.getmembers()
            inventory, expected_files, expected_bytes = inspect_members(
                members, extraction_dir
            )
    except (tarfile.TarError, EOFError) as exc:
        raise ValueError(f"Invalid or corrupt TAR archive: {archive_path}") from exc
    return {
        "members": inventory,
        "archive_member_count": len(inventory),
        "expected_file_count": expected_files,
        "expected_extracted_bytes": expected_bytes,
    }


def _nonempty_directory(path: Path) -> bool:
    return path.is_dir() and next(path.iterdir(), None) is not None


def _validate_output_location(output_dir: Path) -> None:
    resolved = output_dir.resolve()
    if resolved == Path(resolved.anchor) or resolved == PROJECT_ROOT.resolve():
        raise ValueError(f"Refusing unsafe extraction target: {resolved}")


def safe_extract(
    archive_path: Path, extraction_dir: Path, *, force: bool = False
) -> dict[str, Any]:
    archive_path = archive_path.resolve()
    extraction_dir = extraction_dir.resolve()
    _validate_output_location(extraction_dir)
    inspection = inspect_archive(archive_path, extraction_dir)

    if extraction_dir.exists() and not extraction_dir.is_dir():
        raise FileExistsError(f"Extraction target is not a directory: {extraction_dir}")
    if _nonempty_directory(extraction_dir) and not force:
        raise FileExistsError(
            f"Refusing to overwrite non-empty extraction directory: {extraction_dir}. "
            "Use --force to replace it only after a successful new extraction."
        )

    temporary_dir = extraction_dir.with_name(f".{extraction_dir.name}.extracting")
    if temporary_dir.exists():
        if not force:
            raise FileExistsError(
                f"Temporary extraction directory already exists: {temporary_dir}"
            )
        if not temporary_dir.is_dir():
            raise FileExistsError(f"Temporary extraction path is not a directory: {temporary_dir}")
        shutil.rmtree(temporary_dir)
    temporary_dir.mkdir(parents=True)

    extracted_files: list[dict[str, Any]] = []
    try:
        with tarfile.open(archive_path, mode="r:*") as archive:
            for member in archive.getmembers():
                relative = normalized_member_path(member.name)
                destination = temporary_dir / Path(*relative.parts)
                if member.isdir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue

                source = archive.extractfile(member)
                if source is None:
                    raise OSError(f"Could not read regular TAR member: {member.name}")
                destination.parent.mkdir(parents=True, exist_ok=True)
                with source, destination.open("xb") as target:
                    shutil.copyfileobj(source, target, length=1024 * 1024)
                actual_size = destination.stat().st_size
                if actual_size != member.size:
                    raise OSError(
                        f"Extracted size mismatch for {member.name}: "
                        f"expected {member.size}, got {actual_size}"
                    )
                extracted_files.append(
                    {"name": member.name, "size_bytes": actual_size}
                )

        actual_bytes = sum(item["size_bytes"] for item in extracted_files)
        if len(extracted_files) != inspection["expected_file_count"]:
            raise OSError("Extracted file count does not match TAR metadata")
        if actual_bytes != inspection["expected_extracted_bytes"]:
            raise OSError("Extracted byte count does not match TAR metadata")

        if extraction_dir.exists():
            shutil.rmtree(extraction_dir)
        temporary_dir.replace(extraction_dir)
    except Exception:
        if temporary_dir.exists():
            shutil.rmtree(temporary_dir)
        raise

    return {
        **inspection,
        "extracted_file_count": len(extracted_files),
        "extracted_total_bytes": actual_bytes,
        "extracted_files": extracted_files,
        "size_and_count_verified": True,
    }


def verify_existing_extraction(
    archive_path: Path, extraction_dir: Path
) -> dict[str, Any]:
    """Verify a pre-existing extraction without changing any extracted file."""
    archive_path = archive_path.resolve()
    extraction_dir = extraction_dir.resolve()
    if not extraction_dir.is_dir():
        raise FileNotFoundError(f"Existing extraction directory not found: {extraction_dir}")

    inspection = inspect_archive(archive_path, extraction_dir)
    expected = {
        normalized_member_path(str(item["name"])).as_posix().casefold(): int(
            item["size_bytes"]
        )
        for item in inspection["members"]
        if item["type"] == "regular_file"
    }
    actual: dict[str, tuple[Path, int]] = {}
    for path in extraction_dir.rglob("*"):
        if path.is_symlink():
            raise UnsafeArchiveError(f"Existing extraction contains a link: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(extraction_dir).as_posix()
        key = relative.casefold()
        if key in actual:
            raise UnsafeArchiveError(
                f"Existing extraction contains a case-colliding path: {relative}"
            )
        actual[key] = (path, path.stat().st_size)

    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    mismatched = sorted(
        key for key in expected.keys() & actual.keys() if expected[key] != actual[key][1]
    )
    if missing or extra or mismatched:
        problems = []
        if missing:
            problems.append(f"missing={missing}")
        if extra:
            problems.append(f"extra={extra}")
        if mismatched:
            problems.append(f"size_mismatch={mismatched}")
        raise OSError("Existing extraction does not match TAR metadata: " + "; ".join(problems))

    extracted_files = [
        {"name": item["name"], "size_bytes": item["size_bytes"]}
        for item in inspection["members"]
        if item["type"] == "regular_file"
    ]
    return {
        **inspection,
        "extracted_file_count": len(extracted_files),
        "extracted_total_bytes": sum(item["size_bytes"] for item in extracted_files),
        "extracted_files": extracted_files,
        "size_and_count_verified": True,
        "existing_output_verified": True,
    }


def write_metadata(path: Path, metadata: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)
        handle.write("\n")


def extract_dataset(
    archive_path: Path,
    extraction_dir: Path,
    metadata_path: Path,
    *,
    force: bool = False,
    verify_existing: bool = False,
) -> dict[str, Any]:
    if force and verify_existing:
        raise ValueError("--force and --verify-existing cannot be used together")
    result = (
        verify_existing_extraction(archive_path, extraction_dir)
        if verify_existing
        else safe_extract(archive_path, extraction_dir, force=force)
    )
    metadata = {
        "dataset_id": DATASET_ID,
        "script_version": SCRIPT_VERSION,
        "archive_path": str(archive_path.resolve()),
        "archive_size_bytes": archive_path.stat().st_size,
        "archive_sha256": sha256_file(archive_path),
        "extraction_dir": str(extraction_dir.resolve()),
        "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": "verify_existing" if verify_existing else "extract",
        **result,
    }
    write_metadata(metadata_path, metadata)
    return metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Safely inspect and extract the Udacity CH2_002 TAR archive."
    )
    parser.add_argument("--archive", default=str(DEFAULT_ARCHIVE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--metadata", default=str(DEFAULT_METADATA))
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace a non-empty target only after the new extraction verifies successfully.",
    )
    parser.add_argument(
        "--verify-existing",
        action="store_true",
        help="Verify an existing extraction against TAR names and sizes without overwriting it.",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    archive_path = project_path(args.archive)
    extraction_dir = project_path(args.output_dir)
    metadata_path = project_path(args.metadata)
    try:
        metadata = extract_dataset(
            archive_path,
            extraction_dir,
            metadata_path,
            force=args.force,
            verify_existing=args.verify_existing,
        )
    except (FileNotFoundError, FileExistsError, UnsafeArchiveError, ValueError, OSError) as exc:
        print(f"Udacity CH2_002 extraction failed: {exc}", file=sys.stderr)
        return 1

    operation = "existing extraction verification" if args.verify_existing else "extraction"
    print(f"Udacity CH2_002 {operation} complete")
    print(f"- Files extracted: {metadata['extracted_file_count']}")
    print(f"- Bytes extracted: {metadata['extracted_total_bytes']}")
    print(f"- Size/count verified: {metadata['size_and_count_verified']}")
    print(f"- Metadata: {metadata_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
