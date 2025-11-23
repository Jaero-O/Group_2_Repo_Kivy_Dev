from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.properties import StringProperty, NumericProperty
from app.core.db import get_or_create_disease  # reuse insertion if needed
import sqlite3, os


class ResultScreen(Screen):
    prediction_label = StringProperty("")
    prediction_confidence = NumericProperty(0.0)
    severity_percentage = NumericProperty(0.0)
    severity_level = StringProperty("")
    image_path = StringProperty("")
    disease_description = StringProperty("")
    disease_symptoms = StringProperty("")
    disease_prevention = StringProperty("")
    formatted_timestamp = StringProperty("N/A")
    
    # Confidence badge properties
    confidence_badge_text = StringProperty("")
    confidence_badge_color = StringProperty("")

    def on_pre_enter(self, *args):
        self._load_from_app_state()

    def _load_from_app_state(self):
        app = App.get_running_app()
        data = getattr(app, "scan_result", {}) or {}
        self.prediction_label = data.get("label") or ""
        self.prediction_confidence = data.get("confidence") or 0.0
        self.severity_percentage = data.get("severity_percentage") or 0.0
        self.image_path = data.get("image_path") or ""
        self.severity_level = data.get("severity_level") or "Unknown"
        
        # Set confidence badge
        self._update_confidence_badge(self.prediction_confidence)
        
        # Format timestamp nicely
        timestamp = data.get("scan_timestamp") or "N/A"
        if timestamp != "N/A":
            try:
                from datetime import datetime
                dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                self.formatted_timestamp = dt.strftime("%B %d, %Y at %I:%M %p")
            except:
                self.formatted_timestamp = timestamp
        else:
            self.formatted_timestamp = "N/A"
        
        self._load_disease_metadata(self.prediction_label)

    def _load_disease_metadata(self, label: str):
        if not label:
            self.disease_description = ""
            self.disease_symptoms = ""
            self.disease_prevention = ""
            return
        # Direct DB query for disease metadata
        db_path = os.getenv("MANGOFY_DB_PATH", os.path.join(os.getcwd(), "mangofy.db"))
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT description, symptoms, prevention FROM tbl_disease WHERE name=?", (label,))
            row = cur.fetchone()
            if row:
                self.disease_description = row[0] or ""
                self.disease_symptoms = row[1] or ""
                self.disease_prevention = row[2] or ""
            else:
                # If not found yet, create minimal record
                get_or_create_disease(label)
                self.disease_description = "No description available yet."
                self.disease_symptoms = "Symptoms not documented."
                self.disease_prevention = "Prevention steps not documented."
        except Exception:
            self.disease_description = "Metadata lookup failed."
            self.disease_symptoms = ""
            self.disease_prevention = ""
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def go_back(self):
        app = App.get_running_app()
        if app.last_screen == 'image_select':
            app.root.current = 'image_select'
        else:
            app.root.current = 'capture_result'

    def view_full_info(self):
        '''Navigate to ScanDetailScreen to view full scan information.'''
        app = App.get_running_app()
        scan_id = getattr(app, 'current_scan_id', None)
        
        if scan_id:
            app.last_screen = 'result'
            app.root.current = 'scan_detail'
        else:
            print('Warning: No scan_id available for detailed view')
    
    def go_to_retake(self):
        '''Return to scanning screen to retake the scan.'''
        app = App.get_running_app()
        # Clear current scan result
        app.scan_result = None
        app.current_scan_id = None
        # Navigate back to appropriate screen
        if hasattr(app, 'last_screen') and app.last_screen == 'image_select':
            app.root.current = 'image_select'
        else:
            app.root.current = 'capture_result'
    
    def _update_confidence_badge(self, confidence):
        '''Update confidence badge text and color based on confidence value.'''
        if confidence < 0.60:
            self.confidence_badge_text = "⚠ Low Confidence"
            self.confidence_badge_color = "#DD2D1D"  # Red
        elif confidence < 0.85:
            self.confidence_badge_text = "Moderate Confidence"
            self.confidence_badge_color = "#CFBF2C"  # Yellow
        else:
            self.confidence_badge_text = "High Confidence"
            self.confidence_badge_color = "#26A421"  # Green
