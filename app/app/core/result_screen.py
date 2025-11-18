# app/screens/result_screen.py
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, NumericProperty

class ResultScreen(Screen):
    """
    Displays the results of the mango analysis, including the disease,
    confidence, severity, and the analyzed image.
    """
    image_path = StringProperty('')
    disease_name = StringProperty('N/A')
    confidence_score = StringProperty('0%')
    severity_percentage = StringProperty('0.0%')

    def on_enter(self, *args):
        """
        When the screen is entered, populate the UI with the analysis results.
        """
        app = App.get_running_app()
        result = getattr(app, 'analysis_result', None)

        if result:
            self.image_path = result.get("image_path", "")
            self.disease_name = result.get("disease_name", "Unknown")
            
            confidence = result.get("confidence", 0) * 100
            self.confidence_score = f"{confidence:.0f}%"
            
            severity = result.get("severity_percentage", 0)
            self.severity_percentage = f"{severity:.1f}%"
        else:
            print("Error: No analysis result found. Returning to home.")
            self.manager.current = 'home'