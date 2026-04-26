"""Save Success Modal — shown after a scan is successfully saved."""
import os
from kivy.uix.modalview import ModalView
from kivy.properties import StringProperty
from kivy.app import App
from kivy.lang import Builder

# Load KV rules — must be before any Factory usage
_kv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SaveSuccessModal.kv")
Builder.load_file(_kv_path)

class SaveSuccessModal(ModalView):
    message = StringProperty("")

    def __init__(self, tree_name="", **kwargs):
        super().__init__(**kwargs)
        self.message = f'Leaf successfully saved\nto "{tree_name}"'
        self._action_taken = False  # Guard against double-tap on resistive touchscreen

    def _guard(self):
        """Returns True if action should proceed, False if already triggered."""
        if self._action_taken:
            return False
        self._action_taken = True
        return True

    def go_scan(self):
        if not self._guard():
            return
        self.dismiss()
        app = App.get_running_app()
        app.root.current = 'scan'

    def go_home(self):
        if not self._guard():
            return
        self.dismiss()
        app = App.get_running_app()
        app.root.current = 'home'
