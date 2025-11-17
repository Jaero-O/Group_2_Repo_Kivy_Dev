# app/screens/scan_screen.py
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty

class ScanScreen(Screen):
    """
    The screen where the user chooses to either take a photo
    or upload an existing one.
    """
    def select_image(self, image_path: str):
        """
        Called when an image is selected from the ImageSelection screen.
        This method triggers the analysis process.
        """
        if image_path:
            print(f"Image selected for analysis: {image_path}")
            # Store the image path in the App instance to be accessed by the ScanningScreen
            app = App.get_running_app()
            app.analysis_image_path = image_path
            self.manager.current = 'scanning'