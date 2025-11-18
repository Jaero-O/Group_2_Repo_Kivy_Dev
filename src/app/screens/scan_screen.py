from kivy.app import App
from kivy.uix.screenmanager import Screen
import os

class ScanScreen(Screen):
    """
    The screen where the user chooses to either take a photo
    or upload an existing one.
    """
    def select_image(self, image_path: str):
        """
        Called when an image is selected.
        This method triggers the analysis process.
        """
        if not image_path:
            print("ScanScreen: No image path provided.")
            return

        app = App.get_running_app()
        app.analysis_image_path = image_path
        self.manager.current = 'scanning'
