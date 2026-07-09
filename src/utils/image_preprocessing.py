from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import cv2
import numpy as np


MODEL_INPUT_WIDTH = 160
MODEL_INPUT_HEIGHT = 80
BASELINE_PROFILE = "baseline"
ROAD_CROP_V1_PROFILE = "road_crop_v1"
VALID_PREPROCESSING_PROFILES = (BASELINE_PROFILE, ROAD_CROP_V1_PROFILE)


@dataclass(frozen=True)
class CropBounds:
    x_min: int
    x_max: int | None
    y_min: int
    y_max: int


ROAD_CROP_V1_BOUNDS = CropBounds(x_min=0, x_max=None, y_min=55, y_max=150)


def validate_preprocessing_profile(profile_name: str) -> str:
    if profile_name not in VALID_PREPROCESSING_PROFILES:
        valid = ", ".join(VALID_PREPROCESSING_PROFILES)
        raise ValueError(f"Unsupported preprocessing profile: {profile_name}. Valid profiles: {valid}")
    return profile_name


def preprocessing_metadata(profile_name: str) -> dict[str, object]:
    profile_name = validate_preprocessing_profile(profile_name)
    metadata: dict[str, object] = {
        "profile": profile_name,
        "input_width": MODEL_INPUT_WIDTH,
        "input_height": MODEL_INPUT_HEIGHT,
        "pixel_scale": "[0, 1]",
        "color_space": "RGB",
    }
    if profile_name == ROAD_CROP_V1_PROFILE:
        metadata["crop"] = asdict(ROAD_CROP_V1_BOUNDS)
        metadata["crop_reference_width"] = 320
        metadata["crop_reference_height"] = 160
        metadata["crop_description"] = "Full-width simulator frame crop, y=[55, 150), before resize."
    else:
        metadata["crop"] = None
        metadata["crop_description"] = "No crop; resize the full frame."
    return metadata


def checkpoint_preprocessing_profile(checkpoint: object) -> str:
    if not isinstance(checkpoint, dict):
        return BASELINE_PROFILE

    preprocessing = checkpoint.get("preprocessing")
    if isinstance(preprocessing, dict):
        profile = preprocessing.get("profile")
        if isinstance(profile, str):
            return validate_preprocessing_profile(profile)

    profile = checkpoint.get("preprocessing_profile")
    if isinstance(profile, str):
        return validate_preprocessing_profile(profile)

    training_args = checkpoint.get("training_args")
    if isinstance(training_args, dict):
        profile = training_args.get("preprocessing_profile")
        if isinstance(profile, str):
            return validate_preprocessing_profile(profile)

    return BASELINE_PROFILE


def resolve_preprocessing_profile(
    requested_profile: str,
    checkpoint: object | None = None,
) -> str:
    if requested_profile == "checkpoint":
        return checkpoint_preprocessing_profile(checkpoint)
    return validate_preprocessing_profile(requested_profile)


def load_image_rgb(image_path: str | Path) -> np.ndarray:
    image_path = Path(image_path)
    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(f"Could not load image: {image_path}")
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def ensure_rgb(image: np.ndarray, color_order: Literal["RGB", "BGR"] = "RGB") -> np.ndarray:
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"Expected an H x W x 3 image, got shape {image.shape}")
    if color_order == "RGB":
        return image
    if color_order == "BGR":
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    raise ValueError(f"Unsupported color order: {color_order}")


def apply_crop_profile(image_rgb: np.ndarray, profile_name: str) -> np.ndarray:
    profile_name = validate_preprocessing_profile(profile_name)
    image_rgb = ensure_rgb(image_rgb, "RGB")

    if profile_name == BASELINE_PROFILE:
        return image_rgb

    bounds = ROAD_CROP_V1_BOUNDS
    height, width = image_rgb.shape[:2]
    x_max = width if bounds.x_max is None else bounds.x_max
    if not (0 <= bounds.x_min < x_max <= width and 0 <= bounds.y_min < bounds.y_max <= height):
        raise ValueError(
            "road_crop_v1 crop bounds are invalid for image shape "
            f"{width}x{height}: x=[{bounds.x_min}, {x_max}), y=[{bounds.y_min}, {bounds.y_max})"
        )
    return image_rgb[bounds.y_min : bounds.y_max, bounds.x_min : x_max]


def preprocess_image_array(
    image: np.ndarray,
    preprocessing_profile: str = BASELINE_PROFILE,
    *,
    color_order: Literal["RGB", "BGR"] = "RGB",
    output_width: int = MODEL_INPUT_WIDTH,
    output_height: int = MODEL_INPUT_HEIGHT,
) -> np.ndarray:
    image_rgb = ensure_rgb(image, color_order)
    cropped = apply_crop_profile(image_rgb, preprocessing_profile)
    return cv2.resize(cropped, (output_width, output_height))


def image_to_chw_float(image_rgb: np.ndarray) -> np.ndarray:
    image_rgb = ensure_rgb(image_rgb, "RGB")
    return np.ascontiguousarray(image_rgb).astype(np.float32).transpose(2, 0, 1) / 255.0


def preprocess_image_for_model(
    image: np.ndarray,
    preprocessing_profile: str = BASELINE_PROFILE,
    *,
    color_order: Literal["RGB", "BGR"] = "RGB",
    output_width: int = MODEL_INPUT_WIDTH,
    output_height: int = MODEL_INPUT_HEIGHT,
) -> np.ndarray:
    resized = preprocess_image_array(
        image,
        preprocessing_profile,
        color_order=color_order,
        output_width=output_width,
        output_height=output_height,
    )
    return image_to_chw_float(resized)
