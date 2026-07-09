from __future__ import annotations

import torch
from torch import nn


MODEL_ARCH_BASELINE = "baseline"
MODEL_ARCH_CNN_V2 = "cnn_v2"
VALID_MODEL_ARCHES = (MODEL_ARCH_BASELINE, MODEL_ARCH_CNN_V2)


class SteeringModel(nn.Module):
    """Beginner-friendly CNN for simulation behavior cloning.

    The model accepts RGB image tensors shaped like:
        batch_size x 3 x image_height x image_width

    It outputs one continuous steering value per image. The architecture is
    inspired by classic behavior cloning demos, but it stays intentionally
    compact so it is easy to read and train locally.

    This model is for simulation and education only. It is not real vehicle
    control code.
    """

    def __init__(self) -> None:
        super().__init__()

        # Convolution layers learn road, horizon, and lane-marking features.
        self.features = nn.Sequential(
            nn.Conv2d(3, 24, kernel_size=5, stride=2),
            nn.ELU(),
            nn.Conv2d(24, 36, kernel_size=5, stride=2),
            nn.ELU(),
            nn.Conv2d(36, 48, kernel_size=5, stride=2),
            nn.ELU(),
            nn.Conv2d(48, 64, kernel_size=3, stride=1),
            nn.ELU(),
            nn.Conv2d(64, 64, kernel_size=3, stride=1),
            nn.ELU(),
            nn.AdaptiveAvgPool2d((2, 4)),
        )

        # Regression layers convert visual features into one steering value.
        self.regressor = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(p=0.2),
            nn.Linear(64 * 2 * 4, 100),
            nn.ELU(),
            nn.Dropout(p=0.2),
            nn.Linear(100, 50),
            nn.ELU(),
            nn.Linear(50, 10),
            nn.ELU(),
            nn.Linear(10, 1),
        )

    def forward(self, images: torch.Tensor) -> torch.Tensor:
        """Predict one steering value for each image in the batch."""
        # Training code provides pixels in [0, 1]. Centering helps optimization.
        images = images * 2.0 - 1.0
        features = self.features(images)
        return self.regressor(features)


class SteeringModelV2(nn.Module):
    """Slightly stronger single-frame CNN for simulator steering regression.

    The model keeps the same RGB image input contract and one-value steering
    output as ``SteeringModel``. It adds more convolutional channels, one extra
    spatial block, BatchNorm2d, and a wider MLP head while remaining lightweight
    enough for CPU-only offline experiments.
    """

    def __init__(self) -> None:
        super().__init__()

        self.features = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=5, stride=2),
            nn.BatchNorm2d(32),
            nn.ELU(),
            nn.Conv2d(32, 48, kernel_size=5, stride=2),
            nn.BatchNorm2d(48),
            nn.ELU(),
            nn.Conv2d(48, 64, kernel_size=5, stride=2),
            nn.BatchNorm2d(64),
            nn.ELU(),
            nn.Conv2d(64, 96, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(96),
            nn.ELU(),
            nn.Conv2d(96, 128, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(128),
            nn.ELU(),
            nn.Conv2d(128, 128, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(128),
            nn.ELU(),
            nn.AdaptiveAvgPool2d((2, 4)),
        )

        self.regressor = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(p=0.25),
            nn.Linear(128 * 2 * 4, 256),
            nn.ELU(),
            nn.Dropout(p=0.25),
            nn.Linear(256, 100),
            nn.ELU(),
            nn.Linear(100, 50),
            nn.ELU(),
            nn.Linear(50, 10),
            nn.ELU(),
            nn.Linear(10, 1),
        )

    def forward(self, images: torch.Tensor) -> torch.Tensor:
        """Predict one unconstrained steering value for each image."""
        images = images * 2.0 - 1.0
        features = self.features(images)
        return self.regressor(features)


def validate_model_arch(model_arch: str) -> str:
    if model_arch not in VALID_MODEL_ARCHES:
        valid = ", ".join(VALID_MODEL_ARCHES)
        raise ValueError(f"Unsupported model architecture: {model_arch}. Valid architectures: {valid}")
    return model_arch


def make_steering_model(model_arch: str = MODEL_ARCH_BASELINE) -> nn.Module:
    model_arch = validate_model_arch(model_arch)
    if model_arch == MODEL_ARCH_CNN_V2:
        return SteeringModelV2()
    return SteeringModel()


def model_arch_from_checkpoint(checkpoint: object) -> str:
    if not isinstance(checkpoint, dict):
        return MODEL_ARCH_BASELINE

    for key in ("model_arch", "model_architecture", "model_class"):
        value = checkpoint.get(key)
        if isinstance(value, str):
            normalized = normalize_model_arch(value)
            if normalized is not None:
                return normalized
            raise ValueError(f"Unsupported model architecture in checkpoint metadata: {value}")

    training_args = checkpoint.get("training_args")
    if isinstance(training_args, dict):
        for key in ("model_arch", "model_architecture"):
            value = training_args.get(key)
            if isinstance(value, str):
                normalized = normalize_model_arch(value)
                if normalized is not None:
                    return normalized
                raise ValueError(f"Unsupported model architecture in training metadata: {value}")

    return MODEL_ARCH_BASELINE


def normalize_model_arch(value: str) -> str | None:
    if value in VALID_MODEL_ARCHES:
        return value
    if value == "SteeringModel":
        return MODEL_ARCH_BASELINE
    if value in {"SteeringModelV2", "StrongerSteeringModel"}:
        return MODEL_ARCH_CNN_V2
    return None


def resolve_model_arch(requested_model_arch: str, checkpoint: object | None = None) -> str:
    if requested_model_arch == "checkpoint":
        return model_arch_from_checkpoint(checkpoint)
    return validate_model_arch(requested_model_arch)
