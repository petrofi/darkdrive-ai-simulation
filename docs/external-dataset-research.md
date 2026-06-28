# External Dataset Research

DarkDrive needs additional image + steering-label data to reduce the current zero-steering bias. The priority is public simulator or behavior cloning datasets that can be converted into:

```text
image_path,steering,throttle,brake,speed,source_dataset
```

Safety boundary: external datasets are used only for offline simulator-model research. They do not imply autonomous driving capability and do not enable simulator control.

## Ranking Key

- A: use immediately.
- B: useful but needs conversion, manual download, or license review.
- C: not suitable now.

## Candidate Summary

| Rank | Dataset | Source URL | License / usage notes | Approx. size | Format | Images | Steering labels | Throttle/brake/speed | Simulator or real-world | Recommended | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B | Udacity CarND Behavioral Cloning sample data | https://github.com/udacity/CarND-Behavioral-Cloning-P3 | Public educational project data. The project is public, but the standalone sample-data license/terms should be reviewed before automatic download. | About 300-400 MB | Udacity `driving_log.csv` with `center,left,right,steering,throttle,brake,speed` | Yes | Yes | Yes | Simulator | Yes, after license/terms review | Best format match for DarkDrive. Manual download/extraction is recommended because license terms are not explicit enough for silent automated download. |
| B | DonkeyCar simulator tub data | https://docs.donkeycar.com/guide/deep_learning/simulator/ | DonkeyCar docs are public. Individual sample tub files may be hosted separately and should be reviewed before use. | Varies | DonkeyCar tub records with image, angle/steering, throttle | Yes | Yes, usually `user/angle` | Throttle yes, brake/speed usually absent | Simulator | Yes, with conversion | Useful for simulator behavior cloning, but tub structure differs from DarkDrive and needs conversion. |
| C | Udacity Self-Driving Car Challenge 2 dataset | https://github.com/udacity/self-driving-car/tree/master/datasets | Public Udacity dataset repository with dataset notes. Large real-world dataset; not the first choice for this sprint. | Larger than 1 GB, often tens of GB | Real-world camera/log data | Yes | May include steering/control logs depending on split | Varies | Real-world | No for now | Too large and more complex than the current simulator behavior cloning workflow. |
| C | comma2k19 | https://github.com/commaai/comma2k19 | Public comma.ai dataset repository with clear research availability. | Very large | Real-world camera/video, CAN, and vehicle-state logs | Yes | Steering/control signal exists in logs, not simple CSV | Vehicle state logs, not DarkDrive simple format | Real-world | No for now | High-quality dataset, but too large and complex for the current simple simulator pipeline. |
| C | TuSimple lane detection benchmark | https://github.com/TuSimple/tusimple-benchmark | Public benchmark for lane detection. | Varies | Lane annotations | Yes | No | No | Real-world | No | Useful for lane detection research, not behavior cloning. |
| C | BDD100K | https://bdd-data.berkeley.edu/ | Public research dataset with usage terms. | Very large | Detection, segmentation, tracking, lane/drivable annotations | Yes | No simple steering labels | No | Real-world | No | Excellent perception dataset, but not a steering-label behavior cloning dataset. |

## Initial Supported Dataset Keys

The download and conversion scripts currently recognize these research keys:

| Dataset key | Download behavior | Conversion support |
| --- | --- | --- |
| `udacity-carnd-sample` | Prints manual license/terms review and extraction instructions. Automatic download is disabled by default. | `--format udacity` |
| `donkeycar-simulator-tub` | Prints manual download instructions. | `--format donkeycar` best-effort JSON tub conversion |
| `udacity-challenge2` | Manual only. Refuses large automatic downloads. | Not supported in this sprint |
| `comma2k19` | Manual only. Future research only. | Not supported in this sprint |

## Recommendation

The best next dataset target is an Udacity-format behavior cloning dataset because it already matches DarkDrive's simulator data schema. The safest workflow is:

1. Review the source/license terms.
2. Download manually if terms are acceptable.
3. Extract to `data/external/<dataset_name>/`.
4. Convert to unified DarkDrive format.
5. Validate image paths and steering distribution.
6. Merge with local simulator data using near-zero downsampling.

No external dataset should be committed to Git.

