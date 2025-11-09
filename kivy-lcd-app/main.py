from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.core.window import Window
from kivy.properties import NumericProperty
import os

# ================================
# ✅ FULLSCREEN PORTRAIT SETTINGS
# ================================
Window.fullscreen = 'auto'   # Fullscreen
Window.show_cursor = False    # Hide mouse cursor
Window.rotation = 270           # Portrait orientation

# 🧩 Core imports
from app.core import setup_window, BASE_WIDTH, BASE_HEIGHT

# 🧩 Screen imports
from app.screens import (
    WelcomeScreen, HomeScreen, ScanScreen, RecordsScreen,
    ShareScreen, HelpScreen, GuideScreen, ScanningScreen,
    CaptureResultScreen, ResultScreen, SaveScreen, ImageSelection,
    AnthracnoseScreen, SystemSpecScreen, PrecautionScreen, AboutUsScreen
)

# =========================================
# ✅ INITIAL SETUP
# =========================================
setup_window()


# =========================================
# ✅ APP CLASS
# =========================================
class MangofyApp(App):
    scale_x = NumericProperty(1)
    scale_y = NumericProperty(1)
    last_screen = None  # ✅ Track where 'result' was opened from

    def build(self):
        # ✅ Locate the KV directory inside the app folder
        kv_dir = os.path.join(os.path.dirname(__file__), 'app', 'kv')

        # ✅ Load all KV files from /app/kv/
        kv_files = [
            "WelcomeScreen.kv", "HomeScreen.kv", "ScanScreen.kv",
            "RecordsScreen.kv", "ShareScreen.kv", "HelpScreen.kv",
            "GuideScreen.kv", "ScanningScreen.kv", "CaptureResultScreen.kv",
            "ResultScreen.kv", "SaveScreen.kv", "ImageSelection.kv",
            "AnthracnoseScreen.kv", "SystemSpecScreen.kv", "PrecautionScreen.kv",
            "AboutUsScreen.kv"
        ]
        for kv in kv_files:
            kv_path = os.path.join(kv_dir, kv)
            if os.path.exists(kv_path):
                Builder.load_file(kv_path)
            else:
                print(f"[Warning] KV file not found: {kv_path}")

        # ✅ Setup ScreenManager
        sm = ScreenManager(transition=FadeTransition(duration=0.1))
        for scr, name in [
            (WelcomeScreen, 'welcome'), (HomeScreen, 'home'),
            (ScanScreen, 'scan'), (RecordsScreen, 'records'),
            (ShareScreen, 'share'), (HelpScreen, 'help'),
            (GuideScreen, 'guide'), (ScanningScreen, 'scanning'),
            (CaptureResultScreen, 'capture_result'), (ResultScreen, 'result'),
            (SaveScreen, 'save'), (ImageSelection, 'image_select'),
            (AnthracnoseScreen, 'anthracnose'), (SystemSpecScreen, 'system_spec'),
            (PrecautionScreen, 'precaution'), (AboutUsScreen, 'about_us')
        ]:
            sm.add_widget(scr(name=name))

        sm.current = 'welcome'

        # ✅ Bind scaling
        Window.bind(on_resize=self._update_scaling)
        self._update_scaling(Window, Window.width, Window.height)

        return sm

    def _update_scaling(self, window, width, height):
        self.scale_x = width / BASE_WIDTH
        self.scale_y = height / BASE_HEIGHT


if __name__ == '__main__':
    MangofyApp().run()

