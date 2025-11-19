from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import StringProperty

class HomeScreen(Screen):
    """Represents the main home screen of the app."""
    pass


class TouchableButton(ButtonBehavior, BoxLayout):
    """Python backing class for KV <TouchableButton> rule."""
    screen_name = StringProperty('')
    icon_source = StringProperty('')
    button_text = StringProperty('')
