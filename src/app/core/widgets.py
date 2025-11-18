# app/core/widgets.py
from kivy.uix.widget import Widget
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import ListProperty, NumericProperty, ObjectProperty
from kivy.graphics.texture import Texture
from kivy.clock import Clock
from kivy.uix.image import AsyncImage
import numpy as np

# =========================================
# ✅ BUTTON CLASSES
# =========================================
class RoundedButton(ButtonBehavior, Widget):
    radius = NumericProperty(18)
    shadow_color = ListProperty([0, 0, 0, 0.25])
    shadow_offset_y = NumericProperty(3)
    shadow_offset_x = NumericProperty(0)

    def on_press(self):
        self.shadow_offset_y = 1

    def on_release(self):
        self.shadow_offset_y = 3


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

    def on_press(self):
        self.shadow_offset_y = 1

    def on_release(self):
        self.shadow_offset_y = 3

class RecycleViewImage(ButtonBehavior, AsyncImage): # This is the viewclass for the RecycleView
    """
    An image that acts like a button, used in the image grid.
    It holds the record data associated with the image.
    The 'record_data' property is automatically populated by the RecycleView
    from the 'data' list.
    """
    record_data = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Use fit_mode instead of deprecated properties
        self.fit_mode = "cover"
