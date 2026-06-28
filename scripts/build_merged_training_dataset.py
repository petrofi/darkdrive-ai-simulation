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

from src.utils.driving_log import load_driving_log, resolve_image_path


UNIFIED_COLUMNS = ["image_path", "steering", "throttle", "brake", "speed", "source_dataset"]


def local_udacity_to_unified(csv_path: Path, images_dir: Path) -> pd.DataFrame:
    data = load_driving_log(csv_path, "udacity")
    rows: list[dict[str, object]] = []
    for _, row in data.dropna(subset=["steering"]).iterrows():
        image_path = resolve_image_path(row["center"], csv_path, images_dir)
        if not image_path.exists():
            continue
        rows.append(
            {
                "image_path": str(image_path.resolve()),
                "steering": float(row["steering"]),
                "throttle": float(row["throttle"]) if pd.notna(row.get("throttle")) else 0.0,
                "brake": float(row["brake"]) if pd.notna(row.get("brake")) else 0.0,
                "speed": float(row["speed"]) if pd.notna(row.get("speed")) else 0.0,
                "source_dataset": "local_udacity_simulator",
            }
        )
    return pd.DataFrame(rows, columns=UNIFIED_COLUMNS)


def load_external_unified(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        print(f"External CSV not found: {csv_path}")
        return pd.DataFrame(columns=UNIFIED_COLUMNS)
    data = load_driving_log(csv_path, "simple")
    for column in UNIFIED_COLUMNS:
        if column not in data.columns:
            data[column] = "external_unknown" if column == "source_dataset" else 0.0
    return data[UNIFIED_COLUMNS].copy()


def print_distribution(label: str, data: pd.DataFrame) -> None:
    steering = pd.to_numeric(data["steering"], errors="coerce").dropna()
    near_zero = int((steering.abs() <= 0.05).sum())
    left = int((steering < -0.05).sum())
    right = int((steering > 0.05).sum())
    total = max(len(steering), 1)
    print(f"{label}:")
    print(f"- rows: {len(steering)}")
    print(f"- near zero abs<=0.05: {near_zero} ({near_zero / total * 100:.2f}%)")
    print(f"- left steering < -0.05: {left} ({left / total * 100:.2f}%)")
    print(f"- right steering > 0.05: {right} ({right / total * 100:.2f}%)")


def downsample_near_zero(data: pd.DataFrame, max_near_zero_ratio: float, seed: int) -> pd.DataFrame:
    steering = pd.to_numeric(data["steering"], errors="coerce")
    valid_data = data[steering.notna()].copy()
    steering = pd.to_numeric(valid_data["steering"], errors="coerce")
    near_zero = valid_data[steering.abs() <= 0.05]
    turning = valid_data[steering.abs() > 0.05]

    if len(valid_data) == 0 or len(turning) == 0:
        return valid_data

    current_ratio = len(near_zero) / len(valid_data)
    if current_ratio <= max_near_zero_ratio:
        return valid_data.sample(frac=1.0, random_state=seed).reset_index(drop=True)

    max_near_zero_count = int((max_near_zero_ratio * len(turning)) / max(1.0 - max_near_zero_ratio, 1e-8))
    max_near_zero_count = max(0, min(max_near_zero_count, len(near_zero)))
    sampled_near_zero = near_zero.sample(n=max_near_zero_count, random_state=seed)
    merged = pd.concat([turning, sampled_near_zero], ignore_index=True)
    return merged.sample(frac=1.0, random_state=seed).reset_index(drop=True)


def save_distribution(data: pd.DataFrame, output_path: Path) -> None:
    steering = pd.to_numeric(data["steering"], errors="coerce").dropna()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 5))
    plt.hist(steering, bins=40, color="#16a34a", edgecolor="white", alpha=0.9)
    plt.title("Merged Steering Distribution")
    plt.xlabel("Steering")
    plt.ylabel("Frame count")
    plt.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f"Saved plot: {output_path}")


def build(
    local_csv: Path,
    local_images_dir: Path,
    external_csv: Path,
    output_csv: Path,
    max_near_zero_ratio: float,
    seed: int,
    plot_output: Path,
) -> bool:
    local_data = local_udacity_to_unified(local_csv, local_images_dir)
    external_data = load_external_unified(external_csv)
    combined = pd.concat([local_data, external_data], ignore_index=True)

    print_distribution("Before balancing", combined)
    balanced = downsample_near_zero(combined, max_near_zero_ratio, seed)
    print_distribution("After balancing", balanced)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    balanced.to_csv(output_csv, index=False)
    save_distribution(balanced, plot_output)

    print("Merged dataset summary:")
    print(f"- Local rows used: {len(local_data)}")
    print(f"- External rows loaded: {len(external_data)}")
    print(f"- Output rows: {len(balanced)}")
    print(f"- Output CSV: {output_csv}")
    return len(balanced) > 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a balanced merged DarkDrive training dataset.")
    parser.add_argument("--local-csv", default="data/processed/simulator/driving_log.csv")
    parser.add_argument("--local-images-dir", default="data/processed/simulator/IMG")
    parser.add_argument("--external-csv", required=True)
    parser.add_argument("--output-csv", default="data/processed/merged_training/driving_log.csv")
    parser.add_argument("--max-near-zero-ratio", type=float, default=0.35)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--plot-output", default="screenshots/merged_steering_distribution.png")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    ok = build(
        Path(args.local_csv),
        Path(args.local_images_dir),
        Path(args.external_csv),
        Path(args.output_csv),
        args.max_near_zero_ratio,
        args.seed,
        Path(args.plot_output),
    )
    raise SystemExit(0 if ok else 1)

