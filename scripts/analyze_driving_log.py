from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.driving_log import image_columns, load_driving_log, resolve_image_path


def save_distribution(values: pd.Series, title: str, xlabel: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    clean_values = pd.to_numeric(values, errors="coerce").dropna()
    plt.figure(figsize=(8, 5))
    plt.hist(clean_values, bins=40, color="#2563eb", edgecolor="white", alpha=0.9)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel("Frame count")
    plt.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f"Saved plot: {output_path}")


def save_sample_grid(
    data: pd.DataFrame,
    csv_path: Path,
    images_dir: Path,
    output_path: Path,
    max_images: int = 12,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if len(data) == 0:
        print("No rows available for sample frame grid.")
        return

    sample_count = min(max_images, len(data))
    sample_indices = np.linspace(0, len(data) - 1, sample_count, dtype=int)
    sample_rows = data.iloc[sample_indices]

    columns = 4
    rows = (sample_count + columns - 1) // columns
    plt.figure(figsize=(12, rows * 3))

    for plot_index, (_, row) in enumerate(sample_rows.iterrows(), start=1):
        image_path = resolve_image_path(row["center"], csv_path, images_dir)
        image = cv2.imread(str(image_path))
        if image is None:
            continue

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        plt.subplot(rows, columns, plot_index)
        plt.imshow(image)
        plt.axis("off")
        steering = row.get("steering", float("nan"))
        speed = row.get("speed", float("nan"))
        plt.title(f"steer={steering:.3f} speed={speed:.2f}", fontsize=9)

    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f"Saved sample frame grid: {output_path}")


def print_stats(data: pd.DataFrame, column: str) -> None:
    if column not in data.columns:
        return

    values = pd.to_numeric(data[column], errors="coerce").dropna()
    if len(values) == 0:
        print(f"{column}: no numeric values")
        return

    print(f"{column} min: {values.min():.6f}")
    print(f"{column} max: {values.max():.6f}")
    print(f"{column} mean: {values.mean():.6f}")
    print(f"{column} std: {values.std():.6f}")


def analyze(csv_path: Path, images_dir: Path, dataset_format: str) -> bool:
    print("DarkDrive simulator driving log analysis")
    print("Simulation-only dataset analysis. No real vehicle control is used.")

    if not csv_path.exists():
        print(f"FAIL CSV not found: {csv_path}")
        return False

    if not images_dir.exists():
        print(f"FAIL images directory not found: {images_dir}")
        return False

    try:
        data = load_driving_log(csv_path, dataset_format)
    except Exception as exc:
        print(f"FAIL could not read CSV: {exc}")
        return False

    print(f"CSV path: {csv_path}")
    print(f"Images directory: {images_dir}")
    print(f"Dataset format: {dataset_format}")
    print(f"CSV columns: {', '.join(data.columns)}")
    print(f"Total rows: {len(data)}")

    print("First 5 rows:")
    print(data.head(5).to_string(index=False))

    for column in image_columns(dataset_format):
        existing = 0
        missing = 0
        for _, row in data.iterrows():
            image_path = resolve_image_path(row[column], csv_path, images_dir)
            if image_path.exists():
                existing += 1
            else:
                missing += 1
        print(f"{column} images existing: {existing}")
        print(f"{column} images missing: {missing}")

    for column in ["steering", "throttle", "brake", "speed"]:
        print_stats(data, column)

    if "steering" in data.columns:
        save_distribution(
            data["steering"],
            "Steering Distribution",
            "Steering angle",
            Path("screenshots/steering_distribution.png"),
        )

    if "speed" in data.columns:
        save_distribution(
            data["speed"],
            "Speed Distribution",
            "Speed",
            Path("screenshots/speed_distribution.png"),
        )

    if dataset_format == "udacity" and "center" in data.columns:
        save_sample_grid(
            data,
            csv_path,
            images_dir,
            Path("screenshots/simulator_sample_frames.png"),
        )

    print("PASS driving log analysis complete")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze a simulator driving log.")
    parser.add_argument("--csv", default="data/processed/simulator/driving_log.csv")
    parser.add_argument("--images-dir", default="data/processed/simulator/IMG")
    parser.add_argument("--format", default="udacity", choices=["simple", "udacity"])
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    success = analyze(Path(args.csv), Path(args.images_dir), args.format)
    raise SystemExit(0 if success else 1)
