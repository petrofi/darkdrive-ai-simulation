from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

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
from src.training.train_behavior_cloning import (
    DrivingDataset,
    choose_device,
    split_data_frame,
)
from src.utils.driving_log import (
    filter_rows_with_existing_images,
    load_driving_log,
    primary_image_column,
    resolve_image_path,
)
from src.utils.image_preprocessing import (
    BASELINE_PROFILE,
    VALID_PREPROCESSING_PROFILES,
    preprocessing_metadata,
    resolve_preprocessing_profile,
)


NEAR_ZERO_ABS = 0.05
STRONG_TURN_ABS = 0.5
STEERING_BINS = [
    ("0.00-0.05", 0.0, 0.05, True),
    ("0.05-0.25", 0.05, 0.25, False),
    ("0.25-0.50", 0.25, 0.50, False),
    ("0.50-1.00", 0.50, 1.00, False),
]


def load_checkpoint(model_path: Path) -> object | None:
    try:
        return torch.load(model_path, map_location="cpu", weights_only=True)
    except TypeError:
        return torch.load(model_path, map_location="cpu")
    except Exception as exc:
        print(f"Could not safely load checkpoint: {exc}")
        return None


def load_model(model_path: Path, device: torch.device) -> tuple[SteeringModel, object] | None:
    if not model_path.exists():
        print(f"Model not found: {model_path}")
        print("Train the model on validated simulator data before evaluation.")
        return None

    checkpoint = load_checkpoint(model_path)
    if checkpoint is None:
        return None
    state_dict = checkpoint.get("model_state_dict", checkpoint) if isinstance(checkpoint, dict) else checkpoint

    model = SteeringModel().to(device)
    try:
        model.load_state_dict(state_dict)
    except RuntimeError as exc:
        print(f"Could not load model checkpoint: {exc}")
        return None

    model.eval()
    return model, checkpoint


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


def numeric_or_none(value: float) -> float | None:
    if np.isnan(value) or np.isinf(value):
        return None
    return float(value)


def regression_metrics(predictions: np.ndarray, actuals: np.ndarray) -> dict[str, float | None]:
    if len(actuals) == 0:
        return {"mae": None, "rmse": None, "signed_bias": None}
    errors = predictions - actuals
    return {
        "mae": float(np.mean(np.abs(errors))),
        "rmse": float(np.sqrt(np.mean(errors**2))),
        "signed_bias": float(np.mean(errors)),
    }


def subgroup_metrics(
    predictions: np.ndarray,
    actuals: np.ndarray,
    mask: np.ndarray,
) -> dict[str, float | int | None]:
    selected_predictions = predictions[mask]
    selected_actuals = actuals[mask]
    metrics = regression_metrics(selected_predictions, selected_actuals)
    return {"count": int(mask.sum()), **metrics}


def direction_error_metrics(predictions: np.ndarray, actuals: np.ndarray) -> dict[str, float | int]:
    mask = np.abs(actuals) > NEAR_ZERO_ABS
    count = int(mask.sum())
    if count == 0:
        return {"count": 0, "incorrect_count": 0, "incorrect_pct": 0.0}

    prediction_signs = np.sign(predictions[mask])
    actual_signs = np.sign(actuals[mask])
    incorrect_count = int((prediction_signs != actual_signs).sum())
    return {
        "count": count,
        "incorrect_count": incorrect_count,
        "incorrect_pct": incorrect_count / count * 100.0,
    }


def bin_mask(actuals: np.ndarray, lower: float, upper: float, include_lower: bool) -> np.ndarray:
    absolute = np.abs(actuals)
    if include_lower:
        return (absolute >= lower) & (absolute <= upper)
    return (absolute > lower) & (absolute <= upper)


def calculate_metrics(
    predictions: np.ndarray,
    actuals: np.ndarray,
    source_sessions: pd.Series | None = None,
) -> dict[str, Any]:
    overall = regression_metrics(predictions, actuals)
    zero_baseline_mae = float(np.mean(np.abs(actuals))) if len(actuals) else 0.0
    mae = overall["mae"] or 0.0
    improvement = zero_baseline_mae - mae
    improvement_pct = improvement / zero_baseline_mae * 100.0 if zero_baseline_mae else 0.0
    prediction_std = float(np.std(predictions, ddof=1)) if len(predictions) > 1 else 0.0
    actual_std = float(np.std(actuals, ddof=1)) if len(actuals) > 1 else 0.0
    std_ratio = prediction_std / actual_std if actual_std else 0.0

    near_zero_mask = np.abs(actuals) <= NEAR_ZERO_ABS
    left_mask = actuals < -NEAR_ZERO_ABS
    right_mask = actuals > NEAR_ZERO_ABS
    strong_turn_mask = np.abs(actuals) >= STRONG_TURN_ABS

    steering_bins = {
        label: subgroup_metrics(predictions, actuals, bin_mask(actuals, lower, upper, include_lower))
        for label, lower, upper, include_lower in STEERING_BINS
    }

    source_metrics: dict[str, dict[str, float | int | None]] = {}
    if source_sessions is not None:
        for source_session in sorted(source_sessions.dropna().astype(str).unique()):
            mask = source_sessions.astype(str).to_numpy() == source_session
            source_metrics[source_session] = subgroup_metrics(predictions, actuals, mask)

    return {
        "sample_count": int(len(actuals)),
        "overall": overall,
        "zero_baseline_mae": zero_baseline_mae,
        "mae_improvement_over_zero": improvement,
        "mae_improvement_over_zero_pct": improvement_pct,
        "near_zero": subgroup_metrics(predictions, actuals, near_zero_mask),
        "left": subgroup_metrics(predictions, actuals, left_mask),
        "right": subgroup_metrics(predictions, actuals, right_mask),
        "strong_turn": subgroup_metrics(predictions, actuals, strong_turn_mask),
        "prediction_mean": float(np.mean(predictions)) if len(predictions) else 0.0,
        "prediction_std": prediction_std,
        "actual_mean": float(np.mean(actuals)) if len(actuals) else 0.0,
        "actual_std": actual_std,
        "prediction_actual_std_ratio": std_ratio,
        "signed_bias": overall["signed_bias"],
        "direction_error": direction_error_metrics(predictions, actuals),
        "steering_bins": steering_bins,
        "source_sessions": source_metrics,
    }


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


def save_error_by_bin_plot(metrics: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    labels = list(metrics["steering_bins"].keys())
    maes = [
        metrics["steering_bins"][label]["mae"]
        if metrics["steering_bins"][label]["mae"] is not None
        else 0.0
        for label in labels
    ]
    counts = [metrics["steering_bins"][label]["count"] for label in labels]

    plt.figure(figsize=(8, 5))
    bars = plt.bar(labels, maes, color="#16a34a", alpha=0.85)
    plt.title("MAE by Steering Magnitude Bin")
    plt.xlabel("abs(actual steering)")
    plt.ylabel("MAE")
    plt.grid(True, axis="y", alpha=0.25)
    for bar, count in zip(bars, counts):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"n={count}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f"Saved error-by-bin plot: {output_path}")


def save_prediction_samples(
    data: pd.DataFrame,
    predictions: np.ndarray,
    actuals: np.ndarray,
    csv_path: Path,
    images_dir: Path | None,
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


def default_output_paths(model_path: Path, csv_path: Path) -> tuple[Path, Path, Path]:
    model_stem = model_path.stem
    csv_text = str(csv_path).replace("\\", "/").lower()
    if "data/processed/local_v3_training" in csv_text and not model_stem.startswith(
        "steering_model_local_v3"
    ):
        return (
            Path(f"screenshots/prediction_vs_actual_{model_stem}_on_local_v3.png"),
            Path(f"screenshots/prediction_samples_{model_stem}_on_local_v3.png"),
            Path(f"screenshots/error_by_steering_bin_{model_stem}_on_local_v3.png"),
        )
    if model_stem.startswith("steering_model_local_v3") and model_stem != "steering_model_local_v3":
        return (
            Path(f"screenshots/prediction_vs_actual_{model_stem}.png"),
            Path(f"screenshots/prediction_samples_{model_stem}.png"),
            Path(f"screenshots/error_by_steering_bin_{model_stem}.png"),
        )
    if model_stem == "steering_model_local_v3" or "data/processed/local_v3_training" in csv_text:
        return (
            Path("screenshots/prediction_vs_actual_local_v3.png"),
            Path("screenshots/prediction_samples_local_v3.png"),
            Path("screenshots/error_by_steering_bin_local_v3.png"),
        )
    if model_stem == "steering_model_local_v2" or "data/processed/local_v2_training" in csv_text:
        return (
            Path("screenshots/prediction_vs_actual_local_v2.png"),
            Path("screenshots/prediction_samples_local_v2.png"),
            Path("screenshots/error_by_steering_bin_local_v2.png"),
        )
    if model_stem == "steering_model_merged_v1" or "data/processed/merged_training" in csv_text:
        return (
            Path("screenshots/prediction_vs_actual_merged_v1.png"),
            Path("screenshots/prediction_samples_merged_v1.png"),
            Path("screenshots/error_by_steering_bin_merged_v1.png"),
        )
    return (
        Path("screenshots/prediction_vs_actual.png"),
        Path("screenshots/prediction_samples.png"),
        Path("screenshots/error_by_steering_bin.png"),
    )


def load_evaluation_frame(
    csv_path: Path,
    images_dir: Path | None,
    dataset_format: str,
    validation_split: float,
    seed: int,
    validation_csv: Path | None = None,
) -> tuple[pd.DataFrame | None, Path, bool]:
    evaluation_csv = validation_csv or csv_path
    split_mode_explicit = validation_csv is not None
    if not evaluation_csv.exists():
        print(f"Evaluation CSV not found: {evaluation_csv}")
        return None, evaluation_csv, split_mode_explicit

    try:
        data = load_driving_log(evaluation_csv, dataset_format)
    except Exception as exc:
        print(f"Could not read evaluation log: {exc}")
        return None, evaluation_csv, split_mode_explicit

    if len(data) == 0:
        print("Evaluation log is empty.")
        return None, evaluation_csv, split_mode_explicit

    invalid_steering = int(data["steering"].isna().sum())
    if invalid_steering:
        print(f"Evaluation log has invalid steering values: {invalid_steering}")
        return None, evaluation_csv, split_mode_explicit

    data, missing_images = filter_rows_with_existing_images(
        data,
        evaluation_csv,
        images_dir,
        dataset_format,
    )
    if missing_images:
        print(f"Evaluation log has missing center images: {missing_images}")
        return None, evaluation_csv, split_mode_explicit

    if len(data) == 0:
        print("No usable rows available for evaluation.")
        return None, evaluation_csv, split_mode_explicit

    if split_mode_explicit:
        return data.reset_index(drop=True), evaluation_csv, split_mode_explicit

    _, validation_data = split_data_frame(data, validation_split, seed)
    return validation_data.reset_index(drop=True), evaluation_csv, split_mode_explicit


def print_metrics(metrics: dict[str, Any]) -> None:
    print("Evaluation summary:")
    print(f"- Rows evaluated: {metrics['sample_count']}")
    print(f"- MAE: {metrics['overall']['mae']:.6f}")
    print(f"- RMSE: {metrics['overall']['rmse']:.6f}")
    print(f"- Zero-steering baseline MAE: {metrics['zero_baseline_mae']:.6f}")
    print(
        "- MAE improvement over zero baseline: "
        f"{metrics['mae_improvement_over_zero']:.6f} "
        f"({metrics['mae_improvement_over_zero_pct']:.2f}%)"
    )
    print(f"- Prediction mean/std: {metrics['prediction_mean']:.6f} / {metrics['prediction_std']:.6f}")
    print(f"- Actual mean/std: {metrics['actual_mean']:.6f} / {metrics['actual_std']:.6f}")
    print(f"- Prediction/actual std ratio: {metrics['prediction_actual_std_ratio']:.6f}")
    print(f"- Signed bias mean(prediction - actual): {metrics['signed_bias']:.6f}")
    print(
        "- Incorrect direction where abs(actual)>0.05: "
        f"{metrics['direction_error']['incorrect_count']}/{metrics['direction_error']['count']} "
        f"({metrics['direction_error']['incorrect_pct']:.2f}%)"
    )

    print("Subgroup metrics:")
    for label in ["near_zero", "left", "right", "strong_turn"]:
        group = metrics[label]
        mae = "N/A" if group["mae"] is None else f"{group['mae']:.6f}"
        rmse = "N/A" if group["rmse"] is None else f"{group['rmse']:.6f}"
        print(f"- {label}: count={group['count']} MAE={mae} RMSE={rmse}")

    print("Steering magnitude bin metrics:")
    for label, group in metrics["steering_bins"].items():
        mae = "N/A" if group["mae"] is None else f"{group['mae']:.6f}"
        print(f"- {label}: count={group['count']} MAE={mae}")

    if metrics["source_sessions"]:
        print("Source-session metrics:")
        for source_session, group in metrics["source_sessions"].items():
            mae = "N/A" if group["mae"] is None else f"{group['mae']:.6f}"
            rmse = "N/A" if group["rmse"] is None else f"{group['rmse']:.6f}"
            print(f"- {source_session}: count={group['count']} MAE={mae} RMSE={rmse}")


def evaluate_model(
    model_path: Path,
    csv_path: Path,
    images_dir: Path | None,
    dataset_format: str,
    batch_size: int,
    validation_split: float,
    device_name: str,
    seed: int,
    validation_csv: Path | None = None,
    metrics_json: Path | None = None,
    preprocessing_profile: str = "checkpoint",
) -> dict[str, Any] | None:
    print("DarkDrive steering model evaluation")
    print("Simulation-only evaluation. No real vehicle control is used.")

    device = choose_device(device_name)
    loaded_model = load_model(model_path, device)
    if loaded_model is None:
        return None
    model, checkpoint = loaded_model
    resolved_preprocessing_profile = resolve_preprocessing_profile(preprocessing_profile, checkpoint)

    evaluation_data, evaluation_csv, explicit_validation = load_evaluation_frame(
        csv_path,
        images_dir,
        dataset_format,
        validation_split,
        seed,
        validation_csv=validation_csv,
    )
    if evaluation_data is None:
        return None

    validation_dataset = DrivingDataset(
        evaluation_csv,
        dataset_format=dataset_format,
        images_dir=images_dir,
        data_frame=evaluation_data,
        augment=False,
        preprocessing_profile=resolved_preprocessing_profile,
    )
    validation_loader = DataLoader(validation_dataset, batch_size=batch_size, shuffle=False)

    predictions, actuals = collect_predictions(model, validation_loader, device)
    source_sessions = evaluation_data["source_session"] if "source_session" in evaluation_data.columns else None
    metrics = calculate_metrics(predictions, actuals, source_sessions)

    prediction_plot_path, prediction_samples_path, error_bin_plot_path = default_output_paths(
        model_path,
        evaluation_csv,
    )
    save_prediction_plot(predictions, actuals, prediction_plot_path)
    save_prediction_samples(
        evaluation_data,
        predictions,
        actuals,
        evaluation_csv,
        images_dir,
        prediction_samples_path,
    )
    save_error_by_bin_plot(metrics, error_bin_plot_path)

    metrics["model_path"] = str(model_path)
    metrics["evaluation_csv"] = str(evaluation_csv)
    metrics["explicit_validation_manifest"] = explicit_validation
    metrics["preprocessing_profile"] = resolved_preprocessing_profile
    metrics["preprocessing"] = preprocessing_metadata(resolved_preprocessing_profile)
    metrics["device"] = str(device)
    metrics["artifacts"] = {
        "prediction_plot": str(prediction_plot_path),
        "prediction_samples": str(prediction_samples_path),
        "error_by_steering_bin": str(error_bin_plot_path),
    }

    print_metrics(metrics)
    print(f"- Preprocessing profile: {resolved_preprocessing_profile}")
    print(f"- Preprocessing metadata: {preprocessing_metadata(resolved_preprocessing_profile)}")
    print(f"- Device: {device}")
    print(f"- Split mode: {'explicit validation manifest' if explicit_validation else 'random row split'}")

    if metrics_json is not None:
        metrics_json.parent.mkdir(parents=True, exist_ok=True)
        metrics_json.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        print(f"Saved metrics JSON: {metrics_json}")

    return metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a trained simulator steering model.")
    parser.add_argument("--model", default="models/steering_model_sim_v1.pt")
    parser.add_argument("--csv", default="data/processed/simulator/driving_log.csv")
    parser.add_argument(
        "--validation-csv",
        default=None,
        help="Explicit validation manifest. When supplied, no random split is performed.",
    )
    parser.add_argument("--images-dir", default=None)
    parser.add_argument("--format", default="udacity", choices=["simple", "udacity"])
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--validation-split", type=float, default=0.2)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--preprocessing-profile",
        choices=("checkpoint", *VALID_PREPROCESSING_PROFILES),
        default="checkpoint",
        help=(
            "Image preprocessing profile. Use checkpoint to read checkpoint metadata; "
            f"old checkpoints default to {BASELINE_PROFILE}."
        ),
    )
    parser.add_argument(
        "--metrics-json",
        default=None,
        help="Optional ignored JSON output path for evaluation metrics.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    metrics = evaluate_model(
        Path(args.model),
        Path(args.csv),
        Path(args.images_dir) if args.images_dir else None,
        args.format,
        args.batch_size,
        args.validation_split,
        args.device,
        args.seed,
        validation_csv=Path(args.validation_csv) if args.validation_csv else None,
        metrics_json=Path(args.metrics_json) if args.metrics_json else None,
        preprocessing_profile=args.preprocessing_profile,
    )
    raise SystemExit(0 if metrics is not None else 1)
