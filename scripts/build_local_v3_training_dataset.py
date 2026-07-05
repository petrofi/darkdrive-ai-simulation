from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.driving_log import load_driving_log, resolve_image_path


UNIFIED_COLUMNS = [
    "image_path",
    "steering",
    "throttle",
    "brake",
    "speed",
    "source_dataset",
    "source_session",
]
CONTROL_COLUMNS = ["throttle", "brake", "speed"]
NEAR_ZERO_ABS = 0.05
STRONG_TURN_ABS = 0.5


@dataclass(frozen=True)
class SessionSpec:
    name: str
    csv_path: Path
    images_dir: Path
    source_dataset: str


@dataclass
class ConvertedSession:
    spec: SessionSpec
    data: pd.DataFrame
    input_rows: int
    missing_images: int
    invalid_steering: int
    out_of_range_steering: int
    skipped_rows: int


def default_source_dataset(session_name: str) -> str:
    return "local_simulator_v1" if session_name == "v1" else "local_simulator_v2"


def default_train_sessions() -> list[SessionSpec]:
    return [
        SessionSpec(
            "v1",
            PROJECT_ROOT / "data/processed/simulator/driving_log.csv",
            PROJECT_ROOT / "data/processed/simulator/IMG",
            "local_simulator_v1",
        ),
        SessionSpec(
            "session_a_normal",
            PROJECT_ROOT / "data/processed/simulator_v2/session_a_normal/driving_log.csv",
            PROJECT_ROOT / "data/processed/simulator_v2/session_a_normal/IMG",
            "local_simulator_v2",
        ),
        SessionSpec(
            "session_b_new_training",
            PROJECT_ROOT / "data/processed/simulator_v2/session_b_new_training/driving_log.csv",
            PROJECT_ROOT / "data/processed/simulator_v2/session_b_new_training/IMG",
            "local_simulator_v2",
        ),
        SessionSpec(
            "session_d_curve_focused",
            PROJECT_ROOT / "data/processed/simulator_v2/session_d_curve_focused/driving_log.csv",
            PROJECT_ROOT / "data/processed/simulator_v2/session_d_curve_focused/IMG",
            "local_simulator_v2",
        ),
    ]


def default_validation_sessions() -> list[SessionSpec]:
    return [
        SessionSpec(
            "session_c2_right_recovery",
            PROJECT_ROOT / "data/processed/simulator_v2/session_c2_right_recovery/driving_log.csv",
            PROJECT_ROOT / "data/processed/simulator_v2/session_c2_right_recovery/IMG",
            "local_simulator_v2",
        )
    ]


def project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def parse_session(value: str) -> SessionSpec:
    parts = [part.strip() for part in value.split(",", 3)]
    if len(parts) not in (3, 4) or not all(parts[:3]):
        raise argparse.ArgumentTypeError(
            "session specs must use name,path_to_csv,path_to_images_dir[,source_dataset]"
        )
    name, csv_path, images_dir = parts[:3]
    source_dataset = parts[3] if len(parts) == 4 and parts[3] else default_source_dataset(name)
    return SessionSpec(name, project_path(csv_path), project_path(images_dir), source_dataset)


def stable_random_state(seed: int, *parts: object) -> int:
    material = "|".join([str(seed), *(str(part) for part in parts)])
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def sample_rows(data: pd.DataFrame, count: int, seed: int, label: str) -> pd.DataFrame:
    if count >= len(data):
        return data.copy()
    if count <= 0:
        return data.iloc[0:0].copy()
    return data.sample(n=count, random_state=stable_random_state(seed, label)).copy()


def safe_session_image_path(raw_path: object, csv_path: Path, images_dir: Path) -> Path:
    normalized_path = str(raw_path).strip().strip('"').strip("'").replace("\\", "/")
    image_name = Path(normalized_path).name

    if image_name:
        in_session_dir = images_dir / image_name
        if in_session_dir.exists():
            return in_session_dir.resolve()

    resolved = resolve_image_path(raw_path, csv_path, images_dir)
    if resolved.exists():
        return resolved.resolve()

    if image_name:
        return (images_dir / image_name).resolve()
    return resolved.resolve()


def float_or_missing(value: object) -> float | None:
    if pd.isna(value):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric):
        return None
    return numeric


def convert_session(session: SessionSpec) -> ConvertedSession:
    if not session.csv_path.exists():
        raise FileNotFoundError(f"Session CSV not found: {session.csv_path}")

    source = load_driving_log(session.csv_path, "udacity")
    rows: list[dict[str, object]] = []
    missing_images = 0
    invalid_steering = 0
    out_of_range_steering = 0

    for _, row in source.iterrows():
        steering = float_or_missing(row.get("steering"))
        if steering is None:
            invalid_steering += 1
            continue
        if steering < -1.0 or steering > 1.0:
            out_of_range_steering += 1
            continue

        image_path = safe_session_image_path(row.get("center"), session.csv_path, session.images_dir)
        if not image_path.exists():
            missing_images += 1
            continue

        rows.append(
            {
                "image_path": str(image_path),
                "steering": steering,
                "throttle": float_or_missing(row.get("throttle")),
                "brake": float_or_missing(row.get("brake")),
                "speed": float_or_missing(row.get("speed")),
                "source_dataset": session.source_dataset,
                "source_session": session.name,
            }
        )

    data = pd.DataFrame(rows, columns=UNIFIED_COLUMNS)
    skipped_rows = missing_images + invalid_steering + out_of_range_steering
    return ConvertedSession(
        spec=session,
        data=data,
        input_rows=len(source),
        missing_images=missing_images,
        invalid_steering=invalid_steering,
        out_of_range_steering=out_of_range_steering,
        skipped_rows=skipped_rows,
    )


def steering_masks(data: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    steering = pd.to_numeric(data["steering"], errors="coerce")
    near_zero = steering.abs() <= NEAR_ZERO_ABS
    left = steering < -NEAR_ZERO_ABS
    right = steering > NEAR_ZERO_ABS
    strong = steering.abs() >= STRONG_TURN_ABS
    return near_zero, left, right, strong


def downsample_near_zero_session(
    data: pd.DataFrame,
    max_near_zero_ratio: float,
    seed: int,
    session_name: str,
) -> tuple[pd.DataFrame, dict[str, object]]:
    near_zero, _, _, _ = steering_masks(data)
    near_zero_rows = data[near_zero]
    non_zero_rows = data[~near_zero]

    if len(non_zero_rows) == 0:
        retained_near_zero = near_zero_rows.copy()
    else:
        max_near_zero_count = int(
            (max_near_zero_ratio * len(non_zero_rows)) / (1.0 - max_near_zero_ratio)
        )
        retained_near_zero = sample_rows(
            near_zero_rows,
            min(len(near_zero_rows), max_near_zero_count),
            seed,
            f"{session_name}:near-zero",
        )

    sampled = pd.concat([non_zero_rows, retained_near_zero], ignore_index=True)
    return (
        sampled,
        {
            "rule": "keep all non-zero rows; cap near-zero rows per source session",
            "max_near_zero_ratio": max_near_zero_ratio,
            "before_rows": len(data),
            "after_rows": len(sampled),
            "near_zero_before": len(near_zero_rows),
            "near_zero_after": len(retained_near_zero),
        },
    )


def downsample_curve_left_session(
    data: pd.DataFrame,
    left_to_right_ratio: float,
    seed: int,
    session_name: str,
) -> tuple[pd.DataFrame, dict[str, object]]:
    near_zero, left, right, strong = steering_masks(data)
    near_zero_rows = data[near_zero]
    right_rows = data[right]
    left_rows = data[left]
    strong_left_rows = data[left & strong]
    softer_left_rows = data[left & ~strong]

    target_left_count = int(round(len(right_rows) * left_to_right_ratio))
    target_left_count = max(len(strong_left_rows), target_left_count)
    target_left_count = min(len(left_rows), target_left_count)
    softer_left_count = max(0, target_left_count - len(strong_left_rows))
    retained_softer_left = sample_rows(
        softer_left_rows,
        softer_left_count,
        seed,
        f"{session_name}:softer-left",
    )

    sampled = pd.concat(
        [near_zero_rows, right_rows, strong_left_rows, retained_softer_left],
        ignore_index=True,
    )
    return (
        sampled,
        {
            "rule": "keep all near-zero, right-steering, and strong-left rows; downsample softer left rows",
            "left_to_right_ratio": left_to_right_ratio,
            "before_rows": len(data),
            "after_rows": len(sampled),
            "left_before": len(left_rows),
            "left_after": len(strong_left_rows) + len(retained_softer_left),
            "right_retained": len(right_rows),
            "strong_left_retained": len(strong_left_rows),
            "softer_left_before": len(softer_left_rows),
            "softer_left_after": len(retained_softer_left),
        },
    )


def sample_training_sessions(
    converted_sessions: list[ConvertedSession],
    seed: int,
    max_normal_near_zero_ratio: float,
    curve_session_name: str,
    curve_left_to_right_ratio: float,
) -> tuple[pd.DataFrame, dict[str, dict[str, object]]]:
    sampled_frames: list[pd.DataFrame] = []
    sampling_report: dict[str, dict[str, object]] = {}

    for converted in converted_sessions:
        if converted.spec.name == curve_session_name:
            sampled, report = downsample_curve_left_session(
                converted.data,
                curve_left_to_right_ratio,
                seed,
                converted.spec.name,
            )
        else:
            sampled, report = downsample_near_zero_session(
                converted.data,
                max_normal_near_zero_ratio,
                seed,
                converted.spec.name,
            )
        sampled_frames.append(sampled)
        sampling_report[converted.spec.name] = report

    combined = pd.concat(sampled_frames, ignore_index=True) if sampled_frames else empty_manifest()
    if not combined.empty:
        combined = combined.sample(
            frac=1.0,
            random_state=stable_random_state(seed, "final-train-shuffle"),
        ).reset_index(drop=True)
    return combined, sampling_report


def empty_manifest() -> pd.DataFrame:
    return pd.DataFrame(columns=UNIFIED_COLUMNS)


def optional_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def count_corrupt_images(paths: pd.Series, image_cache: dict[str, bool]) -> int:
    try:
        from PIL import Image
    except ImportError:
        return -1

    corrupt = 0
    for value in paths.dropna().astype(str).unique():
        if value in image_cache:
            is_corrupt = image_cache[value]
        else:
            try:
                with Image.open(value) as image:
                    image.verify()
                is_corrupt = False
            except Exception:
                is_corrupt = True
            image_cache[value] = is_corrupt
        if is_corrupt:
            corrupt += 1
    return corrupt


def distribution_metrics(
    data: pd.DataFrame,
    check_corrupt_images: bool = True,
    image_cache: dict[str, bool] | None = None,
) -> dict[str, object]:
    image_cache = image_cache if image_cache is not None else {}
    steering = pd.to_numeric(data["steering"], errors="coerce")
    valid_steering = steering.dropna()
    total_valid = max(len(valid_steering), 1)

    near_zero = int((valid_steering.abs() <= NEAR_ZERO_ABS).sum())
    left = int((valid_steering < -NEAR_ZERO_ABS).sum())
    right = int((valid_steering > NEAR_ZERO_ABS).sum())
    strong = int((valid_steering.abs() >= STRONG_TURN_ABS).sum())
    missing_images = int(sum(0 if Path(str(path)).exists() else 1 for path in data["image_path"]))
    resolved_images = len(data) - missing_images
    corrupt_images = (
        count_corrupt_images(data.loc[data["image_path"].map(lambda value: Path(str(value)).exists()), "image_path"], image_cache)
        if check_corrupt_images and len(data)
        else 0
    )

    numeric_control_availability: dict[str, dict[str, int]] = {}
    for column in CONTROL_COLUMNS:
        numeric = pd.to_numeric(data[column], errors="coerce") if column in data.columns else pd.Series(dtype=float)
        numeric_control_availability[column] = {
            "available": int(numeric.notna().sum()),
            "missing_or_nan": int(numeric.isna().sum()),
        }

    return {
        "total_rows": int(len(data)),
        "resolved_image_count": int(resolved_images),
        "missing_images": int(missing_images),
        "corrupt_images": int(corrupt_images),
        "duplicate_rows": int(data.duplicated().sum()),
        "duplicate_image_paths": int(data["image_path"].duplicated().sum()) if "image_path" in data else 0,
        "invalid_steering_labels": int(steering.isna().sum()),
        "steering_outside_range": int(((valid_steering < -1.0) | (valid_steering > 1.0)).sum()),
        "nan_values": {column: int(data[column].isna().sum()) for column in data.columns},
        "steering_min": optional_float(valid_steering.min()) if len(valid_steering) else None,
        "steering_max": optional_float(valid_steering.max()) if len(valid_steering) else None,
        "steering_mean": optional_float(valid_steering.mean()) if len(valid_steering) else None,
        "steering_std": optional_float(valid_steering.std()) if len(valid_steering) else None,
        "near_zero_count": near_zero,
        "near_zero_pct": near_zero / total_valid * 100,
        "left_count": left,
        "left_pct": left / total_valid * 100,
        "right_count": right,
        "right_pct": right / total_valid * 100,
        "strong_turn_count": strong,
        "strong_turn_pct": strong / total_valid * 100,
        "rows_per_source_session": {
            str(key): int(value)
            for key, value in data["source_session"].fillna("unknown").value_counts().sort_index().items()
        }
        if "source_session" in data
        else {},
        "rows_per_source_dataset": {
            str(key): int(value)
            for key, value in data["source_dataset"].fillna("unknown").value_counts().sort_index().items()
        }
        if "source_dataset" in data
        else {},
        "control_availability": numeric_control_availability,
    }


def session_conversion_report(
    converted: ConvertedSession,
    check_corrupt_images: bool,
    image_cache: dict[str, bool],
) -> dict[str, object]:
    return {
        "name": converted.spec.name,
        "csv_path": str(converted.spec.csv_path),
        "images_dir": str(converted.spec.images_dir),
        "source_dataset": converted.spec.source_dataset,
        "input_rows": converted.input_rows,
        "converted_rows": len(converted.data),
        "missing_images": converted.missing_images,
        "invalid_steering": converted.invalid_steering,
        "out_of_range_steering": converted.out_of_range_steering,
        "skipped_rows": converted.skipped_rows,
        "metrics": distribution_metrics(converted.data, check_corrupt_images, image_cache),
    }


def csv_row_keys(data: pd.DataFrame) -> set[tuple[object, ...]]:
    return {tuple(row[column] for column in UNIFIED_COLUMNS) for _, row in data.iterrows()}


def leakage_report(train_data: pd.DataFrame, validation_data: pd.DataFrame) -> dict[str, object]:
    train_sources = set(train_data["source_session"].astype(str))
    validation_sources = set(validation_data["source_session"].astype(str))
    train_paths = set(train_data["image_path"].astype(str))
    validation_paths = set(validation_data["image_path"].astype(str))
    train_names = {Path(path).name for path in train_paths}
    validation_names = {Path(path).name for path in validation_paths}
    train_rows = csv_row_keys(train_data)
    validation_rows = csv_row_keys(validation_data)

    return {
        "overlapping_source_sessions": sorted(train_sources & validation_sources),
        "overlapping_source_session_count": len(train_sources & validation_sources),
        "overlapping_image_path_count": len(train_paths & validation_paths),
        "overlapping_csv_row_count": len(train_rows & validation_rows),
        "overlapping_image_filename_count": len(train_names & validation_names),
        "validation_session_names_in_training": sorted(
            source for source in validation_sources if source in train_sources
        ),
        "session_d_rows_in_validation": int(
            (validation_data["source_session"].astype(str) == "session_d_curve_focused").sum()
        ),
        "session_c2_rows_in_training": int(
            (train_data["source_session"].astype(str) == "session_c2_right_recovery").sum()
        ),
    }


def verdict_for_summary(
    train_metrics: dict[str, object],
    validation_metrics: dict[str, object],
    leakage: dict[str, object],
    conversion_reports: list[dict[str, object]],
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    conversion_missing = sum(int(report["missing_images"]) for report in conversion_reports)
    conversion_invalid = sum(
        int(report["invalid_steering"]) + int(report["out_of_range_steering"])
        for report in conversion_reports
    )

    if conversion_missing:
        reasons.append(f"{conversion_missing} source rows had missing images")
    if conversion_invalid:
        reasons.append(f"{conversion_invalid} source rows had invalid steering labels")
    if int(train_metrics["missing_images"]) or int(validation_metrics["missing_images"]):
        reasons.append("one or more output manifest images are missing")
    if int(train_metrics["corrupt_images"]) or int(validation_metrics["corrupt_images"]):
        reasons.append("one or more output manifest images are corrupt")
    if int(train_metrics["invalid_steering_labels"]) or int(validation_metrics["invalid_steering_labels"]):
        reasons.append("one or more output manifest steering labels are invalid")
    if int(leakage["overlapping_source_session_count"]):
        reasons.append("train and validation source sessions overlap")
    if int(leakage["overlapping_image_path_count"]):
        reasons.append("train and validation image paths overlap")
    if int(leakage["overlapping_csv_row_count"]):
        reasons.append("train and validation CSV rows overlap")
    if int(leakage["session_c2_rows_in_training"]):
        reasons.append("Session C2 appears in training")
    if int(leakage["session_d_rows_in_validation"]):
        reasons.append("Session D appears in validation")

    if reasons:
        return "C) Invalid due to leakage or missing data", reasons

    near_zero_pct = float(train_metrics["near_zero_pct"])
    left_count = int(train_metrics["left_count"])
    right_count = int(train_metrics["right_count"])
    strong_pct = float(train_metrics["strong_turn_pct"])
    direction_ratio = min(left_count, right_count) / max(left_count, right_count, 1)

    balance_reasons: list[str] = []
    if not 25.0 <= near_zero_pct <= 32.0:
        balance_reasons.append(f"training near-zero share is {near_zero_pct:.2f}%")
    if direction_ratio < 0.90:
        balance_reasons.append(f"left/right non-zero balance ratio is {direction_ratio:.3f}")
    if strong_pct < 18.0:
        balance_reasons.append(f"strong-turn share is {strong_pct:.2f}%")

    if balance_reasons:
        return "B) Valid but balancing needs adjustment", balance_reasons

    return "A) Local V3 dataset ready for session-aware training", [
        "no leakage or missing data detected",
        "training near-zero, direction balance, and strong-turn coverage passed V3 gates",
    ]


def write_source_distribution(
    output_path: Path,
    train_data: pd.DataFrame,
    validation_data: pd.DataFrame,
) -> None:
    rows: list[dict[str, object]] = []
    for split_name, frame in [("train", train_data), ("validation", validation_data)]:
        for source_session, source_data in frame.groupby("source_session"):
            metrics = distribution_metrics(source_data, check_corrupt_images=False)
            rows.append(
                {
                    "split": split_name,
                    "source_session": source_session,
                    "rows": metrics["total_rows"],
                    "near_zero_pct": metrics["near_zero_pct"],
                    "left_pct": metrics["left_pct"],
                    "right_pct": metrics["right_pct"],
                    "strong_turn_pct": metrics["strong_turn_pct"],
                }
            )
    pd.DataFrame(rows).to_csv(output_path, index=False)


def build(args: argparse.Namespace) -> bool:
    train_specs = args.train_session or default_train_sessions()
    validation_specs = args.validation_session or default_validation_sessions()
    train_names = {session.name for session in train_specs}
    validation_names = {session.name for session in validation_specs}
    if train_names & validation_names:
        print(f"FAIL source sessions overlap before build: {sorted(train_names & validation_names)}")
        return False

    output_dir = project_path(args.output_dir)
    train_csv = output_dir / "train.csv"
    validation_csv = output_dir / "validation.csv"
    summary_json = output_dir / "dataset_summary.json"
    source_distribution_csv = output_dir / "source_distribution.csv"
    image_cache: dict[str, bool] = {}

    converted_train = [convert_session(session) for session in train_specs]
    converted_validation = [convert_session(session) for session in validation_specs]
    conversion_reports = [
        session_conversion_report(session, not args.skip_corrupt_check, image_cache)
        for session in [*converted_train, *converted_validation]
    ]

    if any(report["skipped_rows"] for report in conversion_reports):
        print("FAIL one or more source sessions had missing images or invalid steering labels.")
        for report in conversion_reports:
            if report["skipped_rows"]:
                print(
                    f"- {report['name']}: skipped={report['skipped_rows']} "
                    f"missing_images={report['missing_images']} "
                    f"invalid_steering={report['invalid_steering']} "
                    f"out_of_range={report['out_of_range_steering']}"
                )
        return False

    train_data, sampling_report = sample_training_sessions(
        converted_train,
        args.seed,
        args.max_normal_near_zero_ratio,
        args.curve_session_name,
        args.curve_left_to_right_ratio,
    )
    validation_data = (
        pd.concat([session.data for session in converted_validation], ignore_index=True)
        if converted_validation
        else empty_manifest()
    )

    train_metrics = distribution_metrics(train_data, not args.skip_corrupt_check, image_cache)
    validation_metrics = distribution_metrics(validation_data, not args.skip_corrupt_check, image_cache)
    leakage = leakage_report(train_data, validation_data)
    verdict, verdict_reasons = verdict_for_summary(
        train_metrics,
        validation_metrics,
        leakage,
        conversion_reports,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    train_data.to_csv(train_csv, index=False)
    validation_data.to_csv(validation_csv, index=False)
    if not args.no_source_distribution_csv:
        write_source_distribution(source_distribution_csv, train_data, validation_data)

    summary = {
        "simulation_only": True,
        "seed": args.seed,
        "camera_policy": "center camera only; side-camera correction labels are not generated",
        "schema": UNIFIED_COLUMNS,
        "thresholds": {
            "near_zero_abs": NEAR_ZERO_ABS,
            "strong_turn_abs": STRONG_TURN_ABS,
        },
        "train_sessions": [session.name for session in train_specs],
        "validation_sessions": [session.name for session in validation_specs],
        "sampling": sampling_report,
        "source_sessions": conversion_reports,
        "splits": {
            "train": train_metrics,
            "validation": validation_metrics,
        },
        "leakage_checks": leakage,
        "verdict": verdict,
        "verdict_reasons": verdict_reasons,
        "outputs": {
            "train_csv": str(train_csv),
            "validation_csv": str(validation_csv),
            "dataset_summary_json": str(summary_json),
            "source_distribution_csv": str(source_distribution_csv)
            if not args.no_source_distribution_csv
            else None,
        },
    }
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("Local V3 dataset build complete")
    print(f"- train CSV: {train_csv}")
    print(f"- validation CSV: {validation_csv}")
    print(f"- summary JSON: {summary_json}")
    print(f"- seed: {args.seed}")
    print(f"- train rows: {train_metrics['total_rows']}")
    print(f"- validation rows: {validation_metrics['total_rows']}")
    print(
        "- train distribution: "
        f"near-zero={train_metrics['near_zero_pct']:.2f}% "
        f"left={train_metrics['left_pct']:.2f}% "
        f"right={train_metrics['right_pct']:.2f}% "
        f"strong={train_metrics['strong_turn_pct']:.2f}%"
    )
    print(
        "- validation distribution: "
        f"near-zero={validation_metrics['near_zero_pct']:.2f}% "
        f"left={validation_metrics['left_pct']:.2f}% "
        f"right={validation_metrics['right_pct']:.2f}% "
        f"strong={validation_metrics['strong_turn_pct']:.2f}%"
    )
    print(
        "- leakage: "
        f"source_overlap={leakage['overlapping_source_session_count']} "
        f"image_path_overlap={leakage['overlapping_image_path_count']} "
        f"csv_row_overlap={leakage['overlapping_csv_row_count']} "
        f"filename_overlap={leakage['overlapping_image_filename_count']}"
    )
    print(f"- verdict: {verdict}")
    return not verdict.startswith("C)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Local V3 session-aware train and validation manifests."
    )
    parser.add_argument(
        "--output-dir",
        default="data/processed/local_v3_training",
        help="Directory for train.csv, validation.csv, and dataset_summary.json.",
    )
    parser.add_argument(
        "--train-session",
        action="append",
        type=parse_session,
        default=[],
        help=(
            "Training session spec: name,path_to_csv,path_to_images_dir[,source_dataset]. "
            "Repeat for multiple sessions. Defaults to v1, Session A, Session B, and Session D."
        ),
    )
    parser.add_argument(
        "--validation-session",
        action="append",
        type=parse_session,
        default=[],
        help=(
            "Validation holdout session spec: name,path_to_csv,path_to_images_dir[,source_dataset]. "
            "Repeat for multiple complete-session holdouts. Defaults to Session C2."
        ),
    )
    parser.add_argument("--seed", type=int, default=42, help="Deterministic sampling seed.")
    parser.add_argument(
        "--max-normal-near-zero-ratio",
        type=float,
        default=0.30,
        help="Per-session near-zero cap for v1/A/B-style normal sessions.",
    )
    parser.add_argument(
        "--curve-session-name",
        default="session_d_curve_focused",
        help="Training source that should use the curve-focused left-downsampling rule.",
    )
    parser.add_argument(
        "--curve-left-to-right-ratio",
        type=float,
        default=0.85,
        help="Target retained left/right count ratio for the curve-focused session.",
    )
    parser.add_argument(
        "--skip-corrupt-check",
        action="store_true",
        help="Skip PIL image verification. Missing images are still checked.",
    )
    parser.add_argument(
        "--no-source-distribution-csv",
        action="store_true",
        help="Do not write the optional source_distribution.csv file.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(0 if build(parse_args()) else 1)
