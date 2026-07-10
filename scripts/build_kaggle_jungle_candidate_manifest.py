"""Build and validate an ignored, center-camera Kaggle jungle candidate manifest."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from validate_kaggle_udacity_behavioral_dataset import (
    DATASET_ID,
    DetectedSchema,
    distribution_metrics,
    finite_float,
    image_files,
    image_index,
    image_is_valid,
    read_candidate_csv,
    resolve_image,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KAGGLE_ROOT = (
    PROJECT_ROOT
    / "data/external/kaggle_udacity_behavioral_cloning_lake_jungle/extracted"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data/processed/external/kaggle_jungle_candidate"
DEFAULT_TRACK_NAME = "self_driving_car_dataset_jungle"
EXCLUDED_TRACK_NAME = "self_driving_car_dataset_make"
OUTPUT_FILENAMES = ("manifest.csv", "dataset_summary.json", "source_distribution.csv")
OUTPUT_COLUMNS = [
    "image_path",
    "steering",
    "throttle",
    "brake",
    "speed",
    "source_dataset",
    "source_track",
    "source_row_index",
    "camera",
    "is_external",
    "original_center_path",
    "original_left_path",
    "original_right_path",
]
REQUIRED_SOURCE_FIELDS = ("center", "left", "right", "steering")
FORBIDDEN_INTERNAL_SESSIONS = (
    "session_c2",
    "session_c2_right_recovery",
    "session_e",
    "session_e_independent_test",
    "session_e2",
    "session_e2_independent_test",
)


def project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def discover_track_root(kaggle_root: Path, track_name: str) -> Path:
    if not kaggle_root.is_dir():
        raise FileNotFoundError(f"Kaggle extracted root not found: {kaggle_root}")

    matches: list[Path] = []
    if kaggle_root.name == track_name:
        matches.append(kaggle_root.resolve())
    matches.extend(
        path.resolve()
        for path in kaggle_root.rglob(track_name)
        if path.is_dir()
    )
    matches = sorted(set(matches))
    if not matches:
        raise FileNotFoundError(
            f"Track {track_name!r} was not found recursively under {kaggle_root}"
        )
    if len(matches) > 1:
        formatted = "; ".join(str(path) for path in matches)
        raise ValueError(f"Ambiguous track {track_name!r}; found {len(matches)} roots: {formatted}")
    return matches[0]


def find_track_csv(track_root: Path) -> Path:
    csv_files = sorted(path.resolve() for path in track_root.rglob("*.csv") if path.is_file())
    if not csv_files:
        raise FileNotFoundError(f"No CSV file found under track root: {track_root}")

    named = [path for path in csv_files if path.name.lower() == "driving_log.csv"]
    if len(named) == 1:
        return named[0]
    if len(csv_files) == 1:
        return csv_files[0]
    choices = "; ".join(str(path) for path in (named or csv_files))
    raise ValueError(f"Ambiguous driving log under {track_root}: {choices}")


def validate_schema(schema: DetectedSchema) -> None:
    missing = [field for field in REQUIRED_SOURCE_FIELDS if field not in schema.mapping]
    if missing:
        raise ValueError(
            "Unsupported jungle CSV schema; missing required field(s): "
            + ", ".join(missing)
        )


def optional_number(value: object) -> float | None:
    return finite_float(value)


def _raw_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def prepare_manifest(
    track_root: Path,
    csv_path: Path,
    track_name: str,
) -> tuple[pd.DataFrame, dict[str, Any], DetectedSchema]:
    data, schema = read_candidate_csv(csv_path)
    validate_schema(schema)
    if data.empty:
        raise ValueError(f"Jungle driving log contains no rows: {csv_path}")

    images = image_files(track_root)
    index = image_index(track_root, images)
    resolved: dict[str, list[Path | None]] = {}
    for camera in ("center", "left", "right"):
        column = schema.mapping[camera]
        resolved[camera] = [
            resolve_image(value, csv_path, track_root, index) for value in data[column]
        ]

    missing_by_camera = {
        camera: int(sum(path is None for path in paths))
        for camera, paths in resolved.items()
    }
    if missing_by_camera["center"]:
        raw_column = schema.mapping["center"]
        first_missing = next(
            _raw_text(data.iloc[index_value][raw_column])
            for index_value, path in enumerate(resolved["center"])
            if path is None
        )
        raise FileNotFoundError(
            f"Jungle source has {missing_by_camera['center']} missing center image(s); "
            f"first unresolved reference: {first_missing}"
        )

    steering_column = schema.mapping["steering"]
    steering = data[steering_column].map(finite_float)
    invalid_steering = int(steering.isna().sum())
    if invalid_steering:
        raise ValueError(f"Jungle source has {invalid_steering} invalid steering label(s)")
    out_of_range = int(steering.map(lambda value: value < -1.0 or value > 1.0).sum())
    if out_of_range:
        raise ValueError(
            f"Jungle source has {out_of_range} steering label(s) outside [-1, 1]"
        )

    prepared = pd.DataFrame()
    prepared["image_path"] = [str(path) for path in resolved["center"]]
    prepared["steering"] = steering.astype(float)
    for field in ("throttle", "brake", "speed"):
        source_column = schema.mapping.get(field)
        prepared[field] = (
            data[source_column].map(optional_number) if source_column is not None else None
        )
    prepared["source_dataset"] = DATASET_ID
    prepared["source_track"] = track_name
    first_source_row = 2 if schema.header_present else 1
    prepared["source_row_index"] = range(first_source_row, first_source_row + len(data))
    prepared["camera"] = "center"
    prepared["is_external"] = True
    prepared["original_center_path"] = data[schema.mapping["center"]].map(_raw_text)
    prepared["original_left_path"] = data[schema.mapping["left"]].map(_raw_text)
    prepared["original_right_path"] = data[schema.mapping["right"]].map(_raw_text)
    prepared = prepared[OUTPUT_COLUMNS]

    duplicate_image_paths = int(prepared["image_path"].duplicated().sum())
    if duplicate_image_paths:
        raise ValueError(
            f"Jungle source has {duplicate_image_paths} duplicate center image path(s)"
        )

    source_diagnostics = {
        "source_csv_rows": int(len(data)),
        "source_image_files": int(len(images)),
        "resolved_center_images": int(len(data) - missing_by_camera["center"]),
        "resolved_left_images": int(len(data) - missing_by_camera["left"]),
        "resolved_right_images": int(len(data) - missing_by_camera["right"]),
        "missing_center_images": missing_by_camera["center"],
        "missing_left_images": missing_by_camera["left"],
        "missing_right_images": missing_by_camera["right"],
        "duplicate_source_rows": int(data.duplicated().sum()),
    }
    return prepared, source_diagnostics, schema


def manifest_metrics(
    manifest: pd.DataFrame,
    *,
    check_corrupt_images: bool = True,
) -> dict[str, Any]:
    steering = manifest["steering"].map(finite_float)
    finite = [value for value in steering.tolist() if value is not None]
    paths = manifest["image_path"].astype(str)
    existing_unique_paths = sorted({Path(value) for value in paths if Path(value).is_file()})
    missing_images = int(sum(not Path(value).is_file() for value in paths))
    corrupt_images = (
        int(sum(not image_is_valid(path) for path in existing_unique_paths))
        if check_corrupt_images
        else None
    )
    filename_counts = Counter(Path(value).name.lower() for value in paths)
    duplicate_filenames = sum(count - 1 for count in filename_counts.values() if count > 1)
    text_columns = [
        "image_path",
        "source_dataset",
        "source_track",
        "original_center_path",
        "original_left_path",
        "original_right_path",
    ]
    searchable = manifest[text_columns].astype(str).agg(" ".join, axis=1).str.lower()
    forbidden_pattern = re.compile(
        r"(?:^|[^a-z0-9])(?:"
        + "|".join(re.escape(value) for value in FORBIDDEN_INTERNAL_SESSIONS)
        + r")(?:[^a-z0-9]|$)"
    )
    forbidden_rows = int(searchable.map(lambda value: bool(forbidden_pattern.search(value))).sum())
    make_rows = int(manifest["source_track"].astype(str).str.lower().str.contains("make").sum())

    metrics: dict[str, Any] = {
        "total_manifest_rows": int(len(manifest)),
        "missing_images": missing_images,
        "corrupt_images": corrupt_images,
        "corrupt_scan_performed": check_corrupt_images,
        "duplicate_rows": int(manifest.duplicated().sum()),
        "duplicate_image_paths": int(paths.duplicated().sum()),
        "duplicate_image_filenames": int(duplicate_filenames),
        "invalid_steering_labels": int(steering.isna().sum()),
        "out_of_range_steering_labels": int(
            sum(value < -1.0 or value > 1.0 for value in finite)
        ),
        "throttle_available_count": int(manifest["throttle"].map(finite_float).notna().sum()),
        "brake_available_count": int(manifest["brake"].map(finite_float).notna().sum()),
        "speed_available_count": int(manifest["speed"].map(finite_float).notna().sum()),
        "source_dataset_distribution": {
            str(key): int(value)
            for key, value in manifest["source_dataset"].value_counts().sort_index().items()
        },
        "source_track_distribution": {
            str(key): int(value)
            for key, value in manifest["source_track"].value_counts().sort_index().items()
        },
        "camera_distribution": {
            str(key): int(value)
            for key, value in manifest["camera"].value_counts().sort_index().items()
        },
        "make_rows_included": make_rows,
        "forbidden_internal_session_rows": forbidden_rows,
        **distribution_metrics(finite),
    }
    return metrics


def validated_source_comparison(
    kaggle_root: Path,
    track_name: str,
    metrics: dict[str, Any],
) -> dict[str, Any]:
    report_path = kaggle_root.parent / "metadata" / "validation_report.json"
    result: dict[str, Any] = {
        "report_path": str(report_path.resolve()),
        "available": False,
        "matches": True,
        "basis": "all source CSV rows are retained in source order without sampling",
    }
    if not report_path.is_file():
        return result

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return result
    source_track = next(
        (track for track in report.get("tracks", []) if track.get("track_id") == track_name),
        None,
    )
    if not source_track or not isinstance(source_track.get("metrics"), dict):
        return result

    source_metrics = source_track["metrics"]
    comparisons = {
        "rows": (source_metrics.get("csv_rows"), metrics["total_manifest_rows"]),
        "near_zero_pct": (source_metrics.get("near_zero_pct"), metrics["near_zero_pct"]),
        "left_pct": (source_metrics.get("left_pct"), metrics["left_pct"]),
        "right_pct": (source_metrics.get("right_pct"), metrics["right_pct"]),
        "strong_turn_pct": (source_metrics.get("strong_turn_pct"), metrics["strong_turn_pct"]),
    }
    matches = True
    details: dict[str, Any] = {}
    for name, (expected, actual) in comparisons.items():
        if expected is None:
            matches = False
            delta = None
        else:
            delta = float(actual) - float(expected)
            matches = matches and math.isclose(float(actual), float(expected), abs_tol=1e-9)
        details[name] = {"validated_source": expected, "manifest": actual, "delta": delta}
    return {
        "report_path": str(report_path.resolve()),
        "available": True,
        "matches": bool(matches),
        "basis": "compared with EXP-016 validation metadata",
        "metrics": details,
    }


def assign_candidate_verdict(
    metrics: dict[str, Any],
    comparison: dict[str, Any],
) -> tuple[str, str, list[str]]:
    invalid_reasons: list[str] = []
    for key, label in (
        ("missing_images", "missing image(s)"),
        ("corrupt_images", "corrupt image(s)"),
        ("invalid_steering_labels", "invalid steering label(s)"),
        ("out_of_range_steering_labels", "out-of-range steering label(s)"),
        ("duplicate_image_paths", "duplicate image path(s)"),
        ("make_rows_included", "make-track row(s)"),
        ("forbidden_internal_session_rows", "forbidden internal-session row(s)"),
    ):
        count = metrics.get(key)
        if count:
            invalid_reasons.append(f"{count} {label}")
    expected_sources = {DATASET_ID: metrics["total_manifest_rows"]}
    if metrics["source_dataset_distribution"] != expected_sources:
        invalid_reasons.append("unexpected source_dataset values are present")
    expected_tracks = {DEFAULT_TRACK_NAME: metrics["total_manifest_rows"]}
    if metrics["source_track_distribution"] != expected_tracks:
        invalid_reasons.append("unexpected source_track values are present")
    if metrics["camera_distribution"] != {"center": metrics["total_manifest_rows"]}:
        invalid_reasons.append("non-center camera rows are present")
    if invalid_reasons:
        return "J3", "Invalid", invalid_reasons

    filtering_reasons: list[str] = []
    if not comparison.get("matches", False):
        filtering_reasons.append("manifest distribution differs from validated jungle source")
    if metrics["near_zero_pct"] > 55.0:
        filtering_reasons.append(f"near-zero share is high at {metrics['near_zero_pct']:.2f}%")
    if metrics["left_pct"] < 20.0 or metrics["right_pct"] < 20.0:
        filtering_reasons.append("left or right steering share is below 20%")
    if metrics["strong_turn_pct"] < 15.0:
        filtering_reasons.append(
            f"strong-turn share is below 15% at {metrics['strong_turn_pct']:.2f}%"
        )
    if filtering_reasons:
        return "J2", "Valid but needs filtering", filtering_reasons
    return (
        "J1",
        "Jungle candidate manifest ready for review",
        ["center-camera integrity, provenance, exclusion, and distribution gates passed"],
    )


def build_source_distribution(manifest: pd.DataFrame) -> pd.DataFrame:
    distribution = (
        manifest.groupby(
            ["source_dataset", "source_track", "camera", "is_external"],
            dropna=False,
        )
        .size()
        .reset_index(name="rows")
        .sort_values(["source_dataset", "source_track", "camera"])
        .reset_index(drop=True)
    )
    distribution["pct_of_candidate"] = distribution["rows"] / len(manifest) * 100
    return distribution


def ensure_outputs_available(output_dir: Path, force: bool) -> None:
    existing = [output_dir / name for name in OUTPUT_FILENAMES if (output_dir / name).exists()]
    if existing and not force:
        raise FileExistsError(
            "Refusing to overwrite generated output(s) without --force: "
            + ", ".join(str(path) for path in existing)
        )


def write_json(path: Path, value: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def build_candidate_manifest(
    kaggle_root: Path,
    output_dir: Path,
    track_name: str = DEFAULT_TRACK_NAME,
    *,
    force: bool = False,
    check_corrupt_images: bool = True,
) -> dict[str, Any]:
    kaggle_root = kaggle_root.resolve()
    output_dir = output_dir.resolve()
    if track_name != DEFAULT_TRACK_NAME:
        raise ValueError(
            f"Only the reviewed jungle track is allowed; expected {DEFAULT_TRACK_NAME!r}"
        )
    ensure_outputs_available(output_dir, force)
    track_root = discover_track_root(kaggle_root, track_name)
    csv_path = find_track_csv(track_root)
    manifest, source_diagnostics, schema = prepare_manifest(track_root, csv_path, track_name)
    metrics = manifest_metrics(manifest, check_corrupt_images=check_corrupt_images)
    comparison = validated_source_comparison(kaggle_root, track_name, metrics)
    verdict, verdict_label, verdict_reasons = assign_candidate_verdict(metrics, comparison)
    if verdict == "J3":
        raise ValueError("Candidate validation failed: " + "; ".join(verdict_reasons))

    distribution = build_source_distribution(manifest)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.csv"
    summary_path = output_dir / "dataset_summary.json"
    distribution_path = output_dir / "source_distribution.csv"
    summary: dict[str, Any] = {
        "candidate_id": "kaggle_jungle_candidate",
        "source_dataset": DATASET_ID,
        "source_track": track_name,
        "excluded_track": EXCLUDED_TRACK_NAME,
        "kaggle_root": str(kaggle_root),
        "track_root": str(track_root),
        "source_csv": str(csv_path),
        "output_dir": str(output_dir),
        "outputs": {
            "manifest": str(manifest_path),
            "dataset_summary": str(summary_path),
            "source_distribution": str(distribution_path),
        },
        "manifest_columns": OUTPUT_COLUMNS,
        "camera_policy": "center camera only; no side-camera steering offsets",
        "ordering_policy": "all source CSV rows retained in original order",
        "schema": {
            "header_present": schema.header_present,
            "columns": schema.columns,
            "mapping": schema.mapping,
        },
        "source_diagnostics": source_diagnostics,
        "metrics": metrics,
        "validated_source_comparison": comparison,
        "candidate_verdict": verdict,
        "candidate_verdict_label": verdict_label,
        "candidate_verdict_reasons": verdict_reasons,
        "license_status": "unresolved; no archive-specific license/README/terms file was found",
        "training_authorized": False,
        "training_note": "No training, checkpoint evaluation, or Local V3 merge is authorized by this manifest build.",
    }

    manifest.to_csv(manifest_path, index=False, lineterminator="\n")
    distribution.to_csv(distribution_path, index=False, lineterminator="\n")
    write_json(summary_path, summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a validated center-camera manifest from the Kaggle jungle track."
    )
    parser.add_argument("--kaggle-root", default=str(DEFAULT_KAGGLE_ROOT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--track-name", default=DEFAULT_TRACK_NAME)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the three generated candidate outputs if they already exist.",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        summary = build_candidate_manifest(
            project_path(args.kaggle_root),
            project_path(args.output_dir),
            args.track_name,
            force=args.force,
            check_corrupt_images=True,
        )
    except (FileNotFoundError, FileExistsError, ValueError, OSError) as exc:
        print(f"Kaggle jungle candidate build failed: {exc}", file=sys.stderr)
        return 1

    metrics = summary["metrics"]
    print("Kaggle jungle center-camera candidate manifest complete")
    print(f"- Track: {summary['source_track']}")
    print(f"- Excluded track: {summary['excluded_track']}")
    print(f"- Rows: {metrics['total_manifest_rows']}")
    print(
        "- Near-zero/left/right/strong: "
        f"{metrics['near_zero_pct']:.2f}%/{metrics['left_pct']:.2f}%/"
        f"{metrics['right_pct']:.2f}%/{metrics['strong_turn_pct']:.2f}%"
    )
    print(
        "- Missing/corrupt/duplicate paths/invalid labels: "
        f"{metrics['missing_images']}/{metrics['corrupt_images']}/"
        f"{metrics['duplicate_image_paths']}/"
        f"{metrics['invalid_steering_labels'] + metrics['out_of_range_steering_labels']}"
    )
    print(
        "- Make/forbidden internal rows: "
        f"{metrics['make_rows_included']}/{metrics['forbidden_internal_session_rows']}"
    )
    print(
        f"- Verdict: {summary['candidate_verdict']} - "
        f"{summary['candidate_verdict_label']}"
    )
    print(f"- Output: {summary['outputs']['manifest']}")
    print("- No model was trained or evaluated; Local V3 was not modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
