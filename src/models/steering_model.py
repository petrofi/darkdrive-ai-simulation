from __future__ import annotations

import torch
from torch import nn


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
