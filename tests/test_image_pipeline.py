import os, sys, unittest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import pipeline utilities
from src.app.core.image_pipeline import normalize_exposure, resize_for_lcd, stitch_frames, process_for_analysis

try:
    import cv2
    import numpy as np
except Exception:
    cv2 = None
    np = None

class TestImagePipeline(unittest.TestCase):
    def setUp(self):
        if cv2 is None or np is None:
            self.skipTest('OpenCV/NumPy not available')
        os.makedirs(os.path.join(project_root, 'data', 'processed'), exist_ok=True)

    def _synthetic_image(self, w=320, h=240):
        # Left darker, right overexposed gradient
        img = np.zeros((h, w, 3), dtype='uint8')
        for x in range(w):
            val = int(50 + (205 * (x / (w - 1))))  # 50..255
            img[:, x] = (val, val, val)
        return img

    def test_normalize_exposure_reduces_gradient(self):
        img = self._synthetic_image()
        left_mean_before = img[:, : img.shape[1]//4].mean()
        right_mean_before = img[:, -img.shape[1]//4 :].mean()
        diff_before = abs(right_mean_before - left_mean_before)
        norm = normalize_exposure(img)
        left_mean_after = norm[:, : norm.shape[1]//4].mean()
        right_mean_after = norm[:, -norm.shape[1]//4 :].mean()
        diff_after = abs(right_mean_after - left_mean_after)
        self.assertLess(diff_after, diff_before, 'Exposure normalization did not reduce luminance disparity')

    def test_resize_for_lcd_dimensions(self):
        img = self._synthetic_image(640, 300)
        lcd = resize_for_lcd(img, target=(480,800))
        self.assertEqual(lcd.shape[0], 800)
        self.assertEqual(lcd.shape[1], 480)
        # Ensure original image area fits entirely within canvas (non-background nonzero variance)
        self.assertGreater(lcd.std(), 0.0)

    def test_stitch_frames_output_size(self):
        frames = [self._synthetic_image(160, 120) for _ in range(4)]
        stitched = stitch_frames(frames)
        self.assertEqual(stitched.shape[0], max(f.shape[0] for f in frames))
        self.assertGreater(stitched.shape[1], max(f.shape[1] for f in frames))

    def test_process_for_analysis_creates_files(self):
        # Write synthetic image to disk
        img = self._synthetic_image()
        tmp_dir = os.path.join(project_root, 'data', 'captures')
        os.makedirs(tmp_dir, exist_ok=True)
        path = os.path.join(tmp_dir, 'synthetic.jpg')
        cv2.imwrite(path, img)
        norm_path = process_for_analysis(path)
        self.assertIsNotNone(norm_path)
        self.assertTrue(os.path.exists(norm_path), 'Normalized image file not written')
        base = os.path.splitext(os.path.basename(path))[0]
        lcd_path = os.path.join(project_root, 'data', 'processed', f'{base}_lcd.jpg')
        self.assertTrue(os.path.exists(lcd_path), 'LCD resized image file not written')

if __name__ == '__main__':
    unittest.main()
