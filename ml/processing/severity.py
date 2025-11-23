import os
from typing import Tuple

try:
    import cv2  # type: ignore
except Exception:
    cv2 = None  # Optional; we degrade gracefully

from PIL import Image
import numpy as np

__all__ = ["compute_severity", "segment_lesions"]


def _load_image(image_path: str) -> np.ndarray:
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    img = Image.open(image_path).convert("RGB")
    return np.asarray(img)


def segment_lesions(rgb: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Return (leaf_mask, lesion_mask).

    Strategy (progressive fallback):
    1. If OpenCV available: convert to HSV, build leaf mask by green range threshold, lesion mask by brown/dark thresholds within leaf.
    2. Fallback: use simple luminance & green channel heuristics.
    """
    # Ensure shape
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("Expected RGB image array")

    if cv2 is not None:
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        h, s, v = cv2.split(hsv)

        # Leaf (greenish) range (tunable)
        leaf_lower = np.array([25, 40, 40])  # hue ~25 (yellow-green) min saturation/value
        leaf_upper = np.array([95, 255, 255])  # hue ~95 (green)
        leaf_mask = cv2.inRange(hsv, leaf_lower, leaf_upper).astype(bool)

        # Lesions: darker / brown (lower V or higher hue near 10-25 but low saturation)
        brown_lower = np.array([5, 10, 20])
        brown_upper = np.array([35, 180, 200])
        brown_mask = cv2.inRange(hsv, brown_lower, brown_upper).astype(bool)

        # Dark spots (low V) inside leaf
        dark_mask = (v < 70) & leaf_mask

        lesion_mask = (brown_mask | dark_mask) & leaf_mask
        return leaf_mask, lesion_mask

    # Fallback heuristics (no OpenCV):
    r = rgb[..., 0].astype(np.float32)
    g = rgb[..., 1].astype(np.float32)
    b = rgb[..., 2].astype(np.float32)
    luminance = 0.299 * r + 0.587 * g + 0.114 * b

    # Leaf mask: pixels where green channel dominates and luminance medium/high
    leaf_mask = (g > r * 0.9) & (g > b * 0.9) & (luminance > 40)

    # Lesion mask: darker (low luminance) or brownish (R relatively high but G not dominating)
    brownish = (r > g * 0.8) & (r > b * 0.8) & (luminance < 160)
    dark_spot = (luminance < 65)
    lesion_mask = (brownish | dark_spot) & leaf_mask
    return leaf_mask, lesion_mask


def compute_severity(image_path: str) -> float:
    """Compute severity percentage = (lesion_area / leaf_area) * 100.

    Returns 0.0 if leaf area insufficient (e.g. small mask) to avoid division noise.
    """
    rgb = _load_image(image_path)
    leaf_mask, lesion_mask = segment_lesions(rgb)

    leaf_area = int(np.count_nonzero(leaf_mask))
    if leaf_area < 200:  # threshold to avoid tiny noise classification
        return 0.0

    lesion_area = int(np.count_nonzero(lesion_mask))
    severity = (lesion_area / leaf_area) * 100.0
    # Clamp
    if severity < 0:
        severity = 0.0
    if severity > 100:
        severity = 100.0
    return round(severity, 2)


def compute_severity_with_areas(image_path: str) -> Tuple[float, float, float]:
    """Compute severity percentage and return areas.
    
    Returns:
        Tuple of (severity_percentage, total_leaf_area, lesion_area)
    """
    rgb = _load_image(image_path)
    leaf_mask, lesion_mask = segment_lesions(rgb)

    leaf_area = float(np.count_nonzero(leaf_mask))
    if leaf_area < 200:  # threshold to avoid tiny noise classification
        return 0.0, 0.0, 0.0

    lesion_area = float(np.count_nonzero(lesion_mask))
    severity = (lesion_area / leaf_area) * 100.0
    # Clamp
    if severity < 0:
        severity = 0.0
    if severity > 100:
        severity = 100.0
    return round(severity, 2), leaf_area, lesion_area
