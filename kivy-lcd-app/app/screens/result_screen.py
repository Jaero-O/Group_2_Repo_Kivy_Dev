"""Result Screen - Displays scan results with disease classification and severity."""
from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.properties import StringProperty, NumericProperty
from app.core.db import get_or_create_disease
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

    # Classification tag properties (replaces old confidence badge)
    confidence_badge_text = StringProperty("")
    confidence_badge_color = StringProperty("")

    def on_pre_enter(self, *args):
        self._load_from_database_or_app_state()

    def _load_from_database_or_app_state(self):
        app = App.get_running_app()
        scan_id = getattr(app, 'current_scan_id', None)
        print(f"[ResultScreen] on_pre_enter: scan_id={scan_id}")
        if scan_id:
            print(f"[ResultScreen] Loading from database with scan_id={scan_id}")
            self._load_from_database(scan_id)
        else:
            print(f"[ResultScreen] Loading from app.scan_result")
            self._load_from_app_state()

    def _load_from_database(self, scan_id):
        db_path = os.getenv("MANGOFY_DB_PATH", os.path.join(os.getcwd(), "mangofy.db"))
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    sr.disease_class, sr.confidence_score, 
                    sr.severity_percentage, sr.severity_level,
                    sr.image_path, sr.scan_timestamp,
                    d.name, d.description, d.symptoms, d.prevention
                FROM tbl_scan_record sr
                LEFT JOIN tbl_disease d ON sr.disease_id = d.id
                WHERE sr.id = ?
            """, (scan_id,))
            row = cur.fetchone()
            conn.close()

            if row:
                disease_class, confidence, severity_pct, severity_lvl, img_path, timestamp, \
                    disease_name, description, symptoms, prevention = row

                self.prediction_label = disease_class or disease_name or "Unknown"
                self.prediction_confidence = confidence or 0.0
                self.severity_percentage = severity_pct or 0.0
                self.severity_level = severity_lvl or "None"

                placeholder_image = os.path.join(os.getcwd(), 'assets', 'placeholder.png')
                if img_path:
                    if not os.path.isabs(img_path):
                        app_root = os.getcwd()
                        abs_path = os.path.abspath(os.path.join(app_root, img_path))
                        print(f"[ResultScreen] Image path: {img_path} -> {abs_path}")
                    else:
                        abs_path = img_path
                        print(f"[ResultScreen] Image path (absolute): {abs_path}")

                    if os.path.exists(abs_path):
                        self.image_path = abs_path
                        print(f"[ResultScreen] Image exists: True")
                    else:
                        self.image_path = placeholder_image
                        print(f"[ResultScreen] Image exists: False. Falling back to placeholder: {placeholder_image}")
                else:
                    self.image_path = placeholder_image
                    print(f"[ResultScreen] No image path in database. Using placeholder: {placeholder_image}")

                self.disease_description = description or ""
                self.disease_symptoms = symptoms or ""
                self.disease_prevention = prevention or ""

                if timestamp and timestamp != "N/A":
                    try:
                        from datetime import datetime
                        if "T" in timestamp:
                            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                        else:
                            dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                        self.formatted_timestamp = dt.strftime("%B %d, %Y %I:%M %p")
                    except Exception as e:
                        print(f"Timestamp parse error: {e}")
                        self.formatted_timestamp = timestamp or "N/A"
                else:
                    self.formatted_timestamp = "N/A"

                self._update_classification_tag(self.prediction_confidence)
                print(f"[ResultScreen] Loaded from DB: {self.prediction_label}, {self.prediction_confidence:.2%}, {self.severity_level}")
            else:
                print(f"[ResultScreen] No data found for scan_id={scan_id}")
                self._set_defaults()

        except Exception as e:
            print(f"[ResultScreen] Database load error: {e}")
            import traceback
            traceback.print_exc()
            self._set_defaults()

    def _set_defaults(self):
        self.prediction_label = "Unknown"
        self.prediction_confidence = 0.0
        self.severity_percentage = 0.0
        self.severity_level = "None"
        self.image_path = ""
        self.disease_description = ""
        self.disease_symptoms = ""
        self.disease_prevention = ""
        self.formatted_timestamp = "N/A"
        self.confidence_badge_text = "No Data"
        self.confidence_badge_color = "#808080"

    def _load_from_app_state(self):
        app = App.get_running_app()
        data = getattr(app, "scan_result", {}) or {}
        print(f"[ResultScreen] app.scan_result data: {data}")

        self.prediction_label = data.get("label") or ""
        self.prediction_confidence = data.get("confidence") or 0.0
        self.severity_percentage = data.get("severity_percentage") or 0.0
        self.severity_level = data.get("severity_level") or "None"

        placeholder_image = os.path.join(os.getcwd(), 'assets', 'placeholder.png')
        image_path = data.get("image_path") or ""
        if image_path and os.path.exists(image_path):
            self.image_path = image_path
            print(f"[ResultScreen] Image path (app state): {image_path} exists")
        else:
            self.image_path = placeholder_image
            print(f"[ResultScreen] Image missing or invalid: {image_path}. Using placeholder: {placeholder_image}")

        print(f"[ResultScreen] Loaded from app state: {self.prediction_label}, {self.prediction_confidence:.2%}, image={self.image_path}")

        self._update_classification_tag(self.prediction_confidence)

        timestamp = data.get("scan_timestamp") or "N/A"
        if timestamp != "N/A":
            try:
                from datetime import datetime
                if "T" in timestamp:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                else:
                    dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                self.formatted_timestamp = dt.strftime("%B %d, %Y %I:%M %p")
            except Exception as e:
                print(f"Timestamp parse error: {e}")
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
        app = App.get_running_app()
        scan_id = getattr(app, 'current_scan_id', None)
        if scan_id:
            app.last_screen = 'result'
            app.root.current = 'scan_detail'
        else:
            print('Warning: No scan_id available for detailed view')

    def go_to_retake(self):
        app = App.get_running_app()
        app.scan_result = None
        app.current_scan_id = None
        if hasattr(app, 'last_screen') and app.last_screen == 'image_select':
            app.root.current = 'image_select'
        else:
            app.root.current = 'capture_result'

    def _update_classification_tag(self, confidence):
        if confidence < 0.60:
            self.confidence_badge_text = "Advance"
            self.confidence_badge_color = "#FFB4A8"   # rgba(255, 180, 168, 1)
        elif confidence < 0.85:
            self.confidence_badge_text = "Early"
            self.confidence_badge_color = "#FFF695"   # rgba(255, 246, 149, 1)
        else:
            self.confidence_badge_text = "Healthy"
            self.confidence_badge_color = "#C9FF8E"   # rgba(201, 255, 142, 1)
