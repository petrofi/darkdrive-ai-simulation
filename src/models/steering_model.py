from __future__ import annotations

import torch
from torch import nn


class SteeringModel(nn.Module):
    """Baseline CNN for simulation behavior cloning.

    The model accepts RGB image tensors shaped like:
        batch_size x 3 x image_height x image_width

    It outputs one continuous steering value per image. This is intentionally
    small and beginner-friendly, and it is only for simulation experiments.
    """

    def __init__(self) -> None:
        super().__init__()

        # Convolution layers learn simple visual features from simulated camera images.
        self.features = nn.Sequential(
            nn.Conv2d(3, 16, kernel_size=5, stride=2),
            nn.ReLU(),
            nn.Conv2d(16, 32, kernel_size=5, stride=2),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, stride=2),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((4, 4)),
        )

        # Regression layers convert visual features into one steering value.
        self.regressor = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 4 * 4, 100),
            nn.ReLU(),
            nn.Linear(100, 1),
        )

    def forward(self, images: torch.Tensor) -> torch.Tensor:
        """Predict one steering value for each image in the batch."""
        features = self.features(images)
        return self.regressor(features)
