from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.core.window import Window
from kivy.uix.widget import Widget
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import ListProperty, NumericProperty, ObjectProperty
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.metrics import sp
import numpy as np

# =========================================
# ✅ SCREEN SETTINGS
# =========================================
BASE_WIDTH, BASE_HEIGHT = 360, 640   # Design resolution
TARGET_WIDTH, TARGET_HEIGHT = 480, 800
DEV_MODE = False  # True = 360×640 editing, False = deployment (480×800 or fullscreen)

# Detect Raspberry Pi (optional deployment mode)
IS_PI = False
try:
    with open("/proc/cpuinfo") as f:
        IS_PI = "Raspberry Pi" in f.read()
except Exception:
    IS_PI = False

# ---------- Apply Window Settings ----------
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


# =========================================
# ✅ RESPONSIVE UTILS
# =========================================
def scale_x(px): return px * (Window.width / BASE_WIDTH)
def scale_y(py): return py * (Window.height / BASE_HEIGHT)
def responsive_font(size): return sp(size * (Window.width / BASE_WIDTH))


# =========================================
# ✅ BUTTON CLASSES
# =========================================
class RoundedButton(ButtonBehavior, Widget):
    radius = NumericProperty(18)
    shadow_color = ListProperty([0, 0, 0, 0.25])
    shadow_offset_y = NumericProperty(3)
    shadow_offset_x = NumericProperty(0)

    def on_press(self): self.shadow_offset_y = 1
    def on_release(self): self.shadow_offset_y = 3


class ScanButton(ButtonBehavior, Widget):
    color = ListProperty([1, 1, 1, 1])
    shadow_color = ListProperty([0, 0, 0, 0.25])
    shadow_offset_y = NumericProperty(3)
    shadow_offset_x = NumericProperty(0)

    def on_press(self):
        self.color = [0.9, 0.9, 0.9, 1]
        self.shadow_offset_y = 1

    def on_release(self):
        self.color = [1, 1, 1, 1]
        self.shadow_offset_y = 3


class GradientScanButton(ButtonBehavior, Widget):
    shadow_color = ListProperty([0, 0, 0, 0.25])
    shadow_offset_y = NumericProperty(3)
    shadow_offset_x = NumericProperty(0)
    gradient_texture = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self.create_gradient_texture, 0)

    def create_gradient_texture(self, *args):
        grad = np.zeros((1, 256, 4), dtype=np.float32)
        for i in range(256):
            t = i / 255.0
            r = (1 - t) * (0 / 255.0) + t * (255 / 255.0)
            g = (1 - t) * (157 / 255.0) + t * (192 / 255.0)
            b = (1 - t) * (0 / 255.0) + t * (75 / 255.0)
            grad[0, i] = [r, g, b, 1.0]

        texture = Texture.create(size=(256, 1), colorfmt='rgba')
        texture.blit_buffer(np.flipud((grad * 255).astype(np.uint8)).tobytes(),
                            colorfmt='rgba', bufferfmt='ubyte')
        texture.wrap = 'repeat'
        texture.uvsize = (1, -1)
        self.gradient_texture = texture

    def on_press(self): self.shadow_offset_y = 1
    def on_release(self): self.shadow_offset_y = 3


# =========================================
# ✅ SCREEN CLASSES
# =========================================
class WelcomeScreen(Screen):
    def on_enter(self):
        Clock.schedule_once(self.start_fade_animation, 0.2)

    def start_fade_animation(self, dt):
        label = self.ids.get('tap_label')
        if label:
            anim = (Animation(opacity=0, duration=1.2) +
                    Animation(opacity=1, duration=1.2))
            anim.repeat = True
            anim.start(label)

    def on_touch_down(self, touch):
        self.manager.current = 'home'
        return True


# These are placeholders but required to load the .kv files
class HomeScreen(Screen): pass
class ScanScreen(Screen): pass
class RecordsScreen(Screen): pass
class ShareScreen(Screen): pass
class HelpScreen(Screen): pass
class GuideScreen(Screen): pass


class ScanningScreen(Screen):
    def on_enter(self):
        Clock.schedule_once(self.go_to_result, 2)

    def go_to_result(self, dt):
        self.manager.current = 'capture_result'


class CaptureResultScreen(Screen): pass
class ResultScreen(Screen): pass
class SaveScreen(Screen): pass


# =========================================
# ✅ APP CLASS
# =========================================
class MangofyApp(App):
    scale_x = NumericProperty(1)
    scale_y = NumericProperty(1)

    def build(self):
        # Load all screen .kv files
        for kv_file in [
            "WelcomeScreen.kv", "HomeScreen.kv", "ScanScreen.kv",
            "RecordsScreen.kv", "ShareScreen.kv", "HelpScreen.kv",
            "GuideScreen.kv", "ScanningScreen.kv", "CaptureResultScreen.kv",
            "ResultScreen.kv", "SaveScreen.kv"
        ]:
            Builder.load_file(kv_file)

        sm = ScreenManager(transition=FadeTransition(duration=0.1))
        for scr, name in [
            (WelcomeScreen, 'welcome'), (HomeScreen, 'home'),
            (ScanScreen, 'scan'), (RecordsScreen, 'records'),
            (ShareScreen, 'share'), (HelpScreen, 'help'),
            (GuideScreen, 'guide'), (ScanningScreen, 'scanning'),
            (CaptureResultScreen, 'capture_result'),
            (ResultScreen, 'result'), (SaveScreen, 'save')
        ]:
            sm.add_widget(scr(name=name))

        sm.current = 'welcome'

        Window.bind(on_resize=self._update_scaling)
        self._update_scaling(Window, Window.width, Window.height)
        return sm

    def _update_scaling(self, window, width, height):
        self.scale_x = width / BASE_WIDTH
        self.scale_y = height / BASE_HEIGHT


if __name__ == '__main__':
    MangofyApp().run()
