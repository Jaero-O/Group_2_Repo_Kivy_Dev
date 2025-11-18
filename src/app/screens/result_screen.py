from kivy.uix.screenmanager import Screen
from kivy.app import App

class ResultScreen(Screen):
    """Screen that displays the scanning result and handles smart back navigation."""

    def go_back(self):
        """
        Navigate back based on the last active screen.
        - Returns to 'image_select' if the user came from image selection.
        - Otherwise, returns to 'capture_result'.
        """
        app = App.get_running_app()  # Get the running app instance

        if app.last_screen == 'image_select':
            app.root.current = 'image_select'  # Navigate back to image selection
        else:
            app.root.current = 'capture_result'  # Navigate back to capture result
