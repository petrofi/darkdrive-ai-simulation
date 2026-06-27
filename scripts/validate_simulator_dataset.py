from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.driving_log import (
    image_columns,
    load_driving_log,
    primary_image_column,
    required_columns,
    resolve_image_path,
)


def validate_dataset(csv_path: Path, images_dir: Path, dataset_format: str) -> bool:
    print("DarkDrive AI Simulation dataset validation")
    print("Simulation-only dataset check. No real vehicle control is used.")

    if not csv_path.exists():
        print(f"FAIL CSV not found: {csv_path}")
        print("No simulator dataset found yet. Open the simulator, record driving data if supported, and save it to data/processed/simulator.")
        return False

    if not images_dir.exists():
        print(f"FAIL images directory not found: {images_dir}")
        print("Expected image folder: data/processed/simulator/IMG")
        return False

    try:
        data = load_driving_log(csv_path, dataset_format)
    except Exception as exc:
        print(f"FAIL could not read CSV: {exc}")
        return False

    expected_columns = required_columns(dataset_format)
    missing_columns = [column for column in expected_columns if column not in data.columns]
    if missing_columns:
        print(f"FAIL missing required columns: {', '.join(missing_columns)}")
        print(f"Expected columns: {','.join(expected_columns)}")
        return False

    row_count = len(data)
    print(f"Total rows: {row_count}")
    if row_count == 0:
        print("FAIL CSV has no rows.")
        return False

    path_column = primary_image_column(dataset_format)
    missing_images: list[tuple[int, str, Path]] = []
    found_images = 0
    for row_index, row in data.iterrows():
        image_path = resolve_image_path(row[path_column], csv_path, images_dir)
        if not image_path.exists():
            missing_images.append((row_index, path_column, image_path))
        else:
            found_images += 1

    if dataset_format == "udacity":
        for camera_column in image_columns(dataset_format):
            camera_found = 0
            camera_missing = 0
            for _, row in data.iterrows():
                image_path = resolve_image_path(row[camera_column], csv_path, images_dir)
                if image_path.exists():
                    camera_found += 1
                else:
                    camera_missing += 1
            print(f"{camera_column} images found: {camera_found}")
            print(f"{camera_column} images missing: {camera_missing}")

    steering = pd.to_numeric(data["steering"], errors="coerce")
    invalid_steering = int(steering.isna().sum())
    if invalid_steering:
        print(f"FAIL invalid steering values: {invalid_steering}")
        return False

    print(f"Found images: {found_images}")
    print(f"Missing images: {len(missing_images)}")
    if missing_images:
        row_index, column_name, image_path = missing_images[0]
        print(f"Example missing path: row {row_index}, column {column_name}: {image_path}")

    print(f"Steering min: {steering.min():.6f}")
    print(f"Steering max: {steering.max():.6f}")
    print(f"Steering mean: {steering.mean():.6f}")

    for column in ["throttle", "brake", "speed"]:
        if column in data.columns:
            values = pd.to_numeric(data[column], errors="coerce").dropna()
            if len(values) > 0:
                print(f"{column.title()} min: {values.min():.6f}")
                print(f"{column.title()} max: {values.max():.6f}")
                print(f"{column.title()} mean: {values.mean():.6f}")

    passed = len(missing_images) == 0
    print(f"{'PASS' if passed else 'FAIL'} dataset validation summary")
    return passed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a simulation driving dataset.")
    parser.add_argument("--csv", default="data/processed/simulator/driving_log.csv", help="Path to driving_log.csv.")
    parser.add_argument("--images-dir", default="data/processed/simulator/IMG", help="Directory containing images.")
    parser.add_argument("--format", default="udacity", choices=["simple", "udacity"], help="Dataset format to validate.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    success = validate_dataset(Path(args.csv), Path(args.images_dir), args.format)
    raise SystemExit(0 if success else 1)
