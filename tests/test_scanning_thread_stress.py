import unittest, os, sys, time
from unittest.mock import patch, MagicMock

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.app.screens.scanning_screen import ScanningScreen

class TestScanningThreadStress(unittest.TestCase):
    def setUp(self):
        # Patch App
        self.patcher_app = patch('src.app.screens.scanning_screen.App')
        mock_App = self.patcher_app.start()
        self.addCleanup(self.patcher_app.stop)
        self.mock_app = MagicMock()
        mock_App.get_running_app.return_value = self.mock_app

        # Provide initial image path
        self.mock_app.analysis_image_path = 'dummy.jpg'

        # Instantiate screen
        self.screen = ScanningScreen(name='scanning')
        self.screen.manager = MagicMock()
        self.screen.manager.current = 'scanning'

        # Patch Clock.schedule_once to run immediately
        self.patcher_clock = patch('src.app.screens.scanning_screen.Clock.schedule_once', side_effect=lambda cb, dt=0: cb(dt))
        self.patcher_clock.start()
        self.addCleanup(self.patcher_clock.stop)

        # Replace threading.Thread so .start() runs target immediately
        self.orig_thread = None
        class InstantThread:
            def __init__(self, target, args=()):
                self._target = target
                self._args = args
            def start(self):
                self._target(*self._args)
        self.patcher_thread = patch('src.app.screens.scanning_screen.threading.Thread', InstantThread)
        self.patcher_thread.start()
        self.addCleanup(self.patcher_thread.stop)

    def test_multiple_rapid_scans(self):
        results = []
        def fake_analyze(path):
            return {
                'disease_name': f'Disease_{path}',
                'confidence': 0.9,
                'severity_percentage': 12.3,
                'severity_name': 'Stage',
            }
        with patch('src.app.screens.scanning_screen.analyze_image', side_effect=fake_analyze):
            for i in range(5):
                img = f'image_{i}.jpg'
                self.mock_app.analysis_image_path = img
                self.screen.on_enter()
                results.append(self.mock_app.analysis_result)
        # Ensure each result has required keys and unique disease_name
        seen = set()
        for r in results:
            for key in ['disease_name','confidence','severity_percentage','severity_name','image_path']:
                self.assertIn(key, r, f'Missing key {key} in result {r}')
            seen.add(r['disease_name'])
        self.assertEqual(len(seen), 5, 'Disease names not unique across rapid scans')

if __name__ == '__main__':
    unittest.main()
