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

from src.app.screens.scanning_screen import ScanningScreen

class TestScanningScreen(unittest.TestCase):

    def setUp(self):
        """Set up a clean ScanningScreen instance before each test."""
        self.patcher_app = patch('src.app.screens.scanning_screen.App')
        self.patcher_thread = patch('src.app.screens.scanning_screen.threading.Thread')

        mock_App = self.patcher_app.start()
        self.mock_Thread = self.patcher_thread.start()

        self.addCleanup(self.patcher_app.stop)
        self.addCleanup(self.patcher_thread.stop)

        self.mock_app = MagicMock()
        mock_App.get_running_app.return_value = self.mock_app

        self.screen = ScanningScreen(name='scanning')
        self.screen.manager = MagicMock()

    def test_on_enter_starts_analysis_thread(self):
        """Test that a background thread is started when an image path is present."""
        # --- Setup ---
        self.mock_app.analysis_image_path = '/path/to/image.jpg'

        # --- Action ---
        self.screen.on_enter()

        # --- Assertions ---
        # Verify that a Thread was created and started
        self.mock_Thread.assert_called_once_with(
            target=self.screen._perform_analysis,
            args=('/path/to/image.jpg',)
        )
        self.mock_Thread.return_value.start.assert_called_once()

    def test_on_enter_no_image_path(self):
        """Test that it navigates back if no image path is found."""
        # --- Setup ---
        self.mock_app.analysis_image_path = None

        # --- Action ---
        self.screen.on_enter()

        # --- Assertions ---
        # Verify that no thread was started
        self.mock_Thread.assert_not_called()
        # Verify that it navigated back to the home screen
        self.assertEqual(self.screen.manager.current, 'home')