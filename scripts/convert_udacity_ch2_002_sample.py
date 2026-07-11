"""Create a bounded, provenance-rich CH2_002 sample without steering normalization."""

from __future__ import annotations

import argparse
import bisect
import csv
import json
import math
import shutil
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATASET_ID = "udacity_ch2_002"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BAG_ROOT = PROJECT_ROOT / "data/external/udacity_ch2_002/extracted"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data/processed/external/udacity_ch2_002_sample"
CAMERA_TOPIC = "/center_camera/image_color/compressed"
STEERING_TOPIC = "/vehicle/steering_report"
STEERING_FIELD = "steering_wheel_angle"
STEERING_UNIT = "radian"
STEERING_SCALE_STATUS = "physical steering-wheel angle; not normalized"
MAX_TOTAL_FRAMES = 500
DEFAULT_FRAMES_PER_BAG = 100
MATCH_THRESHOLD_NS = 100_000_000
SCRIPT_VERSION = "1.0.0"
MANIFEST_COLUMNS = [
    "image_path",
    "image_timestamp",
    "steering_timestamp",
    "timestamp_delta_ms",
    "steering_raw",
    "steering_unit",
    "steering_scale_status",
    "source_dataset",
    "source_bag",
    "source_camera_topic",
    "source_steering_topic",
    "source_message_index",
    "is_external",
    "domain",
]


def project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def percentile(values: list[float], percent: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percent / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def evenly_spaced_indices(message_count: int, requested: int) -> list[int]:
    """Return deterministic one-based indices spanning the complete topic."""
    if message_count <= 0 or requested <= 0:
        return []
    count = min(message_count, requested)
    if count == 1:
        return [1]
    return sorted(
        {
            1 + round(position * (message_count - 1) / (count - 1))
            for position in range(count)
        }
    )


def nearest_timestamp_index(timestamps: list[int], target: int) -> int:
    if not timestamps:
        raise ValueError("Cannot match against an empty timestamp stream")
    index = bisect.bisect_left(timestamps, target)
    if index == 0:
        return 0
    if index == len(timestamps):
        return len(timestamps) - 1
    before = index - 1
    return before if target - timestamps[before] <= timestamps[index] - target else index


def _safe_output_target(output_dir: Path) -> None:
    resolved = output_dir.resolve()
    if resolved == Path(resolved.anchor) or resolved == PROJECT_ROOT.resolve():
        raise ValueError(f"Refusing unsafe sample output target: {resolved}")


def prepare_temporary_output(output_dir: Path, force: bool) -> Path:
    _safe_output_target(output_dir)
    if output_dir.exists() and not output_dir.is_dir():
        raise FileExistsError(f"Sample output target is not a directory: {output_dir}")
    if output_dir.is_dir() and next(output_dir.iterdir(), None) is not None and not force:
        raise FileExistsError(
            f"Refusing to overwrite non-empty sample output: {output_dir}. Use --force explicitly."
        )
    temporary = output_dir.with_name(f".{output_dir.name}.building")
    if temporary.exists():
        if not force or not temporary.is_dir():
            raise FileExistsError(f"Temporary sample output already exists: {temporary}")
        shutil.rmtree(temporary)
    (temporary / "IMG").mkdir(parents=True)
    return temporary


def source_connections(reader: Any, topic: str) -> list[Any]:
    return [connection for connection in reader.connections if connection.topic == topic]


def collect_steering(reader: Any, connections: list[Any]) -> tuple[list[int], list[float]]:
    timestamps: list[int] = []
    values: list[float] = []
    for connection, timestamp, rawdata in reader.messages(connections=connections):
        message = reader.deserialize(rawdata, connection.msgtype)
        value = float(getattr(message, STEERING_FIELD))
        if not math.isfinite(value):
            raise ValueError(
                f"Non-finite {STEERING_FIELD} in {connection.topic} at {timestamp}"
            )
        timestamps.append(timestamp)
        values.append(value)
    if any(later < earlier for earlier, later in zip(timestamps, timestamps[1:])):
        raise ValueError(f"Non-monotonic steering timestamps in {STEERING_TOPIC}")
    return timestamps, values


def convert_bag(
    path: Path, image_dir: Path, frames_per_bag: int
) -> list[dict[str, object]]:
    import cv2
    import numpy as np
    from rosbags.highlevel import AnyReader

    reader = AnyReader([path])
    rows: list[dict[str, object]] = []
    try:
        reader.open()
        camera_connections = source_connections(reader, CAMERA_TOPIC)
        steering_connections = source_connections(reader, STEERING_TOPIC)
        if len(camera_connections) != 1 or len(steering_connections) != 1:
            raise ValueError(
                f"Expected exactly one camera and steering connection in {path.name}; "
                f"found {len(camera_connections)} and {len(steering_connections)}"
            )
        camera_connection = camera_connections[0]
        if camera_connection.msgtype != "sensor_msgs/msg/CompressedImage":
            raise ValueError(f"Unsupported camera message type: {camera_connection.msgtype}")
        if STEERING_FIELD not in steering_connections[0].msgdef.data.split("=" * 80, 1)[0]:
            raise ValueError(f"Steering field {STEERING_FIELD!r} is not defined in the root message")

        selected_indices = set(
            evenly_spaced_indices(camera_connection.msgcount, frames_per_bag)
        )
        steering_timestamps, steering_values = collect_steering(
            reader, steering_connections
        )
        message_index = 0
        for connection, image_timestamp, rawdata in reader.messages(
            connections=camera_connections
        ):
            message_index += 1
            if message_index not in selected_indices:
                continue
            message = reader.deserialize(rawdata, connection.msgtype)
            image_bytes = bytes(message.data)
            decoded = cv2.imdecode(
                np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR
            )
            if decoded is None or decoded.shape[:2] != (480, 640):
                raise ValueError(
                    f"Camera decode failed or dimensions changed in {path.name} message {message_index}"
                )

            steering_index = nearest_timestamp_index(steering_timestamps, image_timestamp)
            steering_timestamp = steering_timestamps[steering_index]
            delta_ms = abs(steering_timestamp - image_timestamp) / 1_000_000
            if delta_ms > MATCH_THRESHOLD_NS / 1_000_000:
                raise ValueError(
                    f"Timestamp delta {delta_ms:.3f} ms exceeds threshold in {path.name}"
                )
            filename = f"{path.stem}_center_{message_index:06d}.jpg"
            image_path = image_dir / filename
            with image_path.open("xb") as handle:
                handle.write(image_bytes)
            rows.append(
                {
                    "image_path": str(Path("IMG") / filename).replace("\\", "/"),
                    "image_timestamp": image_timestamp,
                    "steering_timestamp": steering_timestamp,
                    "timestamp_delta_ms": delta_ms,
                    "steering_raw": steering_values[steering_index],
                    "steering_unit": STEERING_UNIT,
                    "steering_scale_status": STEERING_SCALE_STATUS,
                    "source_dataset": DATASET_ID,
                    "source_bag": path.name,
                    "source_camera_topic": CAMERA_TOPIC,
                    "source_steering_topic": STEERING_TOPIC,
                    "source_message_index": message_index,
                    "is_external": "true",
                    "domain": "real_world_offline_dataset",
                }
            )
        if len(rows) != len(selected_indices):
            raise OSError(
                f"Selected {len(selected_indices)} frames but exported {len(rows)} from {path.name}"
            )
    finally:
        reader.close()
    return rows


def validate_sample(output_dir: Path, rows: list[dict[str, object]]) -> dict[str, Any]:
    import cv2

    paths = [str(row["image_path"]) for row in rows]
    missing = 0
    unreadable = 0
    for relative in paths:
        path = output_dir / relative
        if not path.is_file():
            missing += 1
        elif cv2.imread(str(path), cv2.IMREAD_COLOR) is None:
            unreadable += 1
    steering = [float(row["steering_raw"]) for row in rows]
    deltas = [float(row["timestamp_delta_ms"]) for row in rows]
    invalid = sum(not math.isfinite(value) for value in steering)
    return {
        "exported_rows": len(rows),
        "readable_images": len(rows) - missing - unreadable,
        "missing_files": missing,
        "unreadable_images": unreadable,
        "duplicate_image_paths": len(paths) - len(set(paths)),
        "invalid_raw_steering_values": invalid,
        "bag_distribution": dict(sorted(Counter(str(row["source_bag"]) for row in rows).items())),
        "timestamp_delta_ms": {
            "minimum": min(deltas) if deltas else None,
            "median": statistics.median(deltas) if deltas else None,
            "p90": percentile(deltas, 90),
            "p95": percentile(deltas, 95),
            "maximum": max(deltas) if deltas else None,
        },
        "steering_raw_radian": {
            "minimum": min(steering) if steering else None,
            "maximum": max(steering) if steering else None,
            "mean": statistics.fmean(steering) if steering else None,
            "standard_deviation": statistics.pstdev(steering) if steering else None,
        },
    }


def write_manifest(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def convert_sample(
    bag_root: Path,
    output_dir: Path,
    *,
    frames_per_bag: int = DEFAULT_FRAMES_PER_BAG,
    force: bool = False,
) -> dict[str, Any]:
    bag_paths = sorted(path for path in bag_root.rglob("*.bag") if path.is_file())
    if not bag_paths:
        raise FileNotFoundError(f"No bag files found under: {bag_root}")
    requested_total = frames_per_bag * len(bag_paths)
    if frames_per_bag <= 0 or requested_total > MAX_TOTAL_FRAMES:
        raise ValueError(
            f"Requested {requested_total} frames; sample conversion limit is {MAX_TOTAL_FRAMES}"
        )

    output_dir = output_dir.resolve()
    temporary = prepare_temporary_output(output_dir, force)
    try:
        rows: list[dict[str, object]] = []
        for path in bag_paths:
            print(f"Sampling {path.name}...", flush=True)
            rows.extend(convert_bag(path, temporary / "IMG", frames_per_bag))
        if len(rows) > MAX_TOTAL_FRAMES:
            raise ValueError("Sample conversion exceeded the 500-frame hard limit")
        write_manifest(temporary / "manifest.csv", rows)
        validation = validate_sample(temporary, rows)
        if any(
            validation[key]
            for key in (
                "missing_files",
                "unreadable_images",
                "duplicate_image_paths",
                "invalid_raw_steering_values",
            )
        ):
            raise ValueError(f"Generated sample failed validation: {validation}")
        summary = {
            "dataset_id": DATASET_ID,
            "script_version": SCRIPT_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_bag_root": str(bag_root.resolve()),
            "output_dir": str(output_dir),
            "selection": "deterministic evenly spaced center-camera frames per bag",
            "frames_per_bag": frames_per_bag,
            "camera_topic": CAMERA_TOPIC,
            "steering_topic": STEERING_TOPIC,
            "steering_field": STEERING_FIELD,
            "steering_unit": STEERING_UNIT,
            "steering_scale_status": STEERING_SCALE_STATUS,
            "normalization_applied": False,
            "synchronization": "nearest steering bag timestamp; 100 ms maximum",
            "manifest_columns": MANIFEST_COLUMNS,
            "validation": validation,
            "training_authorized": False,
            "domain": "real_world_offline_dataset",
        }
        write_json(temporary / "sample_summary.json", summary)

        if output_dir.exists():
            shutil.rmtree(output_dir)
        temporary.replace(output_dir)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export at most 500 synchronized CH2_002 center-camera samples."
    )
    parser.add_argument("--bag-root", default=str(DEFAULT_BAG_ROOT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--frames-per-bag", type=int, default=DEFAULT_FRAMES_PER_BAG)
    parser.add_argument("--force", action="store_true")
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        summary = convert_sample(
            project_path(args.bag_root),
            project_path(args.output_dir),
            frames_per_bag=args.frames_per_bag,
            force=args.force,
        )
    except (FileNotFoundError, FileExistsError, ValueError, OSError, ImportError) as exc:
        print(f"Udacity CH2_002 sample conversion failed: {exc}", file=sys.stderr)
        return 1
    validation = summary["validation"]
    print("Udacity CH2_002 sample conversion complete")
    print(f"- Exported/readable images: {validation['exported_rows']}/{validation['readable_images']}")
    print(f"- Missing/unreadable/duplicates/invalid steering: {validation['missing_files']}/{validation['unreadable_images']}/{validation['duplicate_image_paths']}/{validation['invalid_raw_steering_values']}")
    print(f"- Output: {summary['output_dir']}")
    print("- Steering remains raw radians; no simulator normalization was applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
