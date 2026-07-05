from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
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
from src.utils.driving_log import (
    filter_rows_with_existing_images,
    load_driving_log,
    primary_image_column,
    required_columns,
    resolve_image_path,
)


IMAGE_WIDTH = 160
IMAGE_HEIGHT = 80
RANDOM_SEED = 42
TRAINING_CHART_PATH = Path("screenshots/training_loss.png")


@dataclass(frozen=True)
class ManifestValidation:
    role: str
    csv_path: Path
    input_rows: int
    usable_rows: int
    missing_images: int
    invalid_steering: int
    nan_labels: int
    source_sessions: list[str]


@dataclass(frozen=True)
class TrainingFrames:
    training_data: pd.DataFrame
    validation_data: pd.DataFrame
    training_csv: Path
    validation_csv: Path
    explicit_manifests: bool
    training_validation: ManifestValidation
    validation_validation: ManifestValidation
    skipped_invalid_steering: int
    skipped_missing_images: int


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
            self.data = load_driving_log(self.csv_path, self.dataset_format)
        else:
            self.data = data_frame.copy().reset_index(drop=True)

        required_columns = self._required_columns()
        missing_columns = required_columns - set(self.data.columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Driving log is missing required columns: {missing}")

    def _required_columns(self) -> set[str]:
        return set(required_columns(self.dataset_format))

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
        path_column = primary_image_column(self.dataset_format)
        return resolve_image_path(row[path_column], self.csv_path, self.images_dir)


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


def source_sessions(data: pd.DataFrame) -> list[str]:
    if "source_session" not in data.columns:
        return []
    return sorted(str(value) for value in data["source_session"].dropna().unique())


def resolved_image_paths(
    data: pd.DataFrame,
    csv_path: str | Path,
    images_dir: str | Path | None,
    dataset_format: str,
) -> list[str]:
    path_column = primary_image_column(dataset_format)
    return [
        str(resolve_image_path(row[path_column], csv_path, images_dir))
        for _, row in data.iterrows()
    ]


def validate_manifest(
    csv_path: str | Path,
    dataset_format: str,
    images_dir: str | Path | None,
    role: str,
    *,
    fail_on_missing_images: bool,
    fail_on_invalid_labels: bool,
) -> tuple[pd.DataFrame | None, ManifestValidation]:
    csv_path = Path(csv_path)
    if not csv_path.exists():
        print(f"{role.capitalize()} manifest not found: {csv_path}")
        return None, ManifestValidation(role, csv_path, 0, 0, 0, 0, 0, [])

    try:
        data = load_driving_log(csv_path, dataset_format)
    except ValueError as exc:
        print(f"{role.capitalize()} manifest format error: {exc}")
        return None, ManifestValidation(role, csv_path, 0, 0, 0, 0, 0, [])
    except Exception as exc:
        print(f"Could not read {role} manifest: {exc}")
        return None, ManifestValidation(role, csv_path, 0, 0, 0, 0, 0, [])

    if len(data) == 0:
        print(f"{role.capitalize()} manifest is empty: {csv_path}")
        return None, ManifestValidation(role, csv_path, 0, 0, 0, 0, 0, [])

    if "steering" not in data.columns:
        print(f"{role.capitalize()} manifest is missing required steering column: {csv_path}")
        return None, ManifestValidation(role, csv_path, len(data), 0, 0, len(data), len(data), [])

    steering = pd.to_numeric(data["steering"], errors="coerce")
    invalid_steering = int(steering.isna().sum())
    nan_labels = int(steering.isna().sum())
    if invalid_steering:
        message = f"{role.capitalize()} manifest has invalid steering labels: {invalid_steering}"
        if fail_on_invalid_labels:
            print(message)
            return None, ManifestValidation(
                role,
                csv_path,
                len(data),
                0,
                0,
                invalid_steering,
                nan_labels,
                source_sessions(data),
            )
        print(f"Skipping rows with invalid steering values in {role}: {invalid_steering}")
        data = data.dropna(subset=["steering"]).reset_index(drop=True)

    filtered_data, missing_images = filter_rows_with_existing_images(
        data,
        csv_path,
        images_dir,
        dataset_format,
    )
    if missing_images:
        message = f"{role.capitalize()} manifest has missing center images: {missing_images}"
        if fail_on_missing_images:
            print(message)
            return None, ManifestValidation(
                role,
                csv_path,
                len(data),
                0,
                missing_images,
                invalid_steering,
                nan_labels,
                source_sessions(data),
            )
        print(f"Skipping rows with missing center images in {role}: {missing_images}")

    if len(filtered_data) == 0:
        print(f"No usable rows remain in {role} manifest after validation.")
        return None, ManifestValidation(
            role,
            csv_path,
            len(data),
            0,
            missing_images,
            invalid_steering,
            nan_labels,
            source_sessions(data),
        )

    validation = ManifestValidation(
        role=role,
        csv_path=csv_path,
        input_rows=len(data),
        usable_rows=len(filtered_data),
        missing_images=missing_images,
        invalid_steering=invalid_steering,
        nan_labels=nan_labels,
        source_sessions=source_sessions(filtered_data),
    )
    return filtered_data, validation


def validate_explicit_split(
    training_data: pd.DataFrame,
    validation_data: pd.DataFrame,
    training_csv: str | Path,
    validation_csv: str | Path,
    images_dir: str | Path | None,
    dataset_format: str,
) -> dict[str, object]:
    training_paths = set(resolved_image_paths(training_data, training_csv, images_dir, dataset_format))
    validation_paths = set(
        resolved_image_paths(validation_data, validation_csv, images_dir, dataset_format)
    )
    overlapping_paths = training_paths & validation_paths

    training_sessions = set(source_sessions(training_data))
    validation_sessions = set(source_sessions(validation_data))
    overlapping_sessions = (
        training_sessions & validation_sessions
        if training_sessions and validation_sessions
        else set()
    )

    return {
        "overlapping_image_paths": sorted(overlapping_paths),
        "overlapping_image_path_count": len(overlapping_paths),
        "overlapping_source_sessions": sorted(overlapping_sessions),
        "overlapping_source_session_count": len(overlapping_sessions),
    }


def prepare_training_frames(
    csv_path: str | Path,
    dataset_format: str,
    images_dir: str | Path | None,
    validation_split: float,
    seed: int,
    train_csv_path: str | Path | None = None,
    validation_csv_path: str | Path | None = None,
) -> TrainingFrames | None:
    if bool(train_csv_path) != bool(validation_csv_path):
        print("Explicit training requires both --train-csv and --validation-csv.")
        return None

    if train_csv_path and validation_csv_path:
        training_data, training_validation = validate_manifest(
            train_csv_path,
            dataset_format,
            images_dir,
            "training",
            fail_on_missing_images=True,
            fail_on_invalid_labels=True,
        )
        validation_data, validation_validation = validate_manifest(
            validation_csv_path,
            dataset_format,
            images_dir,
            "validation",
            fail_on_missing_images=True,
            fail_on_invalid_labels=True,
        )
        if training_data is None or validation_data is None:
            return None

        split_check = validate_explicit_split(
            training_data,
            validation_data,
            train_csv_path,
            validation_csv_path,
            images_dir,
            dataset_format,
        )
        if split_check["overlapping_image_path_count"]:
            print(
                "Training and validation manifests overlap by image path: "
                f"{split_check['overlapping_image_path_count']}"
            )
            return None
        if split_check["overlapping_source_session_count"]:
            print(
                "Training and validation manifests overlap by source_session: "
                f"{split_check['overlapping_source_sessions']}"
            )
            return None

        return TrainingFrames(
            training_data=training_data.reset_index(drop=True),
            validation_data=validation_data.reset_index(drop=True),
            training_csv=Path(train_csv_path),
            validation_csv=Path(validation_csv_path),
            explicit_manifests=True,
            training_validation=training_validation,
            validation_validation=validation_validation,
            skipped_invalid_steering=0,
            skipped_missing_images=0,
        )

    full_data, full_validation = validate_manifest(
        csv_path,
        dataset_format,
        images_dir,
        "dataset",
        fail_on_missing_images=False,
        fail_on_invalid_labels=False,
    )
    if full_data is None:
        return None

    training_data, validation_data = split_data_frame(full_data, validation_split, seed)
    return TrainingFrames(
        training_data=training_data,
        validation_data=validation_data,
        training_csv=Path(csv_path),
        validation_csv=Path(csv_path),
        explicit_manifests=False,
        training_validation=ManifestValidation(
            role="training",
            csv_path=Path(csv_path),
            input_rows=len(training_data),
            usable_rows=len(training_data),
            missing_images=0,
            invalid_steering=0,
            nan_labels=0,
            source_sessions=source_sessions(training_data),
        ),
        validation_validation=ManifestValidation(
            role="validation",
            csv_path=Path(csv_path),
            input_rows=len(validation_data),
            usable_rows=len(validation_data),
            missing_images=0,
            invalid_steering=0,
            nan_labels=0,
            source_sessions=source_sessions(validation_data),
        ),
        skipped_invalid_steering=full_validation.invalid_steering,
        skipped_missing_images=full_validation.missing_images,
    )


def choose_device(device_name: str) -> torch.device:
    if device_name == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(device_name)


def count_parameters(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)


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
        "model_architecture": "SteeringModel",
        "parameter_count": count_parameters(model),
        "image_width": IMAGE_WIDTH,
        "image_height": IMAGE_HEIGHT,
        "simulation_only": True,
        "training_args": args,
        "history": history,
    }
    torch.save(checkpoint, output_path)
    print(f"Model checkpoint saved to {output_path}")


def default_chart_output(
    output_path: str | Path,
    csv_path: str | Path,
    dataset_format: str,
) -> Path:
    """Choose a beginner-friendly default chart name for simulator training."""
    output_stem = Path(output_path).stem
    csv_text = str(csv_path).replace("\\", "/").lower()
    if output_stem == "steering_model_local_v2" or "data/processed/local_v2_training" in csv_text:
        return Path("screenshots/training_loss_local_v2.png")
    if output_stem.startswith("steering_model_local_v3") or "data/processed/local_v3_training" in csv_text:
        return Path("screenshots/training_loss_local_v3.png")
    if output_stem == "steering_model_merged_v1" or "data/processed/merged_training" in csv_text:
        return Path("screenshots/training_loss_merged_v1.png")
    if output_stem == "steering_model_sim_v1" or (
        dataset_format == "udacity" and "data/processed/simulator" in csv_text
    ):
        return Path("screenshots/training_loss_sim_v1.png")
    return TRAINING_CHART_PATH


def make_loss_function(loss_name: str) -> nn.Module:
    if loss_name == "huber":
        return nn.SmoothL1Loss()
    return nn.MSELoss()


def train(
    csv_path: str | Path,
    dataset_format: str = "simple",
    images_dir: str | Path | None = None,
    train_csv_path: str | Path | None = None,
    validation_csv_path: str | Path | None = None,
    epochs: int = 5,
    batch_size: int = 32,
    output_path: str | Path = "models/steering_model_v1.pt",
    chart_output: str | Path | None = None,
    validation_split: float = 0.2,
    learning_rate: float = 1e-3,
    weight_decay: float = 1e-4,
    loss_name: str = "mse",
    augment: bool = True,
    device_name: str = "auto",
    num_workers: int = 0,
    seed: int = RANDOM_SEED,
) -> bool:
    csv_path = Path(csv_path)
    frames = prepare_training_frames(
        csv_path,
        dataset_format,
        images_dir,
        validation_split,
        seed,
        train_csv_path=train_csv_path,
        validation_csv_path=validation_csv_path,
    )
    if frames is None:
        print("Training stopped before model initialization.")
        return False

    if chart_output is None:
        chart_reference = validation_csv_path or train_csv_path or csv_path
        chart_output = default_chart_output(output_path, chart_reference, dataset_format)

    np.random.seed(seed)
    torch.manual_seed(seed)
    training_dataset = DrivingDataset(
        frames.training_csv,
        dataset_format=dataset_format,
        images_dir=images_dir,
        data_frame=frames.training_data,
        augment=augment,
    )
    validation_dataset = DrivingDataset(
        frames.validation_csv,
        dataset_format=dataset_format,
        images_dir=images_dir,
        data_frame=frames.validation_data,
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
    parameter_count = count_parameters(model)
    loss_function = make_loss_function(loss_name)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)

    print("Simulation-only training mode.")
    print(f"Dataset format: {dataset_format}")
    print(f"Split mode: {'explicit manifests' if frames.explicit_manifests else 'random row split'}")
    print(f"Training rows: {len(training_dataset)}")
    print(f"Validation rows: {len(validation_dataset)}")
    print(f"Training source sessions: {frames.training_validation.source_sessions or ['not recorded']}")
    print(f"Validation source sessions: {frames.validation_validation.source_sessions or ['not recorded']}")
    print(f"Device: {device}")
    print(f"Augmentation: {'on' if augment else 'off'}")
    print(f"Model parameters: {parameter_count}")
    print("Starting behavior cloning training...")

    history = {
        "training_loss": [],
        "validation_loss": [],
        "training_mae": [],
        "validation_mae": [],
    }
    best_validation_loss = float("inf")
    best_epoch = 0
    best_state_dict: dict[str, torch.Tensor] | None = None

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

            if validation_loss < best_validation_loss:
                best_validation_loss = validation_loss
                best_epoch = epoch + 1
                best_state_dict = {
                    name: value.detach().cpu().clone()
                    for name, value in model.state_dict().items()
                }
                best_note = " - best checkpoint updated"
            else:
                best_note = ""

            print(
                f"Epoch {epoch + 1}/{epochs} - "
                f"training loss: {training_loss:.6f} - "
                f"validation loss: {validation_loss:.6f} - "
                f"training MAE: {training_mae:.4f} - "
                f"validation MAE: {validation_mae:.4f}"
                f"{best_note}"
            )
    except FileNotFoundError as exc:
        print(f"Training stopped because an image file was missing: {exc}")
        print("Validate the dataset and image paths before training.")
        return False

    checkpoint_args = {
        "csv": str(csv_path),
        "train_csv": str(frames.training_csv),
        "validation_csv": str(frames.validation_csv),
        "explicit_manifests": frames.explicit_manifests,
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
        "model_architecture": "SteeringModel",
        "input_image_width": IMAGE_WIDTH,
        "input_image_height": IMAGE_HEIGHT,
        "parameter_count": parameter_count,
        "best_epoch": best_epoch,
        "best_validation_loss": best_validation_loss,
        "train_row_count": len(training_dataset),
        "validation_row_count": len(validation_dataset),
        "training_source_sessions": frames.training_validation.source_sessions,
        "validation_source_sessions": frames.validation_validation.source_sessions,
        "usable_rows": len(training_dataset) + len(validation_dataset),
        "skipped_missing_images": frames.skipped_missing_images,
        "skipped_invalid_steering": frames.skipped_invalid_steering,
    }

    if best_state_dict is not None:
        model.load_state_dict(best_state_dict)

    save_checkpoint(model, output_path, checkpoint_args, history)
    save_loss_chart(history["training_loss"], history["validation_loss"], chart_output)
    print("Training summary:")
    print(f"- Training rows: {len(training_dataset)}")
    print(f"- Validation rows: {len(validation_dataset)}")
    print(f"- Best epoch: {best_epoch}")
    print(f"- Best validation loss: {best_validation_loss:.6f}")
    print(f"- Final training loss: {history['training_loss'][-1]:.6f}")
    print(f"- Final validation loss: {history['validation_loss'][-1]:.6f}")
    print(f"- Output checkpoint: {output_path}")
    print(f"- Loss chart: {chart_output}")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a simulation-only behavior cloning steering model.")
    parser.add_argument(
        "--csv",
        default="data/processed/driving_log.csv",
        help="CSV file with a simple or Udacity-style simulated driving log.",
    )
    parser.add_argument(
        "--train-csv",
        default=None,
        help="Explicit training manifest. Must be supplied together with --validation-csv.",
    )
    parser.add_argument(
        "--validation-csv",
        default=None,
        help="Explicit validation manifest. Must be supplied together with --train-csv.",
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
        default=None,
        help="Where to save the training loss chart. Defaults to a simulator-specific chart for simulator data.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    success = train(
        args.csv,
        dataset_format=args.format,
        images_dir=args.images_dir,
        train_csv_path=args.train_csv,
        validation_csv_path=args.validation_csv,
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
    raise SystemExit(0 if success else 1)
