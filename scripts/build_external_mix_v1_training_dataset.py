from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCAL_TRAIN_CSV = PROJECT_ROOT / "data/processed/local_v3_training/train.csv"
DEFAULT_EXTERNAL_ROOT = (
    PROJECT_ROOT / "data/external/udacity_behavioral_cloning_public/extracted/data"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data/processed/external_mix_v1_training"
EXTERNAL_DATASET_ID = "udacity_behavioral_cloning_public"
INTERNAL_DATASET_ID = "internal_local_v3"
EXTERNAL_SESSION_ID = "external_udacity_public"
NEAR_ZERO_ABS = 0.05
STRONG_TURN_ABS = 0.5
OUTPUT_FILENAMES = (
    "train.csv",
    "dataset_summary.json",
    "source_distribution.csv",
    "external_subset_report.csv",
)
OUTPUT_COLUMNS = [
    "image_path",
    "steering",
    "throttle",
    "brake",
    "speed",
    "source_session",
    "source_dataset",
    "source_row_index",
    "is_external",
    "source_path",
]
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


def stable_random_state(seed: int, label: str) -> int:
    digest = hashlib.sha256(f"{seed}|{label}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def sample_rows(data: pd.DataFrame, count: int, seed: int, label: str) -> pd.DataFrame:
    if count <= 0:
        return data.iloc[0:0].copy()
    if count >= len(data):
        return data.copy()
    return data.sample(n=count, random_state=stable_random_state(seed, label)).copy()


def finite_numeric(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.where(numeric.map(lambda value: math.isfinite(value) if pd.notna(value) else False))


def steering_masks(data: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    steering = finite_numeric(data["steering"])
    return (
        steering.abs() <= NEAR_ZERO_ABS,
        steering < -NEAR_ZERO_ABS,
        steering > NEAR_ZERO_ABS,
        steering.abs() >= STRONG_TURN_ABS,
    )


def normalized_session_key(value: object) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")
    return normalized


def is_forbidden_session(value: object) -> bool:
    return normalized_session_key(value) in FORBIDDEN_SESSION_KEYS


def image_is_valid(path: Path) -> bool:
    try:
        from PIL import Image

        with Image.open(path) as image:
            image.verify()
        return True
    except Exception:
        return False


def data_metrics(data: pd.DataFrame, *, check_corrupt_images: bool = True) -> dict[str, Any]:
    steering = finite_numeric(data["steering"])
    valid = steering.dropna()
    denominator = len(data) if len(data) else 1
    paths = data["image_path"].astype(str)
    existing_paths = sorted({Path(value) for value in paths if Path(value).is_file()})
    missing_images = int(sum(not Path(value).is_file() for value in paths))
    corrupt_images = (
        int(sum(not image_is_valid(path) for path in existing_paths))
        if check_corrupt_images
        else -1
    )

    near_zero = int((valid.abs() <= NEAR_ZERO_ABS).sum())
    left = int((valid < -NEAR_ZERO_ABS).sum())
    right = int((valid > NEAR_ZERO_ABS).sum())
    strong = int((valid.abs() >= STRONG_TURN_ABS).sum())
    metrics: dict[str, Any] = {
        "total_rows": int(len(data)),
        "missing_images": missing_images,
        "corrupt_images": corrupt_images,
        "duplicate_rows": int(data.duplicated().sum()),
        "duplicate_image_paths": int(paths.duplicated().sum()),
        "invalid_steering_labels": int(steering.isna().sum()),
        "out_of_range_steering_labels": int(((valid < -1.0) | (valid > 1.0)).sum()),
        "near_zero_count": near_zero,
        "near_zero_pct": near_zero / denominator * 100,
        "left_count": left,
        "left_pct": left / denominator * 100,
        "right_count": right,
        "right_pct": right / denominator * 100,
        "strong_turn_count": strong,
        "strong_turn_pct": strong / denominator * 100,
    }
    if "source_dataset" in data:
        metrics["rows_per_source_dataset"] = {
            str(key): int(value)
            for key, value in data["source_dataset"].value_counts().sort_index().items()
        }
    if "source_session" in data:
        metrics["rows_per_source_session"] = {
            str(key): int(value)
            for key, value in data["source_session"].value_counts().sort_index().items()
        }
    return metrics


def validate_source_frame(data: pd.DataFrame, label: str) -> None:
    steering = finite_numeric(data["steering"])
    invalid = int(steering.isna().sum())
    out_of_range = int(((steering < -1.0) | (steering > 1.0)).sum())
    paths = data["image_path"].astype(str)
    missing = [value for value in paths if not Path(value).is_file()]
    duplicates = int(paths.duplicated().sum())
    if invalid:
        raise ValueError(f"{label} has {invalid} invalid steering label(s)")
    if out_of_range:
        raise ValueError(f"{label} has {out_of_range} out-of-range steering label(s)")
    if missing:
        raise FileNotFoundError(
            f"{label} has {len(missing)} missing image(s); first missing path: {missing[0]}"
        )
    if duplicates:
        raise ValueError(f"{label} has {duplicates} duplicate image path(s)")


def prepare_local_rows(csv_path: Path) -> pd.DataFrame:
    if not csv_path.is_file():
        raise FileNotFoundError(f"Local V3 training manifest not found: {csv_path}")
    data = pd.read_csv(csv_path)
    required = {"image_path", "steering", "source_session"}
    missing_columns = sorted(required - set(data.columns))
    if missing_columns:
        raise ValueError(f"Local V3 manifest is missing columns: {', '.join(missing_columns)}")
    forbidden = sorted(
        {str(value) for value in data["source_session"] if is_forbidden_session(value)}
    )
    if forbidden:
        raise ValueError(f"Forbidden training session(s) found: {', '.join(forbidden)}")

    prepared = pd.DataFrame()
    prepared["image_path"] = data["image_path"].astype(str).map(lambda value: str(Path(value).resolve()))
    prepared["steering"] = finite_numeric(data["steering"])
    for column in ("throttle", "brake", "speed"):
        prepared[column] = finite_numeric(data[column]) if column in data else None
    prepared["source_session"] = data["source_session"].astype(str)
    prepared["source_dataset"] = INTERNAL_DATASET_ID
    prepared["source_row_index"] = range(len(data))
    prepared["is_external"] = False
    prepared["source_path"] = data["image_path"].astype(str)
    prepared = prepared[OUTPUT_COLUMNS]
    validate_source_frame(prepared, "Local V3 training manifest")
    return prepared


def resolve_external_image(raw_value: object, external_root: Path) -> Path:
    normalized = str(raw_value).strip().strip('"').strip("'").replace("\\", "/")
    raw_path = Path(normalized)
    candidates = []
    if raw_path.is_absolute():
        candidates.append(raw_path)
    candidates.extend(
        [
            external_root / normalized,
            external_root / "IMG" / raw_path.name,
        ]
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return (external_root / "IMG" / raw_path.name).resolve()


def prepare_external_rows(external_root: Path) -> pd.DataFrame:
    csv_path = external_root / "driving_log.csv"
    images_dir = external_root / "IMG"
    if not csv_path.is_file():
        raise FileNotFoundError(f"External driving_log.csv not found: {csv_path}")
    if not images_dir.is_dir():
        raise FileNotFoundError(f"External IMG directory not found: {images_dir}")
    data = pd.read_csv(csv_path, skipinitialspace=True)
    data.columns = [str(column).strip().lower() for column in data.columns]
    required = {"center", "steering"}
    missing_columns = sorted(required - set(data.columns))
    if missing_columns:
        raise ValueError(f"External driving log is missing columns: {', '.join(missing_columns)}")

    prepared = pd.DataFrame()
    prepared["image_path"] = data["center"].map(
        lambda value: str(resolve_external_image(value, external_root))
    )
    prepared["steering"] = finite_numeric(data["steering"])
    for column in ("throttle", "brake", "speed"):
        prepared[column] = finite_numeric(data[column]) if column in data else None
    prepared["source_session"] = EXTERNAL_SESSION_ID
    prepared["source_dataset"] = EXTERNAL_DATASET_ID
    prepared["source_row_index"] = range(2, len(data) + 2)
    prepared["is_external"] = True
    prepared["source_path"] = data["center"].astype(str).str.strip()
    prepared = prepared[OUTPUT_COLUMNS]
    validate_source_frame(prepared, "External Udacity source")
    return prepared


def maximum_external_rows(local_rows: int, max_final_ratio: float) -> int:
    if not 0.0 < max_final_ratio < 1.0:
        raise ValueError("--max-external-final-ratio must be between 0 and 1")
    return int(math.floor((max_final_ratio * local_rows) / (1.0 - max_final_ratio)))


def choose_direction_counts(
    total: int,
    left_available: int,
    right_available: int,
    strong_left: int,
    strong_right: int,
) -> tuple[int, int]:
    retained_strong_left = min(strong_left, total)
    retained_strong_right = min(strong_right, max(0, total - retained_strong_left))
    lower_left = max(0, total - right_available, retained_strong_left)
    upper_left = min(total, left_available, total - retained_strong_right)
    if lower_left > upper_left:
        raise ValueError("External non-zero rows cannot satisfy the requested balanced sample")
    ideal_left = total // 2
    left_count = min(max(ideal_left, lower_left), upper_left)
    return left_count, total - left_count


def sample_direction(
    pool: pd.DataFrame,
    count: int,
    seed: int,
    label: str,
) -> pd.DataFrame:
    _, _, _, strong_mask = steering_masks(pool)
    strong = pool[strong_mask]
    softer = pool[~strong_mask]
    if len(strong) >= count:
        return sample_rows(strong, count, seed, f"{label}:strong-limited")
    retained_soft = sample_rows(softer, count - len(strong), seed, f"{label}:softer")
    return pd.concat([strong, retained_soft], ignore_index=True)


def sample_external_rows(
    data: pd.DataFrame,
    *,
    local_rows: int,
    seed: int,
    target_rows: int,
    near_zero_cap_ratio: float,
    max_external_final_ratio: float,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    if target_rows <= 0:
        raise ValueError("--external-target-rows must be positive")
    if not 0.0 <= near_zero_cap_ratio < 1.0:
        raise ValueError("--external-near-zero-cap-ratio must be in [0, 1)")

    near_zero_mask, left_mask, right_mask, strong_mask = steering_masks(data)
    near_zero_pool = data[near_zero_mask]
    left_pool = data[left_mask]
    right_pool = data[right_mask]
    non_zero_available = len(left_pool) + len(right_pool)
    ratio_limit = maximum_external_rows(local_rows, max_external_final_ratio)
    effective_target = min(target_rows, len(data), ratio_limit)

    max_total_supported_by_non_zero = int(
        math.floor(non_zero_available / (1.0 - near_zero_cap_ratio))
    )
    effective_target = min(effective_target, max_total_supported_by_non_zero)
    if effective_target <= 0:
        raise ValueError("No external sample can satisfy the configured caps")

    near_zero_count = min(
        len(near_zero_pool), int(math.floor(effective_target * near_zero_cap_ratio))
    )
    non_zero_count = effective_target - near_zero_count
    strong_left = int((left_mask & strong_mask).sum())
    strong_right = int((right_mask & strong_mask).sum())
    left_count, right_count = choose_direction_counts(
        non_zero_count,
        len(left_pool),
        len(right_pool),
        strong_left,
        strong_right,
    )

    sampled_near_zero = sample_rows(near_zero_pool, near_zero_count, seed, "near-zero")
    sampled_left = sample_direction(left_pool, left_count, seed, "left")
    sampled_right = sample_direction(right_pool, right_count, seed, "right")
    sampled = pd.concat(
        [sampled_near_zero, sampled_left, sampled_right], ignore_index=True
    )
    sampled = sampled.sample(
        frac=1.0, random_state=stable_random_state(seed, "external-final-shuffle")
    ).reset_index(drop=True)

    selected_near, selected_left, selected_right, selected_strong = steering_masks(sampled)
    bucket_rows = [
        {
            "bucket": "near_zero",
            "overlaps_other_buckets": False,
            "available_rows": len(near_zero_pool),
            "selected_rows": int(selected_near.sum()),
            "selected_pct_of_subset": float(selected_near.mean() * 100),
            "selection_rule": "deterministic sample capped by external-near-zero-cap-ratio",
        },
        {
            "bucket": "left",
            "overlaps_other_buckets": False,
            "available_rows": len(left_pool),
            "selected_rows": int(selected_left.sum()),
            "selected_pct_of_subset": float(selected_left.mean() * 100),
            "selection_rule": "balanced with right; all available strong-left rows retained when capacity permits",
        },
        {
            "bucket": "right",
            "overlaps_other_buckets": False,
            "available_rows": len(right_pool),
            "selected_rows": int(selected_right.sum()),
            "selected_pct_of_subset": float(selected_right.mean() * 100),
            "selection_rule": "balanced with left; all available strong-right rows retained when capacity permits",
        },
        {
            "bucket": "strong_turn",
            "overlaps_other_buckets": True,
            "available_rows": int(strong_mask.sum()),
            "selected_rows": int(selected_strong.sum()),
            "selected_pct_of_subset": float(selected_strong.mean() * 100),
            "selection_rule": "retain all strong turns unless the requested sample has insufficient capacity",
        },
    ]
    report = pd.DataFrame(bucket_rows)
    strategy = {
        "requested_external_rows": int(target_rows),
        "effective_external_rows": int(len(sampled)),
        "external_ratio_row_limit": int(ratio_limit),
        "near_zero_cap_ratio": float(near_zero_cap_ratio),
        "max_external_final_ratio": float(max_external_final_ratio),
        "strong_turn_rows_available": int(strong_mask.sum()),
        "strong_turn_rows_selected": int(selected_strong.sum()),
        "all_strong_turn_rows_retained": bool(selected_strong.sum() == strong_mask.sum()),
        "target_reduction_reasons": [
            reason
            for condition, reason in (
                (target_rows > len(data), "external source has fewer rows than requested"),
                (target_rows > ratio_limit, "final external-ratio cap reduced the target"),
                (
                    min(target_rows, len(data), ratio_limit) > max_total_supported_by_non_zero,
                    "near-zero cap and available non-zero rows reduced the target",
                ),
            )
            if condition
        ],
    }
    return sampled, report, strategy


def source_distribution(data: pd.DataFrame) -> pd.DataFrame:
    distribution = (
        data.groupby(["source_dataset", "source_session", "is_external"], dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values(["is_external", "source_dataset", "source_session"])
        .reset_index(drop=True)
    )
    distribution["pct_of_candidate"] = distribution["rows"] / len(data) * 100
    return distribution


def candidate_verdict(
    combined: pd.DataFrame,
    *,
    local_rows: int,
    external_near_zero_cap_ratio: float,
    max_external_final_ratio: float,
    check_corrupt_images: bool = True,
) -> dict[str, Any]:
    metrics = data_metrics(combined, check_corrupt_images=check_corrupt_images)
    is_external = combined["is_external"].eq(True)
    external = combined[is_external]
    internal = combined[~is_external]
    external_metrics = data_metrics(external, check_corrupt_images=False)
    external_ratio = len(external) / len(combined) if len(combined) else 0.0
    external_near_zero_ratio = (
        external_metrics["near_zero_count"] / len(external) if len(external) else 0.0
    )
    forbidden_counts = {
        str(key): int(value)
        for key, value in combined.loc[
            combined["source_session"].map(is_forbidden_session), "source_session"
        ].value_counts().items()
    }

    invalid_reasons: list[str] = []
    if metrics["missing_images"]:
        invalid_reasons.append(f"{metrics['missing_images']} image path(s) are missing")
    if check_corrupt_images and metrics["corrupt_images"]:
        invalid_reasons.append(f"{metrics['corrupt_images']} image(s) are corrupt")
    if metrics["duplicate_rows"]:
        invalid_reasons.append(f"{metrics['duplicate_rows']} duplicate row(s) detected")
    if metrics["duplicate_image_paths"]:
        invalid_reasons.append(
            f"{metrics['duplicate_image_paths']} duplicate image path(s) detected"
        )
    if metrics["invalid_steering_labels"] or metrics["out_of_range_steering_labels"]:
        invalid_reasons.append("invalid or out-of-range steering labels detected")
    if forbidden_counts:
        invalid_reasons.append("forbidden training sessions detected")
    if len(internal) != local_rows:
        invalid_reasons.append(
            f"internal row count {len(internal)} does not preserve all {local_rows} Local V3 rows"
        )
    if invalid_reasons:
        verdict = "M3"
        reasons = invalid_reasons
    else:
        resampling_reasons: list[str] = []
        if not 2500 <= len(external) <= 3500:
            resampling_reasons.append(
                f"external subset size {len(external)} is outside the preferred 2500-3500 range"
            )
        if external_ratio > max_external_final_ratio + 1e-12:
            resampling_reasons.append(
                f"external ratio {external_ratio:.4f} exceeds {max_external_final_ratio:.4f}"
            )
        if external_near_zero_ratio > external_near_zero_cap_ratio + 1e-12:
            resampling_reasons.append(
                "external near-zero ratio exceeds the configured cap"
            )
        if not 27.0 <= metrics["near_zero_pct"] <= 34.0:
            resampling_reasons.append(
                f"combined near-zero share is {metrics['near_zero_pct']:.2f}%"
            )
        if not 30.0 <= metrics["left_pct"] <= 38.0:
            resampling_reasons.append(f"combined left share is {metrics['left_pct']:.2f}%")
        if not 30.0 <= metrics["right_pct"] <= 38.0:
            resampling_reasons.append(f"combined right share is {metrics['right_pct']:.2f}%")
        if metrics["strong_turn_pct"] < 20.0:
            resampling_reasons.append(
                f"combined strong-turn share is {metrics['strong_turn_pct']:.2f}%"
            )
        verdict = "M2" if resampling_reasons else "M1"
        reasons = resampling_reasons or [
            "candidate passed integrity, cap, session, and steering-distribution gates"
        ]

    return {
        "verdict": verdict,
        "verdict_label": {
            "M1": "External Mix V1 candidate ready for review",
            "M2": "Valid but needs resampling",
            "M3": "Invalid",
        }[verdict],
        "verdict_reasons": reasons,
        "total_rows": int(len(combined)),
        "internal_rows": int(len(internal)),
        "external_rows": int(len(external)),
        "external_ratio": external_ratio,
        "external_near_zero_ratio": external_near_zero_ratio,
        "external_ratio_within_cap": bool(external_ratio <= max_external_final_ratio + 1e-12),
        "external_near_zero_cap_respected": bool(
            external_near_zero_ratio <= external_near_zero_cap_ratio + 1e-12
        ),
        "forbidden_session_counts": forbidden_counts,
        "metrics": metrics,
        "external_subset_metrics": external_metrics,
    }


def ensure_outputs_available(output_dir: Path, force: bool) -> None:
    existing = [output_dir / filename for filename in OUTPUT_FILENAMES if (output_dir / filename).exists()]
    if existing and not force:
        joined = ", ".join(str(path) for path in existing)
        raise FileExistsError(f"Refusing to overwrite existing output(s) without --force: {joined}")


def write_json(path: Path, value: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def build(args: argparse.Namespace) -> dict[str, Any]:
    local_csv = project_path(args.local_train_csv)
    external_root = project_path(args.external_root)
    output_dir = project_path(args.output_dir)
    ensure_outputs_available(output_dir, bool(args.force))

    local = prepare_local_rows(local_csv)
    external_source = prepare_external_rows(external_root)
    sampled_external, subset_report, strategy = sample_external_rows(
        external_source,
        local_rows=len(local),
        seed=int(args.seed),
        target_rows=int(args.external_target_rows),
        near_zero_cap_ratio=float(args.external_near_zero_cap_ratio),
        max_external_final_ratio=float(args.max_external_final_ratio),
    )
    combined = pd.concat([local, sampled_external], ignore_index=True)
    combined = combined.sample(
        frac=1.0, random_state=stable_random_state(int(args.seed), "combined-final-shuffle")
    ).reset_index(drop=True)
    validation = candidate_verdict(
        combined,
        local_rows=len(local),
        external_near_zero_cap_ratio=float(args.external_near_zero_cap_ratio),
        max_external_final_ratio=float(args.max_external_final_ratio),
        check_corrupt_images=True,
    )
    if validation["verdict"] == "M3":
        raise ValueError("Candidate validation failed: " + "; ".join(validation["verdict_reasons"]))

    distribution = source_distribution(combined)
    summary = {
        "simulation_only": True,
        "training_performed": False,
        "model_evaluation_performed": False,
        "seed": int(args.seed),
        "camera_policy": "center camera only; no side-camera steering offsets",
        "thresholds": {
            "near_zero_abs_lte": NEAR_ZERO_ABS,
            "strong_turn_abs_gte": STRONG_TURN_ABS,
        },
        "schema": OUTPUT_COLUMNS,
        "inputs": {
            "local_train_csv": str(local_csv.resolve()),
            "external_root": str(external_root.resolve()),
            "local_validation_used": False,
        },
        "sampling_strategy": strategy,
        "input_metrics": {
            "local_v3_train": data_metrics(local, check_corrupt_images=False),
            "full_external_source": data_metrics(external_source, check_corrupt_images=False),
        },
        "candidate_metrics": validation["metrics"],
        "external_subset_metrics": validation["external_subset_metrics"],
        "source_distribution": distribution.to_dict(orient="records"),
        "validation": {key: value for key, value in validation.items() if key not in {"metrics", "external_subset_metrics"}},
        "outputs": {filename: str((output_dir / filename).resolve()) for filename in OUTPUT_FILENAMES},
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output_dir / "train.csv", index=False, lineterminator="\n")
    distribution.to_csv(output_dir / "source_distribution.csv", index=False, lineterminator="\n")
    subset_report.to_csv(output_dir / "external_subset_report.csv", index=False, lineterminator="\n")
    write_json(output_dir / "dataset_summary.json", summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a capped, deterministic External Mix V1 training candidate without training."
    )
    parser.add_argument("--local-train-csv", default=str(DEFAULT_LOCAL_TRAIN_CSV))
    parser.add_argument("--external-root", default=str(DEFAULT_EXTERNAL_ROOT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--external-target-rows", type=int, default=3000)
    parser.add_argument("--external-near-zero-cap-ratio", type=float, default=0.25)
    parser.add_argument("--max-external-final-ratio", type=float, default=0.25)
    parser.add_argument("--force", action="store_true")
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        summary = build(args)
    except (FileNotFoundError, FileExistsError, ValueError, OSError, pd.errors.ParserError) as exc:
        print(f"External Mix V1 build failed: {exc}", file=sys.stderr)
        return 1

    validation = summary["validation"]
    metrics = summary["candidate_metrics"]
    external = summary["external_subset_metrics"]
    print("External Mix V1 candidate built")
    print(f"- Output: {project_path(args.output_dir)}")
    print(f"- Rows: {metrics['total_rows']} ({validation['internal_rows']} internal, {validation['external_rows']} external)")
    print(f"- External ratio: {validation['external_ratio'] * 100:.2f}%")
    print(
        "- External distribution: "
        f"near-zero {external['near_zero_pct']:.2f}%, left {external['left_pct']:.2f}%, "
        f"right {external['right_pct']:.2f}%, strong {external['strong_turn_pct']:.2f}%"
    )
    print(
        "- Combined distribution: "
        f"near-zero {metrics['near_zero_pct']:.2f}%, left {metrics['left_pct']:.2f}%, "
        f"right {metrics['right_pct']:.2f}%, strong {metrics['strong_turn_pct']:.2f}%"
    )
    print(f"- Verdict: {validation['verdict']} - {validation['verdict_label']}")
    print("- No model was trained or evaluated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
