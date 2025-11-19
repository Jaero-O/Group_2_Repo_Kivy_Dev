from kivy.uix.screenmanager import Screen
from kivy.app import App
import threading
from kivy.clock import Clock
import os


class ScanLiveCamera(Screen):
    """Screen that captures an image from a Raspberry Pi camera and
    forwards it to the analysis pipeline. This class is defensive: on
    platforms without the necessary camera libraries, it will navigate
    back to the `scan` screen and log a warning.
    """
    def on_enter(self):
        app = App.get_running_app()
        # Start background capture so the UI remains responsive
            try:
                Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'scan'), 0)
            except Exception:
                pass

    def _capture_and_analyze(self):
        pass