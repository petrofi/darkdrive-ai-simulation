# Web Lane Image Sources

These images are included for OpenCV lane detection experiments only.
They do not include steering labels, so they are not behavior cloning
training data.

Use simulator data with `image + steering` labels for steering model training.

## Images

- `andre_branco_unsplash_road.jpg`
  - Source: Wikimedia Commons
  - File page: https://commons.wikimedia.org/wiki/File:Andr%C3%A9_Branco_2016-01-10_(Unsplash).jpg
  - Author: Andre Branco
  - License: CC0 1.0 Public Domain Dedication

- `approaching_morrisons_roundabout.jpg`
  - Source: Wikimedia Commons / Geograph
  - File page: https://commons.wikimedia.org/wiki/File:Approaching_the_Morrisons_Roundabout_-_geograph.org.uk_-_825010.jpg
  - Author: Peter Church
  - License: CC BY-SA 2.0

- `bike_lane_painted_buffer.jpg`
  - Source: Wikimedia Commons
  - File page: https://commons.wikimedia.org/wiki/File:Bike_Lane_Painted_Buffer.jpg
  - Author: Hannah.Ferrier
  - License: CC BY 4.0

## 500-Image Wikimedia Batch

The folder below contains 500 additional road/lane-related images downloaded
from Wikimedia Commons search results as resized thumbnails:

```text
data/samples/web_lane_images/wikimedia_batch/
```

Per-image source, author, license, and download metadata is stored in:

```text
data/samples/web_lane_images/wikimedia_batch_manifest.csv
```

The batch was processed with the OpenCV lane detection pipeline, and the
processing summary is stored in:

```text
data/samples/web_lane_images/processing_report.csv
```

## Notes

The project remains simulation-only. These public web images are useful for
testing image processing ideas such as grayscale conversion, Canny edges, and
Hough line detection. They should not be presented as driving model training
data because they do not contain steering, throttle, brake, or speed labels.
