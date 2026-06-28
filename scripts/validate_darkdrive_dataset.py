from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.driving_log import load_driving_log, resolve_image_path


REQUIRED_COLUMNS = ["image_path", "steering", "throttle", "brake", "speed", "source_dataset"]
BUCKETS = [
    (-1.0, -0.75, "[-1.0, -0.75)"),
    (-0.75, -0.5, "[-0.75, -0.5)"),
    (-0.5, -0.25, "[-0.5, -0.25)"),
    (-0.25, -0.05, "[-0.25, -0.05)"),
    (-0.05, 0.05, "[-0.05, 0.05]"),
    (0.05, 0.25, "(0.05, 0.25]"),
    (0.25, 0.5, "(0.25, 0.5]"),
    (0.5, 0.75, "(0.5, 0.75]"),
    (0.75, 1.0, "(0.75, 1.0]"),
]


def bucket_count(values: pd.Series, lower: float, upper: float, label: str) -> int:
    if label.startswith("[") and label.endswith("]"):
        return int(((values >= lower) & (values <= upper)).sum())
    if label.startswith("["):
        return int(((values >= lower) & (values < upper)).sum())
    return int(((values > lower) & (values <= upper)).sum())


def validate(csv_path: Path, images_dir: Path | None) -> bool:
    print("DarkDrive unified dataset validation")
    print("Simulation-only dataset check. No real vehicle control is used.")

    if not csv_path.exists():
        print(f"FAIL CSV not found: {csv_path}")
        return False

    try:
        data = load_driving_log(csv_path, "simple")
    except Exception as exc:
        print(f"FAIL could not read CSV: {exc}")
        return False

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing_columns:
        print(f"FAIL missing required columns: {', '.join(missing_columns)}")
        return False

    steering = pd.to_numeric(data["steering"], errors="coerce")
    invalid_steering = int(steering.isna().sum())

    found_images = 0
    missing_images = 0
    for _, row in data.iterrows():
        image_path = resolve_image_path(row["image_path"], csv_path, images_dir)
        if image_path.exists():
            found_images += 1
        else:
            missing_images += 1

    clean_steering = steering.dropna()
    near_zero_count = int((clean_steering.abs() <= 0.05).sum())
    near_zero_pct = near_zero_count / max(len(clean_steering), 1) * 100

    print(f"Total rows: {len(data)}")
    print(f"Found images: {found_images}")
    print(f"Missing images: {missing_images}")
    print(f"Invalid steering values: {invalid_steering}")

    if len(clean_steering):
        print(f"Steering min: {clean_steering.min():.6f}")
        print(f"Steering max: {clean_steering.max():.6f}")
        print(f"Steering mean: {clean_steering.mean():.6f}")
        print(f"Steering std: {clean_steering.std():.6f}")
        print(f"Near-zero steering abs<=0.05: {near_zero_count} ({near_zero_pct:.2f}%)")

    print("Steering histogram buckets:")
    for lower, upper, label in BUCKETS:
        count = bucket_count(clean_steering, lower, upper, label)
        percent = count / max(len(clean_steering), 1) * 100
        print(f"- {label}: {count} ({percent:.2f}%)")

    print("Source dataset counts:")
    for source, count in data["source_dataset"].fillna("unknown").value_counts().sort_index().items():
        print(f"- {source}: {count}")

    passed = missing_images == 0 and invalid_steering == 0 and len(data) > 0
    print(f"{'PASS' if passed else 'FAIL'} unified dataset validation summary")
    return passed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate DarkDrive unified simple-format datasets.")
    parser.add_argument("--csv", required=True, help="Unified driving_log.csv path.")
    parser.add_argument("--images-dir", default=None, help="Optional fallback image directory.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    success = validate(Path(args.csv), Path(args.images_dir) if args.images_dir else None)
    raise SystemExit(0 if success else 1)

