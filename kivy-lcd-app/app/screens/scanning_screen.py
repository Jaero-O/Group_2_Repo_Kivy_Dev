from kivy.uix.screenmanager import Screen
from kivy.clock import Clock

class ScanningScreen(Screen):
    def on_enter(self):
        Clock.schedule_once(self.go_to_result, 2)

    def go_to_result(self, dt):
        self.manager.current = 'capture_result'
