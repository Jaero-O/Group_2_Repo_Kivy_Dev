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
import numpy as np

# ========== SCREEN SETTINGS ==========
WIDTH, HEIGHT = 360, 640

# Detect if running on Raspberry Pi
IS_PI = False
try:
    with open("/proc/cpuinfo") as f:
        IS_PI = "Raspberry Pi" in f.read()
except Exception:
    IS_PI = False

# ---------- Apply Screen Settings ----------
if IS_PI:
    Window.fullscreen = True
    print("Running on Raspberry Pi → fullscreen mode enabled.")
else:
    Window.size = (WIDTH, HEIGHT)
    Window.fullscreen = False
    try:
        import tkinter as tk
        root = tk.Tk()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        root.destroy()

        x = int((screen_width - WIDTH) / 2)
        y = int((screen_height - HEIGHT) / 2)
        Window.left = x
        Window.top = y
        print(f"Centered window at {x}, {y} on desktop.")
    except Exception as e:
        print("Centering skipped:", e)


# -------- General-purpose Rounded Button --------
class RoundedButton(ButtonBehavior, Widget):
    radius = NumericProperty(18)
    shadow_color = ListProperty([0, 0, 0, 0.25])
    shadow_offset_y = NumericProperty(3)
    shadow_offset_x = NumericProperty(0)

    def on_press(self):
        # slight visual feedback
        self.shadow_offset_y = 1

    def on_release(self):
        self.shadow_offset_y = 3


# -------- Home Screen Scan Button --------
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


# -------- Scan Screen Gradient Button --------
class GradientScanButton(ButtonBehavior, Widget):
    shadow_color = ListProperty([0, 0, 0, 0.25])
    shadow_offset_y = NumericProperty(3)
    shadow_offset_x = NumericProperty(0)
    gradient_texture = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create the gradient texture after widget init
        Clock.schedule_once(self.create_gradient_texture, 0)

    def create_gradient_texture(self, *args):
        # Green → Yellow gradient (rgba(0,157,0,1) → rgba(255,192,75,1))
        grad = np.zeros((1, 256, 4), dtype=np.float32)
        for i in range(256):
            t = i / 255.0
            r = (1 - t) * (0 / 255.0) + t * (255 / 255.0)
            g = (1 - t) * (157 / 255.0) + t * (192 / 255.0)
            b = (1 - t) * (0 / 255.0) + t * (75 / 255.0)
            grad[0, i] = [r, g, b, 1.0]

        texture = Texture.create(size=(256, 1), colorfmt='rgba')
        texture.blit_buffer(
            np.flipud((grad * 255).astype(np.uint8)).tobytes(),
            colorfmt='rgba', bufferfmt='ubyte'
        )
        texture.wrap = 'repeat'
        texture.uvsize = (1, -1)
        self.gradient_texture = texture

    def on_press(self):
        # Subtle push-down shadow effect
        self.shadow_offset_y = 1

    def on_release(self):
        self.shadow_offset_y = 3


# -------- Screen Definitions --------
class WelcomeScreen(Screen):
    def on_enter(self):
        Clock.schedule_once(self.start_fade_animation, 0.2)

    def start_fade_animation(self, dt):
        if 'tap_label' in self.ids:
            label = self.ids.tap_label
            anim = (Animation(opacity=0, duration=1.2) +
                    Animation(opacity=1, duration=1.2))
            anim.repeat = True
            anim.start(label)

    def on_touch_down(self, touch):
        self.manager.current = 'home'
        return True


class HomeScreen(Screen):
    pass


class ScanScreen(Screen):
    pass


class RecordsScreen(Screen):
    pass


class ShareScreen(Screen):
    pass


class HelpScreen(Screen):
    pass


class GuideScreen(Screen):
    pass

class ScanningScreen(Screen):
    def on_enter(self):
        # Simulate scanning delay, then go to result screen
        Clock.schedule_once(self.go_to_result, 3)

    def go_to_result(self, dt):
        self.manager.current = 'capture_result'

class CaptureResultScreen(Screen):
    pass

class ResultScreen(Screen):
    pass

class SaveScreen(Screen):
    pass

# --------- App Class ---------
class MangofyApp(App):
    def build(self):
        Builder.load_file("WelcomeScreen.kv")
        Builder.load_file("HomeScreen.kv")
        Builder.load_file("ScanScreen.kv")
        Builder.load_file("RecordsScreen.kv")
        Builder.load_file("ShareScreen.kv")
        Builder.load_file("HelpScreen.kv")
        Builder.load_file("GuideScreen.kv")
        Builder.load_file("ScanningScreen.kv")
        Builder.load_file("CaptureResultScreen.kv")
        Builder.load_file("ResultScreen.kv")
        Builder.load_file("SaveScreen.kv")

        sm = ScreenManager(transition=FadeTransition(duration=0.1))
        sm.add_widget(WelcomeScreen(name='welcome'))
        sm.add_widget(HomeScreen(name='home'))
        sm.add_widget(ScanScreen(name='scan'))
        sm.add_widget(RecordsScreen(name='records'))
        sm.add_widget(ShareScreen(name='share'))
        sm.add_widget(HelpScreen(name='help'))
        sm.add_widget(GuideScreen(name='guide'))
        sm.add_widget(ScanningScreen(name='scanning'))
        sm.add_widget(CaptureResultScreen(name='capture_result'))
        sm.add_widget(ResultScreen(name='result'))
        sm.add_widget(SaveScreen(name='save'))

        sm.current = 'welcome'
        return sm


# --------- Run App ---------
if __name__ == '__main__':
    MangofyApp().run()
