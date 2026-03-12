"""Scanning Modal — opened as a ModalView from ScanScreen when Scan button is pressed."""
import os
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.modalview import ModalView
from kivy.lang import Builder
import subprocess
import json

# Load KV rules — must be before any Factory usage
_kv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ScanningModal.kv")
Builder.load_file(_kv_path)

class ScanningModal(ModalView):
    image_path = StringProperty("")
    status_text = StringProperty("Initializing scan...")
    progress_pct = NumericProperty(0.0)
    cancel_requested = False
    proc = None
    estimated_duration = 45.0
    poll_interval = 0.1
    progress_increment = 0.0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cancel_requested = False
        self.proc = None

    def on_open(self):
        self.progress_pct = 0.0
        self.cancel_requested = False
        self.status_text = "Starting scan..."
        self.progress_increment = (95.0 - self.progress_pct) * self.poll_interval / self.estimated_duration
        Clock.schedule_once(lambda dt: self._start_pipeline(), 0.2)

    def _start_pipeline(self):
        self.status_text = "Running pipeline..."
        Clock.schedule_once(lambda dt: self._run_subprocess(), 0.1)

    def _run_subprocess(self):
        """Call full pipeline script in a subprocess."""
        try:
            import os
            from pathlib import Path
            app_root = Path(__file__).parent.parent.parent.absolute()
            script_path = app_root / "app" / "scan" / "full_code_cleaned.py"

            print(f"=== Scanning Debug Info ===")
            print(f"App root: {app_root}")
            print(f"Script path: {script_path}")
            print(f"Script exists: {script_path.exists()}")
            print(f"Current working dir: {os.getcwd()}")

            os.chdir(str(app_root))
            print(f"Changed to: {os.getcwd()}")

            self.proc = subprocess.Popen(
                ["python3", str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(app_root)
            )
            print(f"Subprocess started with PID: {self.proc.pid}")
            Clock.schedule_interval(self._poll_subprocess, self.poll_interval)
        except Exception as e:
            print(f"Failed to start subprocess: {e}")
            import traceback
            traceback.print_exc()
            self.status_text = f"Pipeline failed: {str(e)}"
            self.progress_pct = 0

    def _poll_subprocess(self, dt):
        if self.cancel_requested:
            if self.proc and self.proc.poll() is None:
                self.proc.terminate()
            self.progress_pct = 0
            self.status_text = "Scan cancelled"
            self.dismiss()
            return False

        if self.proc.poll() is not None:
            stdout, stderr = self.proc.communicate()

            if stderr:
                print("STDERR from scanner:")
                print(stderr)
            if stdout:
                print("STDOUT from scanner:")
                print(stdout)

            if self.proc.returncode != 0:
                error_msg = stderr[:200] if stderr else "Unknown error"
                self.status_text = f"Scan failed: {error_msg}"
                self.progress_pct = 0
                Clock.schedule_once(lambda dt: self.dismiss(), 2.0)
                return False

            try:
                lines = stdout.strip().split('\n')
                final_json = lines[-1] if lines else stdout
                results = json.loads(final_json)

                classification = results.get("classification") or {}
                analysis = results.get("analysis") or {}

                from kivy.app import App
                app = App.get_running_app()

                reduced_image_path = results.get("reduced_image", "output_image_reduced.png")
                
                # Don't set scan_id - not saved to database yet
                app.current_scan_id = None
                
                # Store complete results including temp directory info
                app.scan_result = {
                    "classification": results.get("classification"),
                    "analysis": results.get("analysis"),
                    "temp_scan_dir": results.get("temp_scan_dir"),
                    "scan_timestamp": results.get("scan_timestamp"),
                    "label": classification.get("class", "Unknown"),
                    "confidence": classification.get("confidence", 0.0),
                    "severity_percentage": analysis.get("severity_percent", 0.0) if analysis else 0.0,
                    "severity_level": analysis.get("severity_level", "None") if analysis else "None",
                    "image_path": reduced_image_path,
                    "total_leaf_area": analysis.get("leaf_area_cm2") if analysis else None,
                    "lesion_area": analysis.get("lesion_area_cm2") if analysis else None
                }

                print(f"Scan complete: disease={classification.get('class')}, confidence={classification.get('confidence'):.2%}, temp_dir={results.get('temp_scan_dir')}")

                self.image_path = reduced_image_path
                self.status_text = "Scan complete!"
                self.progress_pct = 100.0

                # Dismiss modal then navigate to capture_result
                Clock.schedule_once(lambda dt: self._finish_scan(), 0.5)
            except Exception as e:
                print(f"Failed to parse results: {e}")
                import traceback
                traceback.print_exc()
                self.status_text = "Scan failed - no valid output"
                self.progress_pct = 0
                Clock.schedule_once(lambda dt: self.dismiss(), 2.0)
            return False

        if self.progress_pct < 95.0:
            self.progress_pct += self.progress_increment
        return True

    def _finish_scan(self):
        """Dismiss modal and navigate to capture_result screen."""
        from kivy.app import App
        app = App.get_running_app()
        self.dismiss()
        Clock.schedule_once(lambda dt: setattr(app.root, 'current', 'capture_result'), 0.15)

    def cancel_scan(self):
        """User requested to cancel the scan — dismiss modal, return to scan screen."""
        self.cancel_requested = True
        self.status_text = "Cancelling scan..."