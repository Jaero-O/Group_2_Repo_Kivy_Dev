from kivy.uix.screenmanager import Screen
from kivy.app import App # Explicit import

class CaptureResultScreen(Screen):
    """Screen that handles capture results and navigates to the result screen."""

    def open_result(self):
        """
        Switch to the 'result' screen and store the last active screen.
        This helps maintain navigation context in the app.
        """
        app = App.get_running_app()
        app.last_screen = 'capture_result'  # Record this screen as last active
        self.manager.current = 'result'  # Navigate to the 'result' screen
