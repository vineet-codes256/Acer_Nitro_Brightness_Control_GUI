# Universal Monitor Control GUI

A modern Python GUI utility for controlling monitor settings (brightness, contrast, color, input source, audio, and more) via DDC/CI on Linux.  
Built with [ttkbootstrap](https://ttkbootstrap.readthedocs.io/) and [ddcutil](https://www.ddcutil.com/).

## Screenshot:  

![Screenshot from 2025-06-02 23-26-37](https://github.com/user-attachments/assets/b772cc8e-2722-47b4-bf7d-d2e4da3f9e8c)


---

## Features

- **Auto-detects monitor and I2C bus**
- **Adjust brightness, contrast, color gains**
- **Switch input source (HDMI, DP, etc.)**
- **Audio volume and mute**
- **Power modes and OSD language**
- **Blue light filter**
- **Theme selection (15+ themes)**
- **Persistent settings**
- **Reset to defaults**

---

## Requirements

- Python 3.8+
- `ddcutil` (install via your package manager)
- `ttkbootstrap` (`pip install ttkbootstrap`)

---

## Usage

```bash
python3 monitor_ctrl.py
```

## Disclaimer
This tool uses DDC/CI commands via ddcutil to control your monitor.
Not all monitors support all features, and some may not report their capabilities accurately.
Controls are always enabled for maximum compatibility, but some may not work on your specific monitor.
Use at your own risk.
If you encounter issues, please report your monitor model and the problem in the Issues section.

