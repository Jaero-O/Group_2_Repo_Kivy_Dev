import unittest
import os
import sys
from unittest.mock import MagicMock, patch, ANY, PropertyMock, call
import io

from importlib import reload
# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Define all mocks in a single place. Note that we patch the targets where they are *used* (in main.py).
@patch('main.setup_window')
@patch('main.database.DatabaseManager', autospec=True)
@patch('main.os')
@patch('main.ScreenManager', autospec=True)
@patch('main.FadeTransition', autospec=True)
@patch('main.Builder', autospec=True)
@patch('main.Window', autospec=True)
@patch('main.Clock', autospec=True)
class TestMangofyApp(unittest.TestCase):

    # Mocks are passed as arguments by the decorators, in reverse order
    def setUp(self):
        """Set up for each test with fresh mocks."""
        # This method is called by the test runner before each test.
        # The mocks from the class decorator are passed to the test methods, not here.
        # We will set them as instance attributes inside each test.
        pass
    
    def _setup_mocks(self, mock_Clock, mock_Window, mock_Builder, mock_FadeTransition,
                     mock_ScreenManager, mock_os, mock_DatabaseManager, mock_setup_window):
        """A helper to assign all mocks to self, called from each test."""
        self.mock_Clock, self.mock_Window, self.mock_Builder, self.mock_FadeTransition, \
        self.mock_ScreenManager, self.mock_os, self.mock_DatabaseManager, self.mock_setup_window = \
            mock_Clock, mock_Window, mock_Builder, mock_FadeTransition, mock_ScreenManager, \
            mock_os, mock_DatabaseManager, mock_setup_window
        # Reload the main module to apply patches for each test
        import main
        reload(main)
        self.main_app_module = main

        self.user_data_dir = '/mock/user/data/dir'
        # The runtime DB location is project-root/mangofy.db
        self.db_path = os.path.join(project_root, "mangofy.db")
        self.log_path = os.path.join(self.user_data_dir, "app.log")

        # --- SOLUTION: Configure os mock to return valid paths ---
        # This prevents the FileNotFoundError during logging setup.
        self.mock_os.path.join.side_effect = os.path.join
        # Ensure abspath resolves to the real project root for tests so
        # main.py computes the expected project-root DB path.
        self.mock_os.path.abspath.side_effect = os.path.abspath
        self.mock_os.path.dirname.side_effect = os.path.dirname
        self.mock_os.path.exists.return_value = True
        self.mock_os.path.isdir.return_value = True
        self.mock_os.listdir.return_value = []

        # --- SOLUTION: Patch the property on the CLASS, not the instance ---
        # The user_data_dir is a read-only property on the App class.
        self.patcher = patch.object(self.main_app_module.MangofyApp, 'user_data_dir', new_callable=PropertyMock, return_value=self.user_data_dir)
        self.mock_user_data_dir = self.patcher.start()
        self.addCleanup(self.patcher.stop)

        # Mock the app instance that will be created
        self.app = self.main_app_module.MangofyApp()


    def _run_startup_sequence(self):
        """Helper to run build() and the scheduled finish_loading() method."""
        self.app.build()
        # The app schedules finish_loading. We find that scheduled function and call it.
        call_args = self.mock_Clock.schedule_once.call_args
        self.assertIsNotNone(call_args, "Clock.schedule_once was not called in build()")
        finish_loading_func = call_args[0][0]
        finish_loading_func(0) # The argument is 'dt' (delta-time)

    def test_build_method_db_failure(self, mock_Clock, mock_Window, mock_Builder, mock_FadeTransition,
                                     mock_ScreenManager, mock_os, mock_DatabaseManager, mock_setup_window):
        """Test that build returns None if database initialization fails."""
        self._setup_mocks(mock_Clock, mock_Window, mock_Builder, mock_FadeTransition, mock_ScreenManager, mock_os, mock_DatabaseManager, mock_setup_window)
        self.mock_DatabaseManager.return_value.initialize_database.side_effect = Exception("DB connection failed")

        # Mock the app's stop method to verify it's called
        with patch.object(self.app, 'stop', autospec=True) as mock_stop:
            self._run_startup_sequence()
            # In the new structure, the exception in finish_loading calls stop.
            self.app.stop.assert_called_once()

    def test_build_method_success(self, mock_Clock, mock_Window, mock_Builder, mock_FadeTransition, mock_ScreenManager, mock_os, mock_DatabaseManager, mock_setup_window):
        """Test that the build method executes its setup sequence correctly."""
        self._setup_mocks(mock_Clock, mock_Window, mock_Builder, mock_FadeTransition, mock_ScreenManager, mock_os, mock_DatabaseManager, mock_setup_window)
        self._run_startup_sequence()

        # Assertions for build()
        self.mock_ScreenManager.assert_called_once_with(transition=self.mock_FadeTransition.return_value)
        self.mock_Clock.schedule_once.assert_called_once()

        # Assertions for finish_loading()
        self.mock_setup_window.assert_called_once()
        self.mock_DatabaseManager.assert_called_once_with(db_path=self.db_path)
        self.mock_DatabaseManager.return_value.initialize_database.assert_called_once()

    def test_kv_file_loading(self, mock_Clock, mock_Window, mock_Builder, mock_FadeTransition, mock_ScreenManager, mock_os, mock_DatabaseManager, mock_setup_window):
        """Test that KV files are loaded dynamically."""
        self._setup_mocks(mock_Clock, mock_Window, mock_Builder, mock_FadeTransition, mock_ScreenManager, mock_os, mock_DatabaseManager, mock_setup_window)
        kv_dir = os.path.join(project_root, 'src', 'app', 'kv')
        self.mock_os.listdir.return_value = ['test1.kv', 'test2.kv', 'not-a-kv.txt']

        self._run_startup_sequence()

        self.mock_os.path.isdir.assert_called_with(kv_dir)
        self.mock_os.listdir.assert_called_with(kv_dir)
        self.assertEqual(self.mock_Builder.load_file.call_count, 2)
        self.mock_Builder.load_file.assert_any_call(os.path.join(kv_dir, 'test1.kv'))
        self.mock_Builder.load_file.assert_any_call(os.path.join(kv_dir, 'test2.kv'))

    def test_screen_registration(self, mock_Clock, mock_Window, mock_Builder, mock_FadeTransition, mock_ScreenManager, mock_os, mock_DatabaseManager, mock_setup_window):
        """Test that all expected screens are added to the ScreenManager."""
        self._setup_mocks(mock_Clock, mock_Window, mock_Builder, mock_FadeTransition, mock_ScreenManager, mock_os, mock_DatabaseManager, mock_setup_window)
        self._run_startup_sequence()

        sm_instance = self.mock_ScreenManager.return_value
        # The loading screen is added in build(), the rest in finish_loading()
        # CaptureResultScreen deprecated; adjust expected count (LoadingScreen + 14 others)
        expected_screen_count = 1 + 14
        self.assertEqual(sm_instance.add_widget.call_count, expected_screen_count)

        # Check that a specific screen was added
        # The call is sm.add_widget(WelcomeScreen(name='welcome')). We check the type.
        from app.screens import WelcomeScreen
        found_welcome = any(
            isinstance(call_args[0][0], WelcomeScreen) for call_args in sm_instance.add_widget.call_args_list
        )
        self.assertTrue(found_welcome, "WelcomeScreen was not added to the ScreenManager")

    def test_initial_screen_set(self, mock_Clock, mock_Window, mock_Builder, mock_FadeTransition, mock_ScreenManager, mock_os, mock_DatabaseManager, mock_setup_window):
        """Test that the initial screen is set to 'welcome'."""
        self._setup_mocks(mock_Clock, mock_Window, mock_Builder, mock_FadeTransition, mock_ScreenManager, mock_os, mock_DatabaseManager, mock_setup_window)
        self._run_startup_sequence()

        sm_instance = self.mock_ScreenManager.return_value
        # The 'current' property is set via a special setter method in Kivy
        self.assertEqual(sm_instance.current, 'welcome')

    def test_window_scaling(self, mock_Clock, mock_Window, mock_Builder, mock_FadeTransition, mock_ScreenManager, mock_os, mock_DatabaseManager, mock_setup_window):
        """Test that window scaling is bound and updated."""
        self._setup_mocks(mock_Clock, mock_Window, mock_Builder, mock_FadeTransition, mock_ScreenManager, mock_os, mock_DatabaseManager, mock_setup_window)
        self.mock_Window.width = 1000
        self.mock_Window.height = 800

        self._run_startup_sequence()

        # Check that bind was called correctly in finish_loading
        self.mock_Window.bind.assert_called_once_with(on_resize=self.app._update_scaling)

        # To test the _update_scaling logic, we patch the constants it uses
        with patch('main.BASE_WIDTH', 100), patch('main.BASE_HEIGHT', 200):
            self.app._update_scaling(self.mock_Window, 50, 100)
            self.assertEqual(self.app.scale_x, 0.5)
            self.assertEqual(self.app.scale_y, 0.5)
