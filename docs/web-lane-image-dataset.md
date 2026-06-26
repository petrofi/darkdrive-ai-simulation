# Web Lane Image Dataset

This project includes a 500-image web lane batch for OpenCV lane detection
experiments.

## Purpose

The web image batch helps test the computer vision pipeline on many different
road and lane scenes. It is useful for:

- grayscale conversion checks
- blur and Canny edge detection checks
- region-of-interest masking checks
- Hough line detection checks
- beginner-friendly batch processing demos

It is not behavior cloning training data because the images do not include
steering, throttle, brake, or speed labels.

## Folder Structure

```text
data/samples/web_lane_images/
|-- andre_branco_unsplash_road.jpg
|-- approaching_morrisons_roundabout.jpg
|-- bike_lane_painted_buffer.jpg
|-- SOURCES.md
|-- wikimedia_batch/
|   |-- web_lane_0001_*.jpg
|   |-- ...
|   `-- web_lane_0500_*.jpg
|-- wikimedia_batch_manifest.csv
`-- processing_report.csv
```

Generated processed outputs are written to:

```text
screenshots/web_lane_batch/
```

That generated output folder is ignored by Git because it can contain hundreds
of result images.

## Download Command

```powershell
python scripts/download_web_lane_images.py --limit 500 --output-dir data/samples/web_lane_images/wikimedia_batch --manifest data/samples/web_lane_images/wikimedia_batch_manifest.csv --thumb-width 640 --delay 0.6
```

## Processing Command

```powershell
python scripts/process_web_lane_images.py --input-dir data/samples/web_lane_images --output-dir screenshots/web_lane_batch --report data/samples/web_lane_images/processing_report.csv --recursive
```

## Current Batch Result

```text
Downloaded source images: 500
Processed total images: 503
Failed processed images: 0
Detected line segments: 76467
```

## Safety Note

This remains a simulation-only and computer-vision-only dataset. Do not use
these images as real driving control data. Steering model training must use
simulated driving frames paired with steering labels.
