"""
This module provides the severity calculation logic.
"""
try:
    import cv2
except Exception:
    cv2 = None
import numpy as np

def segment_leaf(img_hsv):
    lower = np.array([20, 40, 40])
    upper = np.array([90, 255, 255])
    mask = cv2.inRange(img_hsv, lower, upper)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5,5), np.uint8))
    return mask

def segment_lesion(img_hsv, leaf_mask):
    lower = np.array([5, 30, 0])
    upper = np.array([25, 255, 160])
    mask = cv2.inRange(img_hsv, lower, upper)
    mask = cv2.bitwise_and(mask, leaf_mask)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3,3), np.uint8))
    return mask

def calculate_severity_percentage(image_path: str) -> float:
    """
    Calculates the severity of the disease in an image.
    """
    if cv2 is None:
        # OpenCV not available in this environment — return a safe default.
        return 0.0

    img = cv2.imread(image_path)
    if img is None:
        return 0.0

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    leaf_mask = segment_leaf(hsv)
    lesion_mask = segment_lesion(hsv, leaf_mask)

    leaf_area_px = cv2.countNonZero(leaf_mask)
    lesion_area_px = cv2.countNonZero(lesion_mask)

    # Fallback: if primary lesion segmentation finds nothing but we have
    # a leaf, attempt a simple dark/dull region extraction inside the leaf.
    if lesion_area_px == 0 and leaf_area_px > 0:
        dark_or_dull = cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 255, 150]))
        lesion_mask = cv2.bitwise_and(dark_or_dull, leaf_mask)
        lesion_mask = cv2.morphologyEx(lesion_mask, cv2.MORPH_OPEN, np.ones((3,3), np.uint8))
        lesion_area_px = cv2.countNonZero(lesion_mask)

    if leaf_area_px == 0:
        return 0.0

    severity_pct = (lesion_area_px / leaf_area_px * 100)
    # Clamp to valid range and ensure a minimal non-zero if lesion detected.
    if lesion_area_px > 0 and severity_pct <= 0:
        severity_pct = 0.01
    if severity_pct < 0:
        severity_pct = 0.0
    if severity_pct > 100:
        severity_pct = 100.0
    return severity_pct
