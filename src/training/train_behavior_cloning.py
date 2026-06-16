from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset, random_split

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.steering_model import SteeringModel


IMAGE_WIDTH = 160
IMAGE_HEIGHT = 80
RANDOM_SEED = 42
TRAINING_CHART_PATH = Path("screenshots/training_loss.png")
SIMPLE_REQUIRED_COLUMNS = {"image_path", "steering", "throttle", "brake", "speed"}
UDACITY_REQUIRED_COLUMNS = {"center", "left", "right", "steering", "throttle", "brake", "speed"}


class DrivingDataset(Dataset):
    """Dataset for simulated camera frames and steering labels."""

    def __init__(self, csv_path: str | Path, dataset_format: str = "simple") -> None:
        self.csv_path = Path(csv_path)
        self.dataset_format = dataset_format
        self.data = pd.read_csv(self.csv_path)
        self.data.columns = [column.strip() for column in self.data.columns]

        required_columns = self._required_columns()
        missing_columns = required_columns - set(self.data.columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Driving log is missing required columns: {missing}")

    def _required_columns(self) -> set[str]:
        if self.dataset_format == "simple":
            return SIMPLE_REQUIRED_COLUMNS
        if self.dataset_format == "udacity":
            return UDACITY_REQUIRED_COLUMNS
        raise ValueError("dataset_format must be either 'simple' or 'udacity'")

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        row = self.data.iloc[index]
        image_path = self._resolve_image_path(row)
        image = cv2.imread(str(image_path))
        if image is None:
            raise FileNotFoundError(f"Could not load image: {image_path}")

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = cv2.resize(image, (IMAGE_WIDTH, IMAGE_HEIGHT))

        # Convert from H x W x C uint8 pixels to C x H x W float values in [0, 1].
        image_tensor = torch.from_numpy(image).float().permute(2, 0, 1) / 255.0
        steering_tensor = torch.tensor([float(row["steering"])], dtype=torch.float32)
        return image_tensor, steering_tensor

    def _resolve_image_path(self, row: pd.Series) -> Path:
        """Resolve image paths from either supported CSV format."""
        path_column = "image_path" if self.dataset_format == "simple" else "center"
        raw_path = str(row[path_column]).strip()
        image_path = Path(raw_path)

        if image_path.is_absolute():
            return image_path

        cwd_path = Path.cwd() / image_path
        if cwd_path.exists():
            return cwd_path

        # Many simulator logs store image paths relative to the CSV file.
        return self.csv_path.parent / image_path


def split_dataset(dataset: Dataset) -> tuple[Dataset, Dataset]:
    """Create a beginner-friendly 80/20 train/validation split."""
    total_rows = len(dataset)
    if total_rows < 2:
        print("Only one row found. Using the same row for training and validation.")
        return dataset, dataset

    validation_size = max(1, int(total_rows * 0.2))
    training_size = total_rows - validation_size
    generator = torch.Generator().manual_seed(42)
    return random_split(dataset, [training_size, validation_size], generator=generator)


def train_one_epoch(
    model: SteeringModel,
    data_loader: DataLoader,
    loss_function: nn.Module,
    optimizer: torch.optim.Optimizer,
) -> float:
    model.train()
    total_loss = 0.0
    total_samples = 0

    for images, steering in data_loader:
        predictions = model(images)
        loss = loss_function(predictions, steering)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        batch_size = images.size(0)
        total_loss += loss.item() * batch_size
        total_samples += batch_size

    return total_loss / max(total_samples, 1)


def evaluate(model: SteeringModel, data_loader: DataLoader, loss_function: nn.Module) -> float:
    model.eval()
    total_loss = 0.0
    total_samples = 0

    with torch.no_grad():
        for images, steering in data_loader:
            predictions = model(images)
            loss = loss_function(predictions, steering)

            batch_size = images.size(0)
            total_loss += loss.item() * batch_size
            total_samples += batch_size

    return total_loss / max(total_samples, 1)


def save_loss_chart(
    training_losses: list[float],
    validation_losses: list[float],
    output_path: str | Path = TRAINING_CHART_PATH,
) -> None:
    """Save a simple training/validation loss chart for the README and devlog."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    epochs = range(1, len(training_losses) + 1)
    plt.figure(figsize=(8, 5))
    plt.plot(epochs, training_losses, marker="o", label="Training loss")
    plt.plot(epochs, validation_losses, marker="o", label="Validation loss")
    plt.title("Behavior Cloning Loss")
    plt.xlabel("Epoch")
    plt.ylabel("MSE loss")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f"Training loss chart saved to {output_path}")


def train(
    csv_path: str | Path,
    dataset_format: str = "simple",
    epochs: int = 5,
    batch_size: int = 32,
    output_path: str | Path = "models/steering_model_v1.pt",
) -> None:
    csv_path = Path(csv_path)
    if not csv_path.exists():
        print(f"Driving log not found: {csv_path}")
        print("You need simulated driving data first.")
        print("Simple format: image_path,steering,throttle,brake,speed")
        print("Udacity format: center,left,right,steering,throttle,brake,speed")
        print("Place the real simulation training log at data/processed/driving_log.csv.")
        return

    dataset = DrivingDataset(csv_path, dataset_format=dataset_format)
    if len(dataset) == 0:
        print("Driving log is empty. Add simulation driving rows before training.")
        return

    training_dataset, validation_dataset = split_dataset(dataset)
    training_generator = torch.Generator().manual_seed(RANDOM_SEED)
    training_loader = DataLoader(
        training_dataset,
        batch_size=batch_size,
        shuffle=True,
        generator=training_generator,
    )
    validation_loader = DataLoader(validation_dataset, batch_size=batch_size, shuffle=False)

    torch.manual_seed(RANDOM_SEED)
    model = SteeringModel()
    loss_function = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    print("Simulation-only training mode.")
    print(f"Dataset format: {dataset_format}")
    print(f"Training rows: {len(training_dataset)}")
    print(f"Validation rows: {len(validation_dataset)}")
    print("Starting baseline behavior cloning training...")

    training_losses = []
    validation_losses = []
    for epoch in range(epochs):
        training_loss = train_one_epoch(model, training_loader, loss_function, optimizer)
        validation_loss = evaluate(model, validation_loader, loss_function)
        training_losses.append(training_loss)
        validation_losses.append(validation_loss)

        print(
            f"Epoch {epoch + 1}/{epochs} - "
            f"training loss: {training_loss:.6f} - "
            f"validation loss: {validation_loss:.6f}"
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), output_path)
    print(f"Model saved to {output_path}")
    save_loss_chart(training_losses, validation_losses)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a baseline behavior cloning steering model.")
    parser.add_argument(
        "--csv",
        default="data/processed/driving_log.csv",
        help="CSV file with a simple or Udacity-style simulated driving log.",
    )
    parser.add_argument(
        "--format",
        choices=["simple", "udacity"],
        default="simple",
        help="Driving log format to read.",
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
    train(
        args.csv,
        dataset_format=args.format,
        epochs=args.epochs,
        batch_size=args.batch_size,
        output_path=args.output,
    )
