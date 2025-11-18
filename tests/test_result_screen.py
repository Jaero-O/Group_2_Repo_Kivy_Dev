import unittest
import os
import sys
from unittest.mock import MagicMock, patch

# Add project and src directories to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.app.screens.result_screen import ResultScreen

class TestResultScreen(unittest.TestCase):

    def setUp(self):
        """Set up a clean ResultScreen instance before each test."""
        self.patcher_app = patch('src.app.screens.result_screen.App')
        mock_App = self.patcher_app.start()
        self.addCleanup(self.patcher_app.stop)

        self.mock_app = MagicMock()
        # The app now holds the db_manager, so we mock it here.
        self.mock_app.db_manager = MagicMock()
        mock_App.get_running_app.return_value = self.mock_app

        self.screen = ResultScreen(name='result')
        self.screen.manager = MagicMock()
        self.screen.ids = {
            'confidence_layout': MagicMock(),
            'save_button': MagicMock()
        }

    def test_populate_from_new_scan(self):
        """Test populating the screen with a new, unsaved analysis result."""
        # --- Setup ---
        self.mock_app.analysis_result = {
            'image_path': '/path/new_scan.jpg',
            'disease_name': 'Anthracnose',
            'severity_name': 'Advanced Stage',
            'severity_percentage': 25.5,
            'confidence': 0.98,
            'scan_timestamp': '2025-01-01 12:00:00'
        }
        # Mock the return value for the details lookup
        self.mock_app.db_manager.get_disease_and_severity_details.return_value = {
            'disease_description': 'A fungal disease.'
        }
        # --- SOLUTION: Improve mock precision ---
        # This method is only called when saving, not when viewing a new scan.
        # Mocking it to raise an exception ensures the test fails if it's called incorrectly.
        self.mock_app.db_manager.get_lookup_ids.side_effect = ValueError("get_lookup_ids should not be called in this test")

        # --- Action ---
        self.screen.on_enter()

        # --- Assertions ---
        self.assertEqual(self.screen.image_path, '/path/new_scan.jpg')
        self.assertEqual(self.screen.disease_name, 'Anthracnose')
        self.assertEqual(self.screen.severity_percentage_str, '25.5%')
        self.assertEqual(self.screen.confidence_score_str, '98%')
        self.assertEqual(self.screen.disease_description, 'A fungal disease.')
        # Verify that UI elements for a new scan are visible
        self.assertEqual(self.screen.ids.confidence_layout.opacity, 1)
        self.assertEqual(self.screen.ids.save_button.opacity, 1)
        self.assertFalse(self.screen.ids.save_button.disabled)

    def test_populate_from_db_record(self):
        """Test populating the screen with a saved record from the database."""
        # --- Setup ---
        # The app is given a record_id to load
        self.mock_app.analysis_result = {'record_id': 123}

        # --- Action ---
        self.screen.on_enter()

        # --- Assertions ---
        # 1. Verify that the screen requested the record from the DB
        self.mock_app.db_manager.get_record_by_id_async.assert_called_once_with(
            123,
            on_success_callback=self.screen._populate_from_db_record,
            on_error_callback=self.screen._on_db_load_error
        )

        # 2. Simulate the DB callback and verify the screen updates
        db_record = {
            'image_path': '/path/saved_scan.jpg',
            'disease_name': 'Healthy',
            'severity_name': 'Healthy',
            'severity_percentage': 0.0,
            'scan_timestamp': '2025-01-02 13:00:00'
        }
        self.mock_app.db_manager.get_disease_and_severity_details.return_value = {}
        
        # Manually call the callback with the simulated data
        self.screen._populate_from_db_record(db_record)

        self.assertEqual(self.screen.image_path, '/path/saved_scan.jpg')
        self.assertEqual(self.screen.disease_name, 'Healthy')
        # Verify that UI elements for a saved scan are hidden
        self.assertEqual(self.screen.ids.confidence_layout.opacity, 0)
        self.assertEqual(self.screen.ids.save_button.opacity, 0)
        self.assertTrue(self.screen.ids.save_button.disabled)

    def test_go_back_navigation(self):
        """Test that the go_back method navigates to the correct previous screen."""
        # Case 1: Came from a new scan
        self.screen._source_screen = 'scan'
        self.screen.go_back()
        self.assertEqual(self.screen.manager.current, 'scan')

        # Case 2: Came from viewing a saved record
        self.screen._source_screen = 'records'
        self.screen.go_back()
        self.assertEqual(self.screen.manager.current, 'image_selection')