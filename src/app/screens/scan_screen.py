from kivy.uix.screenmanager import Screen
from kivy.app import App
import threading
from kivy.clock import Clock
import os
from app.theme import apply_background, COLORS, FONTS


class ScanScreen(Screen):
    """Image selection / capture staging screen.

    This class preserves the existing `select_image` API used by tests
    (setting `App.get_running_app().analysis_image_path` and navigating
    to the `scanning` screen). Additionally it provides a
    `start_live_capture()` helper that uses the Raspberry Pi camera
    helper in `app.core.camera` to capture a still image in a
    background thread and then navigates to the `scanning` screen.
    The capture logic is defensive (lazy imports) so desktop tests
    and non-RPi environments are not affected.
    """

    def select_image(self, image_path: str):
        """Called when the user selects an image from the gallery.

        Tests expect this to set `App.get_running_app().analysis_image_path`
        and navigate to the `scanning` screen. If `image_path` is falsy,
        do nothing.
        """
        if not image_path:
            return

        app = App.get_running_app()
        app.analysis_image_path = image_path
        # Store last screen for navigation context
        app.last_screen = 'scan'
        if hasattr(self, 'manager') and self.manager:
            self.manager.current = 'scanning'
        # Apply background & update tokens once image selected
        # Styling operations skipped in headless tests to avoid graphics initialization.
        if os.environ.get('HEADLESS_TEST') != '1':
            try:
                apply_background(self, 'bg_primary')
                if 'select_label' in self.ids:
                    self.ids.select_label.color = COLORS['text_primary']
                if 'hint_label' in self.ids:
                    self.ids.hint_label.color = COLORS['text_secondary']
            except Exception:
                pass

    def start_live_capture(self):
        """Begin a background capture from a Raspberry Pi camera.

        This spawns a daemon thread so the UI remains responsive. The
        actual camera API is imported lazily inside the thread to keep
        imports safe for unit tests.
        """
        t = threading.Thread(target=self._capture_and_navigate)
        t.daemon = True
        t.start()
        if os.environ.get('HEADLESS_TEST') != '1':
            try:
                apply_background(self, 'bg_primary')
            except Exception:
                pass

    def start_multi_frame_capture(self, frame_count: int = 4):
        """Capture multiple frames and stitch them before analysis.
        Falls back to single placeholder on desktop.
        """
        t = threading.Thread(target=self._multi_frame_worker, args=(frame_count,))
        t.daemon = True
        t.start()

    def _multi_frame_worker(self, frame_count: int):
        app = App.get_running_app()
        try:
            from app.core.camera import capture_multi_frame_stitched
            save_dir = os.path.join(os.getcwd(), 'data', 'captures')
            os.makedirs(save_dir, exist_ok=True)
            base_path = os.path.join(save_dir, 'capture_multi')
            stitched = capture_multi_frame_stitched(base_path, count=frame_count)
            app.analysis_image_path = stitched
            app.last_screen = 'scan'
            print(f"DIAG: multi-frame stitched: {stitched}")
            def _nav(dt):
                if hasattr(self, 'manager') and self.manager:
                    self.manager.current = 'scanning'
            Clock.schedule_once(_nav, 0)
        except Exception as exc:
            print(f"DIAG: multi-frame capture failed: {exc}")
            # Fallback to placeholder path
            placeholder = os.path.join(os.path.dirname(__file__), '..', 'assets', 'placeholder_bg1.png')
            placeholder = os.path.abspath(os.path.normpath(placeholder))
            app.analysis_image_path = placeholder
            app.last_screen = 'scan'
            def _nav(dt):
                if hasattr(self, 'manager') and self.manager:
                    self.manager.current = 'scanning'
            Clock.schedule_once(_nav, 0)

    def _capture_and_navigate(self):
        """Background worker that uses `capture_image_raspicam` to write
        a file and then schedules navigation to the `scanning` screen.

        On failure (no camera libs or runtime error) the user is sent
        to the `image_selection` screen as a fallback.
        """
        app = App.get_running_app()
        try:
            # lazy import so tests on non-RPi machines don't fail at import time
            from app.core.camera import capture_image_raspicam

            # Ensure save directory exists
            save_dir = os.path.join(os.getcwd(), 'data', 'captures')
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, 'capture.jpg')

            capture_image_raspicam(save_path)

            # Attach image path to the app and prepare UI update
            app.analysis_image_path = save_path
            app.last_screen = 'scan'

            # Diagnostic: announce the captured path so logs show the event
            try:
                print(f"DIAG: captured: {save_path}")
            except Exception:
                pass

            # Update the preview widget on the main thread, then navigate
            # after a short delay so the preview is visible briefly.
            def _show_preview(dt):
                try:
                    if hasattr(self, 'ids') and 'camera_preview' in self.ids:
                        try:
                            self.ids.camera_preview.source = save_path
                            if hasattr(self.ids.camera_preview, 'reload'):
                                self.ids.camera_preview.reload()
                        except Exception:
                            pass

                    if hasattr(self, 'ids') and 'preview_placeholder' in self.ids:
                        try:
                            self.ids.preview_placeholder.opacity = 0
                        except Exception:
                            pass
                except Exception:
                    pass

            def _nav_to_scanning(dt):
                try:
                    if hasattr(self, 'manager') and self.manager:
                        self.manager.current = 'scanning'
                except Exception:
                    pass

            # Show preview immediately, then navigate after 0.4s
            Clock.schedule_once(_show_preview, 0)
            Clock.schedule_once(_nav_to_scanning, 0.4)
        except Exception as exc:
            # Distinguish between 'no camera API available' (desktop/dev)
            # and other runtime errors. If there is no camera API, use a
            # lightweight desktop fallback so developers can test the flow
            # without being bounced to the image selection screen.
            msg = str(exc or '')
            no_camera = 'No Raspberry Pi camera API' in msg or isinstance(exc, NotImplementedError)
            if no_camera:
                # Use a placeholder image from the app assets directory as a
                # fake 'capture' so the preview and scanning flow continue.
                placeholder = os.path.join(os.path.dirname(__file__), '..', 'assets', 'placeholder_bg1.png')
                placeholder = os.path.abspath(os.path.normpath(placeholder))
                
                # Diagnostic output
                try:
                    print(f"DIAG: no camera available, using placeholder: {placeholder}")
                    print(f"DIAG: placeholder exists: {os.path.exists(placeholder)}")
                except Exception:
                    pass
                
                # Set the analysis image path regardless of whether file exists
                # The scanning screen will handle missing files gracefully
                app.analysis_image_path = placeholder
                app.last_screen = 'scan'

                # Synchronous preview update (tests rely on immediate state)
                try:
                    if hasattr(self, 'ids') and 'camera_preview' in self.ids:
                        self.ids.camera_preview.source = placeholder
                        if hasattr(self.ids.camera_preview, 'reload'):
                            self.ids.camera_preview.reload()
                    if hasattr(self, 'ids') and 'preview_placeholder' in self.ids:
                        self.ids.preview_placeholder.opacity = 0
                except Exception:
                    pass

                def _show_placeholder(dt):
                    try:
                        if hasattr(self, 'ids') and 'camera_preview' in self.ids:
                            try:
                                self.ids.camera_preview.source = placeholder
                                if hasattr(self.ids.camera_preview, 'reload'):
                                    self.ids.camera_preview.reload()
                            except Exception:
                                pass
                        if hasattr(self, 'ids') and 'preview_placeholder' in self.ids:
                            try:
                                self.ids.preview_placeholder.opacity = 0
                            except Exception:
                                pass
                    except Exception:
                        pass

                def _nav(dt):
                    try:
                        if hasattr(self, 'manager') and self.manager:
                            self.manager.current = 'scanning'
                            print("DIAG: navigating to 'scanning' screen")
                    except Exception as e:
                        print(f"DIAG: navigation failed: {e}")
                        pass

                Clock.schedule_once(_show_placeholder, 0)
                Clock.schedule_once(_nav, 0.4)
                return

            # Other failures: go to image selection as fallback
            try:
                print(f"DIAG: camera error (not NotImplementedError), falling back to image_selection: {exc}")
                Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'image_selection'), 0)
            except Exception:
                pass
