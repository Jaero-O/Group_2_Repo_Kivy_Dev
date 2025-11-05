from kivy.uix.screenmanager import Screen
from kivy.app import App

class ResultScreen(Screen):
    def go_back(self):
        """Smart back navigation depending on where user came from."""
        app = App.get_running_app()

        if app.last_screen == 'image_select':
            app.root.current = 'image_select'
        else:
            app.root.current = 'capture_result'
