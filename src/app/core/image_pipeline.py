import os
from typing import List, Optional, Tuple

# Lazy imports so tests that patch without OpenCV still import this module.
try:  # pragma: no cover - import branch
    import cv2  # type: ignore
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore
    np = None  # type: ignore


def _ensure_opencv():  # pragma: no cover - simple guard
    if cv2 is None or np is None:
        raise RuntimeError("OpenCV / NumPy not available; ensure opencv-python and numpy are installed.")


def normalize_exposure(img_bgr: 'np.ndarray') -> 'np.ndarray':
    """Apply CLAHE to luminance channel then rebalance average L to original.
    Keeps size, returns BGR image. Assumes uint8 input.
    """
    _ensure_opencv()
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l2 = clahe.apply(l)
    mean_target = float(l.mean())
    mean_current = float(l2.mean()) or 1.0
    scale = mean_target / mean_current
    l2 = (l2.astype('float32') * scale).clip(0, 255).astype('uint8')
    lab2 = cv2.merge([l2, a, b])
    return cv2.cvtColor(lab2, cv2.COLOR_LAB2BGR)


def resize_for_lcd(img_bgr: 'np.ndarray', target: Tuple[int, int] = (480, 800), bg_color=(0, 0, 0)) -> 'np.ndarray':
    """Letterbox resize preserving aspect ratio into target WxH (width,height)."""
    _ensure_opencv()
    tw, th = target
    h, w = img_bgr.shape[:2]
    scale = min(tw / w, th / h)
    nw, nh = int(w * scale), int(h * scale)
    resized = cv2.resize(img_bgr, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas = np.full((th, tw, 3), bg_color, dtype='uint8')
    y0 = (th - nh) // 2
    x0 = (tw - nw) // 2
    canvas[y0:y0 + nh, x0:x0 + nw] = resized
    return canvas


def stitch_frames(frames: List['np.ndarray']) -> 'np.ndarray':
    """Simple horizontal stitch with exposure normalization + feather blend.
    Expects list of BGR images. Returns single stitched BGR image.
    """
    _ensure_opencv()
    if not frames:
        raise ValueError("No frames provided for stitching")
    norm = [normalize_exposure(f) for f in frames]
    heights = [f.shape[0] for f in norm]
    target_h = max(heights)
    resized = [cv2.resize(f, (int(f.shape[1] * target_h / f.shape[0]), target_h)) for f in norm]
    feather = 30
    out = resized[0].astype('float32')
    for nxt in resized[1:]:
        # Create new canvas each iteration
        new_w = int(out.shape[1] + nxt.shape[1])
        canvas = np.zeros((target_h, new_w, 3), dtype='float32')
        canvas[:, :out.shape[1]] = out
        # Feather blend overlap at boundary
        overlap = min(feather, out.shape[1], nxt.shape[1])
        left_slice = canvas[:, out.shape[1] - overlap:out.shape[1]]
        right_slice = nxt[:, :overlap].astype('float32')
        for i in range(overlap):
            alpha = i / overlap
            left_slice[:, i] = left_slice[:, i] * (1 - alpha) + right_slice[:, i] * alpha
        canvas[:, out.shape[1]:out.shape[1] + nxt.shape[1]] = nxt
        out = canvas
    return out.clip(0, 255).astype('uint8')


def process_for_analysis(image_path: str, lcd_target: Tuple[int, int] = (480, 800)) -> Optional[str]:
    """Load image, normalize exposure, resize for LCD preview, persist results.
    Returns path to normalized image for analysis (not the LCD canvas).
    Stores additional attributes on the running Kivy App if available:
      - app.processed_image_path
      - app.lcd_display_image_path
    """
    _ensure_opencv()
    if not os.path.exists(image_path):
        return None
    img = cv2.imread(image_path)
    if img is None:
        return None
    norm = normalize_exposure(img)
    lcd = resize_for_lcd(norm, target=lcd_target)
    processed_dir = os.path.join('data', 'processed')
    os.makedirs(processed_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(image_path))[0]
    norm_path = os.path.join(processed_dir, f"{base}_norm.jpg")
    lcd_path = os.path.join(processed_dir, f"{base}_lcd.jpg")
    cv2.imwrite(norm_path, norm)
    cv2.imwrite(lcd_path, lcd)
    try:  # Attach to Kivy App for UI use if available
        from kivy.app import App
        app = App.get_running_app()
        setattr(app, 'processed_image_path', norm_path)
        setattr(app, 'lcd_display_image_path', lcd_path)
    except Exception:
        pass
    return norm_path
