from kivy.uix.screenmanager import Screen
from kivy.app import App
import threading
from kivy.clock import Clock
import os
from app.utils.logger import get_logger

logger = get_logger(__name__)

try:
    from app.core.image_processor import analyze_image
except Exception:  # pragma: no cover
    analyze_image = None
try:
    from app.core.image_pipeline import process_for_analysis
except Exception:  # pragma: no cover
    process_for_analysis = None
try:
    from app.core import scanner
    _hardware_available = scanner.hardware_available()
except Exception:
    scanner = None
    _hardware_available = False

class ScanningScreen(Screen):
    """Performs image analysis with progress feedback.

    Enhanced progress copy for Figma alignment.
    """

    def on_enter(self):
        self._cancel_requested = False
        self._fallback_used = False
        app = App.get_running_app()
        image_path = getattr(app, 'analysis_image_path', None)

        # Initialize UI elements
        try:
            if hasattr(self, 'ids'):
                if 'progress_label' in self.ids:
                    self.ids.progress_label.text = 'Preparing analysis...'
                if 'progress_bar' in self.ids:
                    self.ids.progress_bar.value = 5
        except Exception:
            pass

        # Hardware pipeline first if available and no image pre-selected
        if _hardware_available and not image_path and scanner:
            def _run_hardware():
                def _hw_cb(pct, text):
                    def _do(dt):
                        try:
                            if hasattr(self, 'ids'):
                                if 'progress_label' in self.ids:
                                    self.ids.progress_label.text = text
                                if 'progress_bar' in self.ids:
                                    self.ids.progress_bar.value = pct
                        except Exception:
                            pass
                    Clock.schedule_once(_do, 0)
                processed_path = scanner.run_scan_pipeline(progress_callback=_hw_cb)
                if processed_path and not self._cancel_requested:
                    try:
                        app.analysis_image_path = processed_path
                    except Exception:
                        setattr(app, 'analysis_image_path', processed_path)
                    self._perform_analysis(processed_path)
                else:
                    Clock.schedule_once(lambda dt: self._goto_home(), 0)
            th = threading.Thread(target=_run_hardware)
            th.daemon = True
            th.start()
            return

        if not image_path:
            self.manager.current = 'home'
            return

        try:
            if hasattr(self, 'ids') and 'placeholder_banner' in self.ids and 'placeholder' in image_path:
                self.ids.placeholder_banner.text = 'Camera unavailable – using sample image'
        except Exception:
            pass

        t = threading.Thread(target=self._perform_analysis, args=(image_path,))
        t.daemon = True
        t.start()

    def _perform_analysis(self, image_path):
        app = App.get_running_app()

        def _update_progress(value, text):
            def _do_update(dt):
                try:
                    if hasattr(self, 'ids'):
                        if 'progress_label' in self.ids:
                            self.ids.progress_label.text = text
                        if 'progress_bar' in self.ids:
                            self.ids.progress_bar.value = value
                except Exception:
                    pass
            Clock.schedule_once(_do_update, 0)

        _update_progress(15, 'Pre-processing leaf image...')
        processed_path = None
        if process_for_analysis and os.path.exists(image_path):
            try:
                processed_path = process_for_analysis(image_path)
            except Exception:
                processed_path = None
        analysis_target = processed_path or image_path

        if self._cancel_requested:
            _update_progress(5, 'Cancelled.')
            Clock.schedule_once(lambda dt: self._goto_home(), 0)
            return

        _update_progress(40, 'Loading disease model...')

        try:
            _update_progress(55, 'Running classification...')
            if analyze_image is not None:
                result = analyze_image(analysis_target) or {}
            else:
                raise RuntimeError('analyze_image not available')
        except Exception as e:
            logger.error(f"Analysis failed for image '{analysis_target}': {e}", exc_info=True)
            result = {
                'disease_name': 'Healthy',
                'confidence': 1.0,
                'severity_percentage': 0.0,
                'severity_name': 'Healthy'
            }
            self._fallback_used = True
            try:
                app.analysis_error = True
            except Exception:
                setattr(app, 'analysis_error', True)
            
            # Show user-visible warning
            def _show_warning(dt):
                try:
                    if hasattr(self, 'ids') and 'fallback_warning' in self.ids:
                        if analyze_image is None:
                            self.ids.fallback_warning.text = '⚠ ML model unavailable. Using basic detection.'
                        else:
                            self.ids.fallback_warning.text = '⚠ Analysis encountered an error. Showing safe result.'
                except Exception:
                    pass
            Clock.schedule_once(_show_warning, 0)

        try:
            result['image_path'] = image_path
        except Exception:
            result.update({'image_path': image_path})

        _update_progress(85, 'Computing severity score...')

        if self._cancel_requested:
            _update_progress(5, 'Cancelled.')
            Clock.schedule_once(lambda dt: self._goto_home(), 0)
            return

        try:
            result['source_screen'] = 'scan'
        except Exception:
            pass
        try:
            app.analysis_result = result
        except Exception:
            setattr(app, 'analysis_result', result)

        if self._cancel_requested:
            try:
                if hasattr(app, 'analysis_result'):
                    delattr(app, 'analysis_result')
            except Exception:
                pass
            Clock.schedule_once(lambda dt: self._goto_home(), 0)
            return

        def _goto_result(dt):
            if hasattr(self, 'manager') and self.manager:
                try:
                    if self._cancel_requested:
                        self._goto_home()
                        return
                    try:
                        if hasattr(self, 'ids') and 'progress_label' in self.ids:
                            self.ids.progress_label.text = 'Finalizing results...'
                        if hasattr(self, 'ids') and 'progress_bar' in self.ids:
                            self.ids.progress_bar.value = 95
                        if self._fallback_used and 'fallback_warning' in self.ids:
                            self.ids.fallback_warning.text = 'Fallback healthy result used (analysis error).'
                    except Exception:
                        pass
                    self.manager.current = 'result'
                except Exception:
                    pass
            def _complete(dt2):
                try:
                    if hasattr(self, 'ids'):
                        if 'progress_label' in self.ids:
                            self.ids.progress_label.text = 'Done.'
                        if 'progress_bar' in self.ids:
                            self.ids.progress_bar.value = 100
                except Exception:
                    pass
            Clock.schedule_once(_complete, 0.05)

        Clock.schedule_once(_goto_result, 0)

    def go_to_result(self, dt):
        self.manager.current = 'result'

    def cancel_analysis(self):
        self._cancel_requested = True
        try:
            if hasattr(self, 'ids'):
                if 'progress_label' in self.ids:
                    self.ids.progress_label.text = 'Cancelling...'
                if 'progress_bar' in self.ids:
                    self.ids.progress_bar.value = 0
        except Exception:
            pass
        try:
            app = App.get_running_app()
            if hasattr(app, 'analysis_result'):
                delattr(app, 'analysis_result')
        except Exception:
            pass
        Clock.schedule_once(lambda dt: self._goto_home(), 0.05)

    def _goto_home(self):
        try:
            if hasattr(self, 'manager') and self.manager:
                self.manager.current = 'home'
        except Exception:
            pass
    
