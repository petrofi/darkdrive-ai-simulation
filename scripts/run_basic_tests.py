from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROAD_IMAGE = PROJECT_ROOT / "data" / "samples" / "road_sample.jpg"
SAMPLE_LOG = PROJECT_ROOT / "data" / "samples" / "sample_driving_log.csv"
MODEL_PATH = PROJECT_ROOT / "models" / "steering_model_v1.pt"
LANE_OUTPUT = PROJECT_ROOT / "screenshots" / "lane_detection_result.png"
TRAINING_LOSS_OUTPUT = PROJECT_ROOT / "screenshots" / "training_loss.png"


@dataclass
class TestResult:
    name: str
    passed: bool
    detail: str


def run_command(name: str, command: list[str]) -> TestResult:
    print(f"\n== {name} ==")
    print(" ".join(command))
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    if completed.stdout:
        print(completed.stdout.strip())
    if completed.stderr:
        print(completed.stderr.strip())

    passed = completed.returncode == 0
    detail = "command completed" if passed else f"exit code {completed.returncode}"
    return TestResult(name=name, passed=passed, detail=detail)


def check_file(name: str, path: Path) -> TestResult:
    exists = path.exists()
    detail = str(path.relative_to(PROJECT_ROOT)) if exists else f"missing: {path.relative_to(PROJECT_ROOT)}"
    print(f"{'PASS' if exists else 'FAIL'} {name}: {detail}")
    return TestResult(name=name, passed=exists, detail=detail)


def main() -> int:
    print("DarkDrive AI Simulation basic pipeline checks")
    print("Simulation-only test helper. No real vehicle control is used.")

    results = [
        check_file("sample road image", ROAD_IMAGE),
        check_file("sample driving log", SAMPLE_LOG),
    ]

    if all(result.passed for result in results):
        lane_result = run_command(
            "lane detection",
            [
                sys.executable,
                "src/lane_detection/basic_lane_detection.py",
                "--image",
                "data/samples/road_sample.jpg",
                "--output",
                "screenshots/lane_detection_result.png",
            ],
        )
        results.append(lane_result)
        results.append(check_file("lane detection output", LANE_OUTPUT))

        training_result = run_command(
            "baseline training",
            [
                sys.executable,
                "src/training/train_behavior_cloning.py",
                "--csv",
                "data/samples/sample_driving_log.csv",
                "--format",
                "simple",
                "--epochs",
                "1",
                "--batch-size",
                "1",
                "--output",
                "models/steering_model_v1.pt",
            ],
        )
        results.append(training_result)
        results.append(check_file("trained model output", MODEL_PATH))
        results.append(check_file("training loss chart", TRAINING_LOSS_OUTPUT))

        if training_result.passed and MODEL_PATH.exists():
            results.append(
                run_command(
                    "steering prediction",
                    [
                        sys.executable,
                        "src/inference/predict_steering.py",
                        "--model",
                        "models/steering_model_v1.pt",
                        "--image",
                        "data/samples/road_sample.jpg",
                    ],
                )
            )
        else:
            results.append(
                TestResult(
                    name="steering prediction",
                    passed=False,
                    detail="skipped because training did not create a model",
                )
            )

    print("\nSummary")
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} - {result.name}: {result.detail}")

    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
