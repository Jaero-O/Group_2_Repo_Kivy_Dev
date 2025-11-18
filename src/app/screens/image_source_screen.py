from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
import os
from kivy.app import App

class ImageSourceScreen(Screen):
    """
    A screen that allows the user to choose the source of the image for analysis,
    such as taking a new photo or selecting from the gallery.
    """
    def on_take_photo(self):
        """
        Handles the 'Take Photo' button press.
        """
        print("LOGIC: 'Take Photo' pressed. Navigating to the live camera screen.")
        # This should navigate to the screen that shows the live camera feed.
        self.manager.current = 'scan_live_camera' # Assuming 'scan_live_camera' is the name of your live camera screen