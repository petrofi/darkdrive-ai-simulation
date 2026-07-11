"""Build and validate the ignored Kaggle Jungle Mix V1 training candidate."""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCAL_TRAIN_CSV = PROJECT_ROOT / "data/processed/local_v3_training/train.csv"
DEFAULT_KAGGLE_JUNGLE_MANIFEST = (
    PROJECT_ROOT / "data/processed/external/kaggle_jungle_candidate/manifest.csv"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data/processed/kaggle_jungle_mix_v1_training"
KAGGLE_DATASET_ID = "kaggle_udacity_behavioral_cloning_lake_jungle"
KAGGLE_JUNGLE_TRACK = "self_driving_car_dataset_jungle"
KAGGLE_MAKE_TRACK = "self_driving_car_dataset_make"
KAGGLE_SESSION_ID = "external_kaggle_jungle"
INTERNAL_FALLBACK_DATASET_ID = "internal_local_v3"
PREVIOUS_EXTERNAL_DATASET_ID = "udacity_behavioral_cloning_public"
OUTPUT_FILENAMES = ("train.csv", "dataset_summary.json", "source_distribution.csv")
OUTPUT_COLUMNS = [
    "image_path",
    "steering",
    "throttle",
    "brake",
    "speed",
    "source_session",
    "source_dataset",
    "source_track",
    "source_row_index",
    "camera",
    "is_external",
    "original_source_path",
]
NEAR_ZERO_ABS = 0.05
STRONG_TURN_ABS = 0.5
FORBIDDEN_SESSION_KEYS = {
    "c2",
    "e",
    "e2",
    "session_c2",
    "session_c2_right_recovery",
    "session_e",
    "session_e_independent_test",
    "session_e2",
    "session_e2_independent_test",
}


def project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def finite_float(value: object) -> float | None:
    try:
        result = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def optional_float(value: object) -> float | None:
    if value is None or pd.isna(value) or not str(value).strip():
        return None
    return finite_float(value)


def normalized_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def is_forbidden_session(value: object) -> bool:
    return normalized_key(value) in FORBIDDEN_SESSION_KEYS


def parse_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    return None


def image_is_valid(path: Path) -> bool:
    try:
        from PIL import Image

        with Image.open(path) as image:
            image.verify()
        return True
    except Exception:
        return False


def require_columns(data: pd.DataFrame, required: set[str], label: str) -> None:
    missing = sorted(required - set(data.columns))
    if missing:
        raise ValueError(f"{label} is missing required column(s): {', '.join(missing)}")


def nonempty_text(series: pd.Series, fallback: str = "") -> pd.Series:
    return series.map(
        lambda value: fallback
        if value is None or pd.isna(value) or not str(value).strip()
        else str(value).strip()
    )


def validate_prepared_source(data: pd.DataFrame, label: str) -> None:
    steering = data["steering"].map(finite_float)
    invalid = int(steering.isna().sum())
    out_of_range = int(
        steering.dropna().map(lambda value: value < -1.0 or value > 1.0).sum()
    )
    paths = data["image_path"].astype(str)
    missing_paths = [value for value in paths if not Path(value).is_file()]
    duplicate_paths = int(paths.duplicated().sum())
    forbidden = sorted(
        {str(value) for value in data["source_session"] if is_forbidden_session(value)}
    )
    if invalid:
        raise ValueError(f"{label} has {invalid} invalid steering label(s)")
    if out_of_range:
        raise ValueError(f"{label} has {out_of_range} steering label(s) outside [-1, 1]")
    if missing_paths:
        raise FileNotFoundError(
            f"{label} has {len(missing_paths)} missing image path(s); "
            f"first missing path: {missing_paths[0]}"
        )
    if duplicate_paths:
        raise ValueError(f"{label} has {duplicate_paths} duplicate image path(s)")
    if forbidden:
        raise ValueError(f"{label} contains forbidden Session C2/E/E2 rows: {', '.join(forbidden)}")


def prepare_local_rows(csv_path: Path) -> pd.DataFrame:
    if not csv_path.is_file():
        raise FileNotFoundError(f"Local V3 training manifest not found: {csv_path}")
    data = pd.read_csv(csv_path)
    require_columns(data, {"image_path", "steering", "source_session"}, "Local V3 manifest")
    if data.empty:
        raise ValueError(f"Local V3 training manifest contains no rows: {csv_path}")

    if "is_external" in data:
        external_flags = data["is_external"].map(parse_bool)
        if external_flags.isna().any() or external_flags.any():
            raise ValueError("Local V3 manifest contains invalid or external is_external values")
    if "source_dataset" in data:
        previous_external = nonempty_text(data["source_dataset"]).eq(
            PREVIOUS_EXTERNAL_DATASET_ID
        )
        if previous_external.any():
            raise ValueError("Local V3 manifest contains the previous external Udacity source")

    prepared = pd.DataFrame()
    prepared["image_path"] = data["image_path"].astype(str).map(
        lambda value: str(Path(value).resolve())
    )
    prepared["steering"] = data["steering"].map(finite_float)
    for column in ("throttle", "brake", "speed"):
        prepared[column] = data[column].map(optional_float) if column in data else None
    prepared["source_session"] = nonempty_text(data["source_session"])
    if "source_dataset" in data:
        prepared["source_dataset"] = nonempty_text(
            data["source_dataset"], INTERNAL_FALLBACK_DATASET_ID
        )
    else:
        prepared["source_dataset"] = INTERNAL_FALLBACK_DATASET_ID
    prepared["source_track"] = (
        nonempty_text(data["source_track"]) if "source_track" in data else ""
    )
    prepared["source_row_index"] = (
        data["source_row_index"]
        if "source_row_index" in data
        else range(2, len(data) + 2)
    )
    prepared["camera"] = nonempty_text(data["camera"], "center") if "camera" in data else "center"
    prepared["is_external"] = False
    prepared["original_source_path"] = (
        nonempty_text(data["original_source_path"])
        if "original_source_path" in data
        else data["image_path"].astype(str)
    )
    prepared = prepared[OUTPUT_COLUMNS]
    non_center = sorted(set(prepared.loc[prepared["camera"] != "center", "camera"]))
    if non_center:
        raise ValueError(f"Local V3 manifest contains non-center camera rows: {non_center}")
    validate_prepared_source(prepared, "Local V3 manifest")
    return prepared


def prepare_kaggle_rows(manifest_path: Path) -> pd.DataFrame:
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Kaggle Jungle candidate manifest not found: {manifest_path}")
    data = pd.read_csv(manifest_path)
    require_columns(
        data,
        {
            "image_path",
            "steering",
            "source_dataset",
            "source_track",
            "source_row_index",
            "camera",
            "is_external",
        },
        "Kaggle Jungle manifest",
    )
    if data.empty:
        raise ValueError(f"Kaggle Jungle candidate manifest contains no rows: {manifest_path}")

    source_track = nonempty_text(data["source_track"])
    make_rows = int(source_track.eq(KAGGLE_MAKE_TRACK).sum())
    if make_rows:
        raise ValueError(f"Kaggle Jungle manifest contains {make_rows} forbidden make-track row(s)")
    wrong_tracks = sorted(set(source_track) - {KAGGLE_JUNGLE_TRACK})
    if wrong_tracks:
        raise ValueError(f"Kaggle Jungle manifest contains unexpected source_track values: {wrong_tracks}")
    source_dataset = nonempty_text(data["source_dataset"])
    wrong_datasets = sorted(set(source_dataset) - {KAGGLE_DATASET_ID})
    if wrong_datasets:
        raise ValueError(
            f"Kaggle Jungle manifest contains unexpected source_dataset values: {wrong_datasets}"
        )
    camera = nonempty_text(data["camera"])
    non_center = sorted(set(camera) - {"center"})
    if non_center:
        raise ValueError(f"Kaggle Jungle manifest contains non-center camera rows: {non_center}")
    external_flags = data["is_external"].map(parse_bool)
    if external_flags.isna().any() or not external_flags.all():
        raise ValueError("Kaggle Jungle manifest must contain only is_external=true rows")

    prepared = pd.DataFrame()
    prepared["image_path"] = data["image_path"].astype(str).map(
        lambda value: str(Path(value).resolve())
    )
    prepared["steering"] = data["steering"].map(finite_float)
    for column in ("throttle", "brake", "speed"):
        prepared[column] = data[column].map(optional_float) if column in data else None
    prepared["source_session"] = (
        nonempty_text(data["source_session"], KAGGLE_SESSION_ID)
        if "source_session" in data
        else KAGGLE_SESSION_ID
    )
    prepared["source_dataset"] = source_dataset
    prepared["source_track"] = source_track
    prepared["source_row_index"] = data["source_row_index"]
    prepared["camera"] = camera
    prepared["is_external"] = True
    if "original_source_path" in data:
        prepared["original_source_path"] = nonempty_text(data["original_source_path"])
    elif "original_center_path" in data:
        prepared["original_source_path"] = nonempty_text(data["original_center_path"])
    else:
        prepared["original_source_path"] = data["image_path"].astype(str)
    prepared = prepared[OUTPUT_COLUMNS]
    validate_prepared_source(prepared, "Kaggle Jungle manifest")
    return prepared


def steering_distribution(values: list[float]) -> dict[str, Any]:
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


def count_distribution(series: pd.Series, *, empty_label: str = "(not_available)") -> dict[str, int]:
    normalized = series.map(
        lambda value: empty_label
        if value is None or pd.isna(value) or not str(value).strip()
        else str(value)
    )
    return {str(key): int(value) for key, value in normalized.value_counts().sort_index().items()}


def candidate_metrics(
    data: pd.DataFrame,
    *,
    check_corrupt_images: bool = True,
) -> dict[str, Any]:
    steering = data["steering"].map(finite_float)
    finite = [value for value in steering.tolist() if value is not None]
    paths = data["image_path"].astype(str)
    unique_existing = sorted({Path(value) for value in paths if Path(value).is_file()})
    missing_images = int(sum(not Path(value).is_file() for value in paths))
    corrupt_images = (
        int(sum(not image_is_valid(path) for path in unique_existing))
        if check_corrupt_images
        else None
    )
    filename_counts = Counter(Path(value).name.lower() for value in paths)
    is_external = data["is_external"].map(parse_bool)
    local_rows = int(is_external.eq(False).sum())
    external_rows = int(is_external.eq(True).sum())
    make_rows = int(data["source_track"].astype(str).eq(KAGGLE_MAKE_TRACK).sum())
    forbidden_rows = int(data["source_session"].map(is_forbidden_session).sum())
    return {
        "total_rows": int(len(data)),
        "local_v3_rows": local_rows,
        "kaggle_jungle_rows": external_rows,
        "external_ratio": external_rows / len(data) if len(data) else 0.0,
        "external_ratio_pct": external_rows / len(data) * 100 if len(data) else 0.0,
        "missing_images": missing_images,
        "corrupt_images": corrupt_images,
        "corrupt_scan_performed": check_corrupt_images,
        "duplicate_rows": int(data.duplicated().sum()),
        "duplicate_image_paths": int(paths.duplicated().sum()),
        "duplicate_image_filenames": int(
            sum(count - 1 for count in filename_counts.values() if count > 1)
        ),
        "invalid_steering_labels": int(steering.isna().sum()),
        "out_of_range_steering_labels": int(
            sum(value < -1.0 or value > 1.0 for value in finite)
        ),
        "throttle_available_count": int(data["throttle"].map(finite_float).notna().sum()),
        "brake_available_count": int(data["brake"].map(finite_float).notna().sum()),
        "speed_available_count": int(data["speed"].map(finite_float).notna().sum()),
        "source_dataset_distribution": count_distribution(data["source_dataset"]),
        "source_session_distribution": count_distribution(data["source_session"]),
        "source_track_distribution": count_distribution(data["source_track"]),
        "camera_distribution": count_distribution(data["camera"]),
        "make_rows_included": make_rows,
        "forbidden_internal_session_rows": forbidden_rows,
        **steering_distribution(finite),
    }


def source_distribution(data: pd.DataFrame) -> pd.DataFrame:
    values = data.copy()
    values["source_track"] = values["source_track"].fillna("")
    result = (
        values.groupby(
            ["source_dataset", "source_session", "source_track", "camera", "is_external"],
            dropna=False,
        )
        .size()
        .reset_index(name="rows")
        .sort_values(["is_external", "source_dataset", "source_session", "source_track"])
        .reset_index(drop=True)
    )
    result["pct_of_candidate"] = result["rows"] / len(values) * 100
    return result


def preservation_checks(
    combined: pd.DataFrame,
    local: pd.DataFrame,
    jungle: pd.DataFrame,
) -> dict[str, Any]:
    combined_local = combined.iloc[: len(local)].reset_index(drop=True)
    combined_jungle = combined.iloc[len(local) :].reset_index(drop=True)
    local_expected = local.reset_index(drop=True)
    jungle_expected = jungle.reset_index(drop=True)
    return {
        "expected_local_v3_rows": int(len(local)),
        "actual_local_v3_rows": int(len(combined_local)),
        "all_local_v3_rows_preserved": bool(combined_local.equals(local_expected)),
        "expected_kaggle_jungle_rows": int(len(jungle)),
        "actual_kaggle_jungle_rows": int(len(combined_jungle)),
        "all_kaggle_jungle_rows_preserved": bool(combined_jungle.equals(jungle_expected)),
        "local_v3_order_preserved": bool(
            combined_local["image_path"].tolist() == local_expected["image_path"].tolist()
        ),
        "kaggle_jungle_order_preserved": bool(
            combined_jungle["image_path"].tolist() == jungle_expected["image_path"].tolist()
        ),
    }


def assign_verdict(
    metrics: dict[str, Any],
    preservation: dict[str, Any],
) -> tuple[str, str, list[str]]:
    invalid_reasons: list[str] = []
    for key, label in (
        ("missing_images", "missing image(s)"),
        ("corrupt_images", "corrupt image(s)"),
        ("duplicate_image_paths", "duplicate image path(s)"),
        ("invalid_steering_labels", "invalid steering label(s)"),
        ("out_of_range_steering_labels", "out-of-range steering label(s)"),
        ("make_rows_included", "forbidden make-track row(s)"),
        ("forbidden_internal_session_rows", "forbidden Session C2/E/E2 row(s)"),
    ):
        count = metrics.get(key)
        if count:
            invalid_reasons.append(f"{count} {label}")
    if not preservation["all_local_v3_rows_preserved"]:
        invalid_reasons.append("not all Local V3 rows were preserved exactly")
    if not preservation["all_kaggle_jungle_rows_preserved"]:
        invalid_reasons.append("not all Kaggle Jungle rows were preserved exactly")
    if metrics["camera_distribution"] != {"center": metrics["total_rows"]}:
        invalid_reasons.append("non-center camera rows are present")
    if invalid_reasons:
        return "KM3", "Invalid", invalid_reasons

    adjustment_reasons: list[str] = []
    if not 0.20 <= metrics["external_ratio"] <= 0.30:
        adjustment_reasons.append(
            f"external ratio {metrics['external_ratio_pct']:.2f}% is outside 20%-30%"
        )
    if not 27.0 <= metrics["near_zero_pct"] <= 38.0:
        adjustment_reasons.append(
            f"near-zero share {metrics['near_zero_pct']:.2f}% is outside 27%-38%"
        )
    if not 30.0 <= metrics["left_pct"] <= 38.0:
        adjustment_reasons.append(f"left share {metrics['left_pct']:.2f}% is outside 30%-38%")
    if not 30.0 <= metrics["right_pct"] <= 38.0:
        adjustment_reasons.append(
            f"right share {metrics['right_pct']:.2f}% is outside 30%-38%"
        )
    if metrics["strong_turn_pct"] < 25.0:
        adjustment_reasons.append(
            f"strong-turn share {metrics['strong_turn_pct']:.2f}% is below 25%"
        )
    if adjustment_reasons:
        return "KM2", "Valid but needs adjustment", adjustment_reasons
    return (
        "KM1",
        "Kaggle Jungle Mix V1 candidate ready for review",
        ["integrity, preservation, exclusion, ratio, balance, and strong-turn gates passed"],
    )


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


def build_candidate(
    local_train_csv: Path,
    kaggle_jungle_manifest: Path,
    output_dir: Path,
    *,
    force: bool = False,
    check_corrupt_images: bool = True,
) -> dict[str, Any]:
    local_train_csv = local_train_csv.resolve()
    kaggle_jungle_manifest = kaggle_jungle_manifest.resolve()
    output_dir = output_dir.resolve()
    ensure_outputs_available(output_dir, force)

    local = prepare_local_rows(local_train_csv)
    jungle = prepare_kaggle_rows(kaggle_jungle_manifest)
    combined = pd.concat([local, jungle], ignore_index=True)[OUTPUT_COLUMNS]
    duplicate_paths = int(combined["image_path"].duplicated().sum())
    if duplicate_paths:
        raise ValueError(f"Combined candidate has {duplicate_paths} duplicate image path(s)")

    metrics = candidate_metrics(combined, check_corrupt_images=check_corrupt_images)
    preservation = preservation_checks(combined, local, jungle)
    verdict, verdict_label, verdict_reasons = assign_verdict(metrics, preservation)
    if verdict == "KM3":
        raise ValueError("Kaggle Jungle Mix V1 validation failed: " + "; ".join(verdict_reasons))

    distribution = source_distribution(combined)
    output_dir.mkdir(parents=True, exist_ok=True)
    train_path = output_dir / "train.csv"
    summary_path = output_dir / "dataset_summary.json"
    distribution_path = output_dir / "source_distribution.csv"
    summary: dict[str, Any] = {
        "candidate_id": "kaggle_jungle_mix_v1_training",
        "local_train_csv": str(local_train_csv),
        "kaggle_jungle_manifest": str(kaggle_jungle_manifest),
        "output_dir": str(output_dir),
        "outputs": {
            "train_csv": str(train_path),
            "dataset_summary": str(summary_path),
            "source_distribution": str(distribution_path),
        },
        "schema": OUTPUT_COLUMNS,
        "mix_policy": {
            "local_v3": "retain 100% in original order",
            "kaggle_jungle": "retain 100% center-camera candidate rows in original order",
            "shuffle": False,
            "sampling": False,
            "image_copying": False,
            "side_camera_offsets": False,
            "excluded_sources": [
                KAGGLE_MAKE_TRACK,
                PREVIOUS_EXTERNAL_DATASET_ID,
                "Session C2",
                "Session E",
                "Session E2",
            ],
        },
        "metrics": metrics,
        "preservation_checks": preservation,
        "candidate_verdict": verdict,
        "candidate_verdict_label": verdict_label,
        "candidate_verdict_reasons": verdict_reasons,
        "license_status": "unresolved for the Kaggle source",
        "training_authorized": False,
        "training_note": "This candidate requires human review before any later controlled training experiment.",
    }
    combined.to_csv(train_path, index=False, lineterminator="\n")
    distribution.to_csv(distribution_path, index=False, lineterminator="\n")
    write_json(summary_path, summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the validated Local V3 + Kaggle Jungle Mix V1 candidate without training."
    )
    parser.add_argument("--local-train-csv", default=str(DEFAULT_LOCAL_TRAIN_CSV))
    parser.add_argument(
        "--kaggle-jungle-manifest", default=str(DEFAULT_KAGGLE_JUNGLE_MANIFEST)
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
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
        summary = build_candidate(
            project_path(args.local_train_csv),
            project_path(args.kaggle_jungle_manifest),
            project_path(args.output_dir),
            force=args.force,
            check_corrupt_images=True,
        )
    except (FileNotFoundError, FileExistsError, ValueError, OSError) as exc:
        print(f"Kaggle Jungle Mix V1 build failed: {exc}", file=sys.stderr)
        return 1

    metrics = summary["metrics"]
    print("Kaggle Jungle Mix V1 candidate build complete")
    print(f"- Rows: {metrics['total_rows']}")
    print(f"- Local V3 rows: {metrics['local_v3_rows']}")
    print(f"- Kaggle Jungle rows: {metrics['kaggle_jungle_rows']}")
    print(f"- External ratio: {metrics['external_ratio_pct']:.2f}%")
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
    print(f"- Output: {summary['outputs']['train_csv']}")
    print("- No model was trained or evaluated; Local V3 manifests were not modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
