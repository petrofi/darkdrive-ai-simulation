# DonkeyCar WSL Manual Checklist

Use this checklist to collect one small DonkeyCar simulator tub safely.

- [ ] Confirm DarkDrive repo is clean before setup.
- [ ] Install Ubuntu for WSL manually if needed.
- [ ] Open Ubuntu/WSL.
- [ ] Run `lsb_release -a`.
- [ ] Run `python3 --version`.
- [ ] Run `pip3 --version`.
- [ ] Run `git --version`.
- [ ] Create `~/donkeycar-workspace`.
- [ ] Create and activate a separate `donkey-env`.
- [ ] Install required Ubuntu packages according to the current DonkeyCar docs.
- [ ] Install DonkeyCar according to the official DonkeyCar docs.
- [ ] Launch or prepare the simulator if available.
- [ ] Collect one small simulator tub with curves and recovery driving.
- [ ] Copy the tub to `data/external/donkeycar/sample_tub/`.
- [ ] Confirm the tub is ignored by Git.
- [ ] Run the DarkDrive DonkeyCar converter.
- [ ] Run the DarkDrive DonkeyCar validator.
- [ ] Compare steering distribution against Session A and `session_b_new_training`.
- [ ] Decide whether another tub is needed before any merge.
- [ ] Do not train yet.
- [ ] Do not merge datasets yet.
- [ ] Do not add simulator control, websocket/autonomous mode, or real vehicle control code.

Conversion reminder:

```powershell
python scripts/convert_donkey_tub_to_darkdrive.py --input data/external/donkeycar/sample_tub --output data/processed/donkeycar/donkeycar_unified.csv --images-output data/processed/donkeycar/IMG --source-name donkeycar_sample
```

Validation reminder:

```powershell
python scripts/validate_donkeycar_conversion.py --csv data/processed/donkeycar/donkeycar_unified.csv --images-dir data/processed/donkeycar/IMG
```
