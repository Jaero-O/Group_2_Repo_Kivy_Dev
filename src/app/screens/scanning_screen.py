import threading
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty
from kivy.clock import Clock
from kivy.lang import Builder
import os
from kivy.clock import mainthread
from app.core.image_processor import analyze_image

class ScanningScreen(Screen):
    """
    A screen that shows a "Scanning..." message while the image
    analysis is being performed in the background.
    """
    def on_enter(self, *args):
        """
        When the screen is entered, start the analysis in a background thread.
        """
        app = App.get_running_app()
        image_path = getattr(app, 'analysis_image_path', None)

        if image_path:
            threading.Thread(target=self._perform_analysis, args=(image_path,)).start()
        else:
            print("Warning: No image path found. Cannot perform analysis.")
            # Or handle this case gracefully, e.g., by going back to the previous screen
            self.manager.current = 'home'

    def _perform_analysis(self, image_path: str):
        """
        Performs the image analysis and navigates to the result screen.
        """
        analysis_result = analyze_image(image_path)
        self._on_scan_complete(analysis_result)

    @mainthread
    def _on_scan_complete(self, result: dict):
        """Called on the main thread when scanning is finished to show the result."""
        app = App.get_running_app()
        app.analysis_result = result
        self.manager.current = 'result'
