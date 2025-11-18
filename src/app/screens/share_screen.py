from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.app import App
import os
import socket
import qrcode
import logging

class ShareScreen(Screen):
    """Screen for sharing captured or processed results."""
    # This property will hold the path to the generated QR code image.
    # The .kv file will bind to this to display the image.
    qr_code_path = StringProperty("app/assets/qr_placeholder.png")
    server_address_text = StringProperty("Initializing...")

    def on_enter(self, *args):
        """Generate a QR code when the screen is entered."""
        self.generate_qr_code()

    def get_local_ip(self):
        """Tries to get the local IP address of the machine."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Doesn't have to be reachable
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[0]
        except (socket.error, OSError): # Catch specific network-related errors
            ip = '127.0.0.1' # Fallback to localhost
        finally:
            s.close()
        return ip

    def generate_qr_code(self):
        """
        Generates a QR code containing the local IP address and saves it as an image.
        """
        app = App.get_running_app()
        ip_address = self.get_local_ip()
        port = 8000 # A standard port for a local web server
        data_to_encode = f"http://{ip_address}:{port}"

        self.server_address_text = f"Scan to connect to:\n{data_to_encode}"
        logging.info(f"ShareScreen: Encoding '{data_to_encode}' into QR code.")

        # Define a path inside the app's user data directory for the QR code
        qr_code_filename = "sharing_qr.png"
        path = os.path.join(app.user_data_dir, qr_code_filename)

        # Generate and save the QR code image
        img = qrcode.make(data_to_encode)
        img.save(path)

        # Update the property to trigger the UI change in the .kv file
        self.qr_code_path = path

        # Explicitly reload the image widget to ensure the new QR code is displayed
        # This avoids the recursion error caused by using on_source in the .kv file.
        if self.ids.qr_code_image:
            self.ids.qr_code_image.reload()
