# README Metrics Provenance

`readme_metrics.json` is the committed source of truth for the aggregate values used by the project README and its generated charts.

## Scope

The file contains only sanitized aggregate metrics. It contains no images, raw telemetry, absolute paths, model weights, personal information, external dataset files, or complete runtime logs.

Dataset values were transcribed from the named committed dataset reports. Model values were transcribed only from evaluations performed on the same complete 4,163-row Session C2 holdout. Metrics from other validation or test sets are intentionally excluded from the model comparison.

The active and dry-run closed-loop values were verified on 2026-07-12 against their ignored local JSON summaries before being sanitized into the aggregate file:

- Active: `20260712T080700_749131Z`
- Dry-run: `20260712T080331_847997Z`

The raw runtime files remain ignored and are not required to regenerate the README assets.

## Interpretation Rules

- Near-zero, left, and right are mutually exclusive steering-direction buckets.
- Strong-turn coverage overlaps left/right and is therefore plotted separately.
- The one unsuccessful active-run record is the controlled `max_runtime` shutdown row, not an operational inference failure.
- Session C2 has been reused for multiple model experiments; it is a common comparison split, not a final independent frozen benchmark.
- Kaggle Jungle licensing remains unresolved. The data and resulting checkpoint are not distributed by this repository.
- Closed-loop observation is qualitative and simulation-only; it is not a lap, safety, or real-world autonomy claim.

## Regeneration

From the repository root:

```powershell
python scripts/generate_readme_assets.py
```

The generator validates required fields and writes deterministic PNG files under `docs/assets/readme/`.
