import unittest, os, sys
from kivy.lang import Builder

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

KV_DIR = os.path.join(src_path, 'app', 'kv')

class TestKvSmoke(unittest.TestCase):
    def test_all_kv_files_load(self):
        self.assertTrue(os.path.isdir(KV_DIR), f"KV directory missing: {KV_DIR}")
        kv_files = [f for f in os.listdir(KV_DIR) if f.endswith('.kv')]
        self.assertGreater(len(kv_files), 0, "No KV files discovered")
        for name in kv_files:
            with self.subTest(kv=name):
                path = os.path.join(KV_DIR, name)
                # Load without raising; repeated loads are acceptable.
                Builder.load_file(path)

if __name__ == '__main__':
    unittest.main()
