from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_external_mix_v1_training_dataset import (  # noqa: E402
    DEFAULT_LOCAL_TRAIN_CSV,
    DEFAULT_OUTPUT_DIR,
    OUTPUT_COLUMNS,
    candidate_verdict,
    finite_numeric,
    project_path,
)


def parse_boolean_column(series: pd.Series) -> tuple[pd.Series, int]:
    mapping = {
        "true": True,
        "false": False,
        "1": True,
        "0": False,
    }
    normalized = series.astype(str).str.strip().str.lower().map(mapping)
    return normalized.fillna(False).astype(bool), int(normalized.isna().sum())


def local_preservation_checks(candidate: pd.DataFrame, local_csv: Path) -> dict[str, Any]:
    if not local_csv.is_file():
        return {
            "local_manifest_exists": False,
            "all_local_rows_preserved": False,
            "missing_local_image_paths": -1,
            "unexpected_internal_image_paths": -1,
            "local_metadata_mismatches": -1,
        }
    local = pd.read_csv(local_csv)
    internal = candidate[~candidate["is_external"]]
    local_paths = local["image_path"].astype(str)
    internal_paths = internal["image_path"].astype(str)
    local_map = local.assign(_path=local_paths).set_index("_path")
    internal_map = internal.assign(_path=internal_paths).set_index("_path")
    missing_paths = sorted(set(local_paths) - set(internal_paths))
    unexpected_paths = sorted(set(internal_paths) - set(local_paths))
    mismatches = 0
    for path in set(local_paths) & set(internal_paths):
        local_row = local_map.loc[path]
        internal_row = internal_map.loc[path]
        if isinstance(local_row, pd.DataFrame) or isinstance(internal_row, pd.DataFrame):
            mismatches += 1
            continue
        local_steering = finite_numeric(pd.Series([local_row["steering"]])).iloc[0]
        internal_steering = finite_numeric(pd.Series([internal_row["steering"]])).iloc[0]
        if not math.isclose(float(local_steering), float(internal_steering), abs_tol=1e-12):
            mismatches += 1
        if str(local_row["source_session"]) != str(internal_row["source_session"]):
            mismatches += 1
    preserved = (
        len(internal) == len(local)
        and not missing_paths
        and not unexpected_paths
        and mismatches == 0
    )
    return {
        "local_manifest_exists": True,
        "local_manifest_rows": int(len(local)),
        "internal_candidate_rows": int(len(internal)),
        "all_local_rows_preserved": preserved,
        "missing_local_image_paths": len(missing_paths),
        "unexpected_internal_image_paths": len(unexpected_paths),
        "local_metadata_mismatches": mismatches,
    }


def validate(
    train_csv: Path,
    local_csv: Path,
    *,
    external_near_zero_cap_ratio: float,
    max_external_final_ratio: float,
    check_corrupt_images: bool = True,
) -> dict[str, Any]:
    if not train_csv.is_file():
        raise FileNotFoundError(f"External Mix V1 train.csv not found: {train_csv}")
    candidate = pd.read_csv(train_csv)
    missing_columns = sorted(set(OUTPUT_COLUMNS) - set(candidate.columns))
    if missing_columns:
        return {
            "verdict": "M3",
            "verdict_label": "Invalid",
            "verdict_reasons": [f"manifest is missing columns: {', '.join(missing_columns)}"],
            "missing_columns": missing_columns,
        }

    parsed_is_external, invalid_boolean_values = parse_boolean_column(candidate["is_external"])
    candidate["is_external"] = parsed_is_external
    preservation = local_preservation_checks(candidate, local_csv)
    local_rows = int(preservation.get("local_manifest_rows", len(candidate[~parsed_is_external])))
    result = candidate_verdict(
        candidate,
        local_rows=local_rows,
        external_near_zero_cap_ratio=external_near_zero_cap_ratio,
        max_external_final_ratio=max_external_final_ratio,
        check_corrupt_images=check_corrupt_images,
    )
    result["required_columns_present"] = True
    result["invalid_is_external_values"] = invalid_boolean_values
    result["local_preservation"] = preservation
    result["distribution_by_source_dataset"] = result["metrics"]["rows_per_source_dataset"]
    result["distribution_by_source_session"] = result["metrics"]["rows_per_source_session"]

    extra_invalid_reasons = []
    if invalid_boolean_values:
        extra_invalid_reasons.append(
            f"is_external has {invalid_boolean_values} invalid boolean value(s)"
        )
    if not preservation["all_local_rows_preserved"]:
        extra_invalid_reasons.append("Local V3 rows or steering/session metadata were not preserved")
    if extra_invalid_reasons:
        result["verdict"] = "M3"
        result["verdict_label"] = "Invalid"
        result["verdict_reasons"] = extra_invalid_reasons + result["verdict_reasons"]
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate External Mix V1 without training or model evaluation."
    )
    parser.add_argument("--train-csv", default=str(DEFAULT_OUTPUT_DIR / "train.csv"))
    parser.add_argument("--local-train-csv", default=str(DEFAULT_LOCAL_TRAIN_CSV))
    parser.add_argument("--external-near-zero-cap-ratio", type=float, default=0.25)
    parser.add_argument("--max-external-final-ratio", type=float, default=0.25)
    parser.add_argument("--skip-corrupt-check", action="store_true")
    parser.add_argument("--json", action="store_true", help="Print the full validation report as JSON.")
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = validate(
            project_path(args.train_csv),
            project_path(args.local_train_csv),
            external_near_zero_cap_ratio=float(args.external_near_zero_cap_ratio),
            max_external_final_ratio=float(args.max_external_final_ratio),
            check_corrupt_images=not args.skip_corrupt_check,
        )
    except (FileNotFoundError, ValueError, OSError, pd.errors.ParserError) as exc:
        print(f"External Mix V1 validation failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        metrics = result.get("metrics", {})
        print("External Mix V1 validation complete")
        print(f"- Verdict: {result['verdict']} - {result['verdict_label']}")
        print(
            f"- Rows: {result.get('total_rows', 0)} "
            f"({result.get('internal_rows', 0)} internal, {result.get('external_rows', 0)} external)"
        )
        print(f"- External ratio: {result.get('external_ratio', 0.0) * 100:.2f}%")
        if metrics:
            print(
                f"- Missing/corrupt images: {metrics['missing_images']}/{metrics['corrupt_images']}"
            )
            print(
                f"- Duplicate rows/image paths: {metrics['duplicate_rows']}/{metrics['duplicate_image_paths']}"
            )
            print(
                f"- Near-zero/left/right/strong: {metrics['near_zero_pct']:.2f}%/"
                f"{metrics['left_pct']:.2f}%/{metrics['right_pct']:.2f}%/"
                f"{metrics['strong_turn_pct']:.2f}%"
            )
        for reason in result["verdict_reasons"]:
            print(f"- {reason}")
        print("- No model was trained or evaluated.")
    return 1 if result["verdict"] == "M3" else 0


if __name__ == "__main__":
    raise SystemExit(main())
