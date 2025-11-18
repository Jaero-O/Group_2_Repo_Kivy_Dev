import os
import sys
import tempfile
import numpy as np
import unittest
try:
    import cv2
    _CV2_AVAILABLE = True
except Exception:
    _CV2_AVAILABLE = False

# Ensure src is importable
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if _CV2_AVAILABLE:
    from ml.severity_calculator import calculate_severity_percentage


@unittest.skipIf(not _CV2_AVAILABLE, "cv2 is not available in this environment")
def test_calculate_severity_on_synthetic_image(tmp_path):
    # Create an image with a green leaf and a brown lesion
    img_path = tmp_path / 'leaf.jpg'
    h, w = 300, 300
    img = np.zeros((h, w, 3), dtype=np.uint8)

    # Draw a green leaf (ellipse)
    cv2.ellipse(img, (150, 150), (100, 140), 0, 0, 360, (0, 255, 0), -1)

    # Draw a darker lesion area inside the leaf (smaller ellipse)
    cv2.ellipse(img, (160, 150), (30, 40), 0, 0, 360, (20, 80, 80), -1)

    cv2.imwrite(str(img_path), img)

    severity = calculate_severity_percentage(str(img_path))

    # Severity should be > 0 and reasonably small (lesion inside leaf)
    assert severity > 0.0
    assert severity < 100.0

    # Given the synthetic sizes, expect a small percentage (e.g., below 50%)
    assert severity < 50.0
