from __future__ import annotations

import argparse
import re
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


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip()).strip("_") or "session"


def save_distribution(steering: pd.Series, session_name: str) -> Path:
    output_path = Path("screenshots") / f"{safe_name(session_name)}_steering_distribution.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(8, 5))
    plt.hist(steering, bins=40, color="#2563eb", edgecolor="white", alpha=0.9)
    plt.title(f"{session_name} Steering Distribution")
    plt.xlabel("Steering")
    plt.ylabel("Frame count")
    plt.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    return output_path


def analyze_session(csv_path: Path, images_dir: Path, dataset_format: str, session_name: str) -> bool:
    print("DarkDrive session dataset report")
    print("Simulation-only dataset analysis. No simulator control is used.")
    print(f"Session name: {session_name}")

    if not csv_path.exists():
        print(f"FAIL CSV not found: {csv_path}")
        return False

    try:
        data = load_driving_log(csv_path, dataset_format)
    except Exception as exc:
        print(f"FAIL could not read CSV: {exc}")
        return False

    if "steering" not in data.columns:
        print("FAIL CSV is missing steering column.")
        return False

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
    strong_turn = int((steering.abs() >= 0.5).sum())

    print(f"Total rows: {len(data)}")
    print(f"Image count: {found_images}")
    print(f"Missing image count: {missing_images}")
    if len(steering):
        print(f"Steering min: {steering.min():.6f}")
        print(f"Steering max: {steering.max():.6f}")
        print(f"Steering mean: {steering.mean():.6f}")
        print(f"Steering std: {steering.std():.6f}")
    print(f"Near-zero percentage abs<=0.05: {near_zero / total * 100:.2f}%")
    print(f"Left steering percentage < -0.05: {left / total * 100:.2f}%")
    print(f"Right steering percentage > 0.05: {right / total * 100:.2f}%")
    print(f"Strong turn percentage abs>=0.5: {strong_turn / total * 100:.2f}%")

    if len(steering):
        output_path = save_distribution(steering, session_name)
        print(f"Saved plot: {output_path}")

    passed = len(data) > 0 and missing_images == 0 and len(steering) > 0
    print(f"{'PASS' if passed else 'FAIL'} session dataset report")
    return passed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze one simulator recording session.")
    parser.add_argument("--csv", required=True, help="Session driving_log.csv path.")
    parser.add_argument("--images-dir", required=True, help="Session IMG directory.")
    parser.add_argument("--format", default="udacity", choices=["udacity", "simple"])
    parser.add_argument("--session-name", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    ok = analyze_session(Path(args.csv), Path(args.images_dir), args.format, args.session_name)
    raise SystemExit(0 if ok else 1)

