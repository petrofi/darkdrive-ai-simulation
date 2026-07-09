from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.steering_model import SteeringModel
from src.utils.image_preprocessing import (
    BASELINE_PROFILE,
    VALID_PREPROCESSING_PROFILES,
    load_image_rgb,
    preprocessing_metadata,
    preprocess_image_for_model,
    resolve_preprocessing_profile,
)


def preprocess_image(
    image_path: str | Path,
    preprocessing_profile: str = BASELINE_PROFILE,
) -> torch.Tensor | None:
    image_path = Path(image_path)
    if not image_path.exists():
        print(f"Image not found: {image_path}")
        return None

    try:
        image = load_image_rgb(image_path)
        image_array = preprocess_image_for_model(image, preprocessing_profile)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Could not read image file: {image_path}")
        print(exc)
        return None

    image_tensor = torch.from_numpy(image_array)
    return image_tensor.unsqueeze(0)


def load_checkpoint(model_path: Path) -> object:
    """Load local model checkpoints without relying on PyTorch's unsafe default."""
    try:
        return torch.load(model_path, map_location="cpu", weights_only=True)
    except TypeError:
        # Older PyTorch versions do not support weights_only yet.
        return torch.load(model_path, map_location="cpu")


def predict(
    model_path: str | Path,
    image_path: str | Path,
    preprocessing_profile: str = "checkpoint",
) -> float | None:
    model_path = Path(model_path)
    if not model_path.exists():
        print(f"Model not found: {model_path}")
        print("No trained model found yet. Train the model after collecting simulated driving data.")
        return None

    checkpoint = load_checkpoint(model_path)
    resolved_preprocessing_profile = resolve_preprocessing_profile(preprocessing_profile, checkpoint)
    image_tensor = preprocess_image(image_path, resolved_preprocessing_profile)
    if image_tensor is None:
        return None

    state_dict = checkpoint.get("model_state_dict", checkpoint) if isinstance(checkpoint, dict) else checkpoint

    model = SteeringModel()
    try:
        model.load_state_dict(state_dict)
    except RuntimeError:
        print("Model architecture does not match this checkpoint.")
        print("Retrain the model with the current training script.")
        return None
    model.eval()

    with torch.no_grad():
        prediction = model(image_tensor).item()

    if isinstance(checkpoint, dict) and checkpoint.get("simulation_only"):
        print("Loaded simulation-only steering checkpoint.")
    print(f"Preprocessing profile: {resolved_preprocessing_profile}")
    print(f"Preprocessing metadata: {preprocessing_metadata(resolved_preprocessing_profile)}")
    print(f"Predicted steering angle: {prediction:.4f}")
    return prediction


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Predict steering for one simulator image.")
    parser.add_argument("--model", default="models/steering_model_v1.pt", help="Path to a trained model file.")
    parser.add_argument("--image", default="data/samples/road_sample.jpg", help="Path to a simulator frame image.")
    parser.add_argument(
        "--preprocessing-profile",
        choices=("checkpoint", *VALID_PREPROCESSING_PROFILES),
        default="checkpoint",
        help=(
            "Image preprocessing profile. Use checkpoint to read checkpoint metadata; "
            f"old checkpoints default to {BASELINE_PROFILE}."
        ),
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    predict(args.model, args.image, args.preprocessing_profile)
