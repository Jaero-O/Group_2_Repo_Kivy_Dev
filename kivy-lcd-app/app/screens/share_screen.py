import os
from pathlib import Path
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty
from kivy.app import App
import json
import qrcode
import time


class ShareScreen(Screen):
    """Screen for sharing captured or processed results."""

    qr_image_source = StringProperty('app/assets/qr_placeholder.png')

    def on_pre_enter(self):
        # Generate or refresh QR code when screen is displayed.
        app = App.get_running_app()
        scan_id = getattr(app, 'current_scan_id', None) or '001'
        self.generate_qr_code(scan_id)

    def generate_qr_code(self, scan_id: str):
        payload = {
            'ssid': 'Pi-Proto-Net',
            'pwd': 'prototype_pass',
            'scan_url': f'http://192.168.4.1:5000/api/scan/{scan_id}',
            'scan_id': scan_id,
            'issued_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        }

        export_dir = Path(os.getcwd()) / 'kivy-lcd-app' / 'app' / 'exports'
        export_dir.mkdir(parents=True, exist_ok=True)
        qr_file = export_dir / f'qr_scan_{scan_id}.png'

        try:
            qrcode.make(json.dumps(payload)).save(str(qr_file))
            self.qr_image_source = str(qr_file)
        except Exception as e:
            print(f'[ShareScreen] QR generation failed: {e}')
            self.qr_image_source = 'app/assets/qr_placeholder.png'
