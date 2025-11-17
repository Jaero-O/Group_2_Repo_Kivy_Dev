# app/screens/scanning_screen.py
import threading
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.clock import mainthread
from app.core import analyze_image

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
            # Start the analysis in a separate thread to avoid blocking the UI
            threading.Thread(target=self._perform_analysis, args=(image_path,)).start()
        else:
            print("Error: No image path found for analysis. Returning to scan screen.")
            self.manager.current = 'scan'

    def _perform_analysis(self, image_path: str):
        """The actual analysis function that runs in a thread."""
        analysis_result = analyze_image(image_path)
        self._on_analysis_complete(analysis_result)

    @mainthread
    def _on_analysis_complete(self, result: dict):
        """
        Called on the main thread when analysis is finished.
        """
        app = App.get_running_app()
        app.analysis_result = result  # Store result for the next screen
        self.manager.current = 'result'