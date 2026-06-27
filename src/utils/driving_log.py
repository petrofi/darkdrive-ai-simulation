from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


SIMPLE_REQUIRED_COLUMNS = ["image_path", "steering", "throttle", "brake", "speed"]
UDACITY_REQUIRED_COLUMNS = ["center", "left", "right", "steering", "throttle", "brake", "speed"]
NUMERIC_COLUMNS = ["steering", "throttle", "brake", "speed"]


def required_columns(dataset_format: str) -> list[str]:
    if dataset_format == "simple":
        return SIMPLE_REQUIRED_COLUMNS
    if dataset_format == "udacity":
        return UDACITY_REQUIRED_COLUMNS
    raise ValueError(f"Unsupported dataset format: {dataset_format}")


def primary_image_column(dataset_format: str) -> str:
    return "image_path" if dataset_format == "simple" else "center"


def image_columns(dataset_format: str) -> list[str]:
    return ["image_path"] if dataset_format == "simple" else ["center", "left", "right"]


def load_driving_log(csv_path: str | Path, dataset_format: str) -> pd.DataFrame:
    """Load simple or Udacity-style logs, including headerless simulator CSVs."""
    csv_path = Path(csv_path)
    expected_columns = required_columns(dataset_format)

    try:
        data = pd.read_csv(csv_path, skipinitialspace=True)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=expected_columns)

    data.columns = [str(column).strip() for column in data.columns]
    has_expected_header = all(column in data.columns for column in expected_columns)

    if not has_expected_header:
        raw_data = pd.read_csv(csv_path, header=None, skipinitialspace=True)
        if raw_data.shape[1] < len(expected_columns):
            raise ValueError(
                f"Expected at least {len(expected_columns)} columns for {dataset_format} format, "
                f"but found {raw_data.shape[1]}."
            )
        data = raw_data.iloc[:, : len(expected_columns)].copy()
        data.columns = expected_columns

    return normalize_driving_log(data)


def normalize_driving_log(data: pd.DataFrame) -> pd.DataFrame:
    """Trim whitespace and convert numeric control columns when present."""
    data = data.copy()
    data.columns = [str(column).strip() for column in data.columns]
    data = data.dropna(how="all").reset_index(drop=True)

    for column in data.select_dtypes(include=["object"]).columns:
        data[column] = data[column].astype(str).str.strip()

    for column in NUMERIC_COLUMNS:
        if column in data.columns:
            data[column] = pd.to_numeric(data[column], errors="coerce")

    return data


def resolve_image_path(raw_path: object, csv_path: str | Path, images_dir: str | Path | None) -> Path:
    """Resolve simulator paths across absolute Windows paths and local IMG folders."""
    csv_path = Path(csv_path)
    images_dir_path = Path(images_dir) if images_dir else None
    normalized_path = str(raw_path).strip().strip('"').strip("'").replace("\\", "/")
    image_path = Path(normalized_path)

    candidates: list[Path] = []

    # Absolute paths are trusted only when they still exist. Old simulator logs
    # often point to a recording folder that was later copied into this repo.
    if image_path.is_absolute():
        candidates.append(image_path)
    else:
        candidates.extend(
            [
                image_path,
                Path.cwd() / image_path,
                csv_path.parent / image_path,
            ]
        )

    path_parts = list(image_path.parts)
    lower_parts = [part.lower() for part in path_parts]
    if images_dir_path is not None:
        if "img" in lower_parts:
            img_index = lower_parts.index("img")
            tail_parts = path_parts[img_index + 1 :]
            if tail_parts:
                candidates.append(images_dir_path / Path(*tail_parts))
        candidates.append(images_dir_path / image_path.name)

    candidates.append(csv_path.parent / "IMG" / image_path.name)

    for candidate in unique_paths(candidates):
        if candidate.exists():
            return candidate

    if images_dir_path is not None:
        return images_dir_path / image_path.name
    return candidates[-1]


def unique_paths(paths: Iterable[Path]) -> list[Path]:
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        key = str(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def filter_rows_with_existing_images(
    data: pd.DataFrame,
    csv_path: str | Path,
    images_dir: str | Path | None,
    dataset_format: str,
) -> tuple[pd.DataFrame, int]:
    """Keep rows whose primary image exists and return the missing row count."""
    path_column = primary_image_column(dataset_format)
    valid_rows = []
    missing_count = 0

    for _, row in data.iterrows():
        image_path = resolve_image_path(row[path_column], csv_path, images_dir)
        if image_path.exists():
            valid_rows.append(row)
        else:
            missing_count += 1

    if not valid_rows:
        return pd.DataFrame(columns=data.columns), missing_count

    return pd.DataFrame(valid_rows).reset_index(drop=True), missing_count
