"""Hardware scanning pipeline (motor + camera + leaf processing).

Provides functions:
- hardware_available(): detect if GPIO / Picamera2 / rembg are usable.
- initialize_camera()
- home_motor()
- scan_and_stitch(progress_callback=None)
- process_leaf_image(..., progress_callback=None)
- run_leaf_processing_parallel(...)
- run_scan_pipeline(progress_callback=None): sequential orchestration returning processed image path.

On non-hardware environments (e.g. CI / Windows development), all functions fall back
silently and generate a placeholder image so unit tests remain deterministic.
"""
from __future__ import annotations
import os, time
from multiprocessing import Process
from typing import Callable, Optional

# Fallback flags
GPIO = None
Picamera2 = None
cv2 = None
np = None
remove = None
Image = None
ImageOps = None

try:
    import RPi.GPIO as _GPIO
    GPIO = _GPIO
except Exception:
    pass
try:
    from picamera2 import Picamera2 as _Picamera2
    Picamera2 = _Picamera2
except Exception:
    pass
try:
    import cv2 as _cv2
    cv2 = _cv2
except Exception:
    pass
try:
    import numpy as _np
    np = _np
except Exception:
    pass
try:
    from rembg import remove as _remove
    remove = _remove
except Exception:
    pass
try:
    from PIL import Image as _Image, ImageOps as _ImageOps
    Image = _Image
    ImageOps = _ImageOps
except Exception:
    pass

# Pins / motion config (match provided implementation)
DIR_PIN = 5
STEP_PIN = 12
ENABLE_PIN = 6
LIGHT_PIN = 13
IR_PIN = 26
MAX_STEPS = 19322
ABS_POSITIONS = [0, 6453, 12956, 19459]
MAX_FREQ = 8000
STEP_DISTANCE_MM = 0.01
STEP_REDUCTION = 150

_current_pos = 0
_picam2 = None

def hardware_available() -> bool:
    return GPIO is not None and Picamera2 is not None and cv2 is not None and np is not None and Image is not None

# Safe initialization for non-hardware environments
if hardware_available():
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(DIR_PIN, GPIO.OUT)
        GPIO.setup(STEP_PIN, GPIO.OUT)
        GPIO.setup(ENABLE_PIN, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(LIGHT_PIN, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(IR_PIN, GPIO.IN)
    except Exception:
        pass

os.environ.setdefault("ORT_LOG_SEVERITY_LEVEL", "3")

def initialize_camera():
    global _picam2
    if not hardware_available():
        return None
    if _picam2:
        return _picam2
    _picam2 = Picamera2()
    _picam2.configure(_picam2.create_still_configuration(main={"size": (2304, 1296)}))
    _picam2.start()
    time.sleep(0.5)
    try:
        _picam2.set_controls({"AfMode": 0, "LensPosition": 9})
    except Exception:
        pass
    try:
        GPIO.output(LIGHT_PIN, GPIO.LOW)
        _picam2.set_controls({"AeEnable": True, "AwbEnable": True})
        time.sleep(3)
        _picam2.set_controls({"AeEnable": False, "AwbEnable": False})
        GPIO.output(LIGHT_PIN, GPIO.HIGH)
    except Exception:
        pass
    return _picam2

# Motor helpers (no-op on non-hardware)

def _pulse_motor(freq: int, steps: int):
    if not hardware_available():
        return
    delay = 1 / freq / 2
    GPIO.output(ENABLE_PIN, GPIO.LOW)
    for _ in range(steps):
        GPIO.output(STEP_PIN, GPIO.HIGH)
        time.sleep(delay)
        GPIO.output(STEP_PIN, GPIO.LOW)
        time.sleep(delay)
    GPIO.output(ENABLE_PIN, GPIO.HIGH)

def move_steps(steps: int, direction):
    global _current_pos
    if not hardware_available():
        _current_pos += steps if direction else -steps
        return
    GPIO.output(DIR_PIN, direction)
    _pulse_motor(MAX_FREQ, steps)
    _current_pos += steps if direction == GPIO.HIGH else -steps

def move_motor_sensor_based(direction, freq=MAX_FREQ, stall_check_interval=1.0):
    global _current_pos
    if not hardware_available():
        _current_pos = 0
        return
    GPIO.output(DIR_PIN, direction)
    delay = 1 / freq / 2
    step_count = 0
    GPIO.output(ENABLE_PIN, GPIO.LOW)
    last_step_time = time.time()
    while True:
        if GPIO.input(IR_PIN) == GPIO.HIGH:
            break
        GPIO.output(STEP_PIN, GPIO.HIGH)
        time.sleep(delay)
        GPIO.output(STEP_PIN, GPIO.LOW)
        time.sleep(delay)
        step_count += 1
        last_step_time = time.time()
        if time.time() - last_step_time > stall_check_interval:
            if GPIO.input(IR_PIN) == GPIO.HIGH:
                break
            last_step_time = time.time()
    GPIO.output(ENABLE_PIN, GPIO.HIGH)
    _current_pos += step_count if direction == GPIO.HIGH else -step_count

def home_motor(retries=1):
    global _current_pos
    if not hardware_available():
        _current_pos = 0
        return
    for _ in range(retries):
        if GPIO.input(IR_PIN) == GPIO.HIGH and _current_pos == 0:
            _current_pos = 0
            return
        move_motor_sensor_based(GPIO.LOW)
        time.sleep(1)
        if GPIO.input(IR_PIN) == GPIO.HIGH:
            _current_pos = 0
            return
    # Failure leaves position as-is

def ensure_home_before_scan():
    if not hardware_available():
        return
    if GPIO.input(IR_PIN) != GPIO.HIGH:
        home_motor()

def capture_image(frame_num: int, picam2_instance=None):
    if not hardware_available():
        # create placeholder image for tests
        placeholder = f"frame_{frame_num:02d}.jpg"
        if Image and np:
            img = np.full((200, 300, 3), 220, dtype=np.uint8)
            if cv2:
                cv2.imwrite(placeholder, img)
        return placeholder
    global _picam2
    if picam2_instance is None:
        picam2_instance = _picam2 or initialize_camera()
    filename = f"frame_{frame_num:02d}.jpg"
    try:
        GPIO.output(LIGHT_PIN, GPIO.LOW)
        time.sleep(0.5)
        picam2_instance.capture_file(filename)
    finally:
        GPIO.output(LIGHT_PIN, GPIO.HIGH)
        time.sleep(0.5)
    return filename

def scan_and_stitch(progress_callback: Optional[Callable[[int,str],None]] = None) -> str:
    home_motor()
    ensure_home_before_scan()
    if progress_callback:
        progress_callback(0, "Starting scan sequence...")
    total_frames = len(ABS_POSITIONS)
    for idx, target in enumerate(ABS_POSITIONS):
        direction = GPIO.HIGH if target > _current_pos else GPIO.LOW
        steps_to_move = max(abs(target - _current_pos) - STEP_REDUCTION, 0)
        move_steps(steps_to_move, direction)
        capture_image(idx)
        if progress_callback:
            pct = int((idx + 1) / total_frames * 45)
            progress_callback(pct, f"Captured frame {idx+1}/{total_frames}")
    if progress_callback:
        progress_callback(50, "Frames captured. Stitching images...")
    frames = [f"frame_{i:02d}.jpg" for i in range(total_frames)]
    if not cv2 or not np:
        # create placeholder stitched image
        stitched_path = "full_leaf_stitched_v3_separate.jpg"
        if Image and np:
            Image.new("RGB", (480, 800), (255,255,255)).save(stitched_path)
        return stitched_path
    images = [cv2.imread(f) for f in frames]
    crop_top_px = [0, 169, 133, 120]
    left_shifts = [0, -9, -13, -29]
    for i in range(1, total_frames):
        h = images[i].shape[0]
        crop_amt = min(crop_top_px[i], h - 1)
        images[i] = images[i][crop_amt:, :].copy()
    width = max(img.shape[1] for img in images)
    total_height = sum(img.shape[0] for img in images)
    stitched = np.zeros((total_height, width, 3), dtype=np.uint8)
    current_y = 0
    for i, (img, shift) in enumerate(zip(images, left_shifts)):
        h, w = img.shape[:2]
        src_x_start = -shift if shift < 0 else 0
        src_x_end = w
        x_start = 0 if shift < 0 else shift
        stitched[current_y:current_y + h, x_start:x_start + (src_x_end - src_x_start)] = img[:, src_x_start:src_x_end]
        current_y += h
        if progress_callback:
            pct = 50 + int((i + 1) / total_frames * 15)
            progress_callback(pct, f"Stitching frame {i+1}/{total_frames}")
    stitched_path = "full_leaf_stitched_v3_separate.jpg"
    cv2.imwrite(stitched_path, stitched)
    if progress_callback:
        progress_callback(65, "Stitching completed.")
    return stitched_path

def process_leaf_image(input_path: str, output_path: str, target_width: int = 480, target_height: int = 800, progress_callback: Optional[Callable[[int,str],None]] = None) -> str:
    if progress_callback:
        progress_callback(70, "Processing leaf image...")
    if not Image or not np or not cv2:
        # simple passthrough placeholder
        if Image:
            Image.new("RGB", (target_width, target_height), (255,255,255)).save(output_path)
        if progress_callback:
            progress_callback(100, f"Leaf processed (placeholder) saved as {output_path}")
        return output_path
    img_pil = Image.open(input_path)
    if remove:
        if progress_callback:
            progress_callback(72, "Removing background...")
        img_no_bg = remove(img_pil).convert("RGBA")
        background = Image.new("RGB", img_no_bg.size, (255, 255, 255))
        background.paste(img_no_bg, mask=img_no_bg.split()[3])
        img_cv = cv2.cvtColor(np.array(background), cv2.COLOR_RGB2BGR)
    else:
        img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    _, leaf_mask = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    leaf_mask = cv2.morphologyEx(leaf_mask, cv2.MORPH_CLOSE, kernel)
    leaf_mask = cv2.morphologyEx(leaf_mask, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(leaf_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        leaf_contour = max(contours, key=cv2.contourArea)
        x, y, w_crop, h_crop = cv2.boundingRect(leaf_contour)
        cropped_leaf = img_cv[y:y+h_crop, x:x+w_crop]
    else:
        cropped_leaf = img_cv
    img_final = Image.fromarray(cv2.cvtColor(cropped_leaf, cv2.COLOR_BGR2RGB))
    img_ratio = img_final.width / img_final.height
    target_ratio = target_width / target_height
    if img_ratio > target_ratio:
        new_width = target_width
        new_height = int(target_width / img_ratio)
    else:
        new_height = target_height
        new_width = int(target_height * img_ratio)
    img_resized = img_final.resize((new_width, new_height), Image.Resampling.LANCZOS)
    img_final_padded = ImageOps.pad(img_resized, (target_width, target_height), color="white")
    img_final_padded.save(output_path)
    if progress_callback:
        progress_callback(100, f"Leaf processed and saved as {output_path}")
    return output_path

def run_leaf_processing_parallel(input_path="full_leaf_stitched_v3_separate.jpg", output_path="output_image_reduced.png", progress_callback: Optional[Callable[[int,str],None]] = None) -> str:
    if not hardware_available():
        return process_leaf_image(input_path, output_path, progress_callback=progress_callback)
    # Run homing and processing concurrently
    def _leaf():
        process_leaf_image(input_path, output_path, progress_callback=progress_callback)
    p_leaf = Process(target=_leaf)
    p_home = Process(target=home_motor)
    p_leaf.start(); p_home.start(); p_leaf.join(); p_home.join()
    return output_path

def cleanup_gpio():
    if not hardware_available():
        return
    try:
        GPIO.output(LIGHT_PIN, GPIO.HIGH)
        GPIO.output(ENABLE_PIN, GPIO.HIGH)
        if _picam2:
            _picam2.stop()
        GPIO.cleanup()
    except Exception:
        pass

def run_scan_pipeline(progress_callback: Optional[Callable[[int,str],None]] = None) -> Optional[str]:
    """Full hardware pipeline: home -> scan & stitch -> parallel homing + leaf processing.
    Returns processed image path or placeholder path on failure."""
    try:
        initialize_camera()
        if progress_callback:
            progress_callback(0, "Homing motor...")
        home_motor()
        stitched = scan_and_stitch(progress_callback=progress_callback)
        if progress_callback:
            progress_callback(68, "Starting parallel processing...")
        processed = run_leaf_processing_parallel(input_path=stitched, output_path="output_image_reduced.png", progress_callback=progress_callback)
        if progress_callback:
            progress_callback(100, "Scan complete!")
        return processed
    except Exception as e:
        if progress_callback:
            progress_callback(0, f"Error: {e}")
        return None
    finally:
        cleanup_gpio()

__all__ = [
    "hardware_available", "initialize_camera", "home_motor", "scan_and_stitch", "process_leaf_image",
    "run_leaf_processing_parallel", "run_scan_pipeline", "cleanup_gpio"
]
