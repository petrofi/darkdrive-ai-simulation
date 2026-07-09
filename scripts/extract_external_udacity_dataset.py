"""Safely extract and discover the public Udacity-format dataset structure."""

from __future__ import annotations

import argparse
import json
import shutil
import stat
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath


DATASET_ID = "udacity_behavioral_cloning_public"
DEFAULT_ZIP_PATH = Path("data/external") / DATASET_ID / "raw" / "data.zip"
DEFAULT_EXTRACTION_DIR = Path("data/external") / DATASET_ID / "extracted"
SCRIPT_VERSION = "1.0.0"


class UnsafeArchiveError(ValueError):
    """Raised when an archive member could escape the intended extraction root."""


@dataclass(frozen=True)
class DatasetDiscovery:
    dataset_root: Path | None
    has_driving_log_csv: bool
    has_img_dir: bool


def project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path(__file__).resolve().parents[1] / path


def metadata_path_for(extraction_dir: Path) -> Path:
    return extraction_dir.parent / "metadata" / "extraction_metadata.json"


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def normalized_member_path(member_name: str) -> PurePosixPath:
    """Validate an archive member path before it is written to disk."""
    normalized = member_name.replace("\\", "/")
    posix_path = PurePosixPath(normalized)
    windows_path = PureWindowsPath(member_name)
    if (
        not normalized
        or posix_path.is_absolute()
        or windows_path.is_absolute()
        or windows_path.drive
        or ".." in posix_path.parts
    ):
        raise UnsafeArchiveError(f"Unsafe archive member path: {member_name!r}")
    return posix_path


def is_zip_symlink(member: zipfile.ZipInfo) -> bool:
    mode = member.external_attr >> 16
    return stat.S_IFMT(mode) == stat.S_IFLNK


def prepare_extraction_dir(extraction_dir: Path, force: bool) -> None:
    if extraction_dir.exists() and any(extraction_dir.iterdir()):
        if not force:
            raise FileExistsError(
                f"Refusing to overwrite existing extracted data: {extraction_dir}. "
                "Use --force only after reviewing the directory."
            )
        shutil.rmtree(extraction_dir)
    extraction_dir.mkdir(parents=True, exist_ok=True)


def safe_extract(zip_path: Path, extraction_dir: Path, force: bool = False) -> tuple[int, int]:
    """Extract an archive after validating every member against zip-slip and links."""
    if not zip_path.exists():
        raise FileNotFoundError(f"Input archive not found: {zip_path}")

    try:
        with zipfile.ZipFile(zip_path) as archive:
            members = archive.infolist()
            destinations: set[Path] = set()
            extraction_root = extraction_dir.resolve()
            for member in members:
                relative_path = normalized_member_path(member.filename)
                if is_zip_symlink(member):
                    raise UnsafeArchiveError(f"Refusing symbolic-link member: {member.filename!r}")
                destination = (extraction_root / Path(*relative_path.parts)).resolve()
                if not is_within(destination, extraction_root):
                    raise UnsafeArchiveError(f"Archive member escapes extraction root: {member.filename!r}")
                if not member.is_dir() and destination in destinations:
                    raise UnsafeArchiveError(f"Duplicate archive member destination: {member.filename!r}")
                destinations.add(destination)

            prepare_extraction_dir(extraction_dir, force)
            extracted_file_count = 0
            extracted_total_bytes = 0
            for member in members:
                relative_path = normalized_member_path(member.filename)
                destination = extraction_dir / Path(*relative_path.parts)
                if member.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, destination.open("wb") as target:
                    shutil.copyfileobj(source, target)
                extracted_file_count += 1
                extracted_total_bytes += destination.stat().st_size
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Invalid or corrupt ZIP archive: {zip_path}") from exc

    return extracted_file_count, extracted_total_bytes


def discover_dataset_root(extraction_dir: Path) -> DatasetDiscovery:
    """Find the directory that contains both driving_log.csv and IMG/."""
    csv_paths = sorted(path for path in extraction_dir.rglob("driving_log.csv") if path.is_file())
    img_dirs = sorted(path for path in extraction_dir.rglob("IMG") if path.is_dir())
    dataset_roots = [csv_path.parent for csv_path in csv_paths if (csv_path.parent / "IMG").is_dir()]
    return DatasetDiscovery(
        dataset_root=dataset_roots[0].resolve() if dataset_roots else None,
        has_driving_log_csv=bool(csv_paths),
        has_img_dir=bool(img_dirs),
    )


def write_extraction_metadata(extraction_dir: Path, metadata: dict[str, object]) -> Path:
    metadata_path = metadata_path_for(extraction_dir)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with metadata_path.open("w", encoding="utf-8", newline="\n") as file_handle:
        json.dump(metadata, file_handle, indent=2, sort_keys=True)
        file_handle.write("\n")
    return metadata_path


def extract_dataset(zip_path: Path, extraction_dir: Path, force: bool = False) -> dict[str, object]:
    file_count, total_bytes = safe_extract(zip_path, extraction_dir, force)
    discovery = discover_dataset_root(extraction_dir)
    metadata: dict[str, object] = {
        "dataset_id": DATASET_ID,
        "zip_path": str(zip_path.resolve()),
        "extraction_dir": str(extraction_dir.resolve()),
        "detected_dataset_root": str(discovery.dataset_root) if discovery.dataset_root else None,
        "extracted_file_count": file_count,
        "extracted_total_bytes": total_bytes,
        "has_driving_log_csv": discovery.has_driving_log_csv,
        "has_img_dir": discovery.has_img_dir,
        "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
        "script_version": SCRIPT_VERSION,
    }
    write_extraction_metadata(extraction_dir, metadata)
    return metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safely extract and discover the external Udacity dataset.")
    parser.add_argument("--zip-path", default=str(DEFAULT_ZIP_PATH), help="Input data.zip archive.")
    parser.add_argument(
        "--extraction-dir",
        default=str(DEFAULT_EXTRACTION_DIR),
        help="Directory where the archive will be extracted.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow replacement of an existing extraction directory after explicit review.",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    zip_path = project_path(args.zip_path)
    extraction_dir = project_path(args.extraction_dir)
    try:
        metadata = extract_dataset(zip_path, extraction_dir, args.force)
    except (FileNotFoundError, FileExistsError, UnsafeArchiveError, ValueError, OSError) as exc:
        print(f"ERROR: Extraction failed: {exc}", file=sys.stderr)
        return 1

    print("External dataset extraction complete")
    print(f"- Files extracted: {metadata['extracted_file_count']}")
    print(f"- Bytes extracted: {metadata['extracted_total_bytes']}")
    print(f"- driving_log.csv present: {metadata['has_driving_log_csv']}")
    print(f"- IMG directory present: {metadata['has_img_dir']}")
    print(f"- Detected dataset root: {metadata['detected_dataset_root']}")
    print(f"- Metadata: {metadata_path_for(extraction_dir)}")
    if not metadata["detected_dataset_root"]:
        print("ERROR: Could not find a directory containing both driving_log.csv and IMG/.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
