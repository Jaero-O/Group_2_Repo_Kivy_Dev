import os, sys, unittest
from unittest.mock import patch, MagicMock

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.app.core.camera import capture_multi_frame_stitched

try:
    import cv2
    import numpy as np
except Exception:
    cv2 = None
    np = None

class TestMultiFrameCapture(unittest.TestCase):
    def setUp(self):
        if cv2 is None or np is None:
            self.skipTest('OpenCV/NumPy not available for stitching test')
        self.capture_dir = os.path.join(project_root, 'data', 'captures')
        os.makedirs(self.capture_dir, exist_ok=True)
        # Create synthetic frames
        self.frames = []
        for i in range(4):
            img = np.full((120, 160, 3), 30 + i*50, dtype='uint8')  # increasing brightness
            path = os.path.join(self.capture_dir, f'synthetic_frame{i}.jpg')
            cv2.imwrite(path, img)
            self.frames.append(path)

    def test_capture_multi_frame_stitched_uses_all_frames(self):
        # Patch single capture call to sequentially return synthetic frames
        def side_effect(path):
            # path provided includes suffix _frameX; choose index from current length captured
            idx = len([f for f in os.listdir(self.capture_dir) if f.startswith('capture_multi_frame')])
            # We cycle across prepared frames
            src = self.frames[idx % len(self.frames)]
            # copy src to path
            import shutil
            shutil.copy(src, path)
            return path
        with patch('src.app.core.camera.capture_image_raspicam', side_effect=side_effect):
            stitched = capture_multi_frame_stitched(os.path.join(self.capture_dir, 'capture_multi'), count=4)
            self.assertTrue(os.path.exists(stitched), 'Stitched output not created')
            img = cv2.imread(stitched)
            self.assertIsNotNone(img, 'Failed to load stitched image')
            # Expect width > single frame width
            self.assertGreater(img.shape[1], 160, 'Stitched image width not greater than single frame width')

if __name__ == '__main__':
    unittest.main()
