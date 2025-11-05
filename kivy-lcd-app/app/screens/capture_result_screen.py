from kivy.uix.screenmanager import Screen

class CaptureResultScreen(Screen):
    def open_result(self):
        app = App.get_running_app()
        app.last_screen = 'capture_result'
        self.manager.current = 'result'
