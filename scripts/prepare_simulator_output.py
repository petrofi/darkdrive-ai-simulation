from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SIMULATOR_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "simulator"
SIMULATOR_IMAGES_DIR = SIMULATOR_OUTPUT_DIR / "IMG"


def main() -> int:
    SIMULATOR_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    print("DarkDrive AI Simulation simulator output setup")
    print("No simulator files are copied or modified.")
    print()
    print("Simulator recording/output folder:")
    print(SIMULATOR_OUTPUT_DIR.resolve())
    print()
    print("If the simulator asks for a recording/output folder, select this folder.")
    print("Expected exported files, if behavior cloning recording is supported:")
    print("- data/processed/simulator/IMG/")
    print("- data/processed/simulator/driving_log.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
