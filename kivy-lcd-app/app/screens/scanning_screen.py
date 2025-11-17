import threading
import random
import os
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.clock import mainthread

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
            # Start the MOCK analysis in a separate thread to avoid blocking the UI
            threading.Thread(target=self._perform_mock_analysis, args=(image_path,)).start()
        else:
            # Fallback for development: if no path is provided, use a default mock path
            # This prevents the error and allows testing the scanning flow directly.
            print("Warning: No image path found. Using a default mock path for analysis.")
            threading.Thread(target=self._perform_mock_analysis, args=("mock/path/to/default.jpg",)).start()

    def _perform_mock_analysis(self, image_path: str):
        """Mocks the analysis process and navigates to the result screen."""
        print(f"MOCK SCAN: Generating random result for {os.path.basename(image_path)}")

        # Simulate a delay for the "scanning" process
        threading.Event().wait(1.5)

        # --- Create a random analysis result ---
        is_healthy = random.choice([True, False])

        if is_healthy:
            disease_name = "Healthy"
            severity_percentage = 0.0
            severity_name = "Healthy"
            confidence = random.uniform(0.85, 0.99)
        else:
            disease_name = "Anthracnose"
            severity_percentage = round(random.uniform(1.0, 60.0), 1)
            severity_name = "Early Stage" if severity_percentage < 10.0 else "Advanced Stage"
            confidence = random.uniform(0.75, 0.98)

        analysis_result = {
            "image_path": image_path,
            "disease_name": disease_name,
            "confidence": confidence,
            "severity_percentage": severity_percentage,
            "severity_name": severity_name
        }

        # Proceed to show the result on the result screen
        self._on_scan_complete(analysis_result)

    @mainthread
    def _on_scan_complete(self, result: dict):
        """Called on the main thread when scanning is finished to show the result."""
        app = App.get_running_app()
        app.analysis_result = result  # Store result for the next screen
        self.manager.current = 'result'
