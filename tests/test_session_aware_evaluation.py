from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluate_steering_model import calculate_metrics  # noqa: E402


class SessionAwareEvaluationTests(unittest.TestCase):
    def test_overall_and_zero_baseline_metrics(self) -> None:
        predictions = np.array([0.0, 0.2, -0.4], dtype=np.float32)
        actuals = np.array([0.0, 0.4, -0.2], dtype=np.float32)
        metrics = calculate_metrics(predictions, actuals)

        self.assertEqual(metrics["sample_count"], 3)
        self.assertAlmostEqual(metrics["overall"]["mae"], (0.0 + 0.2 + 0.2) / 3)
        self.assertAlmostEqual(metrics["overall"]["rmse"], np.sqrt((0.0**2 + 0.2**2 + 0.2**2) / 3))
        self.assertAlmostEqual(metrics["zero_baseline_mae"], np.mean(np.abs(actuals)))
        self.assertGreater(metrics["mae_improvement_over_zero"], 0)

    def test_subgroup_counts_and_empty_groups(self) -> None:
        predictions = np.array([0.0, 0.1, -0.3], dtype=np.float32)
        actuals = np.array([0.0, 0.2, 0.3], dtype=np.float32)
        metrics = calculate_metrics(predictions, actuals)

        self.assertEqual(metrics["near_zero"]["count"], 1)
        self.assertEqual(metrics["left"]["count"], 0)
        self.assertIsNone(metrics["left"]["mae"])
        self.assertEqual(metrics["right"]["count"], 2)
        self.assertEqual(metrics["strong_turn"]["count"], 0)

    def test_steering_bins_and_direction_error(self) -> None:
        predictions = np.array([0.0, -0.1, 0.2, -0.9], dtype=np.float32)
        actuals = np.array([0.03, 0.2, 0.4, -0.8], dtype=np.float32)
        metrics = calculate_metrics(predictions, actuals)

        self.assertEqual(metrics["steering_bins"]["0.00-0.05"]["count"], 1)
        self.assertEqual(metrics["steering_bins"]["0.05-0.25"]["count"], 1)
        self.assertEqual(metrics["steering_bins"]["0.25-0.50"]["count"], 1)
        self.assertEqual(metrics["steering_bins"]["0.50-1.00"]["count"], 1)
        self.assertEqual(metrics["direction_error"]["count"], 3)
        self.assertEqual(metrics["direction_error"]["incorrect_count"], 1)

    def test_source_session_aggregation(self) -> None:
        predictions = np.array([0.0, 0.2, -0.2, 0.4], dtype=np.float32)
        actuals = np.array([0.0, 0.1, -0.3, 0.7], dtype=np.float32)
        sessions = pd.Series(["a", "a", "b", "b"])
        metrics = calculate_metrics(predictions, actuals, sessions)

        self.assertEqual(metrics["source_sessions"]["a"]["count"], 2)
        self.assertEqual(metrics["source_sessions"]["b"]["count"], 2)
        self.assertAlmostEqual(metrics["source_sessions"]["b"]["mae"], (0.1 + 0.3) / 2)


if __name__ == "__main__":
    unittest.main()
