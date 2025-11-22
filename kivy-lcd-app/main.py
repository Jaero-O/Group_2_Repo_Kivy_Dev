import os

# Force PIL text provider to avoid SDL2 integer rendering bug
os.environ['KIVY_TEXT'] = 'pil'

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.core.window import Window
from kivy.properties import NumericProperty

# Core imports
from app.core import setup_window, BASE_WIDTH, BASE_HEIGHT

# Screen imports
from app.screens import (
    WelcomeScreen, HomeScreen, ScanScreen, RecordsScreen,
    ShareScreen, HelpScreen, GuideScreen, ScanningScreen,
    CaptureResultScreen, ResultScreen, SaveScreen, ImageSelection,
    AnthracnoseScreen, SystemSpecScreen, PrecautionScreen, AboutUsScreen,
    ScanDetailScreen, ScanListScreen
)

# =========================================
# INITIAL SETUP
# =========================================
setup_window()


# =========================================
# APP CLASS
# =========================================
class MangofyApp(App):
    scale_x = NumericProperty(1)
    scale_y = NumericProperty(1)
    last_screen = None

    def build(self):
        # Locate the KV directory inside the app folder
        kv_dir = os.path.join(os.path.dirname(__file__), 'app', 'kv')

        # Load all KV files from /app/kv/
        kv_files = [
            "WelcomeScreen.kv", "HomeScreen.kv", "ScanScreen.kv",
            "RecordsScreen.kv", "ShareScreen.kv", "HelpScreen.kv",
            "GuideScreen.kv", "ScanningScreen.kv", "CaptureResultScreen.kv",
            "ResultScreen.kv", "SaveScreen.kv", "ImageSelection.kv",
            "AnthracnoseScreen.kv", "SystemSpecScreen.kv", "PrecautionScreen.kv",
            "AboutUsScreen.kv", "ScanDetailScreen.kv", "ScanListScreen.kv"
        ]
        for kv in kv_files:
            kv_path = os.path.join(kv_dir, kv)
            if os.path.exists(kv_path):
                Builder.load_file(kv_path)
            else:
                print(f"[Warning] KV file not found: {kv_path}")

        # Setup ScreenManager
        sm = ScreenManager(transition=FadeTransition(duration=0.1))
        for scr, name in [
            (WelcomeScreen, 'welcome'), (HomeScreen, 'home'),
            (ScanScreen, 'scan'), (RecordsScreen, 'records'),
            (ShareScreen, 'share'), (HelpScreen, 'help'),
            (GuideScreen, 'guide'), (ScanningScreen, 'scanning'),
            (CaptureResultScreen, 'capture_result'), (ResultScreen, 'result'),
            (SaveScreen, 'save'), (ImageSelection, 'image_select'),
            (AnthracnoseScreen, 'anthracnose'), (SystemSpecScreen, 'system_spec'),
            (PrecautionScreen, 'precaution'), (AboutUsScreen, 'about_us'),
            (ScanDetailScreen, 'scan_detail'), (ScanListScreen, 'scan_list')
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
    
    def get_color_from_hex(self, hex_color: str) -> tuple:
        '''Convert hex color string to RGBA tuple for Kivy.
        
        Args:
            hex_color: Hex color string like "#DD2D1D" or "#26A421"
        
        Returns:
            RGBA tuple (r, g, b, a) with values 0-1
        '''
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            return (r/255.0, g/255.0, b/255.0, 1.0)
        return (0.5, 0.5, 0.5, 1.0)  # Default gray


if __name__ == '__main__':
    MangofyApp().run()

