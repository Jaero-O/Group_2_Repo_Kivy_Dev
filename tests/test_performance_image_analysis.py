import unittest, os, sys, time

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.app.core.image_processor import analyze_image

SAMPLE_IMAGE = os.path.join(project_root, 'data', 'leaf_features_complete.csv')  # not an image; will trigger fallback quickly
MAX_SECONDS = 0.75  # generous threshold for fallback path

class TestPerformanceImageAnalysis(unittest.TestCase):
    def test_analyze_image_performance(self):
        start = time.perf_counter()
        _ = analyze_image(SAMPLE_IMAGE)
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, MAX_SECONDS, f"analyze_image took {elapsed:.3f}s > {MAX_SECONDS}s")

if __name__ == '__main__':
    unittest.main()
