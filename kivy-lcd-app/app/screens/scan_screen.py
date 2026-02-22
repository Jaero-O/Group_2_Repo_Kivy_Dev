"""Scan Screen — main entry point for the scanning workflow."""
from kivy.uix.screenmanager import Screen
from kivy.app import App

class ScanScreen(Screen):
    """
    Represents the scanning screen of the app.

    - Cancel: navigate back to Home
    - Scan: navigate to ScanningScreen
    - Guide: open GuideModal overlay
    """

    def on_pre_enter(self):
        """Reset any previous scan results before screen is shown."""
        app = App.get_running_app()
        if hasattr(app, 'scan_result'):
            app.scan_result = {}
        # Reset modal guards so they can be re-opened each time
        self._guide_open = False
        self._scanning_open = False

    def open_scanning_modal(self):
        """Open ScanningModal as an overlay — guarded against double-tap."""
        if getattr(self, '_scanning_open', False):
            return
        self._scanning_open = True

        from app.modals.scanning_modal import ScanningModal
        modal = ScanningModal()
        modal.bind(on_dismiss=lambda *_: setattr(self, '_scanning_open', False))
        modal.open()

    def open_guide_modal(self):
        """Open GuideModal as an overlay — guarded against double-tap."""
        if getattr(self, '_guide_open', False):
            return
        self._guide_open = True

        from app.modals.guide_modal import GuideModal
        modal = GuideModal()
        modal.bind(on_dismiss=lambda *_: setattr(self, '_guide_open', False))
        modal.open()