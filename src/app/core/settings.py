# app/core/settings.py
from kivy.core.window import Window
import platform, os

# =========================================
# ✅ SCREEN SETTINGS
# =========================================
BASE_WIDTH, BASE_HEIGHT = 360, 640
TARGET_WIDTH, TARGET_HEIGHT = 480, 800
DEV_MODE = False

# Detect Raspberry Pi
IS_PI = False
try:
    # --- SOLUTION: Use platform module for safe OS checking ---
    # os.uname() does not exist on Windows and will crash the app.
    if platform.system() == "Linux":
        IS_PI = 'raspberrypi' in platform.uname().nodename
except Exception:
    IS_PI = False


def setup_window():
    """Apply window configuration during app startup."""
    # --- SOLUTION: Move window configuration logic here ---
    # This function is called at a safe time during app startup.
    if IS_PI or not DEV_MODE:
        Window.fullscreen = IS_PI
        if not IS_PI:
            Window.size = (TARGET_WIDTH, TARGET_HEIGHT)
        print("Running in deployment mode")
    else:
        Window.size = (BASE_WIDTH, BASE_HEIGHT)
        Window.fullscreen = False
        # Let the OS handle window placement.
        print("🧩 Running in DEV mode (360x640).")
