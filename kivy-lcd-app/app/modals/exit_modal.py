"""Exit Modal - Confirmation dialog for exiting the application."""
from kivy.uix.modalview import ModalView
from kivy.app import App
from kivy.lang import Builder
import os

# Load the KV file
kv_path = os.path.join(os.path.dirname(__file__), 'ExitModal.kv')
Builder.load_file(kv_path)


class ExitModal(ModalView):
    """Modal for confirming application exit."""
    
    def __init__(self, **kwargs):
        super(ExitModal, self).__init__(**kwargs)

    def cancel(self):
        """Closes the modal without exiting."""
        self.dismiss()

    def confirm_exit(self):
        """Safely terminates the application."""
        App.get_running_app().stop()