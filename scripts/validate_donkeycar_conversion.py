from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_COLUMNS = ["image_path", "steering", "throttle", "brake", "speed", "source_dataset"]


def resolve_image_path(raw_path: object, csv_path: Path, images_dir: Path | None) -> Path:
    normalized = str(raw_path).strip().strip('"').strip("'").replace("\\", "/")
    image_path = Path(normalized)
    candidates: list[Path] = []
    if image_path.is_absolute():
        candidates.append(image_path)
    else:
        candidates.extend(
            [
                PROJECT_ROOT / image_path,
                Path.cwd() / image_path,
                csv_path.parent / image_path,
                csv_path.parent / "IMG" / image_path.name,
            ]
        )
    if images_dir is not None:
        candidates.append(images_dir / image_path.name)

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1] if candidates else image_path


def validate(csv_path: Path, images_dir: Path | None) -> bool:
    print("DonkeyCar conversion validation")
    print("Simulation-only dataset validation. No training or control loop is started.")

    if not csv_path.exists():
        print(f"FAIL CSV not found: {csv_path}")
        return False

    try:
        data = pd.read_csv(csv_path, skipinitialspace=True)
    except Exception as exc:
        print(f"FAIL could not read CSV: {exc}")
        return False

    data.columns = [str(column).strip() for column in data.columns]
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing_columns:
        print(f"FAIL missing required columns: {', '.join(missing_columns)}")
        return False

    steering = pd.to_numeric(data["steering"], errors="coerce")
    throttle = pd.to_numeric(data["throttle"], errors="coerce")
    brake = pd.to_numeric(data["brake"], errors="coerce")
    speed = pd.to_numeric(data["speed"], errors="coerce")
    invalid_steering = int(steering.isna().sum())
    invalid_controls = int(throttle.isna().sum() + brake.isna().sum() + speed.isna().sum())
    missing_source = int(data["source_dataset"].isna().sum() + (data["source_dataset"].astype(str).str.strip() == "").sum())

    found_images = 0
    missing_images = 0
    for _, row in data.iterrows():
        image_path = resolve_image_path(row["image_path"], csv_path, images_dir)
        if image_path.exists():
            found_images += 1
        else:
            missing_images += 1

    clean_steering = steering.dropna()
    total = max(len(clean_steering), 1)
    near_zero = int((clean_steering.abs() <= 0.05).sum())
    left = int((clean_steering < -0.05).sum())
    right = int((clean_steering > 0.05).sum())
    strong = int((clean_steering.abs() >= 0.5).sum())

    print(f"Total rows: {len(data)}")
    print(f"Found images: {found_images}")
    print(f"Missing images: {missing_images}")
    print(f"Invalid steering values: {invalid_steering}")
    print(f"Invalid throttle/brake/speed values: {invalid_controls}")
    print(f"Missing source_dataset values: {missing_source}")
    if len(clean_steering):
        print(f"Steering min: {clean_steering.min():.6f}")
        print(f"Steering max: {clean_steering.max():.6f}")
        print(f"Steering mean: {clean_steering.mean():.6f}")
        print(f"Steering std: {clean_steering.std():.6f}")
    print(f"Near-zero steering abs<=0.05: {near_zero} ({near_zero / total * 100:.2f}%)")
    print(f"Left steering < -0.05: {left} ({left / total * 100:.2f}%)")
    print(f"Right steering > 0.05: {right} ({right / total * 100:.2f}%)")
    print(f"Strong steering abs>=0.5: {strong} ({strong / total * 100:.2f}%)")

    print("Source dataset counts:")
    for source, count in data["source_dataset"].fillna("unknown").value_counts().sort_index().items():
        print(f"- {source}: {count}")

    passed = (
        len(data) > 0
        and missing_images == 0
        and invalid_steering == 0
        and invalid_controls == 0
        and missing_source == 0
    )
    print(f"{'PASS' if passed else 'FAIL'} DonkeyCar conversion validation summary")
    return passed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a converted DonkeyCar DarkDrive unified CSV.")
    parser.add_argument("--csv", required=True, help="Converted DonkeyCar unified CSV path.")
    parser.add_argument("--images-dir", default=None, help="Optional fallback processed image directory.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    success = validate(Path(args.csv), Path(args.images_dir) if args.images_dir else None)
    raise SystemExit(0 if success else 1)
