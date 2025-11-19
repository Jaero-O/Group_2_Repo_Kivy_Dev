import os
from typing import Optional, Tuple, List

# Optional heavy deps (lazy)
try:  # pragma: no cover
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore
try:  # pragma: no cover
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None  # type: ignore


def _ensure_save_dir(save_path: str):
    d = os.path.dirname(save_path)
    if d:
        os.makedirs(d, exist_ok=True)


def capture_image_raspicam(save_path: str, preview_size: Tuple[int, int] = (1280, 720), still_size: Tuple[int, int] = (1920, 1080), timeout: float = 2.0) -> Optional[str]:
    """Capture an image using Raspberry Pi camera hardware.

    Tries `picamera2` (preferred) with a preview/still configuration. If
    Picamera2 is not available, falls back to the legacy `picamera` API.

    The function is defensive and will raise NotImplementedError when no
    supported API is present. On success it returns `save_path`.
    """
    _ensure_save_dir(save_path)

    # Try picamera2 first (libcamera-based)
    try:
        from picamera2 import Picamera2
        from picamera2.encoders import JpegEncoder
        from picamera2.outputs import FileOutput

        picam = Picamera2()

        # Create a preview configuration for responsiveness and a still
        try:
            preview_config = picam.create_preview_configuration(main={"size": preview_size})
            still_config = picam.create_still_configuration(main={"size": still_size})
        except Exception:
            # Older/backport versions may not expose helpers; fall back to simple config
            preview_config = None
            still_config = None

        # Start preview if possible (non-blocking)
        try:
            if preview_config is not None:
                picam.configure(preview_config)
            picam.start()
        except Exception:
            # If preview start fails continue — we'll attempt capture
            pass

        # Attempt to capture a still image to file. Use FileOutput with JpegEncoder
        try:
            # If still_config available, reconfigure for still capture
            if still_config is not None:
                picam.configure(still_config)
            # Use capture_file if available
            if hasattr(picam, 'capture_file'):
                picam.capture_file(save_path)
            else:
                # Fall back to encoder/output API
                encoder = JpegEncoder()
                output = FileOutput(save_path)
                picam.start_and_capture_file(save_path)
        except Exception:
            # Last resort: capture array and write via PIL/numpy if present
            try:
                arr = picam.capture_array()
                try:
                    from PIL import Image
                    Image.fromarray(arr).save(save_path, quality=85)
                except Exception:
                    # Attempt numpy + imageio
                    import imageio
                    imageio.imwrite(save_path, arr)
            except Exception:
                raise
        finally:
            try:
                picam.stop()
            except Exception:
                pass

        return save_path
    except Exception:
        # swallow and try legacy path
        pass

    # Fallback to older picamera module
    try:
        import picamera
        with picamera.PiCamera() as camera:
            camera.resolution = (1640, 1232)
            camera.capture(save_path)
            return save_path
    except Exception:
        pass

    raise NotImplementedError('No Raspberry Pi camera API available on this platform')


def capture_multi_frame_stitched(base_path: str, count: int = 4) -> Optional[str]:
    """Capture multiple frames and stitch them horizontally after exposure normalization.

    Returns path to stitched image. Falls back to placeholder if camera unavailable.
    Frames saved as base_path_frame{i}.jpg.
    """
    # Prepare directory
    os.makedirs(os.path.dirname(base_path), exist_ok=True)
    frame_paths: List[str] = []
    stitched_path = os.path.join(os.path.dirname(base_path), 'capture_stitched.jpg')
    try:
        for i in range(count):
            p = f"{base_path}_frame{i}.jpg"
            capture_image_raspicam(p)
            frame_paths.append(p)
    except Exception as exc:
        # Fallback: use placeholder repeated frames
        placeholder = os.path.join(os.path.dirname(__file__), '..', 'assets', 'placeholder_bg1.png')
        placeholder = os.path.abspath(os.path.normpath(placeholder))
        frame_paths = [placeholder for _ in range(count)]
        try:
            print(f"DIAG: multi-frame fallback using placeholder due to: {exc}")
        except Exception:
            pass

    # If OpenCV unavailable just return first frame
    if cv2 is None or np is None:
        return frame_paths[0] if frame_paths else None

    # Load frames
    imgs = []
    for fp in frame_paths:
        if os.path.exists(fp):
            img = cv2.imread(fp)
            if img is not None:
                imgs.append(img)
    if not imgs:
        return frame_paths[0] if frame_paths else None

    # Simple normalization using CLAHE per frame
    def _norm(img):
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l,a,b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        l2 = clahe.apply(l)
        lab2 = cv2.merge([l2,a,b])
        return cv2.cvtColor(lab2, cv2.COLOR_LAB2BGR)

    norm_imgs = [_norm(i) for i in imgs]

    # Stitch horizontally
    height = max(i.shape[0] for i in norm_imgs)
    resized = [cv2.resize(i, (int(i.shape[1]*height/i.shape[0]), height)) for i in norm_imgs]
    out = resized[0].astype('float32')
    feather = 30
    for nxt in resized[1:]:
        new_w = int(out.shape[1] + nxt.shape[1])
        canvas = np.zeros((height, new_w, 3), dtype='float32')
        canvas[:, :out.shape[1]] = out
        overlap = min(feather, out.shape[1], nxt.shape[1])
        left_slice = canvas[:, out.shape[1]-overlap:out.shape[1]]
        right_slice = nxt[:, :overlap].astype('float32')
        for i in range(overlap):
            alpha = i/overlap
            left_slice[:, i] = left_slice[:, i]*(1-alpha) + right_slice[:, i]*alpha
        canvas[:, out.shape[1]:out.shape[1]+nxt.shape[1]] = nxt
        out = canvas
    out = out.clip(0,255).astype('uint8')
    cv2.imwrite(stitched_path, out)
    return stitched_path
