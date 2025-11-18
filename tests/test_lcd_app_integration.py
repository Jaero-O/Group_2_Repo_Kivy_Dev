import os
import sys
import unittest
from pprint import pprint

# Add project and src directories to path to allow for absolute imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Add the 'src' directory to the path to ensure we import the correct modules
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.app.core.image_processor import analyze_image

class TestLcdAppIntegration(unittest.TestCase):

    def test_lcd_app_image_analysis_pipeline(self):
        """
        Tests the full image analysis pipeline for the kivy-lcd-app.
        This ensures that the lcd-app's image_processor correctly integrates
        with the main application's ML model.
        """
        # NOTE: This path is relative to the project root where tests are run.
        sample_image_path = "ml/leaf-detection/scripts/20211231_123305 (Custom).jpg"
        
        print(f"\n--- Testing LCD App Integration with: {sample_image_path} ---")
        
        self.assertTrue(os.path.exists(sample_image_path), f"Error: Sample image not found at {sample_image_path}")

        # Run the analysis using the lcd-app's image processor
        result = analyze_image(sample_image_path)

        print("\n--- LCD App Analysis Result ---")
        pprint(result)
        print("-----------------------------\n")

        # Basic assertions to verify the result structure
        self.assertIn("disease_name", result)
        self.assertIn("confidence", result)
        self.assertIn("severity_percentage", result)
        self.assertIn("severity_name", result)
        print("LCD App integration test completed successfully.")