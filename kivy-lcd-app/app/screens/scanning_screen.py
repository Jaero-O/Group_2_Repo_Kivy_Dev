from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty
import subprocess
import json

class ScanningScreen(Screen):
    image_path = StringProperty("")
    status_text = StringProperty("Initializing scan...")
    progress_pct = NumericProperty(0.0)  # Start at 5%
    cancel_requested = False
    proc = None  # Store subprocess handle
    estimated_duration = 45.0  # Estimated pipeline duration in seconds
    poll_interval = 0.1  # seconds
    progress_increment = 0.0  # Calculated dynamically

    def on_enter(self):
        self.progress_pct = 0.0
        self.cancel_requested = False
        self.status_text = "Starting scan..."
        # Calculate increment so progress reaches ~95% in estimated_duration
        self.progress_increment = (95.0 - self.progress_pct) * self.poll_interval / self.estimated_duration
        Clock.schedule_once(lambda dt: self._start_pipeline(), 0.2)

    def _start_pipeline(self):
        self.status_text = "Running pipeline..."
        Clock.schedule_once(lambda dt: self._run_subprocess(), 0.1)

    def _run_subprocess(self):
        """Call full pipeline script in a subprocess."""
        try:
            self.proc = subprocess.Popen(
                ["python3", "/home/kennethbinasa/kivy_v1/kivy-lcd-app/app/scan/full_code_cleaned.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            # Poll subprocess every poll_interval
            Clock.schedule_interval(self._poll_subprocess, self.poll_interval)
        except Exception as e:
            self.status_text = f"Pipeline failed: {str(e)}"
            self.progress_pct = 0

    def _poll_subprocess(self, dt):
        # Handle cancellation
        if self.cancel_requested:
            if self.proc and self.proc.poll() is None:
                self.proc.terminate()
            self.progress_pct = 0
            self.status_text = "Scan cancelled"
            self.manager.current = 'image_select'
            return False  # Stop polling

        # Check if subprocess finished
        if self.proc.poll() is not None:
            stdout, stderr = self.proc.communicate()
            try:
                results = json.loads(stdout)
                self.image_path = results.get("reduced_image", "output_image_reduced.png")
                self.status_text = "Scan complete!"
            except Exception:
                self.status_text = "Scan complete!"
            self.progress_pct = 100.0
            # Auto-transition to result screen after short delay
            Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'capture_result'), 0.5)
            return False  # Stop polling

        # Increment progress proportionally to estimated duration
        if self.progress_pct < 95.0:
            self.progress_pct += self.progress_increment
        return True  # Continue polling

    def cancel_scan(self):
        """User requested to cancel the scan and return to main menu."""
        self.cancel_requested = True
        self.status_text = "Cancelling scan..."
