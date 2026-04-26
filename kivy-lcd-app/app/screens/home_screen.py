from kivy.uix.screenmanager import Screen
from app.modals.exit_modal import ExitModal

class HomeScreen(Screen):
    """Represents the main home screen of the app."""

    def show_exit_confirmation(self):
        """Opens the custom shutdown modal."""
        modal = ExitModal()
        modal.open()
