import os
from kivy.uix.modalview import ModalView
from kivy.lang import Builder

# Load KV rules — must be before any Factory usage
_kv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "GuideModal.kv")
Builder.load_file(_kv_path)

class GuideModal(ModalView):
    """Displays scanning instructions as an overlay modal."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._dismissed = False

    def dismiss(self, *args, **kwargs):
        # Guard against double-tap dismiss on resistive touchscreen
        if self._dismissed:
            return
        self._dismissed = True
        super().dismiss(*args, **kwargs)
