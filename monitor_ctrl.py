import os
import sys
import json
import subprocess
import re
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap import Style

# --- Constants ---
DEFAULT_THEME = "minty"

def get_settings_path():
    config_dir = os.environ.get(
        "XDG_CONFIG_HOME",
        os.path.expanduser("~/.config/Acer_Nitro_Brightness_Control_GUI")
    )
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "settings.json")

SETTINGS_FILE = get_settings_path()

def load_theme():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                return data.get("theme", DEFAULT_THEME)
        except Exception:
            pass
    return DEFAULT_THEME

def save_theme(theme):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump({"theme": theme}, f)
    except Exception as e:
        print(f"Could not save theme: {e}")

def auto_detect_i2c_bus():
    try:
        result = subprocess.run(
            ["ddcutil", "detect"],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        match = re.search(r"I2C bus:\s+/dev/i2c-(\d+)", result.stdout)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"Could not auto-detect I2C bus: {e}")
    return "16"  # fallback/default

I2C_BUS = auto_detect_i2c_bus()

def get_monitor_model():
    try:
        result = subprocess.run(
            ["ddcutil", "detect"],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        match = re.search(r"Model:\s+(.+)", result.stdout)
        if match:
            return match.group(1).strip()
    except Exception as e:
        print(f"Could not detect monitor model: {e}")
    return "Unknown"

def get_supported_vcp_codes(bus):
    try:
        result = subprocess.run(
            ["ddcutil", "capabilities", "--bus", bus],
            check=True, stdout=subprocess.PIPE, text=True
        )
        match = re.search(r"vcp\((.*?)\)", result.stdout)
        if match:
            codes = match.group(1).split()
            return [code.strip().upper() for code in codes]
    except Exception as e:
        print(f"Could not get VCP codes: {e}")
    return []

def probe_vcp_support(bus, code):
    """Try to get the VCP value to check if it's supported, even if not listed."""
    try:
        result = subprocess.run(
            ["ddcutil", "getvcp", code, "--bus", bus],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=2
        )
        if "current value" in result.stdout:
            return True
    except Exception:
        pass
    return False

def get_actual_supported_codes(bus, feature_list, listed_codes):
    actual_codes = set(listed_codes)
    for tab in feature_list:
        for feature in tab["features"]:
            code = feature["code"]
            if code not in actual_codes:
                if probe_vcp_support(bus, code):
                    actual_codes.add(code)
    return actual_codes

MONITOR_MODEL = get_monitor_model()
LISTED_VCP_CODES = get_supported_vcp_codes(I2C_BUS)

# --- Universal VCP Feature Map ---
UNIVERSAL_FEATURES = [
    {
        "tab": "Image",
        "features": [
            {"name": "Brightness", "code": "10", "type": "slider", "min": 0, "max": 100, "default": 50},
            {"name": "Contrast", "code": "12", "type": "slider", "min": 0, "max": 100, "default": 50},
            {"name": "Color Preset", "code": "14", "type": "dropdown", "options": {
                "6500 K": 5, "7500 K": 6, "9300 K": 8, "User 1": 11
            }, "default": "6500 K"},
        ]
    },
    {
        "tab": "Color",
        "features": [
            {"name": "Red Gain", "code": "16", "type": "slider", "min": 0, "max": 100, "default": 50},
            {"name": "Green Gain", "code": "18", "type": "slider", "min": 0, "max": 100, "default": 50},
            {"name": "Blue Gain", "code": "1A", "type": "slider", "min": 0, "max": 100, "default": 50},
            {"name": "Blue Light Filter", "code": "1A", "type": "bluelight", "min": 0, "max": 100, "default": 0},
        ]
    },
    {
        "tab": "Audio",
        "features": [
            {"name": "Speaker Volume", "code": "62", "type": "slider", "min": 0, "max": 100, "default": 50},
            {"name": "Mute / Screen Blank", "code": "8D", "type": "dropdown", "options": {
                "Unmute": 1, "Mute": 2
            }, "default": "Unmute"},
        ]
    },
    {
        "tab": "Input/Power",
        "features": [
            {"name": "Input Source", "code": "60", "type": "dropdown", "options": {
                "HDMI-1": 0x11, "HDMI-2": 0x12, "DisplayPort-1": 0x0f
            }, "default": "HDMI-1"},
            {"name": "Power Mode", "code": "D6", "type": "dropdown", "options": {
                "On": 1, "Standby": 2, "Off": 4, "Turn Off Display": 5
            }, "default": "On"},
        ]
    },
    {
        "tab": "Language",
        "features": [
            {"name": "OSD Language", "code": "CC", "type": "dropdown", "options": {
                "Chinese (traditional)": 1, "English": 2, "French": 3, "German": 4, "Italian": 5,
                "Japanese": 6, "Korean": 7, "Portuguese (Portugal)": 8, "Russian": 9, "Spanish": 10,
                "Turkish": 12, "Chinese (simplified)": 13, "Portuguese (Brazil)": 14, "Dutch": 20,
                "Finnish": 22, "Polish": 30, "Ukranian": 36
            }, "default": "English"},
        ]
    }
]

SUPPORTED_VCP_CODES = get_actual_supported_codes(I2C_BUS, UNIVERSAL_FEATURES, LISTED_VCP_CODES)

# --- Helper Functions ---

def on_slider_change(code, label, var):
    try:
        value = int(float(var.get()))
        set_vcp(code, value)
        label.config(text=str(value))
    except ValueError:
        print(f"Invalid value for VCP {code}: {var.get()}")

def on_dropdown_change(code, label, var, options):
    try:
        value = options[var.get()]
        set_vcp(code, value)
        label.config(text=str(var.get()))
    except KeyError:
        print(f"Invalid selection for VCP {code}: {var.get()}")

def set_vcp(code, value):
    try:
        subprocess.run(
            ["ddcutil", "setvcp", code, str(value), "--bus", I2C_BUS], check=True
        )
    except subprocess.CalledProcessError as e:
        mbox.showwarning("VCP Error", f"Failed to set {code} (VCP): {e}")
        print(f"Error setting VCP {code}: {e}")

def get_vcp(code, fallback=50):
    try:
        result = subprocess.run(
            ["ddcutil", "getvcp", code, "--bus", I2C_BUS],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        output = result.stdout
        for part in output.split(","):
            if "current value" in part:
                return int(part.split("=")[1].strip())
    except Exception as e:
        print(f"Error getting VCP {code}: {e}")
    return fallback

# --- Theme Setup ---
available_themes = [
    "minty", "flatly", "journal", "litera", "lumen", "pulse", "sandstone", "united", "yeti",
    "morph", "simplex", "cerculean", "solar", "superhero", "cyborg", "darkly"
]
current_theme = load_theme()
style = Style(current_theme)
root = style.master
root.title("Universal Monitor Control")
root.geometry("540x700")
root.resizable(False, False)

def on_theme_change(theme):
    style.theme_use(theme)
    save_theme(theme)

# --- Header ---
header = tb.Label(
    root,
    text=f"Monitor Control ({MONITOR_MODEL})",
    font=("Segoe UI", 22, "bold"),
    bootstyle="success",
    anchor="center"
)
header.pack(fill=X, pady=(18, 8), padx=18)

# --- Notebook Tabs ---
notebook = tb.Notebook(root, bootstyle="success")
notebook.pack(fill="both", expand=True, padx=24, pady=16)

# --- Feature UI Generation ---
feature_vars = {}

def create_slider(tab, feature):
    code = feature["code"]
    var = tb.DoubleVar(value=get_vcp(code, feature["default"]))
    label = tb.Label(tab, text=f"{int(var.get())}", font=("Segoe UI", 12), bootstyle="secondary")
    tb.Label(tab, text=feature["name"], font=("Segoe UI", 12, "bold")).pack(pady=(16, 0))
    slider = tb.Scale(
        tab, from_=feature["min"], to=feature["max"], orient=HORIZONTAL, bootstyle="info",
        variable=var, command=lambda v: on_slider_change(code, label, var),
        length=320
    )
    slider.pack(pady=2)
    label.pack()
    feature_vars[code] = (var, label)
    # Optionally, mark as "not detected" if not in SUPPORTED_VCP_CODES
    if code not in SUPPORTED_VCP_CODES:
        tb.Label(tab, text="(Current Status not detected, but should work on many monitors)", font=("Segoe UI", 9, "italic"), bootstyle="warning").pack()
    return var, label

def create_dropdown(tab, feature):
    code = feature["code"]
    options = feature["options"]
    default = feature["default"]
    # Get current VCP value
    current_value = get_vcp(code, options.get(default, 0))
    # Find the label for the current value
    current_label = default
    for label, val in options.items():
        if val == current_value:
            current_label = label
            break
    var = tb.StringVar(value=current_label)
    label = tb.Label(tab, text=current_label, font=("Segoe UI", 12), bootstyle="secondary")
    tb.Label(tab, text=feature["name"], font=("Segoe UI", 12, "bold")).pack(pady=(16, 0))
    menu = tb.OptionMenu(
        tab, var, current_label, *options.keys(),
        command=lambda _: on_dropdown_change(code, label, var, options),
        bootstyle="info"
    )
    menu.pack(pady=2)
    label.pack()
    feature_vars[code] = (var, label)
    if code not in SUPPORTED_VCP_CODES:
        tb.Label(tab, text="(Current Status not detected, but should work on many monitors)", font=("Segoe UI", 9, "italic"), bootstyle="warning").pack()
    return var, label


def create_bluelight(tab, feature):
    # Simulate blue light filter by reducing blue gain
    code = feature["code"]
    var = tb.DoubleVar(value=feature["default"])
    label = tb.Label(tab, text="0% (Blue Gain: 100)", font=("Segoe UI", 12), bootstyle="secondary")
    tb.Label(tab, text="Blue Light Filter", font=("Segoe UI", 12, "bold")).pack(pady=(16, 0))
    def on_bluelight_change(value):
        blue_value = 100 - int(float(value))
        set_vcp(code, blue_value)
        label.config(text=f"{int(float(value))}% (Blue Gain: {blue_value})")
        # Update blue gain slider if present
        if code in feature_vars:
            v, l = feature_vars[code]
            v.set(blue_value)
            l.config(text=f"{blue_value}")
    slider = tb.Scale(
        tab, from_=0, to=100, orient=HORIZONTAL, bootstyle="info",
        variable=var, command=on_bluelight_change, length=320
    )
    slider.pack(pady=2)
    label.pack()
    feature_vars["bluelight"] = (var, label)
    return var, label

# --- Tab and Feature Rendering ---
tab_frames = {}
for tab_def in UNIVERSAL_FEATURES:
    tab_name = tab_def["tab"]
    tab = tb.Frame(notebook)
    notebook.add(tab, text=tab_name)
    tab_frames[tab_name] = tab
    for feature in tab_def["features"]:
        if feature["type"] == "slider":
            create_slider(tab, feature)
        elif feature["type"] == "dropdown":
            create_dropdown(tab, feature)
        elif feature["type"] == "bluelight":
            create_bluelight(tab, feature)

# --- Reset Buttons ---
def reset_image_defaults():
    for feature in UNIVERSAL_FEATURES[0]["features"]:
        code = feature["code"]
        if code in feature_vars:
            var, label = feature_vars[code]
            if feature["type"] == "dropdown":
                var.set(feature["default"])
                label.config(text=str(feature["default"]))
                # Use the numeric value for dropdowns
                set_vcp(code, feature["options"][feature["default"]])
            else:
                var.set(feature["default"])
                label.config(text=str(feature["default"]))
                set_vcp(code, feature["default"])
    if "14" in feature_vars:
        var, label = feature_vars["14"]
        var.set("6500 K")
        label.config(text="6500 K")
        set_vcp("14", 5)

def reset_color_defaults():
    for feature in UNIVERSAL_FEATURES[1]["features"]:
        code = feature["code"]
        if code in feature_vars:
            var, label = feature_vars[code]
            var.set(feature["default"])
            label.config(text=str(feature["default"]))
            set_vcp(code, feature["default"])
    if "bluelight" in feature_vars:
        var, label = feature_vars["bluelight"]
        var.set(0)
        label.config(text="0% (Blue Gain: 100)")
        set_vcp("1A", 100)

tb.Button(tab_frames["Image"], text="Reset Image to Default", command=reset_image_defaults, bootstyle="outline-info").pack(pady=16, fill=X, padx=40)
tb.Button(tab_frames["Color"], text="Reset Color to Default", command=reset_color_defaults, bootstyle="outline-warning").pack(pady=16, fill=X, padx=40)

# --- Theme Selector (top right) ---
theme_frame = tb.Frame(root)
theme_frame.place(relx=1.0, y=75, anchor="ne", x=-24)
tb.Label(theme_frame, text="Theme:", font=("Segoe UI", 10)).pack(side=LEFT, padx=(0, 4))
theme_var = tb.StringVar(value=current_theme)
theme_menu = tb.OptionMenu(
    theme_frame, theme_var, current_theme, *available_themes,
    command=on_theme_change, bootstyle="success"
)
theme_menu.pack(side=LEFT)

# --- Info/Warning if few features are supported ---
if len(SUPPORTED_VCP_CODES) < 5:
    tb.Label(root, text="Warning: This monitor reports limited DDC/CI features. Some controls may still work experimentally.", font=("Segoe UI", 10, "italic"), bootstyle="warning").pack(pady=(0, 8))

root.mainloop()