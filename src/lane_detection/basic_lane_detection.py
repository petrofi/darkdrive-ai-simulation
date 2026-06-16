from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


DEFAULT_OUTPUT_PATH = Path("screenshots/lane_detection_result.png")


def region_of_interest(edges: np.ndarray) -> np.ndarray:
    """Keep the lower center area where lane lines usually appear."""
    height, width = edges.shape
    polygon = np.array(
        [
            [
                (int(width * 0.1), height),
                (int(width * 0.45), int(height * 0.6)),
                (int(width * 0.55), int(height * 0.6)),
                (int(width * 0.9), height),
            ]
        ],
        dtype=np.int32,
    )

    mask = np.zeros_like(edges)
    cv2.fillPoly(mask, polygon, 255)
    return cv2.bitwise_and(edges, mask)


def detect_lanes(image_path: str | Path, output_path: str | Path = DEFAULT_OUTPUT_PATH) -> bool:
    """Run a simple OpenCV lane detection pipeline and save the result."""
    image_path = Path(image_path)
    output_path = Path(output_path)

    if not image_path.exists():
        print(f"Image not found: {image_path}")
        print("Add a simulator frame, then run this script with its image path.")
        return False

    image = cv2.imread(str(image_path))
    if image is None:
        print(f"Could not read image file: {image_path}")
        return False

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, threshold1=50, threshold2=150)
    cropped_edges = region_of_interest(edges)

    lines = cv2.HoughLinesP(
        cropped_edges,
        rho=1,
        theta=np.pi / 180,
        threshold=35,
        minLineLength=30,
        maxLineGap=20,
    )

    line_image = np.zeros_like(image)
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(line_image, (x1, y1), (x2, y2), (0, 255, 0), 4)
    else:
        print("No lane-like lines were detected in this image.")

    result = cv2.addWeighted(image, 0.8, line_image, 1.0, 0.0)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), result)
    print(f"Lane detection result saved to {output_path}")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run basic lane detection on a simulator frame.")
    parser.add_argument("image_path", help="Path to an input simulator image.")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Where to save the lane detection result image.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    detect_lanes(args.image_path, args.output)
