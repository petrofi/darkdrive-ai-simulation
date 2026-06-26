from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import cv2
import numpy as np


DEFAULT_INPUT_DIR = Path("data/samples/web_lane_images")
DEFAULT_OUTPUT_DIR = Path("screenshots/web_lane_batch")
DEFAULT_REPORT_PATH = Path("data/samples/web_lane_images/processing_report.csv")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_IMAGE_WIDTH = 960


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch process web road/lane images with the OpenCV lane detector."
    )
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_INPUT_DIR),
        help="Folder containing road/lane images.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Folder where processed result images will be saved.",
    )
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT_PATH),
        help="CSV report with status and detected line counts.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional maximum number of images to process. Use 0 for all images.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Search for images inside subfolders too.",
    )
    return parser.parse_args()


def resize_if_needed(image: np.ndarray, max_width: int = MAX_IMAGE_WIDTH) -> np.ndarray:
    height, width = image.shape[:2]
    if width <= max_width:
        return image

    scale = max_width / width
    new_size = (max_width, int(height * scale))
    return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)


def region_of_interest(edges: np.ndarray) -> np.ndarray:
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


def find_images(input_dir: Path, recursive: bool) -> list[Path]:
    pattern = "**/*" if recursive else "*"
    return sorted(
        path
        for path in input_dir.glob(pattern)
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def safe_output_name(relative_path: Path, index: int) -> str:
    stem = "_".join(relative_path.with_suffix("").parts)
    stem = re.sub(r"[^A-Za-z0-9]+", "_", stem).strip("_").lower()
    return f"{index:04d}_{stem}.png"


def process_image(image_path: Path, output_path: Path) -> dict[str, str]:
    image = cv2.imread(str(image_path))
    if image is None:
        return {
            "status": "FAIL",
            "message": "OpenCV could not read the image.",
            "line_segments": "0",
            "width": "",
            "height": "",
        }

    image = resize_if_needed(image)
    height, width = image.shape[:2]

    # This matches the beginner-friendly single-image demo pipeline.
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
    line_count = 0 if lines is None else len(lines)
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(line_image, (x1, y1), (x2, y2), (0, 255, 0), 4)

    result = cv2.addWeighted(image, 0.8, line_image, 1.0, 0.0)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    saved = cv2.imwrite(str(output_path), result)
    if not saved:
        return {
            "status": "FAIL",
            "message": "Could not save processed image.",
            "line_segments": str(line_count),
            "width": str(width),
            "height": str(height),
        }

    return {
        "status": "PASS",
        "message": "Processed successfully.",
        "line_segments": str(line_count),
        "width": str(width),
        "height": str(height),
    }


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    report_path = Path(args.report)

    print("Simulation-only lane image processing.")
    print("These web images are for OpenCV experiments, not steering model training.")

    if not input_dir.exists():
        print(f"FAIL: input folder does not exist: {input_dir}")
        return 1

    images = find_images(input_dir, args.recursive)
    if args.limit > 0:
        images = images[: args.limit]

    if not images:
        print(f"FAIL: no images found in {input_dir}")
        return 1

    print(f"Images found: {len(images)}")
    print(f"Output folder: {output_dir}")
    print(f"Report: {report_path}")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "input_path",
        "output_path",
        "status",
        "line_segments",
        "width",
        "height",
        "message",
    ]

    pass_count = 0
    fail_count = 0
    total_lines = 0

    with report_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for index, image_path in enumerate(images, start=1):
            relative_path = image_path.relative_to(input_dir)
            output_path = output_dir / safe_output_name(relative_path, index)
            result = process_image(image_path, output_path)

            if result["status"] == "PASS":
                pass_count += 1
                total_lines += int(result["line_segments"])
            else:
                fail_count += 1

            writer.writerow(
                {
                    "input_path": image_path.as_posix(),
                    "output_path": output_path.as_posix(),
                    **result,
                }
            )

            if index == 1 or index % 50 == 0 or index == len(images):
                print(
                    f"Processed {index}/{len(images)} "
                    f"(pass={pass_count}, fail={fail_count})"
                )

    print("")
    print(f"PASS images: {pass_count}")
    print(f"FAIL images: {fail_count}")
    print(f"Total detected line segments: {total_lines}")
    print(f"Report saved to: {report_path}")

    return 0 if pass_count > 0 and fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
