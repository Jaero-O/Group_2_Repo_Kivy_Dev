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
        scan_id = getattr(app, 'current_scan_id', None)
        if scan_id is None:
            from app.core.db import get_recent_scans
            recent = get_recent_scans(limit=1)
            if recent:
                scan_id = str(recent[0].get('id', '1'))
            else:
                scan_id = '1'

        self.generate_qr_code(str(scan_id))

    def generate_qr_code(self, scan_id: str):
        pi_ip = os.getenv('PI_IP', '192.168.4.1')
        base_url = f'http://{pi_ip}:5000'
        payload = {
            'ssid': 'Pi-Proto-Net',
            'pwd': 'prototype_pass',
            'scan_url': f'{base_url}/api/scan/{scan_id}',
            'scan_all_url': f'{base_url}/api/scan/all',
            'scan_since_url': f'{base_url}/api/scan/since',
            'status_url': f'{base_url}/api/status',
            'scan_id': scan_id,
            'source': 'pi',
            'issued_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        }

        # optional alternative URL for remote testing (ZeroTier fallback)
        zt_ip = os.getenv('ZEROTIER_PI_IP')
        if zt_ip:
            zt_base = f'http://{zt_ip}:5000'
            payload['alt_scan_url'] = f'{zt_base}/api/scan/{scan_id}'
            payload['alt_status_url'] = f'{zt_base}/api/status'

        export_dir = Path(os.getcwd()) / 'kivy-lcd-app' / 'app' / 'exports'
        export_dir.mkdir(parents=True, exist_ok=True)
        qr_file = export_dir / f'qr_scan_{scan_id}.png'

        try:
            qrcode.make(json.dumps(payload)).save(str(qr_file))
            self.qr_image_source = str(qr_file)
        except Exception as e:
            print(f'[ShareScreen] QR generation failed: {e}')
            self.qr_image_source = 'app/assets/qr_placeholder.png'
