from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


UDACITY_REQUIRED_COLUMNS = ["center", "left", "right", "steering", "throttle", "brake", "speed"]


def resolve_image_path(raw_path: str, csv_path: Path, images_dir: Path) -> Path:
    """Resolve common simulator image paths without assuming one exact exporter."""
    image_path = Path(str(raw_path).strip())

    if image_path.is_absolute():
        return image_path

    cwd_path = Path.cwd() / image_path
    if cwd_path.exists():
        return cwd_path

    csv_relative_path = csv_path.parent / image_path
    if csv_relative_path.exists():
        return csv_relative_path

    # Udacity-style logs often store paths as IMG/file.jpg.
    if image_path.parts and image_path.parts[0].lower() == "img":
        return images_dir / Path(*image_path.parts[1:])

    return images_dir / image_path.name


def validate_dataset(csv_path: Path, images_dir: Path, dataset_format: str) -> bool:
    print("DarkDrive AI Simulation dataset validation")
    print("Simulation-only dataset check. No real vehicle control is used.")

    if dataset_format != "udacity":
        print(f"FAIL unsupported format: {dataset_format}")
        print("Currently supported validation format: udacity")
        return False

    if not csv_path.exists():
        print(f"FAIL CSV not found: {csv_path}")
        print("Collect simulator data first and save the log as data/processed/simulator/driving_log.csv.")
        return False

    if not images_dir.exists():
        print(f"FAIL images directory not found: {images_dir}")
        print("Expected image folder: data/processed/simulator/IMG")
        return False

    try:
        data = pd.read_csv(csv_path)
    except Exception as exc:
        print(f"FAIL could not read CSV: {exc}")
        return False

    data.columns = [column.strip() for column in data.columns]
    missing_columns = [column for column in UDACITY_REQUIRED_COLUMNS if column not in data.columns]
    if missing_columns:
        print(f"FAIL missing required columns: {', '.join(missing_columns)}")
        print("Expected columns: center,left,right,steering,throttle,brake,speed")
        return False

    row_count = len(data)
    print(f"Rows: {row_count}")
    if row_count == 0:
        print("FAIL CSV has no rows.")
        return False

    missing_images = []
    for row_index, row in data.iterrows():
        image_path = resolve_image_path(row["center"], csv_path, images_dir)
        if not image_path.exists():
            missing_images.append((row_index, image_path))

    steering = pd.to_numeric(data["steering"], errors="coerce")
    invalid_steering = int(steering.isna().sum())
    if invalid_steering:
        print(f"FAIL invalid steering values: {invalid_steering}")
        return False

    print(f"Missing center images: {len(missing_images)}")
    if missing_images:
        print("First missing images:")
        for row_index, image_path in missing_images[:5]:
            print(f"- row {row_index}: {image_path}")

    print(f"Steering min: {steering.min():.6f}")
    print(f"Steering max: {steering.max():.6f}")
    print(f"Steering mean: {steering.mean():.6f}")

    passed = len(missing_images) == 0
    print(f"{'PASS' if passed else 'FAIL'} dataset validation summary")
    return passed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a simulation driving dataset.")
    parser.add_argument("--csv", default="data/processed/simulator/driving_log.csv", help="Path to driving_log.csv.")
    parser.add_argument("--images-dir", default="data/processed/simulator/IMG", help="Directory containing images.")
    parser.add_argument("--format", default="udacity", choices=["udacity"], help="Dataset format to validate.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    success = validate_dataset(Path(args.csv), Path(args.images_dir), args.format)
    raise SystemExit(0 if success else 1)
