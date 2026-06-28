from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UNIFIED_COLUMNS = ["image_path", "steering", "throttle", "brake", "speed", "source_dataset"]
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}
IMAGE_KEYS = [
    "cam/image_array",
    "cam/image",
    "image",
    "image_path",
    "img",
    "camera/image",
    "camera/image_array",
]
STEERING_KEYS = [
    "user/angle",
    "user/steering",
    "pilot/angle",
    "angle",
    "steering",
]
THROTTLE_KEYS = ["user/throttle", "pilot/throttle", "throttle"]
SPEED_KEYS = ["speed", "vehicle/speed", "encoder/speed", "car/speed"]


def flatten_dict(value: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for raw_key, raw_value in value.items():
        key = str(raw_key)
        full_key = f"{prefix}/{key}" if prefix else key
        flattened[full_key] = raw_value
        if isinstance(raw_value, dict):
            flattened.update(flatten_dict(raw_value, full_key))
    return flattened


def scalar_value(value: Any) -> Any:
    if isinstance(value, dict):
        for key in ("value", "path", "filename", "file", "name"):
            if key in value:
                return scalar_value(value[key])
        return None
    if isinstance(value, list) and len(value) == 1:
        return scalar_value(value[0])
    return value


def first_value(record: dict[str, Any], keys: Iterable[str]) -> Any:
    flattened = flatten_dict(record)
    lower_lookup = {key.lower(): key for key in flattened}
    for key in keys:
        actual_key = lower_lookup.get(key.lower())
        if actual_key is None:
            continue
        value = scalar_value(flattened[actual_key])
        if value not in (None, ""):
            return value
    return None


def to_float(value: Any, default: float | None = None) -> float | None:
    value = scalar_value(value)
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def discover_images(input_dir: Path) -> tuple[list[Path], dict[str, Path]]:
    images = sorted(
        path
        for path in input_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )
    index: dict[str, Path] = {}
    for image in images:
        keys = {image.name.lower()}
        try:
            keys.add(image.relative_to(input_dir).as_posix().lower())
        except ValueError:
            pass
        for key in keys:
            index.setdefault(key, image)
    return images, index


def load_manifest_inputs(input_dir: Path) -> list[str]:
    inputs: list[str] = []
    for path in sorted(path for path in input_dir.rglob("*manifest*") if path.is_file()):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        candidate_inputs = data.get("inputs") or data.get("columns") or data.get("keys")
        if isinstance(candidate_inputs, list):
            inputs = [str(item) for item in candidate_inputs]
            break
    return inputs


def as_record(value: Any, manifest_inputs: list[str]) -> dict[str, Any] | None:
    if isinstance(value, dict):
        if "values" in value and isinstance(value["values"], list) and manifest_inputs:
            return dict(zip(manifest_inputs, value["values"]))
        if manifest_inputs and all(str(index) in value for index in range(min(len(manifest_inputs), len(value)))):
            return {name: value.get(str(index)) for index, name in enumerate(manifest_inputs)}
        return value
    if isinstance(value, list) and manifest_inputs:
        return dict(zip(manifest_inputs, value))
    return None


def iter_json_records(input_dir: Path, manifest_inputs: list[str]) -> Iterable[tuple[Path, dict[str, Any]]]:
    for path in sorted(input_dir.rglob("*.json")):
        if "manifest" in path.name.lower():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue

        if isinstance(data, list):
            for item in data:
                record = as_record(item, manifest_inputs)
                if record is not None:
                    yield path, record
            continue

        record = as_record(data, manifest_inputs)
        if record is not None:
            yield path, record


def iter_catalog_records(input_dir: Path, manifest_inputs: list[str]) -> Iterable[tuple[Path, dict[str, Any]]]:
    catalog_paths = sorted(
        path
        for path in input_dir.rglob("*catalog*")
        if path.is_file() and "manifest" not in path.name.lower()
    )
    for path in catalog_paths:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                data = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            record = as_record(data, manifest_inputs)
            if record is not None:
                yield path, record


def resolve_image_path(raw_value: Any, source_file: Path, input_dir: Path, image_index: dict[str, Path]) -> Path | None:
    value = scalar_value(raw_value)
    if value in (None, ""):
        return None

    normalized = str(value).strip().strip('"').strip("'").replace("\\", "/")
    raw_path = Path(normalized)
    candidates = []
    if raw_path.is_absolute():
        candidates.append(raw_path)
    else:
        candidates.extend(
            [
                source_file.parent / raw_path,
                input_dir / raw_path,
                input_dir / "images" / raw_path.name,
                input_dir / "IMG" / raw_path.name,
            ]
        )

    for candidate in candidates:
        if candidate.exists():
            return candidate

    indexed = image_index.get(normalized.lower()) or image_index.get(raw_path.name.lower())
    if indexed and indexed.exists():
        return indexed
    return None


def project_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(resolved)


def output_image_path(source_path: Path, images_output: Path | None, row_index: int) -> Path:
    if images_output is None:
        return source_path.resolve()

    images_output.mkdir(parents=True, exist_ok=True)
    extension = source_path.suffix.lower() or ".jpg"
    destination = images_output / f"frame_{row_index:06d}{extension}"
    if source_path.resolve() != destination.resolve():
        shutil.copy2(source_path, destination)
    return destination.resolve()


def steering_stats(rows: list[dict[str, object]]) -> pd.Series:
    return pd.to_numeric(pd.Series([row["steering"] for row in rows]), errors="coerce").dropna()


def print_distribution(rows: list[dict[str, object]]) -> None:
    steering = steering_stats(rows)
    total = max(len(steering), 1)
    near_zero = int((steering.abs() <= 0.05).sum())
    left = int((steering < -0.05).sum())
    right = int((steering > 0.05).sum())

    if len(steering):
        print(f"- Steering min: {steering.min():.6f}")
        print(f"- Steering max: {steering.max():.6f}")
        print(f"- Steering mean: {steering.mean():.6f}")
        print(f"- Steering std: {steering.std():.6f}")
    print(f"- Near-zero steering abs<=0.05: {near_zero} ({near_zero / total * 100:.2f}%)")
    print(f"- Left steering < -0.05: {left} ({left / total * 100:.2f}%)")
    print(f"- Right steering > 0.05: {right} ({right / total * 100:.2f}%)")


def convert(args: argparse.Namespace) -> int:
    input_dir = Path(args.input)
    output_csv = Path(args.output)
    images_output = Path(args.images_output) if args.images_output else None

    print("DonkeyCar tub to DarkDrive converter")
    print("Simulation-only dataset preparation. No training or control loop is started.")

    if not input_dir.exists():
        print(f"FAIL input tub folder not found: {input_dir}")
        print("Place a manually collected DonkeyCar tub under data/external/donkeycar/ and retry.")
        return 1
    if not input_dir.is_dir():
        print(f"FAIL input path is not a folder: {input_dir}")
        return 1

    images, image_index = discover_images(input_dir)
    manifest_inputs = load_manifest_inputs(input_dir)
    raw_records = list(iter_json_records(input_dir, manifest_inputs)) + list(
        iter_catalog_records(input_dir, manifest_inputs)
    )

    if not raw_records:
        print(f"FAIL no DonkeyCar JSON record or catalog rows were found under: {input_dir}")
        print("Expected record_*.json, records/*.json, or catalog* files containing image and steering fields.")
        return 1

    rows: list[dict[str, object]] = []
    seen_rows: set[tuple[str, float, float]] = set()
    missing_images = 0
    skipped_missing_control = 0
    skipped_invalid_control = 0
    outside_unit_range = 0

    for source_file, record in raw_records:
        image_value = first_value(record, IMAGE_KEYS)
        steering_value = first_value(record, STEERING_KEYS)
        throttle_value = first_value(record, THROTTLE_KEYS)
        speed_value = first_value(record, SPEED_KEYS)

        if image_value is None or steering_value is None:
            skipped_missing_control += 1
            continue

        steering = to_float(steering_value)
        throttle = to_float(throttle_value, 0.0)
        speed = to_float(speed_value, 0.0)
        if steering is None or throttle is None or speed is None:
            skipped_invalid_control += 1
            continue

        steering *= args.steering_scale
        if abs(steering) > 1.0:
            outside_unit_range += 1
            if args.clip_steering:
                steering = max(-1.0, min(1.0, steering))

        image_path = resolve_image_path(image_value, source_file, input_dir, image_index)
        if image_path is None:
            missing_images += 1
            continue

        dedupe_key = (str(image_path.resolve()), float(steering), float(throttle))
        if dedupe_key in seen_rows:
            continue
        seen_rows.add(dedupe_key)

        final_image_path = output_image_path(image_path, images_output, len(rows))
        rows.append(
            {
                "image_path": project_relative(final_image_path),
                "steering": float(steering),
                "throttle": float(throttle),
                "brake": 0.0,
                "speed": float(speed),
                "source_dataset": args.source_name,
            }
        )

    if not rows:
        print("FAIL no valid rows were converted.")
        print(f"- Records inspected: {len(raw_records)}")
        print(f"- Images discovered: {len(images)}")
        print(f"- Missing images: {missing_images}")
        print(f"- Missing image/steering fields: {skipped_missing_control}")
        print(f"- Invalid numeric controls: {skipped_invalid_control}")
        return 1

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=UNIFIED_COLUMNS).to_csv(output_csv, index=False)

    print("Conversion summary")
    print(f"- Input tub: {input_dir}")
    print(f"- Output CSV: {output_csv}")
    if images_output:
        print(f"- Output images: {images_output}")
        print("- Image mode: copied to DarkDrive processed image folder")
    else:
        print("- Image mode: references original manually placed tub images")
    print(f"- Manifest inputs detected: {len(manifest_inputs)}")
    print(f"- Images discovered: {len(images)}")
    print(f"- Records inspected: {len(raw_records)}")
    print(f"- Rows converted: {len(rows)}")
    print(f"- Missing images: {missing_images}")
    print(f"- Missing image/steering fields: {skipped_missing_control}")
    print(f"- Invalid numeric controls: {skipped_invalid_control}")
    print(f"- Steering values outside [-1, 1]: {outside_unit_range}")
    print("- Steering handling: preserved after --steering-scale; clipping only when --clip-steering is used")
    print("- Missing brake handling: brake is set to 0.0")
    print("- Missing speed handling: speed is set to 0.0")
    print_distribution(rows)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a manually placed DonkeyCar tub into DarkDrive unified CSV format."
    )
    parser.add_argument("--input", required=True, help="DonkeyCar tub folder, for example data/external/donkeycar/sample_tub.")
    parser.add_argument("--output", required=True, help="Output unified CSV path.")
    parser.add_argument("--images-output", default=None, help="Optional processed image output folder.")
    parser.add_argument("--source-name", required=True, help="Value written to the source_dataset column.")
    parser.add_argument(
        "--steering-scale",
        type=float,
        default=1.0,
        help="Multiplier applied to steering labels. Default preserves DonkeyCar values.",
    )
    parser.add_argument(
        "--clip-steering",
        action="store_true",
        help="Clip steering labels to [-1, 1] after scaling. Disabled by default.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(convert(parse_args()))
