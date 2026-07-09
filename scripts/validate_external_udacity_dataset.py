"""Validate an external Udacity-format dataset without using it for training.

The validator is deliberately read-only with respect to raw data.  It records
an ignored report and, only for an X1/X2 result, can create an ignored
normalized manifest for a future reviewed experiment.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Iterable


DATASET_ID = "udacity_behavioral_cloning_public"
DEFAULT_DATASET_ROOT = Path("data/external") / DATASET_ID / "extracted" / "data"
DEFAULT_METADATA_DIR = Path("data/external") / DATASET_ID / "metadata"
DEFAULT_MANIFEST_PATH = Path("data/processed/external") / DATASET_ID / "manifest.csv"
SCRIPT_VERSION = "1.0.0"
CAMERA_COLUMNS = ("center", "left", "right")
ALL_COLUMNS = ("center", "left", "right", "steering", "throttle", "brake", "speed")
REQUIRED_COLUMNS = ("center", "left", "right", "steering")
NEAR_ZERO_ABS = 0.05
STRONG_TURN_ABS = 0.5
MAX_MANIFEST_ROWS = 100_000


@dataclass(frozen=True)
class ParsedRow:
    source_row_index: int
    values: dict[str, str]


@dataclass(frozen=True)
class CsvReadResult:
    rows: list[ParsedRow]
    header_present: bool
    detected_columns: list[str]
    missing_required_columns: list[str]
    malformed_row_indices: list[int]


def project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path(__file__).resolve().parents[1] / path


def clean_value(value: str | None) -> str:
    return (value or "").strip().strip('"').strip("'").strip()


def canonical_column_name(value: str) -> str | None:
    normalized = " ".join(clean_value(value).lower().replace("_", " ").replace("-", " ").split())
    aliases = {
        "center": "center",
        "center image": "center",
        "centerimage": "center",
        "image": "center",
        "image path": "center",
        "left": "left",
        "left image": "left",
        "leftimage": "left",
        "right": "right",
        "right image": "right",
        "rightimage": "right",
        "steering": "steering",
        "steering angle": "steering",
        "throttle": "throttle",
        "brake": "brake",
        "speed": "speed",
    }
    return aliases.get(normalized)


def read_udacity_csv(csv_path: Path) -> CsvReadResult:
    """Read headered or standard headerless Udacity CSV rows with cleanup."""
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file_handle:
        raw_rows = [row for row in csv.reader(file_handle) if any(clean_value(value) for value in row)]

    if not raw_rows:
        return CsvReadResult([], False, [], list(REQUIRED_COLUMNS), [])

    header_mapping: dict[str, int] = {}
    for index, value in enumerate(raw_rows[0]):
        canonical = canonical_column_name(value)
        if canonical and canonical not in header_mapping:
            header_mapping[canonical] = index
    header_present = bool(header_mapping) and ("center" in header_mapping or "steering" in header_mapping)
    data_rows = raw_rows[1:] if header_present else raw_rows
    column_mapping = header_mapping if header_present else {column: index for index, column in enumerate(ALL_COLUMNS)}
    missing_required = [column for column in REQUIRED_COLUMNS if column not in column_mapping]

    parsed_rows: list[ParsedRow] = []
    malformed: list[int] = []
    highest_required_index = max((column_mapping[column] for column in REQUIRED_COLUMNS if column in column_mapping), default=-1)
    for source_row_index, raw_row in enumerate(data_rows, start=2 if header_present else 1):
        if highest_required_index >= len(raw_row):
            malformed.append(source_row_index)
            continue
        values = {
            column: clean_value(raw_row[index]) if index < len(raw_row) else ""
            for column, index in column_mapping.items()
            if column in ALL_COLUMNS
        }
        for column in ALL_COLUMNS:
            values.setdefault(column, "")
        if any(not values[column] for column in REQUIRED_COLUMNS):
            malformed.append(source_row_index)
            continue
        parsed_rows.append(ParsedRow(source_row_index, values))

    return CsvReadResult(
        rows=parsed_rows,
        header_present=header_present,
        detected_columns=[column for column in ALL_COLUMNS if column in column_mapping],
        missing_required_columns=missing_required,
        malformed_row_indices=malformed,
    )


def resolve_image_path(raw_path: str, dataset_root: Path, csv_path: Path, img_dir: Path) -> Path:
    """Resolve POSIX, Windows, relative, and stale absolute Udacity image paths."""
    cleaned = clean_value(raw_path)
    normalized = cleaned.replace("\\", "/")
    basename = Path(normalized).name or PureWindowsPath(cleaned).name
    candidates: list[Path] = []
    native_path = Path(cleaned)
    normalized_path = Path(normalized)
    if native_path.is_absolute():
        candidates.append(native_path)
    if normalized_path.is_absolute() and normalized_path not in candidates:
        candidates.append(normalized_path)
    if normalized:
        candidates.extend((csv_path.parent / normalized_path, dataset_root / normalized_path))
    if basename:
        candidates.append(img_dir / basename)

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()
    return (img_dir / basename).resolve() if basename else img_dir.resolve()


def image_is_valid(path: Path) -> bool:
    """Perform a dependency-free structural image check for common simulator files."""
    try:
        size = path.stat().st_size
        if size < 4:
            return False
        with path.open("rb") as file_handle:
            head = file_handle.read(32)
            file_handle.seek(max(0, size - 16))
            tail = file_handle.read(16)
    except OSError:
        return False

    if head.startswith(b"\xff\xd8\xff"):
        return tail.endswith(b"\xff\xd9")
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return tail.endswith(b"IEND\xaeB`\x82")
    if head.startswith((b"GIF87a", b"GIF89a")):
        return tail.endswith(b";")
    if head.startswith(b"BM"):
        return size >= 54
    return False


def finite_float(value: str) -> float | None:
    try:
        result = float(clean_value(value))
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def numeric_summary(values: Iterable[float]) -> dict[str, float | int | None]:
    numeric_values = list(values)
    if not numeric_values:
        return {"available": 0, "min": None, "mean": None, "max": None}
    return {
        "available": len(numeric_values),
        "min": min(numeric_values),
        "mean": statistics.fmean(numeric_values),
        "max": max(numeric_values),
    }


def read_checksum_record(metadata_dir: Path) -> tuple[bool, str | None, str | None]:
    metadata_path = metadata_dir / "download_metadata.json"
    if not metadata_path.exists():
        return False, None, str(metadata_path)
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, None, str(metadata_path)
    checksum = metadata.get("sha256")
    if isinstance(checksum, str) and len(checksum) == 64:
        return True, checksum, str(metadata_path)
    return False, None, str(metadata_path)


def distribution_assessment(metrics: dict[str, object]) -> tuple[bool, list[str]]:
    """Return whether steering coverage is broadly usable without rebalancing."""
    row_count = int(metrics["valid_steering_count"])
    if row_count == 0:
        return False, ["no valid steering labels"]
    reasons: list[str] = []
    near_zero_pct = float(metrics["near_zero_pct"])
    left_pct = float(metrics["left_pct"])
    right_pct = float(metrics["right_pct"])
    strong_turn_pct = float(metrics["strong_turn_pct"])
    if near_zero_pct > 60.0:
        reasons.append("straight-heavy: near-zero steering exceeds 60%")
    if min(left_pct, right_pct) < 5.0:
        reasons.append("one steering direction has less than 5% coverage")
    if abs(left_pct - right_pct) > 20.0:
        reasons.append("left/right steering differs by more than 20 percentage points")
    if strong_turn_pct < 5.0:
        reasons.append("strong-turn coverage is below 5%")
    return not reasons, reasons


def assign_verdict(metrics: dict[str, object], schema: CsvReadResult, checksum_recorded: bool) -> tuple[str, list[str]]:
    """Classify the dataset against the documented X1/X2/X3 governance gates."""
    fatal_reasons: list[str] = []
    if schema.missing_required_columns:
        fatal_reasons.append("CSV is missing required Udacity columns")
    if schema.malformed_row_indices:
        fatal_reasons.append("CSV contains malformed required-field rows")
    if int(metrics["csv_rows"]) == 0:
        fatal_reasons.append("CSV has no usable rows")
    if not bool(metrics["has_img_dir"]):
        fatal_reasons.append("IMG directory is missing")
    if int(metrics["missing_image_references"]) > 0:
        fatal_reasons.append("one or more image references are missing")
    if int(metrics["corrupt_images"]) > 0:
        fatal_reasons.append("one or more referenced images are corrupt")
    if int(metrics["valid_steering_count"]) == 0:
        fatal_reasons.append("no valid steering labels")

    label_issue_count = int(metrics["invalid_steering_labels"]) + int(metrics["out_of_range_steering_labels"])
    csv_rows = max(int(metrics["csv_rows"]), 1)
    if label_issue_count / csv_rows > 0.05:
        fatal_reasons.append("more than 5% of steering labels are invalid or out of range")
    if fatal_reasons:
        return "X3", fatal_reasons

    distribution_ok, distribution_reasons = distribution_assessment(metrics)
    cleaning_reasons: list[str] = []
    if label_issue_count:
        cleaning_reasons.append("some steering labels need cleaning")
    if int(metrics["duplicate_csv_rows"]) > 0:
        cleaning_reasons.append("duplicate CSV rows need review")
    if int(metrics["duplicate_image_references"]) > 0:
        cleaning_reasons.append("duplicate image references need review")
    if int(metrics["duplicate_image_filenames"]) > 0:
        cleaning_reasons.append("duplicate image filenames need review")
    if not checksum_recorded:
        cleaning_reasons.append("download checksum is not recorded")
    cleaning_reasons.extend(distribution_reasons)
    if cleaning_reasons or not distribution_ok:
        return "X2", cleaning_reasons
    return "X1", ["all structural, checksum, label, image, and distribution gates passed"]


def base_failure_report(dataset_root: Path, metadata_dir: Path, error: str) -> dict[str, object]:
    checksum_recorded, checksum, checksum_path = read_checksum_record(metadata_dir)
    return {
        "dataset_id": DATASET_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "script_version": SCRIPT_VERSION,
        "dataset_root": str(dataset_root),
        "error": error,
        "checksum_recorded": checksum_recorded,
        "sha256": checksum,
        "download_metadata_path": checksum_path,
        "verdict": "X3",
        "verdict_reasons": [error],
        "manifest": {"created": False, "reason": "validation did not complete"},
    }


def validate_dataset(dataset_root: Path, metadata_dir: Path) -> dict[str, object]:
    """Validate the raw extracted data and return a JSON-serializable report."""
    dataset_root = dataset_root.resolve()
    csv_path = dataset_root / "driving_log.csv"
    img_dir = dataset_root / "IMG"
    if not csv_path.exists():
        return base_failure_report(dataset_root, metadata_dir, f"driving_log.csv not found: {csv_path}")
    if not img_dir.is_dir():
        return base_failure_report(dataset_root, metadata_dir, f"IMG directory not found: {img_dir}")
    try:
        schema = read_udacity_csv(csv_path)
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        return base_failure_report(dataset_root, metadata_dir, f"could not read CSV: {exc}")

    camera_resolutions: dict[str, list[Path]] = {camera: [] for camera in CAMERA_COLUMNS}
    missing_by_camera = {camera: 0 for camera in CAMERA_COLUMNS}
    steering_values: list[float] = []
    invalid_steering = 0
    out_of_range_steering = 0
    control_values: dict[str, list[float]] = {column: [] for column in ("throttle", "brake", "speed")}
    normalized_rows: list[dict[str, object]] = []
    duplicate_row_keys: list[tuple[str, ...]] = []

    for parsed in schema.rows:
        values = parsed.values
        resolved_paths = {
            camera: resolve_image_path(values[camera], dataset_root, csv_path, img_dir) for camera in CAMERA_COLUMNS
        }
        for camera, path in resolved_paths.items():
            camera_resolutions[camera].append(path)
            if not path.exists():
                missing_by_camera[camera] += 1

        steering = finite_float(values["steering"])
        steering_is_valid = steering is not None and -1.0 <= steering <= 1.0
        if steering is None:
            invalid_steering += 1
        elif not -1.0 <= steering <= 1.0:
            out_of_range_steering += 1
        else:
            steering_values.append(steering)

        controls: dict[str, float | None] = {}
        for column in control_values:
            value = finite_float(values[column]) if values[column] else None
            controls[column] = value
            if value is not None:
                control_values[column].append(value)

        normalized_rows.append(
            {
                "source_row_index": parsed.source_row_index,
                "values": values,
                "paths": resolved_paths,
                "steering": steering,
                "steering_is_valid": steering_is_valid,
                "controls": controls,
            }
        )
        duplicate_row_keys.append(tuple(values[column] for column in ALL_COLUMNS))

    all_resolved_paths = [path for paths in camera_resolutions.values() for path in paths]
    existing_unique_paths = sorted({path for path in all_resolved_paths if path.exists()})
    corrupt_paths = [path for path in existing_unique_paths if not image_is_valid(path)]
    reference_counter = Counter(str(path) for path in all_resolved_paths)
    filename_counter = Counter(path.name for path in all_resolved_paths if path.name)
    row_counter = Counter(duplicate_row_keys)
    valid_count = len(steering_values)
    denominator = valid_count if valid_count else 1
    near_zero_count = sum(abs(value) <= NEAR_ZERO_ABS for value in steering_values)
    left_count = sum(value < -NEAR_ZERO_ABS for value in steering_values)
    right_count = sum(value > NEAR_ZERO_ABS for value in steering_values)
    strong_turn_count = sum(abs(value) >= STRONG_TURN_ABS for value in steering_values)
    checksum_recorded, checksum, checksum_path = read_checksum_record(metadata_dir)

    metrics: dict[str, object] = {
        "csv_rows": len(schema.rows),
        "total_img_files": sum(1 for path in img_dir.rglob("*") if path.is_file()),
        "has_img_dir": img_dir.is_dir(),
        "center_image_count": len(schema.rows) - missing_by_camera["center"],
        "left_image_count": len(schema.rows) - missing_by_camera["left"],
        "right_image_count": len(schema.rows) - missing_by_camera["right"],
        "missing_center_images": missing_by_camera["center"],
        "missing_left_images": missing_by_camera["left"],
        "missing_right_images": missing_by_camera["right"],
        "missing_image_references": sum(missing_by_camera.values()),
        "corrupt_images": len(corrupt_paths),
        "duplicate_csv_rows": sum(count - 1 for count in row_counter.values() if count > 1),
        "duplicate_image_references": sum(count - 1 for count in reference_counter.values() if count > 1),
        "duplicate_image_filenames": sum(count - 1 for count in filename_counter.values() if count > 1),
        "invalid_steering_labels": invalid_steering,
        "out_of_range_steering_labels": out_of_range_steering,
        "valid_steering_count": valid_count,
        "steering_min": min(steering_values) if steering_values else None,
        "steering_max": max(steering_values) if steering_values else None,
        "steering_mean": statistics.fmean(steering_values) if steering_values else None,
        "steering_std": statistics.pstdev(steering_values) if len(steering_values) > 1 else 0.0 if steering_values else None,
        "near_zero_count": near_zero_count,
        "near_zero_pct": near_zero_count / denominator * 100,
        "left_count": left_count,
        "left_pct": left_count / denominator * 100,
        "right_count": right_count,
        "right_pct": right_count / denominator * 100,
        "strong_turn_count": strong_turn_count,
        "strong_turn_pct": strong_turn_count / denominator * 100,
        "throttle": numeric_summary(control_values["throttle"]),
        "brake": numeric_summary(control_values["brake"]),
        "speed": numeric_summary(control_values["speed"]),
    }
    verdict, verdict_reasons = assign_verdict(metrics, schema, checksum_recorded)
    distribution_ok, distribution_reasons = distribution_assessment(metrics)
    return {
        "dataset_id": DATASET_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "script_version": SCRIPT_VERSION,
        "dataset_root": str(dataset_root),
        "csv_path": str(csv_path),
        "img_dir": str(img_dir),
        "csv_schema": {
            "header_present": schema.header_present,
            "detected_columns": schema.detected_columns,
            "missing_required_columns": schema.missing_required_columns,
            "malformed_row_count": len(schema.malformed_row_indices),
            "malformed_row_indices": schema.malformed_row_indices[:20],
        },
        "checksum_recorded": checksum_recorded,
        "sha256": checksum,
        "download_metadata_path": checksum_path,
        "distribution_usable_without_balancing": distribution_ok,
        "distribution_notes": distribution_reasons,
        "metrics": metrics,
        "verdict": verdict,
        "verdict_reasons": verdict_reasons,
        "_normalized_rows": normalized_rows,
    }


def write_normalized_manifest(report: dict[str, object], manifest_path: Path) -> dict[str, object]:
    """Create an ignored future-experiment manifest only after an X1/X2 validation."""
    verdict = str(report["verdict"])
    normalized_rows = list(report.pop("_normalized_rows", []))
    if verdict not in {"X1", "X2"}:
        return {"created": False, "reason": f"verdict {verdict} is not eligible"}
    if len(normalized_rows) > MAX_MANIFEST_ROWS:
        return {
            "created": False,
            "reason": f"dataset exceeds the {MAX_MANIFEST_ROWS}-row manifest safety threshold",
        }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    written_rows = 0
    all_center_resolved = True
    all_side_resolved = True
    with manifest_path.open("w", encoding="utf-8", newline="") as file_handle:
        writer = csv.DictWriter(
            file_handle,
            fieldnames=[
                "center_image_path",
                "left_image_path",
                "right_image_path",
                "steering",
                "throttle",
                "brake",
                "speed",
                "source_dataset",
                "source_row_index",
            ],
        )
        writer.writeheader()
        for row in normalized_rows:
            paths = row["paths"]
            steering = row["steering"]
            if not row["steering_is_valid"] or not all(path.exists() for path in paths.values()):
                continue
            all_center_resolved = all_center_resolved and paths["center"].exists()
            all_side_resolved = all_side_resolved and paths["left"].exists() and paths["right"].exists()
            controls = row["controls"]
            writer.writerow(
                {
                    "center_image_path": str(paths["center"]),
                    "left_image_path": str(paths["left"]),
                    "right_image_path": str(paths["right"]),
                    "steering": steering,
                    "throttle": controls["throttle"],
                    "brake": controls["brake"],
                    "speed": controls["speed"],
                    "source_dataset": DATASET_ID,
                    "source_row_index": row["source_row_index"],
                }
            )
            written_rows += 1
    return {
        "created": True,
        "path": str(manifest_path.resolve()),
        "manifest_rows": written_rows,
        "image_path_resolution": "all manifest references exist at validation time",
        "missing_references": 0,
        "center_only_training_possible_later": all_center_resolved and written_rows > 0,
        "side_camera_correction_can_be_considered_later": all_side_resolved and written_rows > 0,
        "training_note": "Manifest creation does not authorize training; a reviewed experiment is still required.",
    }


def write_validation_report(report_path: Path, report: dict[str, object]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    serializable_report = {key: value for key, value in report.items() if key != "_normalized_rows"}
    with report_path.open("w", encoding="utf-8", newline="\n") as file_handle:
        json.dump(serializable_report, file_handle, indent=2, sort_keys=True)
        file_handle.write("\n")


def discovered_default_root(metadata_dir: Path) -> Path:
    extraction_metadata = metadata_dir / "extraction_metadata.json"
    if extraction_metadata.exists():
        try:
            metadata = json.loads(extraction_metadata.read_text(encoding="utf-8"))
            detected_root = metadata.get("detected_dataset_root")
            if isinstance(detected_root, str) and detected_root:
                return Path(detected_root)
        except (OSError, json.JSONDecodeError):
            pass
    return project_path(DEFAULT_DATASET_ROOT)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate an external Udacity-format dataset without training.")
    parser.add_argument("--dataset-root", help="Root containing driving_log.csv and IMG/. Defaults to extraction metadata.")
    parser.add_argument(
        "--metadata-dir",
        default=str(DEFAULT_METADATA_DIR),
        help="Directory containing download/extraction metadata and receiving the validation report.",
    )
    parser.add_argument("--report-path", help="Optional path for validation_report.json.")
    parser.add_argument("--manifest-path", default=str(DEFAULT_MANIFEST_PATH), help="Ignored normalized manifest path.")
    parser.add_argument("--no-manifest", action="store_true", help="Do not create a normalized manifest.")
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    metadata_dir = project_path(args.metadata_dir)
    dataset_root = project_path(args.dataset_root) if args.dataset_root else discovered_default_root(metadata_dir)
    report_path = project_path(args.report_path) if args.report_path else metadata_dir / "validation_report.json"
    report = validate_dataset(dataset_root, metadata_dir)
    if not args.no_manifest and report["verdict"] in {"X1", "X2"}:
        report["manifest"] = write_normalized_manifest(report, project_path(args.manifest_path))
    else:
        report.pop("_normalized_rows", None)
        report["manifest"] = {"created": False, "reason": "disabled or validation verdict is X3"}
    write_validation_report(report_path, report)

    print("External Udacity dataset validation complete")
    print(f"- Dataset root: {dataset_root}")
    print(f"- Verdict: {report['verdict']}")
    print(f"- Report: {report_path}")
    for reason in report["verdict_reasons"]:
        print(f"- {reason}")
    return 0 if report["verdict"] in {"X1", "X2"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
