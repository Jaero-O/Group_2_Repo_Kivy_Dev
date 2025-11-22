from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty
from kivy.app import App
from kivy.uix.popup import Popup
from kivy.uix.label import Label
import os

try:
    from ml.processing.severity_constants import severity_stage
except Exception:
    def severity_stage(severity_pct: float, label: str) -> str:
        # Fallback simple mapping
        if label.lower() == 'healthy' or severity_pct < 10:
            return 'Healthy'
        if severity_pct < 30:
            return 'Early Stage'
        return 'Advanced Stage'

try:
    from ml.predictor import DiseasePredictor
    from ml.processing.severity import compute_severity
except Exception:
    DiseasePredictor = None
    compute_severity = None

try:
    from app.core.db import (
        get_or_create_disease,
        get_or_create_severity,
        insert_tree,
    )
except Exception:
    get_or_create_disease = lambda name: -1
    get_or_create_severity = lambda name: -1
    insert_tree = lambda name: -1


class ScanningScreen(Screen):
    image_path = StringProperty("")
    prediction_label = StringProperty("")
    prediction_confidence = NumericProperty(0.0)
    severity_percentage = NumericProperty(0.0)
    status_text = StringProperty("Initializing capture...")
    progress_pct = NumericProperty(0.0)
    current_frame = NumericProperty(0)
    total_frames = NumericProperty(0)
    
    # Cancel and timeout tracking
    cancel_requested = False
    timeout_event = None

    def on_enter(self):
        # Reset cancel state
        self.cancel_requested = False
        
        # Set up 30-second timeout
        if self.timeout_event:
            self.timeout_event.cancel()
        self.timeout_event = Clock.schedule_once(self._on_timeout, 30.0)
        
        # Start multi-frame capture pipeline
        Clock.schedule_once(self._begin_capture_pipeline, 0.2)

    def _begin_capture_pipeline(self, *_):
        if self.cancel_requested:
            self.status_text = "Cancelled"
            return
        
        from app.core.capture import MultiFrameCapture
        test_image = os.getenv("MANGOFY_TEST_IMAGE", "")
        if not test_image or not os.path.exists(test_image):
            self.status_text = "Test image missing; set MANGOFY_TEST_IMAGE"
            self._cancel_timeout()
            return
        output_dir = os.path.join(os.getcwd(), "data", "captures")
        capture = MultiFrameCapture(total_frames=4)
        self.total_frames = capture.total_frames

        def progress_cb(phase, frame_index, total_frames, pct):
            if self.cancel_requested:
                return False  # Signal cancellation
            
            self.progress_pct = pct
            self.current_frame = frame_index
            
            # Detailed status messages based on phase
            if phase == 'homing':
                self.status_text = "Homing motor..."
            elif phase == 'positioning':
                self.status_text = f"Positioning for frame {frame_index}..."
            elif phase == 'capturing':
                self.status_text = f"Scanning {frame_index} out of {total_frames} Frames..."
            elif phase == 'stitching':
                self.status_text = "Stitching Frames..."
            elif phase == 'preprocessing':
                self.status_text = "Processing image..."
            elif phase == 'analyzing':
                self.status_text = "Analyzing disease..."
            elif phase == 'complete':
                self.status_text = "Capture complete"
            elif phase == 'capture_error':
                self.status_text = "Frame error, retrying..."
            elif phase == 'homing_failed':
                self.status_text = "Motor homing failed"
            elif phase == 'capture_failed':
                self.status_text = "Capture failed"
            elif phase == 'stitching_failed':
                self.status_text = "Stitching failed"

        stitched = capture.run(test_image, output_dir, callback=progress_cb)
        
        # Cancel timeout if completed
        self._cancel_timeout()
        
        if self.cancel_requested:
            self.status_text = "Cancelled by user"
            return
        
        if stitched:
            # Run prediction & severity on stitched image
            success = self.run_scan(stitched, tree_name=os.getenv("MANGOFY_DEFAULT_TREE", "Default Tree"))
            if success:
                Clock.schedule_once(self.go_to_capture_result, 0.8)
        else:
            self.status_text = "Capture failed"
            self._show_error_with_options("Capture failed. Try again?")

    def run_scan(self, image_path: str, tree_name: str):
        self.image_path = image_path
        if DiseasePredictor is None:
            self._show_missing_model_popup("TFLite interpreter unavailable. Install tflite-runtime or tensorflow.")
            return False
        model_path = os.getenv("MANGOFY_MODEL_PATH", os.path.join("ml", "models", "mango_mobilenetv2.tflite"))
        if not os.path.exists(model_path):
            self._show_missing_model_popup(f"Model file not found:\n{model_path}\nSet MANGOFY_MODEL_PATH or place the file locally.")
            return False
        try:
            predictor = DiseasePredictor(model_path, labels_path=os.getenv("MANGOFY_LABELS_PATH", ""))
            label, conf = predictor.predict(image_path)
            self.prediction_label = label
            self.prediction_confidence = conf
            
            # Compute severity and get leaf areas
            total_leaf_area = 0.0
            lesion_area = 0.0
            if compute_severity:
                # Try to use the new function with areas
                try:
                    from ml.processing.severity import compute_severity_with_areas
                    self.severity_percentage, total_leaf_area, lesion_area = compute_severity_with_areas(image_path)
                except (ImportError, TypeError):
                    # Fallback to old function if new one not available
                    self.severity_percentage = compute_severity(image_path)
            
            sev_level_name = severity_stage(self.severity_percentage, label)
            # Defer persistence until SaveScreen confirmation
            tree_id = insert_tree(tree_name) if tree_name else None
            app = App.get_running_app()
            app.scan_result = {
                "label": self.prediction_label,
                "confidence": self.prediction_confidence,
                "severity_percentage": self.severity_percentage,
                "total_leaf_area": total_leaf_area,
                "lesion_area": lesion_area,
                "image_path": self.image_path,
                "severity_level": sev_level_name,
                "tree_id": tree_id,
            }
            return True
        except FileNotFoundError as e:
            self._show_missing_model_popup(str(e))
            return False
        except Exception as e:
            self._show_missing_model_popup(f"Prediction error: {e}")
            return False

    def _show_missing_model_popup(self, message: str):
        try:
            Popup(title="Model Missing", content=Label(text=message), size_hint=(0.7, 0.4)).open()
        except Exception:
            # If Popup fails (e.g., context), fallback to console output
            print("[Model Warning]", message)

    # Deprecated: severity level mapping now centralized in severity_constants.severity_stage

    def go_to_capture_result(self, *_):
        self.manager.current = 'capture_result'
    
    def cancel_scan(self):
        '''User requested to cancel the scan.'''
        self.cancel_requested = True
        self.status_text = "Cancelling..."
        self._cancel_timeout()
        # Return to appropriate screen
        Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'image_select'), 1.0)
    
    def _on_timeout(self, dt):
        '''Called when 30-second timeout expires.'''
        if not self.cancel_requested and self.manager.current == 'scanning':
            self.status_text = "Analysis timeout"
            self._show_error_with_options("Analysis timed out after 30 seconds. Try again?")
    
    def _cancel_timeout(self):
        '''Cancel the timeout event if it exists.'''
        if self.timeout_event:
            self.timeout_event.cancel()
            self.timeout_event = None
    
    def _show_error_with_options(self, message: str):
        '''Show error popup with Try Again and Cancel options.'''
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.button import Button
        
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text=message, halign='center', valign='middle'))
        
        buttons = BoxLayout(size_hint_y=0.3, spacing=10)
        
        popup = Popup(
            title="Scan Error",
            content=content,
            size_hint=(0.8, 0.4),
            auto_dismiss=False
        )
        
        def on_try_again(instance):
            popup.dismiss()
            self.cancel_requested = False
            Clock.schedule_once(self._begin_capture_pipeline, 0.2)
        
        def on_cancel(instance):
            popup.dismiss()
            self.manager.current = 'image_select'
        
        buttons.add_widget(Button(text="Cancel", on_press=on_cancel))
        buttons.add_widget(Button(
            text="Try Again",
            background_color=(0.2, 0.7, 0.3, 1.0),
            on_press=on_try_again
        ))
        
        content.add_widget(buttons)
        popup.open()
