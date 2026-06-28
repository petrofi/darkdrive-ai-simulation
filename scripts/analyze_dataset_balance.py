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

from src.utils.driving_log import load_driving_log


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


def bucket_mask(values: pd.Series, lower: float, upper: float, label: str) -> pd.Series:
    if label.startswith("[") and label.endswith("]"):
        return (values >= lower) & (values <= upper)
    if label.startswith("["):
        return (values >= lower) & (values < upper)
    return (values > lower) & (values <= upper)


def save_distribution(values: pd.Series, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 5))
    plt.hist(values, bins=40, color="#2563eb", edgecolor="white", alpha=0.9)
    plt.title("External Steering Distribution")
    plt.xlabel("Steering")
    plt.ylabel("Frame count")
    plt.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f"Saved plot: {output_path}")


def analyze(csv_path: Path, output_path: Path) -> bool:
    print("DarkDrive dataset balance analysis")
    data = load_driving_log(csv_path, "simple")
    if "steering" not in data.columns:
        print("FAIL CSV is missing steering column.")
        return False

    steering = pd.to_numeric(data["steering"], errors="coerce").dropna()
    if steering.empty:
        print("FAIL no numeric steering values found.")
        return False

    print(f"Rows analyzed: {len(steering)}")
    print(f"Steering min/max/mean/std: {steering.min():.6f} / {steering.max():.6f} / {steering.mean():.6f} / {steering.std():.6f}")

    counts: dict[str, int] = {}
    print("Steering buckets:")
    for lower, upper, label in BUCKETS:
        count = int(bucket_mask(steering, lower, upper, label).sum())
        counts[label] = count
        print(f"- {label}: {count} ({count / len(steering) * 100:.2f}%)")

    save_distribution(steering, output_path)

    near_zero_ratio = counts["[-0.05, 0.05]"] / len(steering)
    left_ratio = int((steering < -0.05).sum()) / len(steering)
    right_ratio = int((steering > 0.05).sum()) / len(steering)

    print("Recommendations:")
    made_recommendation = False
    if near_zero_ratio > 0.45:
        print("- too much straight driving")
        made_recommendation = True
    if left_ratio < 0.20:
        print("- more left turn data needed")
        made_recommendation = True
    if right_ratio < 0.20:
        print("- more right turn data needed")
        made_recommendation = True
    if not made_recommendation:
        print("- dataset acceptable")

    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze steering balance for DarkDrive datasets.")
    parser.add_argument("--csv", required=True, help="Unified simple-format driving log.")
    parser.add_argument(
        "--output",
        default="screenshots/external_steering_distribution.png",
        help="Output histogram path.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(0 if analyze(Path(args.csv), Path(args.output)) else 1)

