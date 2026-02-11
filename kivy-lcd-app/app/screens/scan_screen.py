from kivy.uix.screenmanager import Screen
from kivy.app import App

class ScanScreen(Screen):
    """
    Represents the scanning screen of the app.
    
    This screen provides the main entry point to the scanning workflow:
    - Central 'Scan' button initiates the hardware capture pipeline
    - Navigates to ScanningScreen which handles:
      1. Motor homing
      2. Frame capture (4 frames)
      3. Image stitching
      4. Disease analysis
    """
    
    def on_pre_enter(self):
        """Called before screen is displayed."""
        # Reset any previous scan results
        app = App.get_running_app()
        if hasattr(app, 'scan_result'):
            app.scan_result = {}
    
    def start_scanning(self):
        """Initiate hardware scanning workflow."""
        app = App.get_running_app()
        app.last_screen = 'scan'
        app.root.current = 'scanning'

