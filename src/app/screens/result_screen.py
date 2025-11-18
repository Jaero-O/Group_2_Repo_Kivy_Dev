from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, NumericProperty
from kivy.clock import mainthread
from kivy.clock import Clock

class ResultScreen(Screen):
    """
    Displays the analysis results of a scanned image.
    """
    image_path = StringProperty('')
    disease_name = StringProperty('Unknown')
    severity_name = StringProperty('N/A')
    severity_percentage_str = StringProperty('0.0%')
    confidence_score_str = StringProperty('0%')
    scan_timestamp = StringProperty('')

    disease_description = StringProperty('')
    disease_symptoms = StringProperty('')
    disease_prevention = StringProperty('')
    severity_description = StringProperty('')
    disease_description = StringProperty('No description available.')
    disease_symptoms = StringProperty('No symptoms listed.')

    _disease_id = None
    _severity_level_id = None
    _severity_percentage_float = 0.0
    
    # To track where the user came from
    _source_screen = 'scan'

    def on_enter(self, *args):
        """
        Called when the screen is entered. Populates the screen with
        the analysis result from the app instance.
        """
        self._clear_details() # Clear previous details
        app = App.get_running_app()
        result = getattr(app, 'analysis_result', {})

        if not result:
            print("Warning: ResultScreen entered without analysis_result. Returning to home.")
            self.manager.current = 'home'
            return

        record_id = result.get('record_id')

        if record_id is not None:
            # --- Case A: Loading a saved record from the database ---
            self._source_screen = 'records'
            app.db_manager.get_record_by_id_async(
                record_id,
                on_success_callback=self._populate_from_db_record,
                on_error_callback=self._on_db_load_error
            )
        else:
            # --- Case B: Displaying a new scan result ---
            self._source_screen = 'scan'
            self._populate_from_new_scan(result)

    def _populate_from_db_record(self, record: dict):
        """Populate the screen using data fetched from the database."""
        # 1. Populate UI fields
        self.image_path = record.get("image_path", "app/assets/placeholder_gallery.png")
        self.disease_name = record.get("disease_name", "Unknown")
        self.severity_name = record.get("severity_name", "N/A")
        self._severity_percentage_float = record.get("severity_percentage", 0.0)
        self.severity_percentage_str = f"{self._severity_percentage_float:.1f}%"
        self.scan_timestamp = str(record.get("scan_timestamp", ''))

        # 2. Hide new-scan-only widgets
        confidence_layout = self.ids.get('confidence_layout')
        if confidence_layout:
            confidence_layout.opacity = 0
        save_button = self.ids.get('save_button')
        if save_button:
            save_button.opacity = 0
            save_button.disabled = True

        # 3. Fetch detailed descriptions
        self._fetch_and_populate_details()

    def _populate_from_new_scan(self, result: dict):
        """Populate the screen using data from a new analysis result."""
        # --- 1. Populate UI fields from the result dictionary ---
        self.image_path = result.get("image_path", "app/assets/placeholder_gallery.png")
        self.disease_name = result.get("disease_name", "Unknown")
        self.severity_name = result.get("severity_name", "N/A")
        self._severity_percentage_float = result.get("severity_percentage", 0.0)
        self.severity_percentage_str = f"{self._severity_percentage_float:.1f}%"
        self.scan_timestamp = str(result.get("scan_timestamp", ''))

        # --- 2. Show new-scan-only widgets ---
        confidence = result.get("confidence", 0.0)
        self.confidence_score_str = f"{confidence * 100:.0f}%"
        confidence_layout = self.ids.get('confidence_layout')
        if confidence_layout:
            confidence_layout.opacity = 1

        # --- 3. Conditionally enable saving ---
        is_saveable = self.disease_name != 'Unknown'
        save_button = self.ids.get('save_button')
        if save_button:
            save_button.opacity = 1 if is_saveable else 0
            save_button.disabled = not is_saveable

        # --- 4. Prepare data for saving (if applicable) & fetch details ---
        # Don't pre-fetch lookup IDs here; leave that to the explicit save action.
        # Calling DB lookup IDs on screen entry can cause unwanted side effects
        # during tests and should only run when the user initiates a save.

        self._fetch_and_populate_details()

    @mainthread
    def _on_db_load_error(self, error_message):
        """Handle errors when fetching a record from the DB."""
        print(f"Error loading record: {error_message}. Returning to previous screen.")
        self.go_back()
    def _fetch_and_populate_details(self):
        """Fetches and populates the detailed description fields from the database."""
        details = App.get_running_app().db_manager.get_disease_and_severity_details(
            disease_name=self.disease_name,
            severity_name=self.severity_name if self.severity_name != 'N/A' else None
        )
        self.disease_description = details.get('disease_description', 'No description available.')
        self.disease_symptoms = details.get('disease_symptoms', 'No symptoms listed.')
        self.disease_prevention = details.get('disease_prevention', 'No prevention tips available.')
        self.severity_description = details.get('severity_description', 'No severity description available.')

    def _clear_details(self):
        """Resets the detail properties to empty strings."""
        self.disease_description = self.disease_symptoms = self.disease_prevention = self.severity_description = ''

    def _prepare_for_save(self):
        """Fetch necessary IDs from the database to be ready for saving."""
        # Use the screen's properties, which have defaults, instead of the raw result dict.
        print(f"Preparing to save. Disease: '{self.disease_name}', Severity Level: '{self.severity_name}'")

        # Fetch the corresponding IDs from the database
        # This assumes a method 'get_lookup_ids' exists in your db_manager
        # Perform a synchronous lookup of IDs when explicitly preparing for save.
        self._disease_id, self._severity_level_id = App.get_running_app().db_manager.get_lookup_ids(
            disease_name=self.disease_name,
            severity_name=self.severity_name
        )

        if self._disease_id is None or self._severity_level_id is None:
            print(f"Warning: Could not find DB IDs for '{self.disease_name}' or '{self.severity_name}'. Save will be disabled.")

    def _get_severity_name_from_percentage(self, percentage: float) -> str:
        """Determines the severity name based on the percentage."""
        if percentage < 10.0:
            return "Early Stage"
        elif percentage >= 10.0:
            return "Advanced Stage"
        else:
            return "Healthy" # Fallback for 0% or less

    def go_back(self):
        """Navigates back to the scan screen."""
        if self._source_screen == 'records': # This means we came from the image grid
            self.manager.current = 'image_selection'
        else:
            self.manager.current = 'scan'
    def on_leave(self, *args):
        """Clear the result when leaving the screen to prevent stale data."""
        App.get_running_app().analysis_result = {}