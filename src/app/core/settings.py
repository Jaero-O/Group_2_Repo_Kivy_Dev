# app/core/settings.py
from kivy.core.window import Window
import os

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

HEADLESS = os.environ.get('HEADLESS_TEST') == '1'
def _safe_hasattr(obj, name):
    try:
        return hasattr(obj, name)
    except Exception:
        return False

try:
    if HEADLESS:
        print("[HEADLESS] HEADLESS_TEST=1 set: Skipping Window configuration for test environment.")
    else:
        # Ensure Window object looks usable before accessing attributes
        if Window is not None and _safe_hasattr(Window, 'fullscreen') and _safe_hasattr(Window, 'size'):
            if IS_PI or not DEV_MODE:
                try:
                    Window.fullscreen = IS_PI
                except Exception:
                    pass
                if not IS_PI:
                    try:
                        Window.size = (TARGET_WIDTH, TARGET_HEIGHT)
                    except Exception:
                        pass
                print("[INFO] Running in deployment mode -> 480x800 or fullscreen.")
            else:
                try:
                    Window.size = (BASE_WIDTH, BASE_HEIGHT)
                    Window.fullscreen = False
                except Exception:
                    pass
                try:
                    import tkinter as tk
                    root = tk.Tk()
                    screen_width = root.winfo_screenwidth()
                    screen_height = root.winfo_screenheight()
                    root.destroy()
                    if _safe_hasattr(Window, 'left') and _safe_hasattr(Window, 'top'):
                        Window.left = int((screen_width - BASE_WIDTH) / 2)
                        Window.top = int((screen_height - BASE_HEIGHT) / 2)
                    print("[DEV] Running in DEV mode (360x640), centered on screen.")
                except Exception as e:
                    print("[WARN] Centering skipped:", e)
        else:
            print("[WARN] Window provider unavailable; running in reduced mode.")
except Exception as e:
    print(f"[WARN] Window configuration skipped due to error: {e}")


def setup_window():
    """Apply window configuration during app startup."""
    # No extra setup needed for now since logic runs at import
    pass
