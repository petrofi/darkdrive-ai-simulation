from __future__ import annotations

import argparse
import csv
from pathlib import Path

import cv2
import numpy as np


DEFAULT_OUTPUT_DIR = Path("data/processed/synthetic_steering")
DEFAULT_IMAGE_WIDTH = 320
DEFAULT_IMAGE_HEIGHT = 160
DEFAULT_SAMPLES = 1000
RANDOM_SEED = 42


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a simulation-only synthetic steering dataset."
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Folder where IMG/ and driving_log.csv will be generated.",
    )
    parser.add_argument("--samples", type=int, default=DEFAULT_SAMPLES, help="Number of frames to generate.")
    parser.add_argument("--width", type=int, default=DEFAULT_IMAGE_WIDTH, help="Generated image width.")
    parser.add_argument("--height", type=int, default=DEFAULT_IMAGE_HEIGHT, help="Generated image height.")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED, help="Random seed.")
    return parser.parse_args()


def draw_polyline(image: np.ndarray, points: list[tuple[int, int]], color: tuple[int, int, int]) -> None:
    cv2.polylines(image, [np.array(points, dtype=np.int32)], isClosed=False, color=color, thickness=5)


def make_road_frame(
    index: int,
    width: int,
    height: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, float, float]:
    """Generate a toy road frame and matching steering label.

    The steering label comes from the synthetic lane center offset and curve.
    This makes the dataset useful for testing the behavior cloning pipeline,
    while staying entirely simulation-only.
    """
    sky_color = rng.integers([90, 120, 150], [150, 180, 220], dtype=np.uint8)
    grass_color = rng.integers([25, 90, 35], [65, 150, 80], dtype=np.uint8)
    road_color = rng.integers([35, 35, 35], [75, 75, 75], dtype=np.uint8)

    frame = np.zeros((height, width, 3), dtype=np.uint8)
    horizon_y = int(height * rng.uniform(0.42, 0.52))
    frame[:horizon_y, :] = sky_color
    frame[horizon_y:, :] = grass_color

    offset = rng.uniform(-0.55, 0.55)
    curve = rng.uniform(-0.65, 0.65)
    lane_width_bottom = width * rng.uniform(0.52, 0.66)
    lane_width_top = width * rng.uniform(0.12, 0.2)
    bottom_center = width * 0.5 + offset * width * 0.28
    top_center = width * 0.5 - curve * width * 0.12

    y_values = np.linspace(horizon_y, height - 1, 18)
    left_points: list[tuple[int, int]] = []
    right_points: list[tuple[int, int]] = []
    center_points: list[tuple[int, int]] = []

    for y in y_values:
        t = (y - horizon_y) / max(height - horizon_y, 1)
        lane_center = (1 - t) * top_center + t * bottom_center + curve * width * 0.18 * (t**2)
        lane_width = (1 - t) * lane_width_top + t * lane_width_bottom
        left_points.append((int(lane_center - lane_width / 2), int(y)))
        right_points.append((int(lane_center + lane_width / 2), int(y)))
        center_points.append((int(lane_center), int(y)))

    road_polygon = np.array([left_points[0], *left_points[1:], *reversed(right_points)], dtype=np.int32)
    cv2.fillPoly(frame, [road_polygon], tuple(int(value) for value in road_color))

    draw_polyline(frame, left_points, (230, 230, 230))
    draw_polyline(frame, right_points, (245, 245, 245))

    if rng.random() < 0.8:
        dashed_color = (200, 210, 40) if rng.random() < 0.35 else (230, 230, 230)
        for start in range(0, len(center_points) - 1, 3):
            segment = center_points[start : start + 2]
            if len(segment) == 2:
                draw_polyline(frame, segment, dashed_color)

    # Add mild camera noise and shadows so the model sees more than one perfect template.
    if rng.random() < 0.45:
        shadow_x = int(rng.uniform(0.1, 0.9) * width)
        shadow_width = int(rng.uniform(0.12, 0.3) * width)
        overlay = frame.copy()
        cv2.rectangle(
            overlay,
            (max(0, shadow_x - shadow_width), horizon_y),
            (min(width, shadow_x + shadow_width), height),
            (20, 20, 20),
            thickness=-1,
        )
        frame = cv2.addWeighted(overlay, rng.uniform(0.18, 0.32), frame, 0.75, 0)

    noise = rng.normal(0, 5, frame.shape).astype(np.int16)
    frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    steering = float(np.clip(offset * 0.75 + curve * 0.35, -1.0, 1.0))
    speed = float(rng.uniform(8.0, 18.0))

    label_text = f"synthetic sim frame {index:04d}"
    cv2.putText(frame, label_text, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (230, 230, 230), 1)
    return frame, steering, speed


def create_dataset(output_dir: Path, samples: int, width: int, height: int, seed: int) -> None:
    rng = np.random.default_rng(seed)
    images_dir = output_dir / "IMG"
    images_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "driving_log.csv"

    print("Simulation-only synthetic steering dataset generator.")
    print(f"Output folder: {output_dir}")
    print(f"Samples: {samples}")

    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["image_path", "steering", "throttle", "brake", "speed"],
        )
        writer.writeheader()

        for index in range(1, samples + 1):
            frame, steering, speed = make_road_frame(index, width, height, rng)
            image_path = images_dir / f"synthetic_{index:05d}.jpg"
            cv2.imwrite(str(image_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            writer.writerow(
                {
                    "image_path": image_path.as_posix(),
                    "steering": f"{steering:.5f}",
                    "throttle": "0.30",
                    "brake": "0.00",
                    "speed": f"{speed:.2f}",
                }
            )

            if index == 1 or index % 100 == 0 or index == samples:
                print(f"Generated {index}/{samples}")

    print(f"PASS: synthetic driving log saved to {csv_path}")
    print("Use this only for pipeline development. Real learning needs simulator driving data.")


def main() -> int:
    args = parse_args()
    create_dataset(Path(args.output_dir), args.samples, args.width, args.height, args.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
