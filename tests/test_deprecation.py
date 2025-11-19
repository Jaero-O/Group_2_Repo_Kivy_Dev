import os, sys, unittest
from unittest.mock import patch, MagicMock

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from kivy.app import App
from kivy.uix.screenmanager import Screen

class DummyApp(App):
    pass

class TestCaptureResultDeprecation(unittest.TestCase):
    def setUp(self):
        # Provide a dummy app context
        self.app = DummyApp()
        self.app.build = lambda: Screen()
        self.app.run = lambda: None
        App.get_running_app = lambda: self.app

    def test_capture_result_not_registered(self):
         if os.environ.get('HEADLESS_TEST') == '1':
             self.skipTest('HEADLESS_TEST set; skipping heavy Kivy build in deprecation test.')
         # Build minimal screen manager via main app build path
         from main import MangofyApp
         mapp = MangofyApp()
         root = mapp.build()
         # Ensure deprecated screen name is absent
         self.assertNotIn('capture_result', root.screen_names)

if __name__ == '__main__':
    unittest.main()
