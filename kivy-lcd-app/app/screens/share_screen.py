from pathlib import Path
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty
from kivy.app import App
import json
import qrcode


class ShareScreen(Screen):
    """Screen for sharing captured or processed results."""

    qr_image_source = StringProperty('app/assets/qr_placeholder.png')

    def on_pre_enter(self):
        # Generate or refresh QR code when screen is displayed.
        # If a scan is currently active, make the QR point to that scan.
        app = App.get_running_app()
        scan_id = getattr(app, 'current_scan_id', None) or '001'
        self.generate_qr_code(scan_id)

    def generate_qr_code(self, scan_id: str):
        payload = {
            'ssid': 'Pi-Proto-Net',
            'pwd': 'prototype_pass',
            'scan_url': f'http://192.168.4.1:5000/api/scan/{scan_id}',
            'scan_id': scan_id,
            'issued_at': App.get_running_app().root._get_window().clock.get_time() if hasattr(App.get_running_app().root, '_get_window') else ''
        }

        export_dir = Path(self.root_window and self.root_window.user_data_dir or '.') / 'app' / 'exports'
        export_dir.mkdir(parents=True, exist_ok=True)
        qr_file = export_dir / f'qr_scan_{scan_id}.png'

        try:
            qrcode.make(json.dumps(payload)).save(str(qr_file))
            self.qr_image_source = str(qr_file)
        except Exception as e:
            print(f'[ShareScreen] QR generation failed: {e}')
            self.qr_image_source = 'app/assets/qr_placeholder.png'
