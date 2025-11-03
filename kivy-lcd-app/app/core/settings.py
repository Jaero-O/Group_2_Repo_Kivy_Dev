# app/core/settings.py
from kivy.core.window import Window

# =========================================
# ✅ SCREEN SETTINGS
# =========================================
BASE_WIDTH, BASE_HEIGHT = 360, 640
TARGET_WIDTH, TARGET_HEIGHT = 480, 800
DEV_MODE = False

# Detect Raspberry Pi
IS_PI = False
try:
    with open("/proc/cpuinfo") as f:
        IS_PI = "Raspberry Pi" in f.read()
except Exception:
    IS_PI = False

if IS_PI or not DEV_MODE:
    Window.fullscreen = IS_PI
    if not IS_PI:
        Window.size = (TARGET_WIDTH, TARGET_HEIGHT)
    print("🟢 Running in deployment mode → 480x800 or fullscreen.")
else:
    Window.size = (BASE_WIDTH, BASE_HEIGHT)
    Window.fullscreen = False
    try:
        import tkinter as tk
        root = tk.Tk()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        root.destroy()
        Window.left = int((screen_width - BASE_WIDTH) / 2)
        Window.top = int((screen_height - BASE_HEIGHT) / 2)
        print("🧩 Running in DEV mode (360x640), centered on screen.")
    except Exception as e:
        print("⚠️ Centering skipped:", e)


def setup_window():
    """Apply window configuration during app startup."""
    # No extra setup needed for now since logic runs at import
    pass
