from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DatasetOption:
    key: str
    name: str
    source_url: str
    estimated_size_gb: float | None
    license_status: str
    license_clear_for_auto_download: bool
    format: str
    direct_url: str | None
    manual_required: bool
    manual_instructions: str


DATASETS: dict[str, DatasetOption] = {
    "udacity-carnd-sample": DatasetOption(
        key="udacity-carnd-sample",
        name="Udacity CarND Behavioral Cloning sample data",
        source_url="https://github.com/udacity/CarND-Behavioral-Cloning-P3",
        estimated_size_gb=0.35,
        license_status=(
            "Public Udacity educational sample; standalone dataset license is not explicit. "
            "Review project terms before use."
        ),
        license_clear_for_auto_download=False,
        format="Udacity driving_log.csv with center,left,right,steering,throttle,brake,speed",
        direct_url="https://d17h27t6h515a5.cloudfront.net/topher/2016/December/584f6edd_data/data.zip",
        manual_required=True,
        manual_instructions=(
            "Open the Udacity Behavioral Cloning project page, review usage terms, then download "
            "the classroom sample data manually. Extract it into data/external/udacity-carnd-sample/ "
            "so driving_log.csv and IMG/ are inside that folder."
        ),
    ),
    "donkeycar-simulator-tub": DatasetOption(
        key="donkeycar-simulator-tub",
        name="DonkeyCar simulator tub data",
        source_url="https://docs.donkeycar.com/guide/deep_learning/simulator/",
        estimated_size_gb=None,
        license_status=(
            "DonkeyCar docs are public, but individual tub downloads may come from manual links "
            "with separate or unclear terms."
        ),
        license_clear_for_auto_download=False,
        format="DonkeyCar tub records with image, steering/angle, and throttle values",
        direct_url=None,
        manual_required=True,
        manual_instructions=(
            "Follow the DonkeyCar simulator documentation, download any sample tub only after "
            "checking its license/terms, and place the extracted tub under "
            "data/external/donkeycar-simulator-tub/."
        ),
    ),
    "udacity-challenge2": DatasetOption(
        key="udacity-challenge2",
        name="Udacity Self-Driving Car Challenge 2 dataset",
        source_url="https://github.com/udacity/self-driving-car/tree/master/datasets",
        estimated_size_gb=20.0,
        license_status=(
            "Udacity self-driving-car repository provides dataset license information; large "
            "real-world driving dataset, not a simple simulator behavior-cloning set."
        ),
        license_clear_for_auto_download=True,
        format="Real-world driving logs and camera data; conversion is not implemented in this sprint",
        direct_url=None,
        manual_required=True,
        manual_instructions=(
            "Use the Udacity dataset documentation and only download after confirming the license "
            "and storage budget. This is larger than 1GB and should not be downloaded by this script."
        ),
    ),
    "comma2k19": DatasetOption(
        key="comma2k19",
        name="comma2k19",
        source_url="https://github.com/commaai/comma2k19",
        estimated_size_gb=100.0,
        license_status=(
            "Public comma.ai dataset repository; useful license clarity, but large real-world "
            "video/CAN/log data and not an immediate DarkDrive simple-format source."
        ),
        license_clear_for_auto_download=True,
        format="Real-world camera/video and vehicle-state logs; conversion is not implemented",
        direct_url=None,
        manual_required=True,
        manual_instructions=(
            "Read the comma2k19 repository and dataset instructions. Treat it as future research, "
            "not a current behavior-cloning import target."
        ),
    ),
}


def print_dataset_summary(dataset: DatasetOption, output_path: Path) -> None:
    size = "unknown" if dataset.estimated_size_gb is None else f"{dataset.estimated_size_gb:.2f} GB"
    print("External dataset download manager")
    print(f"- Dataset name: {dataset.name}")
    print(f"- Dataset key: {dataset.key}")
    print(f"- Source: {dataset.source_url}")
    print(f"- Estimated size: {size}")
    print(f"- License status: {dataset.license_status}")
    print(f"- Format: {dataset.format}")
    print(f"- Output path: {output_path}")
    print(f"- Manual download required: {'yes' if dataset.manual_required else 'no'}")


def remote_size_gb(url: str) -> float | None:
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            content_length = response.headers.get("Content-Length")
    except (urllib.error.URLError, TimeoutError):
        return None

    if not content_length:
        return None
    return int(content_length) / (1024**3)


def download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as response:
        with destination.open("wb") as output_file:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output_file.write(chunk)


def run(dataset_key: str, output_dir: Path, max_size_gb: float, dry_run: bool) -> int:
    dataset = DATASETS.get(dataset_key)
    if dataset is None:
        print(f"Unknown dataset: {dataset_key}")
        print("Supported datasets:")
        for key in sorted(DATASETS):
            print(f"- {key}")
        return 2

    dataset_output_dir = output_dir / dataset.key
    print_dataset_summary(dataset, dataset_output_dir)

    if dataset.estimated_size_gb is not None and dataset.estimated_size_gb > max_size_gb:
        print()
        print(
            f"Refusing download: estimated size {dataset.estimated_size_gb:.2f} GB "
            f"exceeds --max-size-gb {max_size_gb:.2f}."
        )
        print("Increase --max-size-gb only after confirming storage and license terms.")
        return 1

    if not dataset.license_clear_for_auto_download:
        print()
        print("Automatic download disabled because the dataset license/terms are not explicit enough.")
        print(dataset.manual_instructions)
        return 0

    if dataset.manual_required or dataset.direct_url is None:
        print()
        print("No safe direct download URL is configured for this dataset.")
        print(dataset.manual_instructions)
        return 0

    if dry_run:
        print()
        print("Dry run only. No files were downloaded.")
        return 0

    measured_size = remote_size_gb(dataset.direct_url)
    if measured_size is not None and measured_size > max_size_gb:
        print()
        print(
            f"Refusing download: remote file size {measured_size:.2f} GB "
            f"exceeds --max-size-gb {max_size_gb:.2f}."
        )
        return 1

    destination = dataset_output_dir / Path(dataset.direct_url).name
    print()
    print(f"Downloading to: {destination}")
    download_file(dataset.direct_url, destination)
    print("Download complete.")
    print("If this is an archive, extract it before running convert_external_dataset.py.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safely download or document external driving datasets.")
    parser.add_argument("--dataset", required=True, help="Dataset key to download or inspect.")
    parser.add_argument("--output-dir", default="data/external", help="External dataset root folder.")
    parser.add_argument("--max-size-gb", type=float, default=1.0, help="Refuse downloads larger than this.")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without downloading.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(run(args.dataset, Path(args.output_dir), args.max_size_gb, args.dry_run))

