# CNN Architecture Review V1

This review suggests model improvements without implementing them.

## Current Architecture

The current `SteeringModel` is a compact PyTorch CNN:

- Input: RGB image resized to 160x80.
- Normalization: pixels are converted from `[0, 1]` to `[-1, 1]` inside the model.
- Convolution stack: 24, 36, 48, 64, 64 channels.
- Activations: ELU.
- Pooling: adaptive average pooling to 2x4.
- Regressor: dropout, 100, 50, 10, 1.
- Output: one continuous steering value.

This is a reasonable first baseline. It is small, readable, and fast. It is not yet a research-grade driving model.

## Main Architecture Weaknesses

1. The model has no temporal context.
2. It uses only the center camera.
3. It has no explicit crop policy for road-relevant regions.
4. Adaptive pooling may discard spatial detail needed for lane position.
5. It predicts a single frame independently, so oscillation risk is unknown.
6. It has no output constraint or calibration step.
7. Training uses a random row split, which can overstate generalization because adjacent frames are similar.

## Ranked Improvement Ideas

| Rank | Idea | Expected impact | Reason |
| ---: | --- | --- | --- |
| 1 | Better dataset with recovery and left/right camera correction | Very high | Behavior cloning fails mostly from missing states, not just weak architectures. |
| 2 | NVIDIA Behavioral Cloning Network style preprocessing and CNN | High | This architecture is purpose-built for image-to-steering regression and is the most natural next baseline. |
| 3 | Image normalization and crop improvements | High | Removing irrelevant image regions and using consistent normalization can improve signal quality without much complexity. |
| 4 | Temporal frame stacking | Medium-high | Steering depends on motion and recent trajectory; frame stacking can reduce ambiguity. |
| 5 | Steering smoothing | Medium | Can reduce jitter, but it does not fix wrong predictions. Must be evaluated for lag. |
| 6 | ResNet18 | Medium | Strong visual features, but may overfit a small simulator dataset and adds complexity. |
| 7 | EfficientNet-lite | Medium-low for now | Efficient and modern, but less important than data and a proven driving-specific baseline. |

## NVIDIA Behavioral Cloning Network

Recommendation: test after the improved dataset is collected.

Expected benefit:

- Better inductive bias for steering regression.
- More established behavior cloning reference.
- Easier comparison with Udacity-style projects.

Required controls:

- Same dataset split as the current CNN.
- Same evaluation script.
- Same metrics.
- Same held-out validation session.

## ResNet18

Recommendation: defer until the dataset is larger.

Expected benefit:

- Strong feature extractor.
- Transfer learning may improve representation quality.

Risks:

- More parameters than needed.
- Can overfit correlated simulator frames.
- May make the project look more advanced without actually improving closed-loop behavior.

## EfficientNet-lite

Recommendation: consider after NVIDIA-style CNN and ResNet18 baselines.

Expected benefit:

- Efficient inference.
- Good accuracy-to-size tradeoff.

Risks:

- Added complexity.
- Pretrained natural-image features may not be the limiting factor.
- Dataset and recovery coverage remain more important.

## Temporal Frame Stacking

Recommendation: use after a strong single-frame baseline.

Expected benefit:

- Adds motion context.
- May reduce sudden prediction changes.
- Helps the model distinguish lane curvature from camera pose.

Risks:

- Requires sequence-aware dataset loading.
- Needs careful frame ordering and dropped-frame handling.
- Can add inference latency.

## Steering Smoothing

Recommendation: evaluate as a release-stage filter, not as a model-quality substitute.

Candidate approaches:

- Exponential moving average.
- Steering rate limiter.
- Median filter over a short window.

Required validation:

- Measure steering delay.
- Measure oscillation frequency.
- Confirm curve entry is not delayed too much.

## Image Normalization Improvements

Recommendation: implement before larger architectures.

Options:

- Crop sky, hood, and irrelevant borders if present.
- Normalize using dataset mean and standard deviation.
- Consider color-space conversion only as a controlled experiment.
- Keep preprocessing identical between training, evaluation, and future simulator inference.

## Architecture Verdict

Do not jump directly to a large pretrained network. The current bottleneck is dataset quality and closed-loop state coverage. The best next architecture experiment is an NVIDIA-style behavior cloning CNN after collecting a better recovery-heavy dataset.

