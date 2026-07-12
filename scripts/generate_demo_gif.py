"""Create a GitHub-friendly animated GIF from a real local MP4 recording."""

from __future__ import annotations

import argparse
import hashlib
import math
import sys
from pathlib import Path

try:
    import cv2
except ImportError as exc:  # pragma: no cover - dependency error path
    raise SystemExit("OpenCV is required: install opencv-python") from exc

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover - dependency error path
    raise SystemExit("Pillow is required") from exc


DEFAULT_MAX_BYTES = 15 * 1024 * 1024


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an optimized GIF and poster from a real MP4 segment."
    )
    parser.add_argument("input", type=Path, help="Source MP4 path; never modified.")
    parser.add_argument("output", type=Path, help="Output GIF path.")
    parser.add_argument("--poster", type=Path, default=None, help="Optional poster PNG path.")
    parser.add_argument("--start", type=float, required=True, help="Segment start in seconds.")
    parser.add_argument("--duration", type=float, required=True, help="Segment duration in seconds.")
    parser.add_argument("--fps", type=float, default=10.0, help="Output frames per second.")
    parser.add_argument("--width", type=int, default=720, help="Output width in pixels.")
    parser.add_argument("--colors", type=int, default=128, help="Global GIF palette size.")
    parser.add_argument("--crop-top", type=int, default=0)
    parser.add_argument("--crop-right", type=int, default=0)
    parser.add_argument("--crop-bottom", type=int, default=0)
    parser.add_argument("--crop-left", type=int, default=0)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    return parser.parse_args(argv)


def video_metadata(capture: cv2.VideoCapture) -> dict[str, float | int | str]:
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc_value = int(capture.get(cv2.CAP_PROP_FOURCC))
    fourcc = "".join(chr((fourcc_value >> (8 * index)) & 0xFF) for index in range(4))
    if fps <= 0 or frame_count <= 0 or width <= 0 or height <= 0:
        raise ValueError("Source video metadata is incomplete")
    return {
        "fps": fps,
        "frame_count": frame_count,
        "width": width,
        "height": height,
        "duration": frame_count / fps,
        "codec": fourcc,
    }


def validate_args(args: argparse.Namespace, metadata: dict[str, float | int | str]) -> None:
    if args.start < 0 or args.duration <= 0 or args.fps <= 0:
        raise ValueError("start must be non-negative; duration and fps must be positive")
    if args.width < 240:
        raise ValueError("width must be at least 240 pixels")
    if not 16 <= args.colors <= 256:
        raise ValueError("colors must be in [16, 256]")
    if args.start + args.duration > float(metadata["duration"]) + 0.001:
        raise ValueError("selected segment exceeds source duration")
    crop_width = int(metadata["width"]) - args.crop_left - args.crop_right
    crop_height = int(metadata["height"]) - args.crop_top - args.crop_bottom
    if min(args.crop_top, args.crop_right, args.crop_bottom, args.crop_left) < 0:
        raise ValueError("crop values must be non-negative")
    if crop_width <= 0 or crop_height <= 0:
        raise ValueError("crop removes the complete frame")
    if args.input.resolve() == args.output.resolve():
        raise ValueError("output must not overwrite the source video")
    if args.poster is not None and args.input.resolve() == args.poster.resolve():
        raise ValueError("poster must not overwrite the source video")


def transform_frame(frame: object, args: argparse.Namespace) -> Image.Image:
    height, width = frame.shape[:2]
    x0 = args.crop_left
    x1 = width - args.crop_right
    y0 = args.crop_top
    y1 = height - args.crop_bottom
    cropped = frame[y0:y1, x0:x1]
    rgb = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(rgb)
    output_height = max(1, round(image.height * args.width / image.width))
    return image.resize((args.width, output_height), Image.Resampling.LANCZOS)


def read_segment(
    capture: cv2.VideoCapture,
    args: argparse.Namespace,
) -> list[Image.Image]:
    frame_total = max(2, int(math.floor(args.duration * args.fps)))
    frames: list[Image.Image] = []
    for index in range(frame_total):
        timestamp = args.start + index / args.fps
        capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
        ok, frame = capture.read()
        if not ok:
            raise ValueError(f"Could not decode source frame at {timestamp:.3f} seconds")
        frames.append(transform_frame(frame, args))
    return frames


def build_global_palette(frames: list[Image.Image], colors: int) -> Image.Image:
    sample_width = 160
    sample_height = max(1, round(frames[0].height * sample_width / frames[0].width))
    columns = 10
    rows = math.ceil(len(frames) / columns)
    sheet = Image.new("RGB", (columns * sample_width, rows * sample_height), "black")
    for index, frame in enumerate(frames):
        sample = frame.resize((sample_width, sample_height), Image.Resampling.BILINEAR)
        sheet.paste(sample, ((index % columns) * sample_width, (index // columns) * sample_height))
    return sheet.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)


def save_gif(frames: list[Image.Image], args: argparse.Namespace) -> None:
    palette = build_global_palette(frames, args.colors)
    quantized = [
        frame.quantize(palette=palette, dither=Image.Dither.FLOYDSTEINBERG)
        for frame in frames
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame_duration_ms = max(20, round(1000 / args.fps))
    quantized[0].save(
        args.output,
        save_all=True,
        append_images=quantized[1:],
        duration=frame_duration_ms,
        loop=0,
        disposal=2,
        optimize=False,
    )


def save_poster(frames: list[Image.Image], poster_path: Path | None) -> None:
    if poster_path is None:
        return
    poster_path.parent.mkdir(parents=True, exist_ok=True)
    frames[len(frames) // 2].save(poster_path, format="PNG", optimize=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_gif(path: Path) -> tuple[int, int, int, int, int | None]:
    with Image.open(path) as image:
        frame_count = int(getattr(image, "n_frames", 1))
        duration_ms = 0
        for index in range(frame_count):
            image.seek(index)
            duration_ms += int(image.info.get("duration", 0))
        return image.width, image.height, frame_count, duration_ms, image.info.get("loop")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if not args.input.is_file():
            raise FileNotFoundError(f"Source video not found: {args.input}")
        capture = cv2.VideoCapture(str(args.input))
        if not capture.isOpened():
            raise ValueError(f"Could not open source video: {args.input}")
        try:
            metadata = video_metadata(capture)
            validate_args(args, metadata)
            frames = read_segment(capture, args)
        finally:
            capture.release()
        save_gif(frames, args)
        save_poster(frames, args.poster)
        width, height, frame_count, duration_ms, loop = inspect_gif(args.output)
        output_bytes = args.output.stat().st_size
        if output_bytes > args.max_bytes:
            raise ValueError(
                f"GIF exceeds hard maximum: {output_bytes:,} > {args.max_bytes:,} bytes"
            )
        print("Demo GIF generated successfully")
        print(
            f"- source: duration={float(metadata['duration']):.3f}s, "
            f"resolution={metadata['width']}x{metadata['height']}, "
            f"fps={float(metadata['fps']):.3f}, codec={metadata['codec']}"
        )
        print(f"- selected: {args.start:.3f}s to {args.start + args.duration:.3f}s")
        print(
            f"- GIF: {width}x{height}, frames={frame_count}, "
            f"duration={duration_ms / 1000:.3f}s, loop={loop}, bytes={output_bytes:,}"
        )
        print(f"- SHA-256: {sha256(args.output)}")
        if args.poster is not None:
            print(f"- poster: {args.poster}, bytes={args.poster.stat().st_size:,}")
        return 0
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"Demo GIF generation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
