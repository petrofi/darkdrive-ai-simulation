from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import torch

from src.models.steering_model import SteeringModel


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
    image = cv2.resize(image, (160, 120))
    image_tensor = torch.from_numpy(image).float().permute(2, 0, 1) / 255.0
    return image_tensor.unsqueeze(0)


def predict(model_path: str | Path, image_path: str | Path) -> float | None:
    model_path = Path(model_path)
    if not model_path.exists():
        print(f"Model not found: {model_path}")
        print("Train a simulation behavior cloning model before running inference.")
        return None

    image_tensor = preprocess_image(image_path)
    if image_tensor is None:
        return None

    model = SteeringModel()
    model.load_state_dict(torch.load(model_path, map_location="cpu"))
    model.eval()

    with torch.no_grad():
        prediction = model(image_tensor).item()

    print(f"Predicted steering angle: {prediction:.4f}")
    return prediction


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Predict steering for one simulator image.")
    parser.add_argument("--model", default="models/steering_model.pt", help="Path to a trained model file.")
    parser.add_argument("--image", required=True, help="Path to a simulator frame image.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    predict(args.model, args.image)
