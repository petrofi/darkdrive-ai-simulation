from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.driving_log import load_driving_log, resolve_image_path


UNIFIED_COLUMNS = ["image_path", "steering", "throttle", "brake", "speed", "source_dataset"]


def find_csv(input_dir: Path) -> Path | None:
    candidates = [
        input_dir / "driving_log.csv",
        input_dir / "data" / "driving_log.csv",
        input_dir / "interpolated.csv",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    matches = sorted(input_dir.rglob("driving_log.csv"))
    if matches:
        return matches[0]
    return None


def resolve_external_image(raw_path: object, csv_path: Path, input_dir: Path, images_dir_name: str) -> Path:
    images_dir = csv_path.parent / images_dir_name
    if not images_dir.exists():
        images_dir = input_dir / images_dir_name
    resolved = resolve_image_path(raw_path, csv_path, images_dir)
    if resolved.exists():
        return resolved
    basename_candidate = input_dir / images_dir_name / Path(str(raw_path).replace("\\", "/")).name
    return basename_candidate


def convert_udacity(dataset: str, input_dir: Path, output_dir: Path, images_dir_name: str) -> int:
    csv_path = find_csv(input_dir)
    if csv_path is None:
        print(f"Could not find driving_log.csv under {input_dir}")
        return 1

    data = load_driving_log(csv_path, "udacity")
    rows: list[dict[str, object]] = []
    missing_images = 0
    skipped_rows = 0

    for _, row in data.iterrows():
        if pd.isna(row.get("steering")):
            skipped_rows += 1
            continue

        image_path = resolve_external_image(row["center"], csv_path, input_dir, images_dir_name)
        if not image_path.exists():
            missing_images += 1
            skipped_rows += 1
            continue

        rows.append(
            {
                "image_path": str(image_path.resolve()),
                "steering": float(row["steering"]),
                "throttle": float(row["throttle"]) if "throttle" in row and pd.notna(row["throttle"]) else 0.0,
                "brake": float(row["brake"]) if "brake" in row and pd.notna(row["brake"]) else 0.0,
                "speed": float(row["speed"]) if "speed" in row and pd.notna(row["speed"]) else 0.0,
                "source_dataset": dataset,
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = output_dir / "driving_log.csv"
    pd.DataFrame(rows, columns=UNIFIED_COLUMNS).to_csv(output_csv, index=False)

    print("External dataset conversion summary")
    print(f"- Dataset: {dataset}")
    print(f"- Input CSV: {csv_path}")
    print(f"- Output mode: references original images without copying")
    print(f"- Total rows: {len(data)}")
    print(f"- Converted rows: {len(rows)}")
    print(f"- Skipped rows: {skipped_rows}")
    print(f"- Missing images: {missing_images}")
    print(f"- Output CSV path: {output_csv}")
    return 0 if rows else 1


def find_donkey_records(input_dir: Path) -> list[Path]:
    patterns = ["record_*.json", "records/*.json"]
    records: list[Path] = []
    for pattern in patterns:
        records.extend(input_dir.glob(pattern))
    return sorted(set(records))


def convert_donkeycar(dataset: str, input_dir: Path, output_dir: Path) -> int:
    records = find_donkey_records(input_dir)
    rows: list[dict[str, object]] = []
    missing_images = 0
    skipped_rows = 0

    for record_path in records:
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            skipped_rows += 1
            continue

        image_value = (
            record.get("cam/image_array")
            or record.get("image")
            or record.get("image_path")
            or record.get("cam/image")
        )
        steering_value = record.get("user/angle", record.get("angle", record.get("steering")))
        throttle_value = record.get("user/throttle", record.get("throttle", 0.0))
        if image_value is None or steering_value is None:
            skipped_rows += 1
            continue

        image_path = Path(str(image_value))
        candidates = [
            image_path,
            record_path.parent / image_path,
            input_dir / image_path,
            input_dir / "images" / image_path.name,
        ]
        resolved = next((candidate for candidate in candidates if candidate.exists()), candidates[-1])
        if not resolved.exists():
            missing_images += 1
            skipped_rows += 1
            continue

        rows.append(
            {
                "image_path": str(resolved.resolve()),
                "steering": float(steering_value),
                "throttle": float(throttle_value),
                "brake": 0.0,
                "speed": 0.0,
                "source_dataset": dataset,
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = output_dir / "driving_log.csv"
    pd.DataFrame(rows, columns=UNIFIED_COLUMNS).to_csv(output_csv, index=False)

    print("External dataset conversion summary")
    print(f"- Dataset: {dataset}")
    print(f"- Input directory: {input_dir}")
    print(f"- Output mode: references original images without copying")
    print(f"- Total records: {len(records)}")
    print(f"- Converted rows: {len(rows)}")
    print(f"- Skipped rows: {skipped_rows}")
    print(f"- Missing images: {missing_images}")
    print(f"- Output CSV path: {output_csv}")
    return 0 if rows else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert external driving datasets into DarkDrive format.")
    parser.add_argument("--dataset", required=True, help="Dataset key/name used in source_dataset column.")
    parser.add_argument("--input-dir", required=True, help="Extracted external dataset folder.")
    parser.add_argument("--output-dir", required=True, help="Output folder for converted driving_log.csv.")
    parser.add_argument(
        "--format",
        default="udacity",
        choices=["udacity", "donkeycar"],
        help="External dataset format to convert.",
    )
    parser.add_argument("--images-dir-name", default="IMG", help="Image folder name for Udacity-style data.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    if args.format == "donkeycar":
        raise SystemExit(convert_donkeycar(args.dataset, input_dir, output_dir))
    raise SystemExit(convert_udacity(args.dataset, input_dir, output_dir, args.images_dir_name))

