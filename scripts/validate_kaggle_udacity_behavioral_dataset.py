"""Safely discover and validate the manually downloaded Kaggle Udacity dataset."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
import statistics
import sys
import zipfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_ID = "kaggle_udacity_behavioral_cloning_lake_jungle"
SOURCE_NAME = "Kaggle Udacity Self Driving Car - Behavioural Cloning"
SOURCE_URL = (
    "https://www.kaggle.com/datasets/andy8744/"
    "udacity-self-driving-car-behavioural-cloning"
)
DEFAULT_BASE = PROJECT_ROOT / "data/external" / DATASET_ID
DEFAULT_ZIP = DEFAULT_BASE / "raw" / f"{DATASET_ID}.zip"
DEFAULT_EXTRACTED = DEFAULT_BASE / "extracted"
DEFAULT_METADATA = DEFAULT_BASE / "metadata"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}
NEAR_ZERO_ABS = 0.05
STRONG_TURN_ABS = 0.5
PREVIOUS_NEAR_ZERO_PCT = 60.73917371826779
PREVIOUS_STRONG_TURN_PCT = 0.5475360876057741
HEADERLESS_COLUMNS = ["center", "left", "right", "steering", "throttle", "brake", "speed"]
FIELD_ALIASES = {
    "center": ("center", "center_image", "center_image_path", "centercam", "center_cam"),
    "left": ("left", "left_image", "left_image_path", "leftcam", "left_cam"),
    "right": ("right", "right_image", "right_image_path", "rightcam", "right_cam"),
    "single_image": ("image", "image_path", "filename", "file_name", "path"),
    "steering": ("steering", "steering_angle", "angle"),
    "throttle": ("throttle",),
    "brake": ("brake",),
    "reverse": ("reverse",),
    "speed": ("speed",),
}


class UnsafeArchiveError(ValueError):
    """Raised when a ZIP member could escape the extraction directory."""


@dataclass(frozen=True)
class DetectedSchema:
    header_present: bool
    columns: list[str]
    mapping: dict[str, str]
    missing_required_fields: list[str]


@dataclass(frozen=True)
class CandidateCsv:
    csv_path: Path
    root: Path
    image_folders: list[Path]


def project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_column(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def finite_float(value: object) -> float | None:
    try:
        result = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def download_metadata(zip_path: Path) -> dict[str, Any] | None:
    if not zip_path.is_file():
        return None
    item = zip_path.stat()
    return {
        "dataset_id": DATASET_ID,
        "source_name": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "local_zip_path": str(zip_path.resolve()),
        "file_size_bytes": int(item.st_size),
        "modified_at_utc": datetime.fromtimestamp(item.st_mtime, timezone.utc).isoformat(),
        "sha256": sha256_file(zip_path),
        "recorded_at": utc_now(),
        "manual_download": True,
    }


def normalized_archive_path(name: str) -> PurePosixPath:
    normalized = name.replace("\\", "/")
    posix_path = PurePosixPath(normalized)
    windows_path = PureWindowsPath(name)
    if (
        not normalized
        or posix_path.is_absolute()
        or windows_path.is_absolute()
        or windows_path.drive
        or ".." in posix_path.parts
    ):
        raise UnsafeArchiveError(f"Unsafe archive member path: {name!r}")
    return posix_path


def safe_extract(zip_path: Path, extracted_dir: Path) -> dict[str, Any]:
    if not zip_path.is_file():
        raise FileNotFoundError(f"ZIP archive not found: {zip_path}")
    if extracted_dir.exists() and any(extracted_dir.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty extraction directory: {extracted_dir}")

    extraction_root = extracted_dir.resolve()
    with zipfile.ZipFile(zip_path) as archive:
        members = archive.infolist()
        destinations: set[Path] = set()
        for member in members:
            relative = normalized_archive_path(member.filename)
            mode = member.external_attr >> 16
            if (mode & 0o170000) == 0o120000:
                raise UnsafeArchiveError(f"Refusing symbolic-link member: {member.filename!r}")
            destination = (extraction_root / Path(*relative.parts)).resolve()
            try:
                destination.relative_to(extraction_root)
            except ValueError as exc:
                raise UnsafeArchiveError(
                    f"Archive member escapes extraction root: {member.filename!r}"
                ) from exc
            if not member.is_dir() and destination in destinations:
                raise UnsafeArchiveError(f"Duplicate archive destination: {member.filename!r}")
            destinations.add(destination)

        extracted_dir.mkdir(parents=True, exist_ok=True)
        file_count = 0
        total_bytes = 0
        for member in members:
            relative = normalized_archive_path(member.filename)
            destination = extracted_dir / Path(*relative.parts)
            if member.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target)
            file_count += 1
            total_bytes += destination.stat().st_size

    return {
        "mode": "safe_zip_extraction",
        "zip_path": str(zip_path.resolve()),
        "extracted_dir": str(extracted_dir.resolve()),
        "extracted_file_count": file_count,
        "extracted_total_bytes": total_bytes,
        "recorded_at": utc_now(),
        "zip_slip_checks": "passed",
    }


def existing_extraction_metadata(extracted_dir: Path) -> dict[str, Any]:
    files = [path for path in extracted_dir.rglob("*") if path.is_file()]
    return {
        "mode": "manually_pre_extracted_and_relocated",
        "extracted_dir": str(extracted_dir.resolve()),
        "extracted_file_count": len(files),
        "extracted_total_bytes": int(sum(path.stat().st_size for path in files)),
        "recorded_at": utc_now(),
        "zip_slip_checks": "not_retroactively_verifiable_for_manual_extraction",
    }


def image_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def discover_candidates(extracted_dir: Path) -> list[CandidateCsv]:
    candidates: list[CandidateCsv] = []
    for csv_path in sorted(path for path in extracted_dir.rglob("*.csv") if path.is_file()):
        root = csv_path.parent
        folders = sorted({path.parent for path in image_files(root)})
        candidates.append(CandidateCsv(csv_path.resolve(), root.resolve(), folders))
    return candidates


def first_csv_row(csv_path: Path) -> list[str]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        return next(csv.reader(handle), [])


def schema_mapping(columns: list[str]) -> dict[str, str]:
    normalized_lookup = {normalize_column(column): column for column in columns}
    mapping: dict[str, str] = {}
    for field, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if alias in normalized_lookup:
                mapping[field] = normalized_lookup[alias]
                break
    return mapping


def read_candidate_csv(csv_path: Path) -> tuple[pd.DataFrame, DetectedSchema]:
    first_row = first_csv_row(csv_path)
    normalized_first = {normalize_column(value) for value in first_row}
    known_aliases = {alias for aliases in FIELD_ALIASES.values() for alias in aliases}
    header_present = bool(normalized_first & known_aliases)

    if header_present:
        data = pd.read_csv(csv_path, dtype=str, skipinitialspace=True, encoding="utf-8-sig")
        data.columns = [str(column).strip() for column in data.columns]
    else:
        data = pd.read_csv(
            csv_path,
            header=None,
            dtype=str,
            skipinitialspace=True,
            encoding="utf-8-sig",
        )
        if data.shape[1] < 4:
            columns = [f"column_{index}" for index in range(data.shape[1])]
            data.columns = columns
            return data, DetectedSchema(False, columns, {}, ["image_path", "steering"])
        columns = [
            HEADERLESS_COLUMNS[index] if index < len(HEADERLESS_COLUMNS) else f"extra_{index}"
            for index in range(data.shape[1])
        ]
        data.columns = columns

    for column in data.columns:
        data[column] = data[column].map(lambda value: value.strip() if isinstance(value, str) else value)
    columns = [str(column) for column in data.columns]
    mapping = schema_mapping(columns)
    has_image = any(field in mapping for field in ("center", "left", "right", "single_image"))
    missing = []
    if not has_image:
        missing.append("image_path")
    if "steering" not in mapping:
        missing.append("steering")
    return data, DetectedSchema(header_present, columns, mapping, missing)


def image_index(root: Path, images: list[Path]) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = {}
    for path in images:
        keys = {path.name.lower(), path.as_posix().lower()}
        try:
            keys.add(path.relative_to(root).as_posix().lower())
        except ValueError:
            pass
        for key in keys:
            index.setdefault(key, []).append(path)
    return index


def resolve_image(
    value: object,
    csv_path: Path,
    root: Path,
    index: dict[str, list[Path]],
) -> Path | None:
    if value is None or pd.isna(value):
        return None
    normalized = str(value).strip().strip('"').strip("'").replace("\\", "/")
    if not normalized:
        return None
    raw_path = Path(normalized)
    windows_name = PureWindowsPath(normalized).name
    posix_name = PurePosixPath(normalized).name
    filename = windows_name or posix_name or raw_path.name
    candidates = []
    if raw_path.is_absolute():
        candidates.append(raw_path)
    candidates.extend(
        [
            csv_path.parent / raw_path,
            root / raw_path,
            root / "IMG" / filename,
            root / "IMG_train" / filename,
            root / "images" / filename,
        ]
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    indexed = index.get(normalized.lower(), []) or index.get(filename.lower(), [])
    return indexed[0].resolve() if len(indexed) == 1 else None


def image_is_valid(path: Path) -> bool:
    try:
        from PIL import Image

        with Image.open(path) as image:
            image.verify()
        return True
    except Exception:
        return False


def numeric_availability(data: pd.DataFrame, column: str | None) -> int:
    if column is None:
        return 0
    return int(
        data[column]
        .map(finite_float)
        .map(lambda value: value is not None)
        .sum()
    )


def distribution_metrics(values: list[float]) -> dict[str, Any]:
    total = len(values)
    denominator = total if total else 1
    near_zero = sum(abs(value) <= NEAR_ZERO_ABS for value in values)
    left = sum(value < -NEAR_ZERO_ABS for value in values)
    right = sum(value > NEAR_ZERO_ABS for value in values)
    strong = sum(abs(value) >= STRONG_TURN_ABS for value in values)
    return {
        "valid_steering_count": total,
        "steering_min": min(values) if values else None,
        "steering_max": max(values) if values else None,
        "steering_mean": statistics.fmean(values) if values else None,
        "steering_std": statistics.pstdev(values) if len(values) > 1 else 0.0 if values else None,
        "near_zero_count": near_zero,
        "near_zero_pct": near_zero / denominator * 100,
        "left_count": left,
        "left_pct": left / denominator * 100,
        "right_count": right,
        "right_pct": right / denominator * 100,
        "strong_turn_count": strong,
        "strong_turn_pct": strong / denominator * 100,
    }


def assign_verdict(metrics: dict[str, Any], schema: DetectedSchema) -> tuple[str, list[str]]:
    invalid_reasons: list[str] = []
    if schema.missing_required_fields:
        invalid_reasons.append(
            "missing required schema fields: " + ", ".join(schema.missing_required_fields)
        )
    if metrics.get("csv_rows", 0) == 0:
        invalid_reasons.append("CSV contains no rows")
    if metrics.get("missing_image_references", 0):
        invalid_reasons.append(f"{metrics['missing_image_references']} image reference(s) are missing")
    if metrics.get("corrupt_images", 0) not in (0, None):
        invalid_reasons.append(f"{metrics['corrupt_images']} image file(s) are corrupt")
    if metrics.get("invalid_steering_labels", 0):
        invalid_reasons.append(f"{metrics['invalid_steering_labels']} steering label(s) are invalid")
    if metrics.get("out_of_range_steering_labels", 0):
        invalid_reasons.append(
            f"{metrics['out_of_range_steering_labels']} steering label(s) are outside [-1, 1]"
        )
    if invalid_reasons:
        return "K3", invalid_reasons

    balance = min(metrics["left_count"], metrics["right_count"]) / max(
        metrics["left_count"], metrics["right_count"], 1
    )
    weak_reasons: list[str] = []
    if metrics["near_zero_pct"] > 50.0:
        weak_reasons.append(f"near-zero share is high at {metrics['near_zero_pct']:.2f}%")
    if metrics["left_pct"] < 15.0 or metrics["right_pct"] < 15.0:
        weak_reasons.append("left or right steering share is below 15%")
    if balance < 0.75:
        weak_reasons.append(f"left/right balance ratio is {balance:.3f}")
    if metrics["strong_turn_pct"] < 2.0:
        weak_reasons.append(
            f"strong-turn share is only {metrics['strong_turn_pct']:.2f}%"
        )
    if metrics.get("duplicate_image_paths", 0):
        weak_reasons.append(f"{metrics['duplicate_image_paths']} duplicate image reference(s)")
    if weak_reasons:
        return "K2", weak_reasons
    return "K1", ["integrity, steering balance, near-zero, and strong-turn gates passed"]


def validate_candidate(candidate: CandidateCsv, check_corrupt_images: bool = True) -> dict[str, Any]:
    try:
        data, schema = read_candidate_csv(candidate.csv_path)
    except (OSError, UnicodeDecodeError, csv.Error, pd.errors.ParserError) as exc:
        return {
            "candidate_root": str(candidate.root),
            "csv_path": str(candidate.csv_path),
            "csv_filename": candidate.csv_path.name,
            "image_folder_candidates": [str(path) for path in candidate.image_folders],
            "appears_udacity_style": False,
            "schema_error": str(exc),
            "verdict": "K3",
            "verdict_label": "Invalid or unusable",
            "verdict_reasons": [f"could not parse CSV: {exc}"],
        }

    images = image_files(candidate.root)
    index = image_index(candidate.root, images)
    mapping = schema.mapping
    reference_fields = [field for field in ("center", "left", "right") if field in mapping]
    if not reference_fields and "single_image" in mapping:
        reference_fields = ["single_image"]

    resolved_by_field: dict[str, list[Path | None]] = {}
    for field in reference_fields:
        column = mapping[field]
        resolved_by_field[field] = [
            resolve_image(value, candidate.csv_path, candidate.root, index)
            for value in data[column]
        ]

    missing_by_field = {
        field: int(sum(path is None for path in paths))
        for field, paths in resolved_by_field.items()
    }
    all_resolved = [
        str(path)
        for paths in resolved_by_field.values()
        for path in paths
        if path is not None
    ]
    duplicate_paths = sum(count - 1 for count in Counter(all_resolved).values() if count > 1)
    filename_counts = Counter(path.name.lower() for path in images)
    duplicate_filenames = sum(count - 1 for count in filename_counts.values() if count > 1)
    corrupt_images = (
        int(sum(not image_is_valid(path) for path in images))
        if check_corrupt_images
        else None
    )

    steering_column = mapping.get("steering")
    raw_steering = data[steering_column].tolist() if steering_column else []
    parsed_steering = [finite_float(value) for value in raw_steering]
    invalid_steering = sum(value is None for value in parsed_steering)
    finite_steering = [value for value in parsed_steering if value is not None]
    out_of_range = sum(value < -1.0 or value > 1.0 for value in finite_steering)
    in_range = [value for value in finite_steering if -1.0 <= value <= 1.0]
    metrics: dict[str, Any] = {
        "csv_rows": int(len(data)),
        "total_image_files": len(images),
        "center_image_count": int(len(data) - missing_by_field.get("center", len(data)))
        if "center" in resolved_by_field
        else 0,
        "left_image_count": int(len(data) - missing_by_field.get("left", len(data)))
        if "left" in resolved_by_field
        else 0,
        "right_image_count": int(len(data) - missing_by_field.get("right", len(data)))
        if "right" in resolved_by_field
        else 0,
        "single_image_count": int(len(data) - missing_by_field.get("single_image", len(data)))
        if "single_image" in resolved_by_field
        else 0,
        "missing_center_images": missing_by_field.get("center", 0),
        "missing_left_images": missing_by_field.get("left", 0),
        "missing_right_images": missing_by_field.get("right", 0),
        "missing_single_images": missing_by_field.get("single_image", 0),
        "missing_image_references": int(sum(missing_by_field.values())),
        "corrupt_images": corrupt_images,
        "corrupt_scan_performed": check_corrupt_images,
        "duplicate_csv_rows": int(data.duplicated().sum()),
        "duplicate_image_paths": int(duplicate_paths),
        "duplicate_image_filenames": int(duplicate_filenames),
        "invalid_steering_labels": int(invalid_steering),
        "out_of_range_steering_labels": int(out_of_range),
        "throttle_available": numeric_availability(data, mapping.get("throttle")),
        "brake_available": numeric_availability(data, mapping.get("brake")),
        "reverse_available": numeric_availability(data, mapping.get("reverse")),
        "speed_available": numeric_availability(data, mapping.get("speed")),
        **distribution_metrics(in_range),
    }
    verdict, reasons = assign_verdict(metrics, schema)
    better_distribution = bool(
        verdict != "K3"
        and metrics["near_zero_pct"] < PREVIOUS_NEAR_ZERO_PCT
        and metrics["strong_turn_pct"] > PREVIOUS_STRONG_TURN_PCT
    )
    return {
        "track_id": candidate.root.name,
        "candidate_root": str(candidate.root),
        "csv_path": str(candidate.csv_path),
        "csv_filename": candidate.csv_path.name,
        "image_folder_candidates": [str(path) for path in candidate.image_folders],
        "appears_udacity_style": bool(
            "steering" in mapping and all(field in mapping for field in ("center", "left", "right"))
        ),
        "schema": {
            "header_present": schema.header_present,
            "columns": schema.columns,
            "mapping": schema.mapping,
            "missing_required_fields": schema.missing_required_fields,
        },
        "metrics": metrics,
        "better_distribution_than_previous_external": better_distribution,
        "comparison_baseline": {
            "near_zero_pct": PREVIOUS_NEAR_ZERO_PCT,
            "strong_turn_pct": PREVIOUS_STRONG_TURN_PCT,
        },
        "verdict": verdict,
        "verdict_label": {
            "K1": "Strong external candidate",
            "K2": "Valid but weak",
            "K3": "Invalid or unusable",
        }[verdict],
        "verdict_reasons": reasons,
    }


def validate_dataset(
    zip_path: Path,
    extracted_dir: Path,
    metadata_dir: Path,
    check_corrupt_images: bool = True,
) -> dict[str, Any]:
    metadata_dir.mkdir(parents=True, exist_ok=True)
    download = download_metadata(zip_path)
    if download is not None:
        write_json(metadata_dir / "download_metadata.json", download)

    if extracted_dir.exists() and any(extracted_dir.iterdir()):
        extraction = existing_extraction_metadata(extracted_dir)
    elif zip_path.is_file():
        extraction = safe_extract(zip_path, extracted_dir)
    else:
        raise FileNotFoundError(
            f"Neither extracted data nor ZIP exists: {extracted_dir}; {zip_path}"
        )
    write_json(metadata_dir / "extraction_metadata.json", extraction)

    candidates = discover_candidates(extracted_dir)
    tracks = [
        validate_candidate(candidate, check_corrupt_images=check_corrupt_images)
        for candidate in candidates
    ]
    report = {
        "dataset_id": DATASET_ID,
        "source_name": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "generated_at": utc_now(),
        "zip_metadata": download,
        "extraction_metadata": extraction,
        "extracted_dir": str(extracted_dir.resolve()),
        "candidate_csv_count": len(candidates),
        "detected_candidates": [
            {
                "candidate_root": str(candidate.root),
                "csv_path": str(candidate.csv_path),
                "csv_filename": candidate.csv_path.name,
                "image_folder_candidates": [str(path) for path in candidate.image_folders],
            }
            for candidate in candidates
        ],
        "tracks": tracks,
        "verdict_counts": dict(Counter(track["verdict"] for track in tracks)),
        "any_valid_candidate": any(track["verdict"] in {"K1", "K2"} for track in tracks),
        "training_authorized": False,
        "training_note": "Validation never authorizes training or manifest merging.",
    }
    write_json(metadata_dir / "validation_report.json", report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate all Kaggle Udacity behavioral-cloning tracks without training."
    )
    parser.add_argument("--zip-path", default=str(DEFAULT_ZIP))
    parser.add_argument("--extracted-dir", default=str(DEFAULT_EXTRACTED))
    parser.add_argument("--metadata-dir", default=str(DEFAULT_METADATA))
    parser.add_argument(
        "--skip-corrupt-check",
        action="store_true",
        help="Skip PIL verification only when a full image scan is impractical.",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = validate_dataset(
            project_path(args.zip_path),
            project_path(args.extracted_dir),
            project_path(args.metadata_dir),
            check_corrupt_images=not args.skip_corrupt_check,
        )
    except (FileNotFoundError, FileExistsError, UnsafeArchiveError, ValueError, OSError, zipfile.BadZipFile) as exc:
        print(f"Kaggle Udacity validation failed: {exc}", file=sys.stderr)
        return 1

    print("Kaggle Udacity multi-track validation complete")
    print(f"- Candidate CSV files: {report['candidate_csv_count']}")
    for track in report["tracks"]:
        metrics = track.get("metrics", {})
        print(f"- Track: {track.get('track_id', track['candidate_root'])}")
        print(f"  CSV: {track['csv_path']}")
        print(f"  Verdict: {track['verdict']} - {track['verdict_label']}")
        if metrics:
            print(f"  Rows/images: {metrics['csv_rows']}/{metrics['total_image_files']}")
            print(
                "  Near-zero/left/right/strong: "
                f"{metrics['near_zero_pct']:.2f}%/{metrics['left_pct']:.2f}%/"
                f"{metrics['right_pct']:.2f}%/{metrics['strong_turn_pct']:.2f}%"
            )
            print(
                "  Missing/corrupt/invalid: "
                f"{metrics['missing_image_references']}/{metrics['corrupt_images']}/"
                f"{metrics['invalid_steering_labels'] + metrics['out_of_range_steering_labels']}"
            )
        for reason in track["verdict_reasons"]:
            print(f"  Reason: {reason}")
    print(f"- Report: {project_path(args.metadata_dir) / 'validation_report.json'}")
    print("- No model was trained or evaluated; no training manifest was created.")
    return 0 if report["any_valid_candidate"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
