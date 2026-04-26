import os
import sys
import subprocess
import threading
import time
import signal

# Force PIL text provider to avoid SDL2 integer rendering bug
os.environ['KIVY_TEXT'] = 'pil'

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.core.window import Window
from kivy.properties import NumericProperty
from kivy.clock import Clock

import RPi.GPIO as GPIO

from app.core import setup_window, BASE_WIDTH, BASE_HEIGHT
from app.screens import (
    WelcomeScreen, HomeScreen, ScanScreen, RecordsScreen,
    ShareScreen, HelpScreen, CaptureResultScreen,
    ResultScreen, ImageSelection, AnthracnoseScreen, SystemSpecScreen,
    PrecautionScreen, AboutUsScreen, ScanDetailScreen, ScanListScreen
)

# =========================================
# INITIAL SETUP
# =========================================
setup_window()
Window.fullscreen = 'auto'
Window.show_cursor = True
Window.rotation = 270

# =========================================
# SHUTDOWN CONFIG
# =========================================
BUTTON_PIN = 3
HOLD_TIME  = 3  # seconds

# =========================================
# MODEL SERVER CONFIG
# =========================================
# Path to the Python 3.10 executable that has onnxruntime + rembg installed
PYTHON_310_PATH = os.getenv("ONNX_PYTHON_PATH", "/home/kennethbinasa/onnx_venv/bin/python3")
# Path to model_server.py — same directory as this main.py
MODEL_SERVER_SCRIPT = "/home/kennethbinasa/kivy_v1/kivy-lcd-app/model_server.py"

ONNX_MODEL_PATH = "/home/kennethbinasa/kivy_v1/kivy-lcd-app/app/scan/resnet_leafdisease_datasetresized.onnx"

# =========================================
# APP CLASS
# =========================================
class MangofyApp(App):
    scale_x = NumericProperty(1)
    scale_y = NumericProperty(1)
    last_screen = None

    # Holds the model server subprocess handle
    _model_server_proc = None

    def build(self):
        # ── 1. Launch model server (Python 3.10) ─────────────────────────────
        # This starts immediately in the background while Kivy loads KV files.
        # By the time the user reaches the scan screen, models are ready.
        self._launch_model_server()

        # ── 2. Load KV files ─────────────────────────────────────────────────
        kv_dir = os.path.join(os.path.dirname(__file__), 'app', 'kv')
        kv_files = [
            "WelcomeScreen.kv", "HomeScreen.kv", "ScanScreen.kv", "RecordsScreen.kv",
            "ShareScreen.kv", "HelpScreen.kv", "CaptureResultScreen.kv",
            "ResultScreen.kv", "ImageSelection.kv", "AnthracnoseScreen.kv",
            "SystemSpecScreen.kv", "PrecautionScreen.kv", "AboutUsScreen.kv",
            "ScanDetailScreen.kv", "ScanListScreen.kv"
        ]
        for kv in kv_files:
            kv_path = os.path.join(kv_dir, kv)
            if os.path.exists(kv_path):
                Builder.load_file(kv_path)
            else:
                print(f"[Warning] KV file not found: {kv_path}")

        # ── 3. Build screen manager ───────────────────────────────────────────
        sm = ScreenManager(transition=FadeTransition(duration=0.1))
        for scr, name in [
            (WelcomeScreen,     'welcome'),
            (HomeScreen,        'home'),
            (ScanScreen,        'scan'),
            (RecordsScreen,     'records'),
            (ShareScreen,       'share'),
            (HelpScreen,        'help'),
            (CaptureResultScreen,'capture_result'),
            (ResultScreen,      'result'),
            (ImageSelection,    'image_select'),
            (AnthracnoseScreen, 'anthracnose'),
            (SystemSpecScreen,  'system_spec'),
            (PrecautionScreen,  'precaution'),
            (AboutUsScreen,     'about_us'),
            (ScanDetailScreen,  'scan_detail'),
            (ScanListScreen,    'scan_list'),
        ]:
            sm.add_widget(scr(name=name))

        sm.current = 'welcome'
        Window.bind(on_resize=self._update_scaling)
        self._update_scaling(Window, Window.width, Window.height)

        # ── 4. GPIO shutdown monitor ──────────────────────────────────────────
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        threading.Thread(target=self._monitor_shutdown_button, daemon=True).start()

        return sm

    # =========================================
    # MODEL SERVER MANAGEMENT
    # =========================================
    def _launch_model_server(self):
        """
        Launch model_server.py in Python 3.10 as a background subprocess.
        The server loads U2Net + ONNX once and stays alive until the app exits.
        """
        if not os.path.exists(MODEL_SERVER_SCRIPT):
            print(f"[ModelServer] ERROR: Script not found: {MODEL_SERVER_SCRIPT}")
            return
        if not os.path.exists(ONNX_MODEL_PATH):
            print(f"[ModelServer] ERROR: Model not found: {ONNX_MODEL_PATH}")
            return

        print("[ModelServer] Launching model server...")
        self._model_server_proc = subprocess.Popen(
            [PYTHON_310_PATH, MODEL_SERVER_SCRIPT, "--model", ONNX_MODEL_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Stream server logs to our stderr in the background
        threading.Thread(
            target=self._stream_server_logs,
            args=(self._model_server_proc,),
            daemon=True
        ).start()

        # Wait for ready signal in a background thread so we don't block Kivy
        threading.Thread(target=self._wait_for_model_server, daemon=True).start()

    def _stream_server_logs(self, proc):
        """Forward model_server stderr to our own stderr."""
        for line in proc.stderr:
            print(f"[ModelServer] {line.decode().rstrip()}", file=sys.stderr)

    def _wait_for_model_server(self):
        """Poll for the .ready file. Update UI when server is ready."""
        from model_client import ModelClient
        ready = ModelClient.wait_until_ready(timeout=120.0)
        if ready:
            print("[ModelServer] ✓ Models loaded and ready for scanning.")
            Clock.schedule_once(self._on_model_server_ready, 0)
        else:
            print("[ModelServer] ✗ Timed out waiting for model server to start!")

    def _on_model_server_ready(self, dt):
        """Called on the Kivy main thread once models are loaded."""
        # You can use this to update UI — e.g. enable the Scan button,
        # hide a loading spinner, etc.
        # Example:
        #   scan_screen = self.root.get_screen('scan')
        #   scan_screen.set_scan_ready(True)
        print("[App] Model server ready — scanning is enabled.")

    def _stop_model_server(self):
        """Gracefully stop the model server when the app exits."""
        if self._model_server_proc and self._model_server_proc.poll() is None:
            try:
                from model_client import ModelClient
                ModelClient().shutdown_server()
                self._model_server_proc.wait(timeout=5)
            except Exception:
                self._model_server_proc.terminate()
            print("[ModelServer] Server stopped.")

    def on_stop(self):
        """Kivy calls this when the app is closing."""
        self._stop_model_server()

    # =========================================
    # SHUTDOWN MONITOR  (unchanged)
    # =========================================
    def _monitor_shutdown_button(self):
        while True:
            if GPIO.input(BUTTON_PIN) == GPIO.LOW:
                press_time = time.time()
                while GPIO.input(BUTTON_PIN) == GPIO.LOW:
                    time.sleep(0.1)
                if time.time() - press_time >= HOLD_TIME:
                    Clock.schedule_once(self._safe_shutdown, 0)
            time.sleep(0.1)

    def _safe_shutdown(self, dt):
        print("Long press detected. Performing safe shutdown...")
        try:
            self._stop_model_server()
        except Exception as e:
            print("Model server stop error:", e)
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except:
            pass
        try:
            GPIO.cleanup()
        except:
            pass
        self.stop()
        subprocess.call(["sudo", "shutdown", "-h", "now"])

    # =========================================
    # SCALING  (unchanged)
    # =========================================
    def _update_scaling(self, window, width, height):
        self.scale_x = width / BASE_WIDTH
        self.scale_y = height / BASE_HEIGHT

    def get_color_from_hex(self, hex_color: str) -> tuple:
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return (r/255.0, g/255.0, b/255.0, 1.0)
        return (0.5, 0.5, 0.5, 1.0)


if __name__ == '__main__':
    MangofyApp().run()
