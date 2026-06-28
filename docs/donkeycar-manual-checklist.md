# DonkeyCar Manual Checklist

Use this checklist before any DonkeyCar data is merged into DarkDrive.

- [ ] Decide setup path: WSL/Ubuntu, separate Windows environment, or skip DonkeyCar for now.
- [ ] Confirm the source is simulator-only.
- [ ] Confirm source/license terms if using public data.
- [ ] Collect or obtain one small DonkeyCar tub.
- [ ] Place the tub under `data/external/donkeycar/sample_tub/`.
- [ ] Confirm the tub is not staged in Git.
- [ ] Run the DonkeyCar converter.
- [ ] Run the DonkeyCar conversion validator.
- [ ] Confirm missing image count is zero.
- [ ] Compare steering distribution against Session A and `session_b_new_training`.
- [ ] Decide whether the tub is useful before merging.
- [ ] Do not train until the merge decision is documented.
- [ ] Do not add simulator control, websocket/autonomous mode, or real vehicle control code.
