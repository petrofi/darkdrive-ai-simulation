from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.steering_model import SteeringModel


IMAGE_WIDTH = 160
IMAGE_HEIGHT = 80


def preprocess_image(image_path: str | Path) -> torch.Tensor | None:
    image_path = Path(image_path)
    if not image_path.exists():
        print(f"Image not found: {image_path}")
        return None

    image = cv2.imread(str(image_path))
    if image is None:
        print(f"Could not read image file: {image_path}")
        return None

    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = cv2.resize(image, (IMAGE_WIDTH, IMAGE_HEIGHT))
    image_tensor = torch.from_numpy(image).float().permute(2, 0, 1) / 255.0
    return image_tensor.unsqueeze(0)


def load_checkpoint(model_path: Path) -> object:
    """Load local model checkpoints without relying on PyTorch's unsafe default."""
    try:
        return torch.load(model_path, map_location="cpu", weights_only=True)
    except TypeError:
        # Older PyTorch versions do not support weights_only yet.
        return torch.load(model_path, map_location="cpu")


def predict(model_path: str | Path, image_path: str | Path) -> float | None:
    model_path = Path(model_path)
    if not model_path.exists():
        print(f"Model not found: {model_path}")
        print("No trained model found yet. Train the model after collecting simulated driving data.")
        return None

    image_tensor = preprocess_image(image_path)
    if image_tensor is None:
        return None

    checkpoint = load_checkpoint(model_path)
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
    print(f"Predicted steering angle: {prediction:.4f}")
    return prediction


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Predict steering for one simulator image.")
    parser.add_argument("--model", default="models/steering_model_v1.pt", help="Path to a trained model file.")
    parser.add_argument("--image", default="data/samples/road_sample.jpg", help="Path to a simulator frame image.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    predict(args.model, args.image)
