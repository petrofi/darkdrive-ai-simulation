from __future__ import annotations

import argparse
import csv
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = Path("data/samples/web_lane_images/wikimedia_batch")
DEFAULT_MANIFEST_PATH = Path("data/samples/web_lane_images/wikimedia_batch_manifest.csv")
COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = (
    "DarkDriveAI-Simulation/1.0 educational lane-detection demo "
    "(https://github.com/petrofi/darkdrive-ai-simulation)"
)

SEARCH_QUERIES = [
    "road lane markings",
    "highway lane markings",
    "motorway lane markings",
    "street lane markings",
    "pavement markings road",
    "road surface marking lane",
    "white road markings",
    "yellow road markings",
    "dashed lane line road",
    "solid lane line road",
    "road center line",
    "road edge line",
    "traffic lane road marking",
    "carriageway lane markings",
    "road markings asphalt",
    "road perspective lane",
    "highway road surface markings",
    "road lane divider",
    "urban road lane markings",
    "rural road lane markings",
]

IMAGE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download open-license road/lane images from Wikimedia Commons."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="Target number of images to keep in the output folder.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Folder where downloaded images will be saved.",
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST_PATH),
        help="CSV file where source/license metadata will be written.",
    )
    parser.add_argument(
        "--thumb-width",
        type=int,
        default=640,
        help="Download resized thumbnails to keep the repository lightweight.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.15,
        help="Small delay between image downloads to be polite to Wikimedia.",
    )
    return parser.parse_args()


def fetch_json(params: dict[str, str]) -> dict[str, Any]:
    query_string = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{COMMONS_API_URL}?{query_string}",
        headers={"User-Agent": USER_AGENT},
    )
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = response.read().decode("utf-8")
            return json.loads(payload)
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 3:
                raise
            wait_seconds = 30 * attempt
            print(f"Wikimedia API rate limit reached. Waiting {wait_seconds} seconds...")
            time.sleep(wait_seconds)

    return {}


def strip_markup(value: str) -> str:
    """Convert small metadata snippets into plain text for the manifest."""
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)
    return " ".join(value.split())


def metadata_value(metadata: dict[str, Any], key: str, default: str = "") -> str:
    raw = metadata.get(key, {}).get("value", default)
    return strip_markup(str(raw))


def slugify(text: str, max_length: int = 48) -> str:
    text = text.replace("File:", "")
    text = re.sub(r"\.[A-Za-z0-9]+$", "", text)
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return (text[:max_length] or "commons_image").strip("_")


def image_files(folder: Path) -> list[Path]:
    return sorted(
        path
        for path in folder.glob("*")
        if path.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )


def read_existing_titles(manifest_path: Path) -> set[str]:
    if not manifest_path.exists():
        return set()

    with manifest_path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return {row.get("title", "") for row in reader if row.get("title")}


def append_manifest_row(manifest_path: Path, row: dict[str, str]) -> None:
    fieldnames = [
        "filename",
        "title",
        "source_page",
        "author",
        "license",
        "license_url",
        "download_url",
        "mime",
        "width",
        "height",
    ]
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = manifest_path.exists()
    with manifest_path.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def safe_print(message: str) -> None:
    """Print safely on Windows terminals that may not support every character."""
    print(message.encode("ascii", errors="replace").decode("ascii"))


def download_file(url: str, output_path: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, 5):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                output_path.write_bytes(response.read())
            return
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 4:
                raise
            wait_seconds = 45 * attempt
            print(f"Wikimedia image rate limit reached. Waiting {wait_seconds} seconds...")
            time.sleep(wait_seconds)


def iter_commons_results(limit: int, thumb_width: int) -> Any:
    """Yield Wikimedia Commons image search results until enough candidates exist."""
    seen_titles: set[str] = set()

    for search_query in SEARCH_QUERIES:
        continuation: dict[str, str] = {}
        while len(seen_titles) < limit:
            params = {
                "action": "query",
                "generator": "search",
                "gsrnamespace": "6",
                "gsrlimit": "50",
                "gsrsearch": search_query,
                "prop": "imageinfo",
                "iiprop": "url|mime|size|extmetadata",
                "iiurlwidth": str(thumb_width),
                "format": "json",
            }
            params.update(continuation)
            data = fetch_json(params)
            pages = data.get("query", {}).get("pages", {})

            for page in sorted(pages.values(), key=lambda item: item.get("pageid", 0)):
                title = page.get("title", "")
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)
                yield page

            continuation = data.get("continue", {})
            if not continuation:
                break


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    manifest_path = Path(args.manifest)
    output_dir.mkdir(parents=True, exist_ok=True)

    existing_files = image_files(output_dir)
    existing_titles = read_existing_titles(manifest_path)
    if len(existing_files) >= args.limit:
        print(f"Already have {len(existing_files)} image(s) in {output_dir}.")
        print("Nothing to download.")
        return 0

    print("Simulation-only dataset helper.")
    print("Downloading open-license web images for lane detection demos only.")
    print("These images do not include steering labels.")
    print(f"Target image count: {args.limit}")
    print(f"Output folder: {output_dir}")

    downloaded = 0
    failed = 0

    for page in iter_commons_results(args.limit * 4, args.thumb_width):
        current_count = len(image_files(output_dir))
        if current_count >= args.limit:
            break

        title = page.get("title", "")
        if title in existing_titles:
            continue

        image_info = (page.get("imageinfo") or [{}])[0]
        mime = image_info.get("mime", "")
        if mime not in IMAGE_EXTENSIONS:
            continue

        download_url = image_info.get("thumburl") or image_info.get("url")
        if not download_url:
            continue

        metadata = image_info.get("extmetadata", {})
        extension = IMAGE_EXTENSIONS[mime]
        next_index = current_count + 1
        filename = f"web_lane_{next_index:04d}_{slugify(title)}{extension}"
        output_path = output_dir / filename

        try:
            download_file(download_url, output_path)
            if output_path.stat().st_size < 1024:
                output_path.unlink(missing_ok=True)
                failed += 1
                continue
        except Exception as exc:  # noqa: BLE001 - keep downloader resilient for beginners.
            failed += 1
            safe_print(f"Skip: failed to download {title}: {exc}")
            continue

        source_page = f"https://commons.wikimedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
        append_manifest_row(
            manifest_path,
            {
                "filename": str(output_path.as_posix()),
                "title": title,
                "source_page": source_page,
                "author": metadata_value(metadata, "Artist", "See source page"),
                "license": metadata_value(metadata, "LicenseShortName", "See source page"),
                "license_url": metadata_value(metadata, "LicenseUrl", ""),
                "download_url": download_url,
                "mime": mime,
                "width": str(image_info.get("thumbwidth") or image_info.get("width") or ""),
                "height": str(image_info.get("thumbheight") or image_info.get("height") or ""),
            },
        )
        existing_titles.add(title)
        downloaded += 1

        total = len(image_files(output_dir))
        if downloaded == 1 or total % 25 == 0:
            print(f"Downloaded {total}/{args.limit}: {filename}")

        time.sleep(args.delay)

    total = len(image_files(output_dir))
    print("")
    print(f"Downloaded this run: {downloaded}")
    print(f"Failed/skipped downloads: {failed}")
    print(f"Total images in folder: {total}")
    print(f"Manifest: {manifest_path}")

    if total < args.limit:
        print("Warning: target image count was not reached. Try rerunning later.")
        return 1

    print("PASS: web lane image batch is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
