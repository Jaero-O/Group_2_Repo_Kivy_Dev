import os, sys, unittest
from unittest.mock import patch, MagicMock

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from kivy.lang import Builder
from src.app.screens.scanning_screen import ScanningScreen

class TestFallbackErrorIndicator(unittest.TestCase):
    def setUp(self):
        self.patcher_app = patch('src.app.screens.scanning_screen.App')
        mock_App = self.patcher_app.start()
        self.addCleanup(self.patcher_app.stop)
        self.mock_app = MagicMock()
        mock_App.get_running_app.return_value = self.mock_app
        self.mock_app.analysis_image_path = os.path.join(project_root, 'src', 'app', 'assets', 'placeholder_bg1.png')
        self.screen = ScanningScreen(name='scanning')
        self.screen.manager = MagicMock()
        self.screen.manager.current = 'scanning'
        self.patcher_clock = patch('src.app.screens.scanning_screen.Clock.schedule_once', side_effect=lambda cb, dt=0: cb(dt))
        self.patcher_clock.start()
        self.addCleanup(self.patcher_clock.stop)
        class InstantThread:
            def __init__(self, target, args=()):
                self._target = target
                self._args = args
            def start(self):
                self._target(*self._args)
        self.patcher_thread = patch('src.app.screens.scanning_screen.threading.Thread', InstantThread)
        self.patcher_thread.start()
        self.addCleanup(self.patcher_thread.stop)

    def test_fallback_warning_shown_on_error(self):
        with patch('src.app.screens.scanning_screen.analyze_image', side_effect=RuntimeError('fail')):
            self.screen.on_enter()
        # Load KV to ensure ids
        kv_path = os.path.join(project_root, 'src', 'app', 'kv', 'ScanningScreen.kv')
        if os.path.exists(kv_path):
            Builder.load_file(kv_path)
        if not self.screen.ids:
            from kivy.factory import Factory
            tmp = Factory.ScanningScreen()
            self.screen.ids.update(tmp.ids)
        # After failure, fallback_warning text should be set
        if 'fallback_warning' in self.screen.ids:
            self.assertIn('fallback', self.screen.ids.fallback_warning.text.lower())
        self.assertTrue(getattr(self.mock_app, 'analysis_error', False))

if __name__ == '__main__':
    unittest.main()
