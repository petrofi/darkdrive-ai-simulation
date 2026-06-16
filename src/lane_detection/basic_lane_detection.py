from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np


DEFAULT_IMAGE_PATH = Path("data/samples/road_sample.jpg")
DEFAULT_OUTPUT_PATH = Path("screenshots/lane_detection_result.png")
MAX_IMAGE_WIDTH = 960


def resize_if_needed(image: np.ndarray, max_width: int = MAX_IMAGE_WIDTH) -> np.ndarray:
    """Keep large images manageable while preserving the original aspect ratio."""
    height, width = image.shape[:2]
    if width <= max_width:
        return image

    scale = max_width / width
    new_size = (max_width, int(height * scale))
    return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)


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
        print(f"Error: image not found: {image_path}")
        print("Place a simulation or road sample image at data/samples/road_sample.jpg.")
        print("Then run:")
        print(
            "python src/lane_detection/basic_lane_detection.py "
            "--image data/samples/road_sample.jpg "
            "--output screenshots/lane_detection_result.png"
        )
        return False

    image = cv2.imread(str(image_path))
    if image is None:
        print(f"Error: could not read image file: {image_path}")
        return False

    image = resize_if_needed(image)

    print(f"Loaded image: {image_path}")
    print(f"Processing size: {image.shape[1]}x{image.shape[0]}")

    # Convert the frame to grayscale so edge detection focuses on intensity.
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Smooth small texture and noise before finding edges.
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Detect strong image edges that may include lane markings.
    edges = cv2.Canny(blurred, threshold1=50, threshold2=150)

    # Focus on the lower part of the frame, where lane lines usually appear.
    cropped_edges = region_of_interest(edges)

    # Detect straight line segments from the masked edge image.
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
        print(f"Detected {len(lines)} lane-like line segment(s).")
    else:
        print("No lane-like lines were detected in this image.")

    result = cv2.addWeighted(image, 0.8, line_image, 1.0, 0.0)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    saved = cv2.imwrite(str(output_path), result)
    if not saved:
        print(f"Error: failed to save output image: {output_path}")
        return False

    print(f"Success: lane detection result saved to {output_path}")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run basic lane detection on a simulator frame.")
    parser.add_argument(
        "--image",
        default=str(DEFAULT_IMAGE_PATH),
        help="Path to an input simulation or road sample image.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Where to save the lane detection result image.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    success = detect_lanes(args.image, args.output)
    sys.exit(0 if success else 1)
