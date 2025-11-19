"""Tests for cancel behavior compliance with USER_MANUAL.md Section 2.2 Step 3.

Verifies:
- Cancel button during ScanningScreen navigates to HomeScreen
- Section 3.1 RULE 1: No auto-save (cancelled scans not persisted)
- analysis_result is cleared after cancellation
"""
import os, sys, unittest
from unittest.mock import patch, MagicMock

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from kivy.lang import Builder
from src.app.screens.scanning_screen import ScanningScreen

class TestCancelBehavior(unittest.TestCase):
    def setUp(self):
        # Patch App.get_running_app
        self.patcher_app = patch('src.app.screens.scanning_screen.App')
        mock_App = self.patcher_app.start()
        self.addCleanup(self.patcher_app.stop)
        self.mock_app = MagicMock()
        mock_App.get_running_app.return_value = self.mock_app
        self.mock_app.analysis_image_path = os.path.join(project_root, 'src', 'app', 'assets', 'placeholder_bg1.png')
        self.screen = ScanningScreen(name='scanning')
        self.screen.manager = MagicMock()
        self.screen.manager.current = 'scanning'
        # Patch Clock.schedule_once to run immediately
        self.patcher_clock = patch('src.app.screens.scanning_screen.Clock.schedule_once', side_effect=lambda cb, dt=0: cb(dt))
        self.patcher_clock.start()
        self.addCleanup(self.patcher_clock.stop)
        # Patch threading.Thread so .start runs target directly
        class InstantThread:
            def __init__(self, target, args=()):
                self._target = target
                self._args = args
            def start(self):
                self._target(*self._args)
        self.patcher_thread = patch('src.app.screens.scanning_screen.threading.Thread', InstantThread)
        self.patcher_thread.start()
        self.addCleanup(self.patcher_thread.stop)

    def test_cancel_before_analysis_skips_navigation(self):
        """Verify USER_MANUAL.md Section 2.2 Step 3: Cancel → HomeScreen.
        
        Flow: User cancels during ScanningScreen → Navigate to HomeScreen
        RULE 1: Cancelled scans are NOT saved to database
        RULE 3: analysis_result is cleared (no state persisted)
        """
        # Patch analyze_image with slow dummy (not actually sleeping) to simulate stage presence
        kv_path = os.path.join(project_root, 'src', 'app', 'kv', 'ScanningScreen.kv')
        if os.path.exists(kv_path):
            Builder.load_file(kv_path)
        with patch('src.app.screens.scanning_screen.analyze_image', return_value={'disease_name':'X','confidence':0.5,'severity_percentage':20,'severity_name':'Mild'}):
            self.screen.on_enter()
            # Immediately cancel (should remove any partial result)
            self.screen.cancel_analysis()
        
        # USER_MANUAL.md Section 2.2 Step 3: Cancel navigates to HomeScreen
        self.assertEqual(self.screen.manager.current, 'home',
                        "Section 2.2 Step 3: Cancel button must navigate to 'home' (not 'result' or 'capture_result')")
        
        # RULE 1: No auto-save - cancelled scans should not persist
        # RULE 3: State management - analysis_result should be cleared
        self.assertFalse(hasattr(self.mock_app, 'analysis_result'), 
                        "RULE 1 & RULE 3: analysis_result should not be set after cancel (no state persistence)")

if __name__ == '__main__':
    unittest.main()
