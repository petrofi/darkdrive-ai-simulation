from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.driving_log import load_driving_log, resolve_image_path


UNIFIED_COLUMNS = [
    "image_path",
    "steering",
    "throttle",
    "brake",
    "speed",
    "source_dataset",
    "session_name",
]


@dataclass(frozen=True)
class SessionSpec:
    name: str
    csv_path: Path
    images_dir: Path


def parse_session(value: str) -> SessionSpec:
    parts = [part.strip() for part in value.split(",", 2)]
    if len(parts) != 3 or not all(parts):
        raise argparse.ArgumentTypeError(
            "--session must use name,path_to_csv,path_to_images_dir"
        )
    return SessionSpec(parts[0], Path(parts[1]), Path(parts[2]))


def source_name(session_name: str) -> str:
    lower = session_name.lower()
    if "v1" in lower or "baseline" in lower:
        return "local_simulator_v1"
    return "local_simulator_v2"


def convert_session(session: SessionSpec) -> pd.DataFrame:
    if not session.csv_path.exists():
        print(f"Skipping missing session CSV: {session.csv_path}")
        return pd.DataFrame(columns=UNIFIED_COLUMNS)

    data = load_driving_log(session.csv_path, "udacity")
    rows: list[dict[str, object]] = []
    skipped_missing_images = 0
    skipped_invalid_steering = 0

    for _, row in data.iterrows():
        if pd.isna(row.get("steering")):
            skipped_invalid_steering += 1
            continue

        image_path = resolve_image_path(row["center"], session.csv_path, session.images_dir)
        if not image_path.exists():
            skipped_missing_images += 1
            continue

        rows.append(
            {
                "image_path": str(image_path.resolve()),
                "steering": float(row["steering"]),
                "throttle": float(row["throttle"]) if pd.notna(row.get("throttle")) else 0.0,
                "brake": float(row["brake"]) if pd.notna(row.get("brake")) else 0.0,
                "speed": float(row["speed"]) if pd.notna(row.get("speed")) else 0.0,
                "source_dataset": source_name(session.name),
                "session_name": session.name,
            }
        )

    print(f"Session {session.name}:")
    print(f"- input rows: {len(data)}")
    print(f"- converted rows: {len(rows)}")
    print(f"- skipped missing images: {skipped_missing_images}")
    print(f"- skipped invalid steering: {skipped_invalid_steering}")
    return pd.DataFrame(rows, columns=UNIFIED_COLUMNS)


def distribution_summary(data: pd.DataFrame, label: str) -> None:
    steering = pd.to_numeric(data["steering"], errors="coerce").dropna()
    total = max(len(steering), 1)
    near_zero = int((steering.abs() <= 0.05).sum())
    left = int((steering < -0.05).sum())
    right = int((steering > 0.05).sum())
    strong = int((steering.abs() >= 0.5).sum())

    print(label)
    print(f"- rows: {len(steering)}")
    print(f"- near zero abs<=0.05: {near_zero} ({near_zero / total * 100:.2f}%)")
    print(f"- left steering < -0.05: {left} ({left / total * 100:.2f}%)")
    print(f"- right steering > 0.05: {right} ({right / total * 100:.2f}%)")
    print(f"- strong turns abs>=0.5: {strong} ({strong / total * 100:.2f}%)")
    if len(steering):
        print(f"- steering std: {steering.std():.6f}")


def downsample_near_zero(data: pd.DataFrame, max_near_zero_ratio: float, seed: int) -> pd.DataFrame:
    steering = pd.to_numeric(data["steering"], errors="coerce")
    valid_data = data[steering.notna()].copy()
    steering = pd.to_numeric(valid_data["steering"], errors="coerce")
    near_zero = valid_data[steering.abs() <= 0.05]
    turning = valid_data[steering.abs() > 0.05]

    if len(valid_data) == 0 or len(turning) == 0:
        return valid_data.reset_index(drop=True)

    current_ratio = len(near_zero) / len(valid_data)
    if current_ratio <= max_near_zero_ratio:
        return valid_data.sample(frac=1.0, random_state=seed).reset_index(drop=True)

    max_near_zero_count = int((max_near_zero_ratio * len(turning)) / (1.0 - max_near_zero_ratio))
    max_near_zero_count = min(max_near_zero_count, len(near_zero))
    sampled_near_zero = near_zero.sample(n=max_near_zero_count, random_state=seed)
    balanced = pd.concat([turning, sampled_near_zero], ignore_index=True)
    return balanced.sample(frac=1.0, random_state=seed).reset_index(drop=True)


def save_distribution(data: pd.DataFrame) -> Path:
    output_path = Path("screenshots/local_v2_merged_steering_distribution.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    steering = pd.to_numeric(data["steering"], errors="coerce").dropna()

    plt.figure(figsize=(8, 5))
    plt.hist(steering, bins=40, color="#16a34a", edgecolor="white", alpha=0.9)
    plt.title("Local V2 Merged Steering Distribution")
    plt.xlabel("Steering")
    plt.ylabel("Frame count")
    plt.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    return output_path


def build(sessions: list[SessionSpec], output_csv: Path, max_near_zero_ratio: float, seed: int) -> bool:
    if not sessions:
        print("No sessions provided. Use --session name,path_to_csv,path_to_images_dir.")
        return False

    frames = [convert_session(session) for session in sessions]
    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=UNIFIED_COLUMNS)
    if combined.empty:
        print("No rows converted from provided sessions.")
        return False

    distribution_summary(combined, "Before balancing:")
    balanced = downsample_near_zero(combined, max_near_zero_ratio, seed)
    distribution_summary(balanced, "After balancing:")

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    balanced.to_csv(output_csv, index=False)
    output_plot = save_distribution(balanced)

    print("Local Dataset v2 training dataset summary:")
    print(f"- sessions merged: {len(sessions)}")
    print(f"- output rows: {len(balanced)}")
    print(f"- output CSV: {output_csv}")
    print(f"- saved plot: {output_plot}")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build local Dataset v2 training CSV.")
    parser.add_argument(
        "--output-csv",
        default="data/processed/local_v2_training/driving_log.csv",
        help="Unified output CSV path.",
    )
    parser.add_argument("--max-near-zero-ratio", type=float, default=0.35)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--session",
        action="append",
        type=parse_session,
        default=[],
        help="Session spec: name,path_to_csv,path_to_images_dir. Repeat for multiple sessions.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    ok = build(args.session, Path(args.output_csv), args.max_near_zero_ratio, args.seed)
    raise SystemExit(0 if ok else 1)

