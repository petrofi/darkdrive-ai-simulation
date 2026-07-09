from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluate_steering_model import load_model  # noqa: E402
from src.models.steering_model import (  # noqa: E402
    MODEL_ARCH_BASELINE,
    MODEL_ARCH_CNN_V2,
    SteeringModel,
    SteeringModelV2,
    make_steering_model,
    model_arch_from_checkpoint,
)
from src.training.train_behavior_cloning import (  # noqa: E402
    LOSS_MSE,
    count_parameters,
    loss_metadata,
    save_checkpoint,
)
from src.utils.image_preprocessing import BASELINE_PROFILE  # noqa: E402


class ModelArchitectureTests(unittest.TestCase):
    def test_factory_builds_supported_architectures(self) -> None:
        self.assertIsInstance(make_steering_model(MODEL_ARCH_BASELINE), SteeringModel)
        self.assertIsInstance(make_steering_model(MODEL_ARCH_CNN_V2), SteeringModelV2)

    def test_supported_architectures_keep_forward_contract(self) -> None:
        images = torch.rand(2, 3, 80, 160)

        for model_arch in (MODEL_ARCH_BASELINE, MODEL_ARCH_CNN_V2):
            model = make_steering_model(model_arch)
            model.eval()
            with torch.no_grad():
                outputs = model(images)

            self.assertEqual(outputs.shape, (2, 1))
            self.assertFalse(torch.isnan(outputs).any())

    def test_cnn_v2_is_stronger_but_still_lightweight(self) -> None:
        baseline_params = count_parameters(make_steering_model(MODEL_ARCH_BASELINE))
        cnn_v2_params = count_parameters(make_steering_model(MODEL_ARCH_CNN_V2))

        self.assertGreater(cnn_v2_params, baseline_params)
        self.assertGreaterEqual(cnn_v2_params, 400_000)
        self.assertLess(cnn_v2_params, 1_500_000)

    def test_unsupported_architecture_fails_clearly(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported model architecture"):
            make_steering_model("wide_resnet")

    def test_checkpoint_metadata_stores_model_architecture(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output_path = Path(temp) / "cnn_v2.pt"
            model = make_steering_model(MODEL_ARCH_CNN_V2)

            save_checkpoint(
                model,
                output_path,
                args={
                    "loss": LOSS_MSE,
                    "loss_metadata": loss_metadata(LOSS_MSE),
                    "model_arch": MODEL_ARCH_CNN_V2,
                },
                history={"training_loss": [], "validation_loss": []},
                preprocessing_profile=BASELINE_PROFILE,
                model_arch=MODEL_ARCH_CNN_V2,
            )

            checkpoint = torch.load(output_path, map_location="cpu", weights_only=True)
            self.assertEqual(checkpoint["model_arch"], MODEL_ARCH_CNN_V2)
            self.assertEqual(checkpoint["model_class"], "SteeringModelV2")
            self.assertEqual(checkpoint["model_architecture"], "SteeringModelV2")
            self.assertEqual(checkpoint["training_args"]["model_arch"], MODEL_ARCH_CNN_V2)

    def test_evaluator_loads_baseline_and_cnn_v2_checkpoints(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            device = torch.device("cpu")

            for model_arch in (MODEL_ARCH_BASELINE, MODEL_ARCH_CNN_V2):
                model = make_steering_model(model_arch)
                output_path = root / f"{model_arch}.pt"
                save_checkpoint(
                    model,
                    output_path,
                    args={"loss_metadata": loss_metadata(LOSS_MSE), "model_arch": model_arch},
                    history={"training_loss": [], "validation_loss": []},
                    preprocessing_profile=BASELINE_PROFILE,
                    model_arch=model_arch,
                )

                loaded = load_model(output_path, device)
                self.assertIsNotNone(loaded)
                loaded_model, _, resolved_model_arch = loaded
                self.assertEqual(resolved_model_arch, model_arch)
                self.assertEqual(
                    count_parameters(loaded_model),
                    count_parameters(make_steering_model(model_arch)),
                )

    def test_checkpoint_architecture_resolution_is_backward_compatible(self) -> None:
        self.assertEqual(model_arch_from_checkpoint({}), MODEL_ARCH_BASELINE)
        self.assertEqual(
            model_arch_from_checkpoint({"model_architecture": "SteeringModel"}),
            MODEL_ARCH_BASELINE,
        )
        self.assertEqual(
            model_arch_from_checkpoint({"model_architecture": "SteeringModelV2"}),
            MODEL_ARCH_CNN_V2,
        )

        with self.assertRaisesRegex(ValueError, "Unsupported model architecture"):
            model_arch_from_checkpoint({"model_arch": "unknown"})


if __name__ == "__main__":
    unittest.main()
