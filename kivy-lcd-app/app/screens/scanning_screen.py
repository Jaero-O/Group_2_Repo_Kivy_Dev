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
            # Use relative path from app root
            import os
            from pathlib import Path
            app_root = Path(__file__).parent.parent.parent.absolute()
            script_path = app_root / "app" / "scan" / "full_code_cleaned.py"
            
            print(f"=== Scanning Debug Info ===")
            print(f"App root: {app_root}")
            print(f"Script path: {script_path}")
            print(f"Script exists: {script_path.exists()}")
            print(f"Python command: python3")
            print(f"Current working dir: {os.getcwd()}")
            
            # Change to kivy-lcd-app directory so relative paths work
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
            # Poll subprocess every poll_interval
            Clock.schedule_interval(self._poll_subprocess, self.poll_interval)
        except Exception as e:
            print(f"Failed to start subprocess: {e}")
            import traceback
            traceback.print_exc()
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
            
            # Debug output
            if stderr:
                print("STDERR from scanner:")
                print(stderr)
            if stdout:
                print("STDOUT from scanner:")
                print(stdout)
            
            # Check for errors
            if self.proc.returncode != 0:
                error_msg = stderr[:200] if stderr else "Unknown error"
                self.status_text = f"Scan failed: {error_msg}"
                self.progress_pct = 0
                Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'image_select'), 2.0)
                return False
            
            try:
                # Parse only the last line of stdout (final results JSON)
                lines = stdout.strip().split('\n')
                final_json = lines[-1] if lines else stdout
                results = json.loads(final_json)
                
                # Extract data from results
                classification = results.get("classification") or {}
                analysis = results.get("analysis") or {}
                
                # Prepare data for ResultScreen
                from kivy.app import App
                app = App.get_running_app()
                
                # Get the reduced image path for display
                reduced_image_path = results.get("reduced_image", "output_image_reduced.png")
                scan_id = results.get("database_id")
                
                # Store scan_id for ResultScreen to load from database
                app.current_scan_id = scan_id
                
                # Build scan_result dictionary that ResultScreen expects (fallback)
                app.scan_result = {
                    "label": classification.get("class", "Unknown"),
                    "confidence": classification.get("confidence", 0.0),
                    "severity_percentage": analysis.get("severity_percent", 0.0) if analysis else 0.0,
                    "severity_level": analysis.get("severity_level", "None") if analysis else "None",
                    "image_path": reduced_image_path,
                    "scan_timestamp": results.get("timestamp", "N/A")
                }
                
                print(f"Scan complete: scan_id={scan_id}, disease={classification.get('class')}, confidence={classification.get('confidence'):.2%}")
                
                self.image_path = reduced_image_path
                self.status_text = "Scan complete!"
                self.progress_pct = 100.0
                # Auto-transition to result screen after short delay
                Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'capture_result'), 0.5)
            except Exception as e:
                print(f"Failed to parse results: {e}")
                import traceback
                traceback.print_exc()
                self.status_text = "Scan failed - no valid output"
                self.progress_pct = 0
                Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'image_select'), 2.0)
            return False  # Stop polling

        # Increment progress proportionally to estimated duration
        if self.progress_pct < 95.0:
            self.progress_pct += self.progress_increment
        return True  # Continue polling

    def cancel_scan(self):
        """User requested to cancel the scan and return to main menu."""
        self.cancel_requested = True
        self.status_text = "Cancelling scan..."
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
            # Use relative path from app root
            import os
            from pathlib import Path
            app_root = Path(__file__).parent.parent.parent.absolute()
            script_path = app_root / "app" / "scan" / "full_code_cleaned.py"
            
            print(f"=== Scanning Debug Info ===")
            print(f"App root: {app_root}")
            print(f"Script path: {script_path}")
            print(f"Script exists: {script_path.exists()}")
            print(f"Python command: python3")
            print(f"Current working dir: {os.getcwd()}")
            
            # Change to kivy-lcd-app directory so relative paths work
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
            # Poll subprocess every poll_interval
            Clock.schedule_interval(self._poll_subprocess, self.poll_interval)
        except Exception as e:
            print(f"Failed to start subprocess: {e}")
            import traceback
            traceback.print_exc()
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
            
            # Debug output
            if stderr:
                print("STDERR from scanner:")
                print(stderr)
            if stdout:
                print("STDOUT from scanner:")
                print(stdout)
            
            # Check for errors
            if self.proc.returncode != 0:
                error_msg = stderr[:200] if stderr else "Unknown error"
                self.status_text = f"Scan failed: {error_msg}"
                self.progress_pct = 0
                Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'image_select'), 2.0)
                return False
            
            try:
                # Parse only the last line of stdout (final results JSON)
                lines = stdout.strip().split('\n')
                final_json = lines[-1] if lines else stdout
                results = json.loads(final_json)
                
                # Extract data from results
                classification = results.get("classification") or {}
                analysis = results.get("analysis") or {}
                
                # Prepare data for ResultScreen
                from kivy.app import App
                app = App.get_running_app()
                
                # Get the reduced image path for display
                reduced_image_path = results.get("reduced_image", "output_image_reduced.png")
                scan_id = results.get("database_id")
                
                # Store scan_id for ResultScreen to load from database
                app.current_scan_id = scan_id
                
                # Build scan_result dictionary that ResultScreen expects (fallback)
                app.scan_result = {
                    "label": classification.get("class", "Unknown"),
                    "confidence": classification.get("confidence", 0.0),
                    "severity_percentage": analysis.get("severity_percent", 0.0) if analysis else 0.0,
                    "severity_level": analysis.get("severity_level", "None") if analysis else "None",
                    "image_path": reduced_image_path,
                    "scan_timestamp": results.get("timestamp", "N/A")
                }
                
                print(f"Scan complete: scan_id={scan_id}, disease={classification.get('class')}, confidence={classification.get('confidence'):.2%}")
                
                self.image_path = reduced_image_path
                self.status_text = "Scan complete!"
                self.progress_pct = 100.0
                # Auto-transition to result screen after short delay
                Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'capture_result'), 0.5)
            except Exception as e:
                print(f"Failed to parse results: {e}")
                import traceback
                traceback.print_exc()
                self.status_text = "Scan failed - no valid output"
                self.progress_pct = 0
                Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'image_select'), 2.0)
            return False  # Stop polling

        # Increment progress proportionally to estimated duration
        if self.progress_pct < 95.0:
            self.progress_pct += self.progress_increment
        return True  # Continue polling

    def cancel_scan(self):
        """User requested to cancel the scan and return to main menu."""
        self.cancel_requested = True
        self.status_text = "Cancelling scan..."
