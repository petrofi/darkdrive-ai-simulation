from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.steering_model import SteeringModel
from src.training.train_behavior_cloning import DrivingDataset, choose_device, split_data_frame
from src.utils.driving_log import (
    filter_rows_with_existing_images,
    load_driving_log,
    primary_image_column,
    resolve_image_path,
)


def load_checkpoint(model_path: Path) -> object:
    try:
        return torch.load(model_path, map_location="cpu", weights_only=True)
    except TypeError:
        return torch.load(model_path, map_location="cpu")


def load_model(model_path: Path, device: torch.device) -> SteeringModel | None:
    if not model_path.exists():
        print(f"Model not found: {model_path}")
        print("Train the model on validated simulator data before evaluation.")
        return None

    checkpoint = load_checkpoint(model_path)
    state_dict = checkpoint.get("model_state_dict", checkpoint) if isinstance(checkpoint, dict) else checkpoint

    model = SteeringModel().to(device)
    try:
        model.load_state_dict(state_dict)
    except RuntimeError as exc:
        print(f"Could not load model checkpoint: {exc}")
        return None

    model.eval()
    return model


def collect_predictions(
    model: SteeringModel,
    data_loader: DataLoader,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray]:
    predictions: list[float] = []
    actuals: list[float] = []

    with torch.no_grad():
        for images, steering in data_loader:
            images = images.to(device)
            outputs = model(images).detach().cpu().numpy().reshape(-1)
            labels = steering.numpy().reshape(-1)
            predictions.extend(outputs.tolist())
            actuals.extend(labels.tolist())

    return np.array(predictions, dtype=np.float32), np.array(actuals, dtype=np.float32)


def save_prediction_plot(predictions: np.ndarray, actuals: np.ndarray, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 6))
    plt.scatter(actuals, predictions, s=12, alpha=0.6, color="#2563eb")
    min_value = float(min(actuals.min(), predictions.min()))
    max_value = float(max(actuals.max(), predictions.max()))
    plt.plot([min_value, max_value], [min_value, max_value], color="#dc2626", linestyle="--")
    plt.title("Predicted Steering vs Actual Steering")
    plt.xlabel("Actual steering")
    plt.ylabel("Predicted steering")
    plt.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f"Saved prediction plot: {output_path}")


def save_prediction_samples(
    data: pd.DataFrame,
    predictions: np.ndarray,
    actuals: np.ndarray,
    csv_path: Path,
    images_dir: Path,
    output_path: Path,
    max_images: int = 12,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sample_count = min(max_images, len(data), len(predictions))
    if sample_count == 0:
        print("No prediction samples available.")
        return

    indices = np.linspace(0, len(data) - 1, sample_count, dtype=int)
    columns = 4
    rows = math.ceil(sample_count / columns)
    plt.figure(figsize=(12, rows * 3))
    path_column = primary_image_column("udacity" if "center" in data.columns else "simple")

    for plot_index, data_index in enumerate(indices, start=1):
        row = data.iloc[data_index]
        image_path = resolve_image_path(row[path_column], csv_path, images_dir)
        image = cv2.imread(str(image_path))
        if image is None:
            continue

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        plt.subplot(rows, columns, plot_index)
        plt.imshow(image)
        plt.axis("off")
        plt.title(
            f"pred={predictions[data_index]:.3f}\nactual={actuals[data_index]:.3f}",
            fontsize=9,
        )

    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f"Saved prediction sample grid: {output_path}")


def default_output_paths(model_path: Path, csv_path: Path) -> tuple[Path, Path]:
    model_stem = model_path.stem
    csv_text = str(csv_path).replace("\\", "/").lower()
    if model_stem == "steering_model_merged_v1" or "data/processed/merged_training" in csv_text:
        return (
            Path("screenshots/prediction_vs_actual_merged_v1.png"),
            Path("screenshots/prediction_samples_merged_v1.png"),
        )
    return (
        Path("screenshots/prediction_vs_actual.png"),
        Path("screenshots/prediction_samples.png"),
    )


def evaluate_model(
    model_path: Path,
    csv_path: Path,
    images_dir: Path,
    dataset_format: str,
    batch_size: int,
    validation_split: float,
    device_name: str,
    seed: int,
) -> bool:
    print("DarkDrive steering model evaluation")
    print("Simulation-only evaluation. No real vehicle control is used.")

    device = choose_device(device_name)
    model = load_model(model_path, device)
    if model is None:
        return False

    try:
        data = load_driving_log(csv_path, dataset_format)
    except Exception as exc:
        print(f"Could not read driving log: {exc}")
        return False

    data = data.dropna(subset=["steering"]).reset_index(drop=True)
    data, missing_images = filter_rows_with_existing_images(
        data,
        csv_path,
        images_dir,
        dataset_format,
    )
    if missing_images:
        print(f"Skipping rows with missing center images: {missing_images}")

    if len(data) == 0:
        print("No usable rows available for evaluation.")
        return False

    _, validation_data = split_data_frame(data, validation_split, seed)
    validation_dataset = DrivingDataset(
        csv_path,
        dataset_format=dataset_format,
        images_dir=images_dir,
        data_frame=validation_data,
        augment=False,
    )
    validation_loader = DataLoader(validation_dataset, batch_size=batch_size, shuffle=False)

    predictions, actuals = collect_predictions(model, validation_loader, device)
    errors = predictions - actuals
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors**2)))
    prediction_plot_path, prediction_samples_path = default_output_paths(model_path, csv_path)

    save_prediction_plot(predictions, actuals, prediction_plot_path)
    save_prediction_samples(
        validation_data,
        predictions,
        actuals,
        csv_path,
        images_dir,
        prediction_samples_path,
    )

    print("Evaluation summary:")
    print(f"- Rows evaluated: {len(actuals)}")
    print(f"- MAE: {mae:.6f}")
    print(f"- RMSE: {rmse:.6f}")
    print(f"- Device: {device}")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a trained simulator steering model.")
    parser.add_argument("--model", default="models/steering_model_sim_v1.pt")
    parser.add_argument("--csv", default="data/processed/simulator/driving_log.csv")
    parser.add_argument("--images-dir", default="data/processed/simulator/IMG")
    parser.add_argument("--format", default="udacity", choices=["simple", "udacity"])
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--validation-split", type=float, default=0.2)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    success = evaluate_model(
        Path(args.model),
        Path(args.csv),
        Path(args.images_dir),
        args.format,
        args.batch_size,
        args.validation_split,
        args.device,
        args.seed,
    )
    raise SystemExit(0 if success else 1)
