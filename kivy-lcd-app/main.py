from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.core.window import Window
from kivy.properties import NumericProperty, StringProperty, ObjectProperty
from app.core import init_db
import random
import os

# Core imports
from app.core import setup_window, BASE_WIDTH, BASE_HEIGHT

# Screen imports
from app.screens import (
    WelcomeScreen, HomeScreen, ScanScreen, RecordsScreen,
    ShareScreen, HelpScreen, GuideScreen, ScanningScreen, ResultScreen,
    CaptureResultScreen, SaveScreen, ImageSelectionScreen,
    AnthracnoseScreen, SystemSpecScreen, PrecautionScreen, AboutUsScreen
)

# =========================================
# INITIAL SETUP
# =========================================
setup_window()
# Initialize the database on startup
init_db()


# =========================================
# APP CLASS
# =========================================
class MangofyApp(App):
    scale_x = NumericProperty(1)
    scale_y = NumericProperty(1)
    last_screen = None

    # Properties to share data between screens
    analysis_image_path = StringProperty(None)
    analysis_result = ObjectProperty(None)

    def build(self):
        # Locate the KV directory inside the app folder
        kv_dir = os.path.join(os.path.dirname(__file__), 'app', 'kv')

        # Dynamically load all KV files from the /app/kv/ directory
        if os.path.isdir(kv_dir):
            for filename in os.listdir(kv_dir):
                if filename.endswith(".kv"):
                    kv_path = os.path.join(kv_dir, filename)
                    Builder.load_file(kv_path)

        # Setup ScreenManager
        sm = ScreenManager(transition=FadeTransition(duration=0.1))
        for scr, name in [
            (WelcomeScreen, 'welcome'), (HomeScreen, 'home'),
            (ScanScreen, 'scan'), (RecordsScreen, 'records'),
            (ShareScreen, 'share'), (HelpScreen, 'help'),
            (GuideScreen, 'guide'), (ScanningScreen, 'scanning'),
            (CaptureResultScreen, 'capture_result'), (ResultScreen, 'result'), (SaveScreen, 'save'), 
            (ImageSelectionScreen, 'image_selection'),
            (AnthracnoseScreen, 'anthracnose'), (SystemSpecScreen, 'system_spec'),
            (PrecautionScreen, 'precaution'), (AboutUsScreen, 'about_us')
        ]:
            sm.add_widget(scr(name=name))

        sm.current = 'welcome'

        # Bind scaling
        Window.bind(on_resize=self._update_scaling)
        self._update_scaling(Window, Window.width, Window.height)

        return sm

    def _update_scaling(self, window, width, height):
        self.scale_x = width / BASE_WIDTH
        self.scale_y = height / BASE_HEIGHT


if __name__ == '__main__':
    MangofyApp().run()