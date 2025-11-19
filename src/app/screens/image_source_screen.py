from kivy.uix.screenmanager import Screen
from app.theme import apply_background

class ImageSourceScreen(Screen):
    def on_take_photo(self):
        # Navigate to the live camera scanning screen
        if hasattr(self, 'manager') and self.manager is not None:
            # The unified scan screen now performs live capture on RasPi
            self.manager.current = 'scan'

    def on_pre_enter(self, *args):
        # Apply background for improved parity.
        try:
            apply_background(self, 'bg_primary')
        except Exception:
            pass
