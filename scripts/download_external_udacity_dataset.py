"""Download and register the public Udacity behavioral-cloning sample archive.

This script intentionally only downloads and records provenance.  Extraction,
validation, manifest creation, and any future training are separate steps.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


DATASET_ID = "udacity_behavioral_cloning_public"
DEFAULT_URL = "https://d17h27t6h515a5.cloudfront.net/topher/2016/December/584f6edd_data/data.zip"
DEFAULT_OUTPUT_DIR = Path("data/external") / DATASET_ID / "raw"
SCRIPT_VERSION = "1.0.0"
CHUNK_SIZE = 1024 * 1024


def project_path(value: str | Path) -> Path:
    """Resolve a user-relative path from the repository root."""
    path = Path(value)
    if path.is_absolute():
        return path
    return Path(__file__).resolve().parents[1] / path


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of *path* without loading it into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def metadata_path_for(output_dir: Path) -> Path:
    """Return the metadata location next to a dataset's raw directory."""
    return output_dir.parent / "metadata" / "download_metadata.json"


def write_download_metadata(output_dir: Path, metadata: dict[str, object]) -> Path:
    """Write stable, human-readable download provenance metadata."""
    metadata_path = metadata_path_for(output_dir)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with metadata_path.open("w", encoding="utf-8", newline="\n") as file_handle:
        json.dump(metadata, file_handle, indent=2, sort_keys=True)
        file_handle.write("\n")
    return metadata_path


def ensure_destination_available(destination: Path, force: bool) -> None:
    """Reject accidental replacement of an existing archive."""
    if destination.exists() and not force:
        raise FileExistsError(
            f"Refusing to overwrite existing archive: {destination}. "
            "Use --force only after verifying the file may be replaced."
        )


def download_file(
    url: str,
    destination: Path,
    opener: Callable[..., object] = urllib.request.urlopen,
) -> int:
    """Download *url* atomically and return the byte count.

    A partial response is written to a ``.part`` file and never promoted to the
    requested archive path.  If the server advertises a content length, the
    count must match before the download is accepted.
    """
    partial_path = destination.with_suffix(destination.suffix + ".part")
    if partial_path.exists():
        partial_path.unlink()

    try:
        request = urllib.request.Request(url, headers={"User-Agent": "DarkDrive-Dataset-Ingestion/1.0"})
        with opener(request, timeout=60) as response:
            expected_length_value = response.headers.get("Content-Length")
            expected_length = int(expected_length_value) if expected_length_value else None
            downloaded_bytes = 0
            with partial_path.open("wb") as file_handle:
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    file_handle.write(chunk)
                    downloaded_bytes += len(chunk)

        if expected_length is not None and downloaded_bytes != expected_length:
            raise IOError(
                "Incomplete download: server declared "
                f"{expected_length} bytes but received {downloaded_bytes} bytes."
            )

        os.replace(partial_path, destination)
        return downloaded_bytes
    except BaseException:
        if partial_path.exists():
            partial_path.unlink()
        raise


def download_dataset(url: str, output_dir: Path, force: bool = False) -> tuple[Path, dict[str, object]]:
    """Download the configured archive and persist its immutable provenance."""
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / "data.zip"
    ensure_destination_available(destination, force)
    downloaded_bytes = download_file(url, destination)
    if downloaded_bytes <= 0 or not destination.exists() or destination.stat().st_size != downloaded_bytes:
        raise IOError(f"Incomplete download: archive was not written correctly to {destination}.")

    metadata: dict[str, object] = {
        "dataset_id": DATASET_ID,
        "source_url": url,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "file_size_bytes": destination.stat().st_size,
        "sha256": sha256_file(destination),
        "local_zip_path": str(destination.resolve()),
        "script_version": SCRIPT_VERSION,
    }
    write_download_metadata(output_dir, metadata)
    return destination, metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download and checksum the public Udacity behavioral-cloning dataset archive."
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="Archive URL to download.")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where data.zip is stored (default: %(default)s).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow replacement of an existing data.zip after explicit review.",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = project_path(args.output_dir)
    try:
        archive_path, metadata = download_dataset(args.url, output_dir, args.force)
    except FileExistsError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError) as exc:
        print(f"ERROR: Download failed for {args.url}: {exc}", file=sys.stderr)
        return 1

    print("External dataset download complete")
    print(f"- Dataset ID: {DATASET_ID}")
    print(f"- Archive: {archive_path}")
    print(f"- File size: {metadata['file_size_bytes']} bytes")
    print(f"- SHA256: {metadata['sha256']}")
    print(f"- Metadata: {metadata_path_for(output_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
