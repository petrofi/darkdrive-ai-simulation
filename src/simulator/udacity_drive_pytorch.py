"""Placeholder for a future Udacity-style PyTorch simulator drive loop.

This file documents the planned simulator-only integration point for DarkDrive.
It intentionally does not connect to a simulator or send steering commands yet.

Expected future flow:
1. Connect to the Udacity-style simulator in Autonomous Mode.
2. Receive a front camera image from the simulator.
3. Decode and preprocess the image the same way as training.
4. Run PyTorch SteeringModel inference.
5. Send the predicted steering value back to the simulator.

Safety boundary:
- Simulation only.
- No real vehicle control.
- No RC car control in the current phase.
- No public road deployment.
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path


OPTIONAL_DEPENDENCIES = {
    "socketio": "future simulator Socket.IO connection",
    "eventlet": "future simulator web server loop",
    "torch": "future PyTorch model inference",
    "PIL": "future simulator image decoding",
}


def dependency_available(module_name: str) -> bool:
    """Return True when an optional future dependency can be imported."""

    return importlib.util.find_spec(module_name) is not None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Safe placeholder for a future simulation-only Udacity PyTorch "
            "drive loop. This script does not send simulator commands yet."
        )
    )
    parser.add_argument(
        "--model",
        default="models/steering_model_v1.pt",
        help="Future PyTorch checkpoint path.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Future simulator host. Placeholder only.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=4567,
        help="Future simulator port. Placeholder only.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    model_path = Path(args.model)

    print("DarkDrive Udacity PyTorch drive loop placeholder")
    print("Simulation-only mode.")
    print("No simulator commands are sent by this script yet.")
    print()
    print("Planned future inputs:")
    print(f"- PyTorch model checkpoint: {model_path}")
    print(f"- Simulator host: {args.host}")
    print(f"- Simulator port: {args.port}")
    print("- Simulator camera image stream in Autonomous Mode")
    print()
    print("Planned future output:")
    print("- Predicted steering value sent back to the simulator only")
    print()

    if model_path.exists():
        print(f"Model checkpoint found: {model_path}")
    else:
        print(
            "Model checkpoint not found yet. Train a PyTorch model on validated "
            "simulator data before implementing the drive loop."
        )

    print()
    print("Optional dependency status:")
    for module_name, purpose in OPTIONAL_DEPENDENCIES.items():
        status = "available" if dependency_available(module_name) else "missing"
        print(f"- {module_name}: {status} ({purpose})")

    print()
    print("TODO:")
    print("- Add Socket.IO connection to the simulator.")
    print("- Decode incoming base64 camera images.")
    print("- Reuse DarkDrive image preprocessing.")
    print("- Load SteeringModel from a .pt checkpoint.")
    print("- Run model inference for steering prediction.")
    print("- Send steering response back to the simulator only.")


if __name__ == "__main__":
    main()
