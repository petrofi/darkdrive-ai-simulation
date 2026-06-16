from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.steering_model import SteeringModel


IMAGE_WIDTH = 160
IMAGE_HEIGHT = 80
REQUIRED_COLUMNS = {"image_path", "steering", "throttle", "brake", "speed"}


class DrivingDataset(Dataset):
    """Dataset for simulated camera frames and steering labels."""

    def __init__(self, csv_path: str | Path) -> None:
        self.csv_path = Path(csv_path)
        self.data = pd.read_csv(self.csv_path)

        missing_columns = REQUIRED_COLUMNS - set(self.data.columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Driving log is missing required columns: {missing}")

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        row = self.data.iloc[index]
        image_path = Path(row["image_path"])
        image = cv2.imread(str(image_path))
        if image is None:
            raise FileNotFoundError(f"Could not load image: {image_path}")

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = cv2.resize(image, (IMAGE_WIDTH, IMAGE_HEIGHT))

        # Convert from H x W x C uint8 pixels to C x H x W float values in [0, 1].
        image_tensor = torch.from_numpy(image).float().permute(2, 0, 1) / 255.0
        steering_tensor = torch.tensor([float(row["steering"])], dtype=torch.float32)
        return image_tensor, steering_tensor


def train(
    csv_path: str | Path,
    epochs: int = 5,
    batch_size: int = 32,
    output_path: str | Path = "models/steering_model_v1.pt",
) -> None:
    csv_path = Path(csv_path)
    if not csv_path.exists():
        print(f"Driving log not found: {csv_path}")
        print("You need simulated driving data first.")
        print("Expected CSV columns: image_path,steering,throttle,brake,speed")
        print("Place the real simulation training log at data/processed/driving_log.csv.")
        return

    dataset = DrivingDataset(csv_path)
    if len(dataset) == 0:
        print("Driving log is empty. Add simulation driving rows before training.")
        return

    data_loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    model = SteeringModel()
    loss_function = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    print("Simulation-only training mode.")
    print("Starting baseline behavior cloning training...")
    for epoch in range(epochs):
        total_loss = 0.0
        for images, steering in data_loader:
            predictions = model(images)
            loss = loss_function(predictions, steering)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()

        average_loss = total_loss / len(data_loader)
        print(f"Epoch {epoch + 1}/{epochs} - loss: {average_loss:.6f}")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), output_path)
    print(f"Model saved to {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a baseline behavior cloning steering model.")
    parser.add_argument(
        "--csv",
        default="data/processed/driving_log.csv",
        help="CSV file with image_path, steering, throttle, brake, and speed columns.",
    )
    parser.add_argument("--epochs", type=int, default=5, help="Number of training epochs.")
    parser.add_argument("--batch-size", type=int, default=32, help="Training batch size.")
    parser.add_argument(
        "--output",
        default="models/steering_model_v1.pt",
        help="Where to save the trained model weights.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    train(args.csv, epochs=args.epochs, batch_size=args.batch_size, output_path=args.output)
