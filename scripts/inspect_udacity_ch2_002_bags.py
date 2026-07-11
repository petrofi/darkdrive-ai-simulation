"""Inventory Udacity CH2_002 ROS bags and assess camera/steering synchronization."""

from __future__ import annotations

import argparse
import bisect
import json
import math
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DATASET_ID = "udacity_ch2_002"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BAG_ROOT = PROJECT_ROOT / "data/external/udacity_ch2_002/extracted"
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "data/external/udacity_ch2_002/metadata/bag_inventory.json"
)
SCRIPT_VERSION = "1.0.0"
MATCH_THRESHOLD_NS = 100_000_000
MAX_STEERING_SAMPLES_PER_TOPIC = 10_000


def project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def iso_timestamp(timestamp_ns: int | None) -> str | None:
    if timestamp_ns is None:
        return None
    return datetime.fromtimestamp(timestamp_ns / 1_000_000_000, timezone.utc).isoformat()


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


def stream_metrics(timestamps: list[int]) -> dict[str, Any]:
    if not timestamps:
        return {
            "duplicate_timestamps": 0,
            "non_monotonic_timestamps": 0,
            "major_time_gaps": 0,
            "major_gap_threshold_ms": None,
            "maximum_gap_ms": None,
        }
    deltas = [later - earlier for earlier, later in zip(timestamps, timestamps[1:])]
    positive = [delta for delta in deltas if delta > 0]
    median_positive = statistics.median(positive) if positive else 0
    gap_threshold = max(1_000_000_000, median_positive * 10)
    gaps = [delta for delta in positive if delta > gap_threshold]
    return {
        "duplicate_timestamps": sum(delta == 0 for delta in deltas),
        "non_monotonic_timestamps": sum(delta < 0 for delta in deltas),
        "major_time_gaps": len(gaps),
        "major_gap_threshold_ms": gap_threshold / 1_000_000,
        "maximum_gap_ms": max(positive) / 1_000_000 if positive else None,
    }


def topic_category(topic: str, msgtype: str, msgdef: str) -> dict[str, list[str]]:
    topic_lower = topic.casefold()
    msgtype_lower = msgtype.casefold()
    msgdef_lower = msgdef.split("=" * 80, 1)[0].casefold()
    categories: dict[str, list[str]] = {}

    camera_reasons = []
    if msgtype_lower.endswith("/image") or msgtype_lower.endswith("/compressedimage"):
        camera_reasons.append(f"image message type {msgtype}")
    for token in ("image", "camera", "center", "front", "rgb"):
        if token in topic_lower:
            camera_reasons.append(f"topic contains {token!r}")
    if camera_reasons:
        categories["camera"] = camera_reasons

    steering_reasons = []
    for token in ("steering", "steer", "angle", "control"):
        if token in topic_lower:
            steering_reasons.append(f"topic contains {token!r}")
    if "steering" in msgdef_lower or "steer" in msgdef_lower:
        steering_reasons.append("message definition contains a steering field")
    if steering_reasons:
        categories["steering"] = steering_reasons

    speed_reasons = []
    for token in ("speed", "velocity", "twist"):
        if token in topic_lower or token in msgdef_lower:
            speed_reasons.append(f"topic or schema contains {token!r}")
    if speed_reasons:
        categories["speed"] = speed_reasons

    control_reasons = []
    for token in ("throttle", "accelerator", "brake", "control command"):
        if token in topic_lower or token in msgdef_lower:
            control_reasons.append(f"topic or schema contains {token!r}")
    if control_reasons:
        categories["throttle_brake"] = control_reasons
    return categories


def is_camera_payload(msgtype: str) -> bool:
    lowered = msgtype.casefold()
    return lowered.endswith("/image") or lowered.endswith("/compressedimage")


def is_plausible_steering(topic: str, msgdef: str) -> bool:
    root_definition = msgdef.split("=" * 80, 1)[0]
    lowered = f"{topic}\n{root_definition}".casefold()
    return "steering" in lowered or "steer" in lowered


def message_fields(message: Any) -> list[str]:
    fields = getattr(message, "__dataclass_fields__", {})
    return [name for name in fields if name != "__msgtype__"]


def header_stamp_ns(message: Any) -> int | None:
    header = getattr(message, "header", None)
    stamp = getattr(header, "stamp", None)
    if stamp is None:
        return None
    sec = getattr(stamp, "sec", None)
    nanosec = getattr(stamp, "nanosec", None)
    if sec is None or nanosec is None:
        return None
    return int(sec) * 1_000_000_000 + int(nanosec)


def image_sample(message: Any, bag_timestamp: int, message_index: int) -> dict[str, Any]:
    import cv2
    import numpy as np

    msgtype = str(getattr(message, "__msgtype__", ""))
    compressed = msgtype.casefold().endswith("/compressedimage")
    result: dict[str, Any] = {
        "message_index": message_index,
        "bag_timestamp_ns": bag_timestamp,
        "bag_timestamp": iso_timestamp(bag_timestamp),
        "header_timestamp_ns": header_stamp_ns(message),
        "timestamp_source": "bag record timestamp; header stamp also present"
        if header_stamp_ns(message) is not None
        else "bag record timestamp only",
        "message_type": msgtype,
        "compressed": compressed,
        "encoding": getattr(message, "format", None)
        if compressed
        else getattr(message, "encoding", None),
        "decode_succeeded": False,
        "width": None,
        "height": None,
        "channels": None,
        "error": None,
    }
    try:
        if compressed:
            decoded = cv2.imdecode(
                np.frombuffer(message.data, dtype=np.uint8), cv2.IMREAD_UNCHANGED
            )
        else:
            height = int(message.height)
            width = int(message.width)
            channels = max(1, int(message.step) // width) if width else None
            decoded = np.frombuffer(message.data, dtype=np.uint8)
            if channels:
                decoded = decoded.reshape(height, width, channels)
        if decoded is None:
            raise ValueError("OpenCV returned no decoded image")
        result["height"] = int(decoded.shape[0])
        result["width"] = int(decoded.shape[1])
        result["channels"] = int(decoded.shape[2]) if decoded.ndim == 3 else 1
        result["decode_succeeded"] = True
    except Exception as exc:  # decoding diagnostics should not abort bag inventory
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def steering_field_score(name: str) -> int:
    lowered = name.casefold()
    if lowered == "steering_wheel_angle":
        return 100
    if "steer" in lowered and "angle" in lowered and "cmd" not in lowered:
        return 90
    if "steer" in lowered and "cmd" not in lowered and "torque" not in lowered:
        return 80
    if "steer" in lowered and "cmd" in lowered:
        return 70
    return 0


def definition_line(msgdef: str, field_name: str) -> str | None:
    for line in msgdef.splitlines():
        code = line.split("#", 1)[0].strip().split()
        if len(code) >= 2 and code[1] == field_name:
            return line.strip()
    return None


def documented_unit(line: str | None) -> str | None:
    if not line or "#" not in line:
        return None
    comment = line.split("#", 1)[1].casefold()
    if "rad" in comment:
        return "radian"
    if "degree" in comment or " deg" in comment:
        return "degree"
    if "percent" in comment or "%" in comment:
        return "percent"
    return None


def numeric_fields(message: Any) -> dict[str, float]:
    result: dict[str, float] = {}
    for name in message_fields(message):
        value = getattr(message, name)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        numeric = float(value)
        if math.isfinite(numeric):
            result[name] = numeric
    return result


def summarize_steering(
    topic: str,
    msgtype: str,
    msgdef: str,
    fields: list[str],
    samples: dict[str, list[float]],
    sampled_messages: int,
) -> dict[str, Any]:
    stats: dict[str, Any] = {}
    for name, values in samples.items():
        if not values:
            continue
        stats[name] = {
            "samples": len(values),
            "minimum": min(values),
            "maximum": max(values),
            "mean": statistics.fmean(values),
            "standard_deviation": statistics.pstdev(values),
            "sign_behavior": "bidirectional"
            if min(values) < 0 < max(values)
            else "nonnegative"
            if min(values) >= 0
            else "nonpositive",
            "definition": definition_line(msgdef, name),
        }

    steering_fields = sorted(
        (name for name in stats if steering_field_score(name) > 0),
        key=lambda name: (-steering_field_score(name), name),
    )
    selected = steering_fields[0] if steering_fields else None
    selected_definition = definition_line(msgdef, selected) if selected else None
    unit = documented_unit(selected_definition)
    semantics = "unknown numeric signal"
    confidence = "low"
    evidence: list[str] = []
    if selected == "steering_wheel_angle":
        semantics = "measured steering-wheel angle"
        confidence = "high" if unit == "radian" else "medium"
        evidence.append("field name is steering_wheel_angle")
        if "steering_wheel_angle_cmd" in fields:
            evidence.append("a separate steering_wheel_angle_cmd field distinguishes command from measurement")
        if unit:
            evidence.append(f"message definition documents the field in {unit}s")
    elif selected and "cmd" in selected.casefold():
        semantics = "desired steering command"
        confidence = "medium"
        evidence.append(f"selected field name {selected!r} denotes a command")
    elif selected:
        semantics = "steering-related numeric signal"
        confidence = "medium"
        evidence.append(f"selected field name is {selected!r}")

    return {
        "topic": topic,
        "message_type": msgtype,
        "complete_field_names": fields,
        "sampled_messages": sampled_messages,
        "numeric_field_stats": stats,
        "candidate_numeric_fields": steering_fields,
        "selected_numeric_field": selected,
        "selected_field_definition": selected_definition,
        "likely_unit": unit,
        "unit_status": "documented by message definition" if unit else "unresolved",
        "scale_status": "physical unit; not normalized to simulator [-1, 1]"
        if unit
        else "unresolved; no normalization applied",
        "semantics": semantics,
        "semantics_confidence": confidence,
        "semantics_evidence": evidence,
    }


def nearest_neighbor_sync(
    camera_timestamps: list[int], steering_timestamps: list[int]
) -> tuple[dict[str, Any], list[float]]:
    camera = sorted(camera_timestamps)
    steering = sorted(steering_timestamps)
    deltas_ms: list[float] = []
    coverage_overlap = 0
    if steering:
        for timestamp in camera:
            if steering[0] <= timestamp <= steering[-1]:
                coverage_overlap += 1
            index = bisect.bisect_left(steering, timestamp)
            candidates = []
            if index < len(steering):
                candidates.append(abs(steering[index] - timestamp))
            if index:
                candidates.append(abs(steering[index - 1] - timestamp))
            if candidates:
                deltas_ms.append(min(candidates) / 1_000_000)

    matched_deltas = [delta for delta in deltas_ms if delta <= MATCH_THRESHOLD_NS / 1_000_000]
    matched = len(matched_deltas)
    total = len(camera)
    match_rate = matched / total * 100 if total else 0.0
    median_delta = statistics.median(matched_deltas) if matched_deltas else None
    p95_delta = percentile(matched_deltas, 95)
    camera_stream = stream_metrics(camera_timestamps)
    steering_stream = stream_metrics(steering_timestamps)
    if (
        total
        and match_rate >= 99.0
        and median_delta is not None
        and median_delta <= 50
        and p95_delta is not None
        and p95_delta <= 100
        and camera_stream["non_monotonic_timestamps"] == 0
        and steering_stream["non_monotonic_timestamps"] == 0
    ):
        verdict = "S1"
    elif total and match_rate >= 90.0 and median_delta is not None and median_delta <= 100:
        verdict = "S2"
    else:
        verdict = "S3"
    return (
        {
            "camera_message_count": total,
            "steering_message_count": len(steering),
            "matched_camera_frames": matched,
            "unmatched_camera_frames": total - matched,
            "match_threshold_ms": MATCH_THRESHOLD_NS / 1_000_000,
            "match_rate_pct": match_rate,
            "median_absolute_delta_ms": median_delta,
            "p90_absolute_delta_ms": percentile(matched_deltas, 90),
            "p95_absolute_delta_ms": p95_delta,
            "maximum_absolute_delta_ms": max(matched_deltas) if matched_deltas else None,
            "topic_coverage_overlap_pct": coverage_overlap / total * 100 if total else 0.0,
            "camera_stream": camera_stream,
            "steering_stream": steering_stream,
            "method": "nearest steering bag timestamp per camera bag timestamp",
            "verdict": verdict,
        },
        matched_deltas,
    )


def inspect_bag(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    from rosbags.highlevel import AnyReader

    signature = path.open("rb").read(13).decode("ascii", errors="replace")
    report: dict[str, Any] = {
        "filename": path.name,
        "path": str(path.resolve()),
        "file_size_bytes": path.stat().st_size,
        "signature": signature.rstrip("\n"),
        "bag_format": "ROS1 bag" if signature == "#ROSBAG V2.0\n" else "unsupported",
        "bag_version": "2.0" if signature == "#ROSBAG V2.0\n" else None,
        "readable": False,
        "read_errors": [],
        "skipped_messages": None,
    }
    global_sync_rows: list[dict[str, Any]] = []
    if report["bag_format"] != "ROS1 bag":
        report["read_errors"].append("File signature is not ROS1 bag V2.0")
        return report, global_sync_rows

    reader = AnyReader([path])
    try:
        reader.open()
        connections = list(reader.connections)
        report.update(
            {
                "start_timestamp_ns": reader.start_time,
                "start_timestamp": iso_timestamp(reader.start_time),
                "end_timestamp_ns": reader.end_time,
                "end_timestamp": iso_timestamp(reader.end_time),
                "duration_seconds": reader.duration / 1_000_000_000,
                "total_message_count": reader.message_count,
                "connection_count": len(connections),
            }
        )

        grouped_connections: dict[tuple[str, str], list[Any]] = defaultdict(list)
        for connection in connections:
            grouped_connections[(connection.topic, connection.msgtype)].append(connection)
        topic_states: dict[tuple[str, str], dict[str, Any]] = {}
        topic_timestamps: dict[str, list[int]] = defaultdict(list)
        camera_topics: set[str] = set()
        steering_topics: set[str] = set()
        steering_steps: dict[str, int] = {}
        for (topic, msgtype), topic_connections in grouped_connections.items():
            msgdef = topic_connections[0].msgdef.data
            count = sum(connection.msgcount for connection in topic_connections)
            categories = topic_category(topic, msgtype, msgdef)
            if is_camera_payload(msgtype):
                camera_topics.add(topic)
            if is_plausible_steering(topic, msgdef):
                steering_topics.add(topic)
                steering_steps[topic] = max(1, math.ceil(count / MAX_STEERING_SAMPLES_PER_TOPIC))
            topic_states[(topic, msgtype)] = {
                "topic": topic,
                "message_type": msgtype,
                "message_count": count,
                "connection_count": len(topic_connections),
                "first_timestamp_ns": None,
                "last_timestamp_ns": None,
                "observed_messages": 0,
                "candidate_categories": categories,
                "message_definition": msgdef,
                "camera_samples": [],
                "steering_fields": [],
                "steering_samples": defaultdict(list),
                "sampled_steering_messages": 0,
            }

        observed_total = 0
        for connection, timestamp, rawdata in reader.messages():
            state = topic_states[(connection.topic, connection.msgtype)]
            state["observed_messages"] += 1
            observed_total += 1
            if state["first_timestamp_ns"] is None:
                state["first_timestamp_ns"] = timestamp
            state["last_timestamp_ns"] = timestamp
            topic_timestamps[connection.topic].append(timestamp)

            if connection.topic in camera_topics and len(state["camera_samples"]) < 3:
                message = reader.deserialize(rawdata, connection.msgtype)
                sample = image_sample(message, timestamp, state["observed_messages"])
                state["camera_samples"].append(sample)

            if connection.topic in steering_topics:
                step = steering_steps[connection.topic]
                if (
                    (state["observed_messages"] - 1) % step == 0
                    and state["sampled_steering_messages"] < MAX_STEERING_SAMPLES_PER_TOPIC
                ):
                    message = reader.deserialize(rawdata, connection.msgtype)
                    if not state["steering_fields"]:
                        state["steering_fields"] = message_fields(message)
                    for name, value in numeric_fields(message).items():
                        state["steering_samples"][name].append(value)
                    state["sampled_steering_messages"] += 1

        topics: list[dict[str, Any]] = []
        camera_assessments: list[dict[str, Any]] = []
        steering_assessments: list[dict[str, Any]] = []
        for state in sorted(topic_states.values(), key=lambda item: (item["topic"], item["message_type"])):
            first = state["first_timestamp_ns"]
            last = state["last_timestamp_ns"]
            duration = (last - first) / 1_000_000_000 if first is not None and last is not None else 0
            frequency = (state["observed_messages"] - 1) / duration if duration > 0 else None
            topics.append(
                {
                    "topic": state["topic"],
                    "message_type": state["message_type"],
                    "message_count": state["message_count"],
                    "connection_count": state["connection_count"],
                    "approximate_frequency_hz": frequency,
                    "first_timestamp_ns": first,
                    "first_timestamp": iso_timestamp(first),
                    "last_timestamp_ns": last,
                    "last_timestamp": iso_timestamp(last),
                    "candidate_categories": state["candidate_categories"],
                }
            )
            if state["topic"] in camera_topics:
                successful = next(
                    (sample for sample in state["camera_samples"] if sample["decode_succeeded"]),
                    None,
                )
                camera_assessments.append(
                    {
                        "topic": state["topic"],
                        "message_type": state["message_type"],
                        "samples_inspected": len(state["camera_samples"]),
                        "first_readable_frame": successful,
                        "decoding_succeeds": successful is not None,
                        "sample_attempts": state["camera_samples"],
                    }
                )
            if state["topic"] in steering_topics:
                steering_assessments.append(
                    summarize_steering(
                        state["topic"],
                        state["message_type"],
                        state["message_definition"],
                        state["steering_fields"],
                        state["steering_samples"],
                        state["sampled_steering_messages"],
                    )
                )

        synchronization: list[dict[str, Any]] = []
        for camera_topic in sorted(camera_topics):
            for steering_topic in sorted(steering_topics):
                metrics, deltas = nearest_neighbor_sync(
                    topic_timestamps[camera_topic], topic_timestamps[steering_topic]
                )
                row = {
                    "bag": path.name,
                    "camera_topic": camera_topic,
                    "steering_topic": steering_topic,
                    **metrics,
                }
                synchronization.append(row)
                global_sync_rows.append({**row, "_matched_deltas_ms": deltas})

        report.update(
            {
                "readable": observed_total == reader.message_count,
                "observed_message_count": observed_total,
                "skipped_messages": reader.message_count - observed_total,
                "topics": topics,
                "camera_topic_assessments": camera_assessments,
                "steering_topic_assessments": steering_assessments,
                "timestamp_synchronization": synchronization,
            }
        )
    except Exception as exc:
        report["read_errors"].append(f"{type(exc).__name__}: {exc}")
    finally:
        reader.close()
    return report, global_sync_rows


def global_synchronization(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["camera_topic"], row["steering_topic"])].append(row)
    summaries: list[dict[str, Any]] = []
    for (camera_topic, steering_topic), group in sorted(grouped.items()):
        camera_count = sum(row["camera_message_count"] for row in group)
        steering_count = sum(row["steering_message_count"] for row in group)
        matched = sum(row["matched_camera_frames"] for row in group)
        deltas = [delta for row in group for delta in row["_matched_deltas_ms"]]
        match_rate = matched / camera_count * 100 if camera_count else 0.0
        p95 = percentile(deltas, 95)
        median = statistics.median(deltas) if deltas else None
        verdict = "S1" if match_rate >= 99 and median is not None and median <= 50 and p95 is not None and p95 <= 100 else "S2" if match_rate >= 90 and median is not None and median <= 100 else "S3"
        summaries.append(
            {
                "camera_topic": camera_topic,
                "steering_topic": steering_topic,
                "bags": len(group),
                "camera_message_count": camera_count,
                "steering_message_count_sum_across_pairs": steering_count,
                "matched_camera_frames": matched,
                "unmatched_camera_frames": camera_count - matched,
                "match_rate_pct": match_rate,
                "median_absolute_delta_ms": median,
                "p90_absolute_delta_ms": percentile(deltas, 90),
                "p95_absolute_delta_ms": p95,
                "maximum_absolute_delta_ms": max(deltas) if deltas else None,
                "method": "aggregate of per-bag nearest-neighbor matches at 100 ms threshold",
                "verdict": verdict,
            }
        )
    return summaries


def inspect_bags(bag_root: Path) -> dict[str, Any]:
    bag_paths = sorted(path for path in bag_root.rglob("*.bag") if path.is_file())
    if not bag_paths:
        raise FileNotFoundError(f"No .bag files found recursively under: {bag_root}")
    bags: list[dict[str, Any]] = []
    sync_rows: list[dict[str, Any]] = []
    for path in bag_paths:
        print(f"Inspecting {path.name}...", flush=True)
        bag, bag_sync_rows = inspect_bag(path)
        bags.append(bag)
        sync_rows.extend(bag_sync_rows)
    return {
        "dataset_id": DATASET_ID,
        "script_version": SCRIPT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bag_root": str(bag_root.resolve()),
        "bag_count": len(bags),
        "reader": "rosbags.highlevel.AnyReader",
        "synchronization_policy": {
            "method": "nearest steering bag timestamp for each camera bag timestamp",
            "match_threshold_ms": MATCH_THRESHOLD_NS / 1_000_000,
            "S1": "match >=99%, median <=50 ms, p95 <=100 ms, monotonic streams",
            "S2": "match >=90% and median <=100 ms",
            "S3": "below S2 or unresolved",
        },
        "bags": bags,
        "global_synchronization": global_synchronization(sync_rows),
    }


def write_json(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inventory Udacity CH2_002 ROS1 bags and analyze synchronization."
    )
    parser.add_argument("--bag-root", default=str(DEFAULT_BAG_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = inspect_bags(project_path(args.bag_root))
        output = project_path(args.output)
        write_json(output, report)
    except (FileNotFoundError, ValueError, OSError, ImportError) as exc:
        print(f"Udacity CH2_002 bag inspection failed: {exc}", file=sys.stderr)
        return 1

    readable = sum(bool(bag["readable"]) for bag in report["bags"])
    messages = sum(int(bag.get("total_message_count", 0)) for bag in report["bags"])
    print("Udacity CH2_002 bag inspection complete")
    print(f"- Bags readable: {readable}/{report['bag_count']}")
    print(f"- Messages indexed: {messages}")
    print(f"- Output: {output.resolve()}")
    return 0 if readable == report["bag_count"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
