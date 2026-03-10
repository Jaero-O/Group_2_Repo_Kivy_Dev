"""
ScanningModal.py
================
Key changes:
  - cancel_scan() force-dismisses immediately
  - cancel_flag passed to pipeline so it stops after current step
  - Distinct handling for no_leaf (recoverable) vs hard errors
  - Thread result ignored cleanly if cancelled
  - Removed progress bar / percentage
"""

import os
import threading
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.uix.modalview import ModalView
from kivy.lang import Builder

_kv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ScanningModal.kv")
Builder.load_file(_kv_path)


class ScanningModal(ModalView):
    image_path  = StringProperty("")
    status_text = StringProperty("Initializing scan...")

    PHASE_MAP = {
        "homing":      "Homing motor...",
        "scanning":    "Scanning leaf...",
        "capturing":   "Capturing frames...",
        "stitching":   "Stitching image...",
        "processing":  "Processing image...",
        "classifying": "Classifying disease...",
        "analyzing":   "Analyzing severity...",
        "complete":    "Scan complete!",
        "error":       "An error occurred",
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cancel_requested = False
        self._scan_thread      = None

    def on_open(self):
        self._cancel_requested = False
        self.status_text       = "Starting scan..."
        Clock.schedule_once(lambda dt: self._start_scan(), 0.2)

    # =========================================================================
    # START
    # =========================================================================
    def _start_scan(self):
        from app.scan.full_code_cleaned import ScanPipeline
        try:
            pipeline = ScanPipeline()
        except Exception as e:
            self.status_text = f"Pipeline init failed: {e}"
            Clock.schedule_once(lambda dt: self.dismiss(), 3.0)
            return

        self._cancel_requested = False
        self._scan_thread = threading.Thread(
            target=self._run_in_thread,
            args=(pipeline,),
            daemon=True
        )
        self._scan_thread.start()

    # =========================================================================
    # THREAD
    # =========================================================================
    def _run_in_thread(self, pipeline):
        def on_phase(phase, pct, message, reduced_image):
            Clock.schedule_once(
                lambda dt: self._update_ui(phase, message, reduced_image), 0
            )

        def cancel_flag():
            return self._cancel_requested

        results = pipeline.run_pipeline(on_phase=on_phase, cancel_flag=cancel_flag)
        Clock.schedule_once(lambda dt: self._on_pipeline_done(results), 0)

    # =========================================================================
    # UI UPDATE
    # =========================================================================
    def _update_ui(self, phase, message, reduced_image):
        if self._cancel_requested:
            return
        self.status_text = message if message else self.PHASE_MAP.get(phase, phase)
        if reduced_image:
            self.image_path = reduced_image

    # =========================================================================
    # PIPELINE DONE
    # =========================================================================
    def _on_pipeline_done(self, results):
        if self._cancel_requested:
            return

        status = results.get("status")

        if status == "cancelled":
            self.dismiss()
            return

        if status == "no_leaf":
            self.status_text = "No leaf detected — please reposition and try again."
            Clock.schedule_once(lambda dt: self.dismiss(), 3.0)
            return

        if status != "success":
            errors     = results.get("errors", [])
            last_error = errors[-1] if errors else "Unknown error"
            self.status_text = f"Scan failed: {last_error}"
            Clock.schedule_once(lambda dt: self.dismiss(), 3.0)
            return

        classification = results.get("classification") or {}
        analysis       = results.get("analysis")       or {}

        from kivy.app import App
        app = App.get_running_app()

        app.current_scan_id = results.get("database_id")
        app.scan_result = {
            "label":               classification.get("class", "Unknown"),
            "confidence":          classification.get("confidence", 0.0),
            "severity_percentage": analysis.get("severity_percent", 0.0),
            "severity_level":      analysis.get("severity_level", "None"),
            "image_path":          results.get("reduced_image", ""),
            "scan_timestamp":      results.get("timestamp", "N/A"),
        }

        self.image_path  = results.get("reduced_image", "")
        self.status_text = "Scan complete!"

        print(
            f"Scan complete: scan_id={app.current_scan_id}, "
            f"disease={classification.get('class')}, "
            f"confidence={classification.get('confidence', 0):.2%}"
        )

        Clock.schedule_once(lambda dt: self._finish_scan(), 0.5)

    # =========================================================================
    # FINISH
    # =========================================================================
    def _finish_scan(self):
        from kivy.app import App
        app = App.get_running_app()
        self.dismiss()
        Clock.schedule_once(
            lambda dt: setattr(app.root, 'current', 'capture_result'), 0.15
        )

    # =========================================================================
    # CANCEL
    # =========================================================================
    def cancel_scan(self):
        self._cancel_requested = True
        self.status_text = "Cancelling..."
        Clock.schedule_once(lambda dt: self.dismiss(), 0.3)
