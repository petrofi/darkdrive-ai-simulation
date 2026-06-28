# External Dataset Plan

DarkDrive should use external datasets only to improve offline simulator-model research. External data must not be committed, and no simulator-control or real-vehicle-control code should be added as part of dataset integration.

## Candidate Sources

| Candidate | Status | Why It Matters | Risk |
| --- | --- | --- | --- |
| DonkeyCar simulator tub data collected manually | Recommended first path | Adds a second simulator source and may improve recovery/correction coverage. | Tub versions differ; steering scale and visual domain must be verified. |
| Public DonkeyCar tub datasets | Conditional | Could add more labeled steering data without new recording time. | Use only if license and source terms are clear. |
| Udacity-style public behavior cloning datasets | Conditional | Best schema match for DarkDrive's current Udacity simulator pipeline. | Public mirrors may have unclear license or large downloads. |
| Large real-world datasets | Future research | Useful long-term perception/control research. | Too large and domain-mismatched for the current sprint. |

## Recommended First Path

1. Prepare the DonkeyCar converter and validator.
2. Manually collect a small DonkeyCar simulator tub.
3. Convert the tub into DarkDrive unified CSV.
4. Validate image paths, numeric steering, and `source_dataset`.
5. Compare the converted distribution against local Udacity Session A and `session_b_new_training`.
6. Decide whether to merge only after source-specific metrics are acceptable.

## Current Local Baselines

| Dataset | Rows | Near-Zero | Left | Right | Strong Turns | Verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Session A normal | 2400 | 57.42% | 28.17% | 14.42% | 14.12% | Valid but too straight-biased. |
| session_b_new_training | 1126 | 55.24% | 25.84% | 18.92% | 8.17% | Valid but weak mixed/normal data. |

## Merge Gate

Do not merge DonkeyCar data into a training set until:

- conversion validation passes with zero missing images.
- steering distribution is reported source-by-source.
- source licensing is documented.
- camera resolution and crop assumptions are reviewed.
- the model-release checklist still blocks simulator driving until offline evaluation passes.
