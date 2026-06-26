from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
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
RANDOM_SEED = 42
TRAINING_CHART_PATH = Path("screenshots/training_loss.png")
SIMPLE_REQUIRED_COLUMNS = {"image_path", "steering", "throttle", "brake", "speed"}
UDACITY_REQUIRED_COLUMNS = {"center", "left", "right", "steering", "throttle", "brake", "speed"}


class DrivingDataset(Dataset):
    """Dataset for simulated camera frames and steering labels."""

    def __init__(
        self,
        csv_path: str | Path,
        dataset_format: str = "simple",
        images_dir: str | Path | None = None,
        data_frame: pd.DataFrame | None = None,
        augment: bool = False,
    ) -> None:
        self.csv_path = Path(csv_path)
        self.dataset_format = dataset_format
        self.images_dir = Path(images_dir) if images_dir else None
        self.augment = augment

        if data_frame is None:
            self.data = pd.read_csv(self.csv_path)
            self.data.columns = [column.strip() for column in self.data.columns]
        else:
            self.data = data_frame.copy().reset_index(drop=True)

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
        steering = float(row["steering"])

        if self.augment:
            image, steering = augment_training_image(image, steering)

        # Convert from H x W x C uint8 pixels to C x H x W float values in [0, 1].
        image_tensor = torch.from_numpy(np.ascontiguousarray(image)).float().permute(2, 0, 1) / 255.0
        steering_tensor = torch.tensor([steering], dtype=torch.float32)
        return image_tensor, steering_tensor

    def _resolve_image_path(self, row: pd.Series) -> Path:
        """Resolve image paths from either supported CSV format."""
        path_column = "image_path" if self.dataset_format == "simple" else "center"
        raw_path = str(row[path_column]).strip().replace("\\", "/")
        image_path = Path(raw_path)

        if image_path.is_absolute():
            return image_path

        if image_path.exists():
            return image_path

        cwd_path = Path.cwd() / image_path
        if cwd_path.exists():
            return cwd_path

        csv_relative_path = self.csv_path.parent / image_path
        if csv_relative_path.exists():
            return csv_relative_path

        if self.images_dir:
            if image_path.parts and image_path.parts[0].lower() == "img":
                return self.images_dir / Path(*image_path.parts[1:])
            return self.images_dir / image_path.name

        return csv_relative_path


def augment_training_image(image: np.ndarray, steering: float) -> tuple[np.ndarray, float]:
    """Apply small simulation-style augmentations to reduce overfitting."""
    augmented = image.copy()

    if np.random.rand() < 0.5:
        augmented = cv2.flip(augmented, 1)
        steering = -steering

    brightness = np.random.uniform(0.75, 1.25)
    contrast = np.random.uniform(0.85, 1.15)
    augmented = np.clip((augmented.astype(np.float32) - 127.5) * contrast + 127.5, 0, 255)
    augmented = np.clip(augmented * brightness, 0, 255).astype(np.uint8)

    if np.random.rand() < 0.35:
        shadow_strength = np.random.uniform(0.65, 0.9)
        height, width = augmented.shape[:2]
        split_x = np.random.randint(width // 4, max(width // 4 + 1, width * 3 // 4))
        shadow_mask = np.zeros((height, width), dtype=np.float32)
        shadow_mask[:, :split_x] = shadow_strength
        shadow_mask[:, split_x:] = 1.0
        augmented = np.clip(augmented.astype(np.float32) * shadow_mask[..., None], 0, 255).astype(
            np.uint8
        )

    return augmented, steering


def split_data_frame(
    data: pd.DataFrame,
    validation_split: float,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create a deterministic train/validation split."""
    if len(data) < 2:
        print("Only one row found. Using the same row for training and validation.")
        return data.copy(), data.copy()

    validation_split = min(max(validation_split, 0.05), 0.5)
    shuffled = data.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    validation_size = max(1, int(len(shuffled) * validation_split))
    validation_data = shuffled.iloc[:validation_size].reset_index(drop=True)
    training_data = shuffled.iloc[validation_size:].reset_index(drop=True)
    return training_data, validation_data


def choose_device(device_name: str) -> torch.device:
    if device_name == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(device_name)


def train_one_epoch(
    model: SteeringModel,
    data_loader: DataLoader,
    loss_function: nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
) -> tuple[float, float]:
    model.train()
    total_loss = 0.0
    total_absolute_error = 0.0
    total_samples = 0

    for images, steering in data_loader:
        images = images.to(device)
        steering = steering.to(device)
        predictions = model(images)
        loss = loss_function(predictions, steering)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        batch_size = images.size(0)
        total_loss += loss.item() * batch_size
        total_absolute_error += torch.abs(predictions.detach() - steering).sum().item()
        total_samples += batch_size

    return total_loss / max(total_samples, 1), total_absolute_error / max(total_samples, 1)


def evaluate(
    model: SteeringModel,
    data_loader: DataLoader,
    loss_function: nn.Module,
    device: torch.device,
) -> tuple[float, float]:
    model.eval()
    total_loss = 0.0
    total_absolute_error = 0.0
    total_samples = 0

    with torch.no_grad():
        for images, steering in data_loader:
            images = images.to(device)
            steering = steering.to(device)
            predictions = model(images)
            loss = loss_function(predictions, steering)

            batch_size = images.size(0)
            total_loss += loss.item() * batch_size
            total_absolute_error += torch.abs(predictions - steering).sum().item()
            total_samples += batch_size

    return total_loss / max(total_samples, 1), total_absolute_error / max(total_samples, 1)


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
    plt.ylabel("Loss")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f"Training loss chart saved to {output_path}")


def save_checkpoint(
    model: SteeringModel,
    output_path: str | Path,
    args: dict[str, object],
    history: dict[str, list[float]],
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = {
        "model_state_dict": model.state_dict(),
        "model_class": "SteeringModel",
        "image_width": IMAGE_WIDTH,
        "image_height": IMAGE_HEIGHT,
        "simulation_only": True,
        "training_args": args,
        "history": history,
    }
    torch.save(checkpoint, output_path)
    print(f"Model checkpoint saved to {output_path}")


def make_loss_function(loss_name: str) -> nn.Module:
    if loss_name == "huber":
        return nn.SmoothL1Loss()
    return nn.MSELoss()


def train(
    csv_path: str | Path,
    dataset_format: str = "simple",
    images_dir: str | Path | None = None,
    epochs: int = 5,
    batch_size: int = 32,
    output_path: str | Path = "models/steering_model_v1.pt",
    chart_output: str | Path = TRAINING_CHART_PATH,
    validation_split: float = 0.2,
    learning_rate: float = 1e-3,
    weight_decay: float = 1e-4,
    loss_name: str = "mse",
    augment: bool = True,
    device_name: str = "auto",
    num_workers: int = 0,
    seed: int = RANDOM_SEED,
) -> None:
    csv_path = Path(csv_path)
    if not csv_path.exists():
        print(f"Driving log not found: {csv_path}")
        print("You need simulated driving data first.")
        print("Simple format: image_path,steering,throttle,brake,speed")
        print("Udacity format: center,left,right,steering,throttle,brake,speed")
        print("For simulator data, place the log at data/processed/simulator/driving_log.csv.")
        return

    try:
        full_dataset = DrivingDataset(csv_path, dataset_format=dataset_format, images_dir=images_dir)
    except ValueError as exc:
        print(f"Dataset format error: {exc}")
        print("Run scripts/validate_simulator_dataset.py before training.")
        return

    if len(full_dataset) == 0:
        print("Driving log is empty. Add simulation driving rows before training.")
        return

    np.random.seed(seed)
    torch.manual_seed(seed)
    training_data, validation_data = split_data_frame(full_dataset.data, validation_split, seed)
    training_dataset = DrivingDataset(
        csv_path,
        dataset_format=dataset_format,
        images_dir=images_dir,
        data_frame=training_data,
        augment=augment,
    )
    validation_dataset = DrivingDataset(
        csv_path,
        dataset_format=dataset_format,
        images_dir=images_dir,
        data_frame=validation_data,
        augment=False,
    )

    device = choose_device(device_name)
    pin_memory = device.type == "cuda"
    training_generator = torch.Generator().manual_seed(seed)
    training_loader = DataLoader(
        training_dataset,
        batch_size=batch_size,
        shuffle=True,
        generator=training_generator,
        num_workers=num_workers,
        pin_memory=pin_memory,
    )
    validation_loader = DataLoader(
        validation_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=pin_memory,
    )

    model = SteeringModel().to(device)
    loss_function = make_loss_function(loss_name)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)

    print("Simulation-only training mode.")
    print(f"Dataset format: {dataset_format}")
    print(f"Training rows: {len(training_dataset)}")
    print(f"Validation rows: {len(validation_dataset)}")
    print(f"Device: {device}")
    print(f"Augmentation: {'on' if augment else 'off'}")
    print("Starting behavior cloning training...")

    history = {
        "training_loss": [],
        "validation_loss": [],
        "training_mae": [],
        "validation_mae": [],
    }
    try:
        for epoch in range(epochs):
            training_loss, training_mae = train_one_epoch(
                model, training_loader, loss_function, optimizer, device
            )
            validation_loss, validation_mae = evaluate(model, validation_loader, loss_function, device)

            history["training_loss"].append(training_loss)
            history["validation_loss"].append(validation_loss)
            history["training_mae"].append(training_mae)
            history["validation_mae"].append(validation_mae)

            print(
                f"Epoch {epoch + 1}/{epochs} - "
                f"training loss: {training_loss:.6f} - "
                f"validation loss: {validation_loss:.6f} - "
                f"training MAE: {training_mae:.4f} - "
                f"validation MAE: {validation_mae:.4f}"
            )
    except FileNotFoundError as exc:
        print(f"Training stopped because an image file was missing: {exc}")
        print("Validate the dataset and image paths before training.")
        return

    checkpoint_args = {
        "csv": str(csv_path),
        "format": dataset_format,
        "images_dir": str(images_dir) if images_dir else "",
        "epochs": epochs,
        "batch_size": batch_size,
        "validation_split": validation_split,
        "learning_rate": learning_rate,
        "weight_decay": weight_decay,
        "loss": loss_name,
        "augment": augment,
        "device": str(device),
        "seed": seed,
    }
    save_checkpoint(model, output_path, checkpoint_args, history)
    save_loss_chart(history["training_loss"], history["validation_loss"], chart_output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a simulation-only behavior cloning steering model.")
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
    parser.add_argument(
        "--images-dir",
        default=None,
        help="Optional directory for resolving simulator image filenames.",
    )
    parser.add_argument("--epochs", type=int, default=5, help="Number of training epochs.")
    parser.add_argument("--batch-size", type=int, default=32, help="Training batch size.")
    parser.add_argument("--lr", type=float, default=1e-3, help="Optimizer learning rate.")
    parser.add_argument("--weight-decay", type=float, default=1e-4, help="AdamW weight decay.")
    parser.add_argument(
        "--loss",
        choices=["mse", "huber"],
        default="mse",
        help="Regression loss function.",
    )
    parser.add_argument(
        "--validation-split",
        type=float,
        default=0.2,
        help="Fraction of rows used for validation.",
    )
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "cuda"],
        default="auto",
        help="Training device. Use auto for CUDA when available.",
    )
    parser.add_argument("--num-workers", type=int, default=0, help="DataLoader worker count.")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED, help="Random seed.")
    parser.add_argument(
        "--augment",
        dest="augment",
        action="store_true",
        help="Enable simple image augmentation during training.",
    )
    parser.add_argument(
        "--no-augment",
        dest="augment",
        action="store_false",
        help="Disable image augmentation.",
    )
    parser.set_defaults(augment=True)
    parser.add_argument(
        "--output",
        default="models/steering_model_v1.pt",
        help="Where to save the trained model checkpoint.",
    )
    parser.add_argument(
        "--chart-output",
        default=str(TRAINING_CHART_PATH),
        help="Where to save the training loss chart.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    train(
        args.csv,
        dataset_format=args.format,
        images_dir=args.images_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        output_path=args.output,
        chart_output=args.chart_output,
        validation_split=args.validation_split,
        learning_rate=args.lr,
        weight_decay=args.weight_decay,
        loss_name=args.loss,
        augment=args.augment,
        device_name=args.device,
        num_workers=args.num_workers,
        seed=args.seed,
    )
