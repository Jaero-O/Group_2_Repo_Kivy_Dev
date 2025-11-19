from kivy.uix.screenmanager import Screen
from kivy.app import App

class CaptureResultScreen(Screen):
    """Screen that handles capture results and navigates to the result screen."""

    def open_result(self):
        """
        Switch to the 'result' screen and store the last active screen.
        This helps maintain navigation context in the app.
        """
        app = App.get_running_app()  # Get the running app instance
        app.last_screen = 'capture_result'  # Record this screen as last active
        # Ensure the result data is available to the ResultScreen. If the
        # capture flow saved an image path on the app, pass it along and
        # mark the source as a fresh scan so the Save button appears.
        try:
            img = getattr(app, 'analysis_image_path', None)
            app.analysis_result = {'image_path': img or '', 'source_screen': 'scan'}
        except Exception:
            try:
                setattr(app, 'analysis_result', {'image_path': '', 'source_screen': 'scan'})
            except Exception:
                pass
        self.manager.current = 'result'  # Navigate to the 'result' screen
