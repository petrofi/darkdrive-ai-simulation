from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.driving_log import load_driving_log, primary_image_column, resolve_image_path


def load_stats(csv_path: Path, images_dir: Path, dataset_format: str, name: str) -> dict[str, object]:
    data = load_driving_log(csv_path, dataset_format)
    path_column = primary_image_column(dataset_format)

    found_images = 0
    missing_images = 0
    for _, row in data.iterrows():
        image_path = resolve_image_path(row[path_column], csv_path, images_dir)
        if image_path.exists():
            found_images += 1
        else:
            missing_images += 1

    steering = pd.to_numeric(data["steering"], errors="coerce").dropna()
    total = max(len(steering), 1)
    near_zero = int((steering.abs() <= 0.05).sum())
    left = int((steering < -0.05).sum())
    right = int((steering > 0.05).sum())

    return {
        "name": name,
        "rows": len(data),
        "found_images": found_images,
        "missing_images": missing_images,
        "steering": steering,
        "near_zero_pct": near_zero / total * 100,
        "left_pct": left / total * 100,
        "right_pct": right / total * 100,
        "std": float(steering.std()) if len(steering) else 0.0,
    }


def save_comparison_plot(stats_a: dict[str, object], stats_b: dict[str, object]) -> Path:
    output_path = Path("screenshots/dataset_v1_vs_v2_steering.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    steering_a = stats_a["steering"]
    steering_b = stats_b["steering"]
    assert isinstance(steering_a, pd.Series)
    assert isinstance(steering_b, pd.Series)

    plt.figure(figsize=(9, 5))
    plt.hist(steering_a, bins=40, alpha=0.55, label=str(stats_a["name"]), color="#2563eb")
    plt.hist(steering_b, bins=40, alpha=0.55, label=str(stats_b["name"]), color="#16a34a")
    plt.title("Dataset Steering Distribution Comparison")
    plt.xlabel("Steering")
    plt.ylabel("Frame count")
    plt.legend()
    plt.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    return output_path


def print_stats(stats: dict[str, object]) -> None:
    print(f"{stats['name']}:")
    print(f"- row count: {stats['rows']}")
    print(f"- found images: {stats['found_images']}")
    print(f"- missing images: {stats['missing_images']}")
    print(f"- near-zero percentage abs<=0.05: {stats['near_zero_pct']:.2f}%")
    print(f"- steering std: {stats['std']:.6f}")
    print(f"- left steering percentage < -0.05: {stats['left_pct']:.2f}%")
    print(f"- right steering percentage > 0.05: {stats['right_pct']:.2f}%")


def compare(args: argparse.Namespace) -> bool:
    print("DarkDrive dataset comparison")
    print("Simulation-only dataset analysis. No simulator control is used.")

    stats_a = load_stats(Path(args.csv_a), Path(args.images_dir_a), args.format_a, args.name_a)
    stats_b = load_stats(Path(args.csv_b), Path(args.images_dir_b), args.format_b, args.name_b)

    print_stats(stats_a)
    print_stats(stats_b)

    print("Comparison:")
    print(f"- near-zero change: {stats_a['near_zero_pct']:.2f}% -> {stats_b['near_zero_pct']:.2f}%")
    print(f"- steering std change: {stats_a['std']:.6f} -> {stats_b['std']:.6f}")
    print(f"- left balance change: {stats_a['left_pct']:.2f}% -> {stats_b['left_pct']:.2f}%")
    print(f"- right balance change: {stats_a['right_pct']:.2f}% -> {stats_b['right_pct']:.2f}%")

    output_path = save_comparison_plot(stats_a, stats_b)
    print(f"Saved comparison plot: {output_path}")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare two DarkDrive simulator datasets.")
    parser.add_argument("--csv-a", required=True)
    parser.add_argument("--images-dir-a", required=True)
    parser.add_argument("--name-a", required=True)
    parser.add_argument("--csv-b", required=True)
    parser.add_argument("--images-dir-b", required=True)
    parser.add_argument("--name-b", required=True)
    parser.add_argument("--format-a", default="udacity", choices=["udacity", "simple"])
    parser.add_argument("--format-b", default="udacity", choices=["udacity", "simple"])
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(0 if compare(parse_args()) else 1)

