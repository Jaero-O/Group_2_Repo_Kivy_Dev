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

from src.app.screens.welcome_screen import WelcomeScreen
from src.app.screens.scan_screen import ScanScreen
from src.app.screens.capture_result_screen import CaptureResultScreen
from src.app.screens.image_source_screen import ImageSourceScreen
from main import MangofyApp

class MockApp:
    """A simple, test-aware mock for MangofyApp that correctly handles attribute assignment."""
    def __init__(self):
        self.analysis_image_path = None
        self.last_screen = None
        self.analysis_result = None

class TestWelcomeScreen(unittest.TestCase):
    def setUp(self):
        self.screen = WelcomeScreen()
        self.screen.manager = MagicMock()
        # Mock the ids dictionary that Kivy would populate from the .kv file
        self.screen.ids = {'tap_label': MagicMock()}

    def test_on_touch_down_navigates_to_home(self):
        """Test that tapping the welcome screen navigates to the home screen."""
        self.screen.on_touch_down(MagicMock())  # Pass a dummy touch object
        self.assertEqual(self.screen.manager.current, 'home')


class TestScanScreen(unittest.TestCase):
    def setUp(self):
        # Patch App where it is used, inside the scan_screen module.
        patcher = patch('src.app.screens.scan_screen.App')
        mock_App = patcher.start()
        self.addCleanup(patcher.stop)

        self.mock_app = MockApp()
        mock_App.get_running_app.return_value = self.mock_app

        self.screen = ScanScreen()
        self.screen.manager = MagicMock()

    def test_select_image_sets_app_state_and_navigates(self):
        """Test that selecting an image triggers the analysis process."""
        test_image_path = '/path/to/selected_image.jpg'

        self.screen.select_image(test_image_path)

        # Verify that the image path was stored on the app instance
        self.assertEqual(self.mock_app.analysis_image_path, test_image_path)
        # Verify that the screen manager navigated to the 'scanning' screen
        self.assertEqual(self.screen.manager.current, 'scanning')

    def test_select_image_with_no_path_does_nothing(self):
        """Test that calling select_image with no path does not navigate."""
        # Set a pre-existing value to ensure it's not changed
        self.mock_app.analysis_image_path = 'old_path'
        self.screen.manager.current = 'scan' # Start at the current screen

        self.screen.select_image('') # Call with an empty path

        # Verify that the app state and screen have not changed
        self.assertEqual(self.mock_app.analysis_image_path, 'old_path')
        self.assertEqual(self.screen.manager.current, 'scan')


class TestCaptureResultScreen(unittest.TestCase):
    def setUp(self):
        # Patch App where it is used, inside the capture_result_screen module.
        patcher = patch('src.app.screens.capture_result_screen.App')
        mock_App = patcher.start()
        self.addCleanup(patcher.stop)

        self.mock_app = MockApp()
        mock_App.get_running_app.return_value = self.mock_app

        self.screen = CaptureResultScreen()
        self.screen.manager = MagicMock()

    def test_open_result_sets_context_and_navigates(self):
        """Test that open_result correctly sets context and navigates."""
        self.screen.open_result()

        # Verify that the app's last_screen property was set for navigation context
        self.assertEqual(self.mock_app.last_screen, 'capture_result')
        # Verify navigation to the result screen
        self.assertEqual(self.screen.manager.current, 'result')


class TestImageSourceScreen(unittest.TestCase):
    def setUp(self):
        self.screen = ImageSourceScreen()
        self.screen.manager = MagicMock()

    def test_on_take_photo_navigates_to_live_camera(self):
        """Test that 'Take Photo' navigates to the live camera screen."""
        self.screen.on_take_photo()
        self.assertEqual(self.screen.manager.current, 'scan_live_camera')


if __name__ == '__main__':
    unittest.main()