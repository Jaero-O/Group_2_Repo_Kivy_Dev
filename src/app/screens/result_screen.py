from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from kivy.core.window import Window
import os
from app.theme import apply_background

# Headless test environment safety: provide stub DPI so Label creation
# does not force a real window provider when HEADLESS_TEST is active.
if os.environ.get('HEADLESS_TEST') == '1':
    try:
        from kivy import metrics as _metrics_module
        if getattr(_metrics_module.Metrics, '_dpi', None) is None:
            _metrics_module.Metrics._dpi = 96
    except Exception:
        pass

class ResultScreen(Screen):
    """Screen that displays the scanning result and handles smart back navigation.

    Provides a minimal API used by unit tests:
    - on_enter(): reads `App.get_running_app().analysis_result` and either
      requests a DB lookup (if record_id provided) or populates fields from
      an unsaved scan.
    - _populate_from_db_record(record): callback to populate UI for saved records.
    - _on_db_load_error(err): simple error handler.
    - go_back(): navigate back based on `_source_screen`.
    """

    # Source marker used by tests to control back navigation
    _source_screen = None

    # Indicates the result originated from an in-memory scan (True) or
    # from a saved/selected image (False). Bound from KV to show Save button.
    is_scan_result = BooleanProperty(False)

    # Kivy properties bound from KV so updates reflect in the UI
    image_path = StringProperty('')
    disease_name = StringProperty('')
    disease_description = StringProperty('')
    severity_name = StringProperty('')
    severity_percentage = NumericProperty(0.0)
    confidence = NumericProperty(0.0)
    # Compact mode toggles tighter layout metrics for pixel-parity comparisons
    compact_mode = BooleanProperty(os.environ.get('RESULT_COMPACT') == '1')

    # Lightweight legend item avoids font rendering (no Label dependency)
    # to stay safe in headless tests that lack a Window provider.
    from kivy.uix.widget import Widget as _LegendBase
    class LegendItem(_LegendBase):
        text = StringProperty('')

    def on_kv_post(self, base_widget):
        if os.environ.get('HEADLESS_TEST') == '1':
            legend = self.ids.get('severity_legend')
            if legend and not legend.children:
                for name in ['Healthy','Mild','Moderate','Severe']:
                    legend.add_widget(self.LegendItem(text=name))

    def on_enter(self):
        app = App.get_running_app()
        analysis = getattr(app, 'analysis_result', None) or {}

        # Apply unified background styling early to avoid capture timing issues.
        try:
            apply_background(self, 'bg_primary')
        except Exception:
            pass

        # If analysis contains a record_id, request DB to load it
        record_id = analysis.get('record_id')
        if record_id is not None:
            # request from DB asynchronously
            app.db_manager.get_record_by_id_async(
                record_id,
                on_success_callback=self._populate_from_db_record,
                on_error_callback=self._on_db_load_error
            )
            # remember source for go_back; allow callers to specify origin
            self._source_screen = analysis.get('source_screen', 'records')
            # A DB-backed record is not a fresh scan, so clear scan flag
            self.is_scan_result = False
            return

        # Otherwise, populate from the provided in-memory analysis result
        self._source_screen = analysis.get('source_screen', 'scan')
        # Mark whether this is an unsaved scan result so KV can show Save control
        self.is_scan_result = (self._source_screen == 'scan')
        # Use Kivy properties so KV bindings update automatically
        self.image_path = analysis.get('image_path') or ''
        self.disease_name = analysis.get('disease_name') or ''
        self.severity_percentage = analysis.get('severity_percentage', 0.0) or 0.0
        self.confidence = analysis.get('confidence', 0.0) or 0.0

        # Human-friendly strings used by tests (kept for backward compatibility)
        self.severity_percentage_str = f"{self.severity_percentage}%"
        self.confidence_score_str = f"{int(self.confidence * 100)}%"

        # Lookup extra info from DB manager (synchronous helper expected)
        try:
            details = app.db_manager.get_disease_and_severity_details(self.disease_name, None)
            self.disease_description = details.get('disease_description', '')
            # severity_name can be provided via details or left blank
            self.severity_name = details.get('severity_name', '') if isinstance(details, dict) else ''
        except Exception:
            self.disease_description = ''

        # Expose UI element states expected by tests
        if hasattr(self, 'ids'):
            if 'confidence_layout' in self.ids:
                self.ids.confidence_layout.opacity = 1
            if 'save_button' in self.ids:
                # Show or hide the save button depending on origin
                self.ids.save_button.opacity = 1 if self.is_scan_result else 0
                self.ids.save_button.disabled = not self.is_scan_result

        # Automated screenshot capture (optional) controlled via environment vars.
        # Set AUTO_CAPTURE_RESULT_SCREEN=1 to enable.
        if os.environ.get('AUTO_CAPTURE_RESULT_SCREEN') == '1':
            out_path = os.environ.get('RESULT_SCREENSHOT_PATH', 'screenshots/current_result.png')
            exit_flag = os.environ.get('EXIT_AFTER_CAPTURE') == '1'
            # Ensure directory exists
            try:
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
            except Exception:
                pass

            def _do_capture(dt):
                try:
                    Window.screenshot(name=out_path)
                    print(f"[AUTO_CAPTURE] ResultScreen screenshot saved to {out_path}")
                except Exception as e:
                    print(f"[AUTO_CAPTURE] Failed to capture screenshot: {e}")
                if exit_flag:
                    try:
                        App.get_running_app().stop()
                    except Exception:
                        pass
            # Schedule with slight delay to allow UI layout
            from kivy.clock import Clock
            Clock.schedule_once(_do_capture, 0.6)

    def _populate_from_db_record(self, record: dict):
        # Fill UI fields based on DB record
        self.image_path = record.get('image_path') or ''
        self.disease_name = record.get('disease_name') or ''
        self.severity_percentage = record.get('severity_percentage', 0.0) or 0.0
        self.confidence = record.get('confidence', 0.0) or 0.0
        self.severity_percentage_str = f"{self.severity_percentage}%"
        self.confidence_score_str = f"{int(self.confidence * 100)}%"

        # Get description if available
        try:
            app = App.get_running_app()
            details = app.db_manager.get_disease_and_severity_details(self.disease_name, None)
            self.disease_description = details.get('disease_description', '')
            self.severity_name = details.get('severity_name', '') if isinstance(details, dict) else ''
        except Exception:
            self.disease_description = ''

        # Saved records are not scans; hide scan-only UI
        self.is_scan_result = False
        if hasattr(self, 'ids'):
            if 'confidence_layout' in self.ids:
                self.ids.confidence_layout.opacity = 0
            if 'save_button' in self.ids:
                self.ids.save_button.opacity = 0
                self.ids.save_button.disabled = True

    def _on_db_load_error(self, err):
        print(f"Error loading record: {err}")

    def go_back(self):
        # Navigate back to the appropriate screen depending on where we came from
        if self._source_screen == 'scan':
            self.manager.current = 'scan'
        elif self._source_screen in ('image_selection', 'records'):
            # Viewing a saved/selected image should return to image selection or records
            self.manager.current = 'image_selection'
        else:
            # Default fallback
            self.manager.current = 'home'

    def open_save_screen(self):
        """Prepare the shared `analysis_result` and navigate to the Save screen.

        This is used when the user wants to save an in-memory scan result.
        """
        app = App.get_running_app()
        # Ensure the app.analysis_result contains up-to-date fields
        app.analysis_result = {
            'image_path': getattr(self, 'image_path', ''),
            'disease_name': getattr(self, 'disease_name', ''),
            'severity_percentage': getattr(self, 'severity_percentage', 0.0),
            'confidence': getattr(self, 'confidence', 0.0),
            'severity_name': getattr(self, 'severity_name', '')
        }
        # Navigate to the Save screen
        try:
            self.manager.current = 'save'
        except Exception:
            # If manager isn't available in tests, silently ignore
            pass
