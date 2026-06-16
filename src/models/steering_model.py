from __future__ import annotations

import torch
from torch import nn


class SteeringModel(nn.Module):
    """A small baseline CNN for behavior cloning steering prediction.

    This first version is intentionally simple: it accepts an image tensor and
    outputs one steering value. It is meant for simulation experiments only.
    """

    def __init__(self) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 16, kernel_size=5, stride=2),
            nn.ReLU(),
            nn.Conv2d(16, 32, kernel_size=5, stride=2),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, stride=2),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((4, 4)),
        )
        self.regressor = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 4 * 4, 100),
            nn.ReLU(),
            nn.Linear(100, 1),
        )

    def forward(self, images: torch.Tensor) -> torch.Tensor:
        features = self.features(images)
        return self.regressor(features)
