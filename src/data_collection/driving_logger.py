from __future__ import annotations

import csv
from pathlib import Path


class DrivingLogger:
    """Write simulation driving samples to a CSV file."""

    FIELDNAMES = ["frame_path", "steering", "throttle", "brake", "speed"]

    def __init__(self, log_path: str | Path) -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_header()

    def _ensure_header(self) -> None:
        if not self.log_path.exists() or self.log_path.stat().st_size == 0:
            with self.log_path.open("w", newline="", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=self.FIELDNAMES)
                writer.writeheader()

    def log_frame(
        self,
        frame_path: str | Path,
        steering: float,
        throttle: float,
        brake: float,
        speed: float,
    ) -> None:
        """Append one simulated driving frame and control row."""
        with self.log_path.open("a", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=self.FIELDNAMES)
            writer.writerow(
                {
                    "frame_path": str(frame_path),
                    "steering": steering,
                    "throttle": throttle,
                    "brake": brake,
                    "speed": speed,
                }
            )


if __name__ == "__main__":
    logger = DrivingLogger("data/raw/driving_log.csv")
    logger.log_frame(
        frame_path="data/raw/frame_000001.png",
        steering=0.05,
        throttle=0.4,
        brake=0.0,
        speed=12.3,
    )
    print(f"Example driving row written to {logger.log_path}")
