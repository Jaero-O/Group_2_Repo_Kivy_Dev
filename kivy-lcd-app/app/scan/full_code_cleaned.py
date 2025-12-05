"""
Mango Leaf Disease Detection System
Professional production-ready pipeline
"""

import RPi.GPIO as GPIO
import time
from picamera2 import Picamera2
import cv2
import numpy as np
import os
import sys
import json
import subprocess
from datetime import datetime
from multiprocessing import Process
from PIL import Image, ImageOps

# Suppress ONNX warnings
os.environ["ORT_LOG_SEVERITY_LEVEL"] = "3"
from rembg.bg import remove
from rembg.session_factory import new_session
from analyze_leaf import analyze_leaf

# ============================================================
# CONFIGURATION
# ============================================================
CONFIG = {
    "model_path": "/home/kennethbinasa/kivy_v1/kivy-lcd-app/app/scan/resnet_leafdisease_datasetresized.onnx",
    "classifier_script": "/home/kennethbinasa/kivy_v1/kivy-lcd-app/app/scan/classify_leaf.py",
    "python_310_path": "/home/kennethbinasa/onnx_venv/bin/python",
    "input_image_path": "output_image_original.png",
    # GPIO Pins
    "dir_pin": 5,
    "step_pin": 12,
    "enable_pin": 6,
    "light_pin": 13,
    "ir_pin": 26,
    # Motion parameters
    "max_steps": 19322,
    "abs_positions": [0, 6453, 12956, 19359],
    "max_freq": 8000,
    "step_distance_mm": 0.01,
    "step_reduction": 150,
    # Image processing
    "camera_size": (2304, 1296),
    "target_width": 480,
    "target_height": 800,
    "crop_top_px": [0, 169, 133, 120],
    "left_shifts": [0, -9, -13, -29],
    # Output
    "output_stitched": "full_leaf_stitched_v3_separate.jpg",
    "output_reduced": "output_image_reduced.png",
    "output_json": "scan_results.json"
}

# ============================================================
# GLOBAL STATE
# ============================================================
current_pos = 0
results = {
    "timestamp": datetime.now().isoformat(),
    "timings": {},
    "classification": None,
    "analysis": None,
    "errors": []
}

# ============================================================
# UTILITY: Live JSON reporting
# ============================================================
def report_phase(phase, pct=0, frame_index=0, total_frames=4, reduced_image=None, message=None):
    data = {
        "phase": phase,
        "pct": pct,
        "frame_index": frame_index,
        "total_frames": total_frames
    }
    if reduced_image:
        data["reduced_image"] = reduced_image
    if message:
        data["message"] = message
    print(json.dumps(data), flush=True)

# ============================================================
# GPIO INITIALIZATION
# ============================================================
GPIO.setmode(GPIO.BCM)
GPIO.setup(CONFIG["dir_pin"], GPIO.OUT)
GPIO.setup(CONFIG["step_pin"], GPIO.OUT)
GPIO.setup(CONFIG["enable_pin"], GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup(CONFIG["light_pin"], GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup(CONFIG["ir_pin"], GPIO.IN)

# ============================================================
# CAMERA INITIALIZATION
# ============================================================
picam2 = Picamera2()
picam2.configure(picam2.create_still_configuration(main={"size": CONFIG["camera_size"]}))
picam2.start()
time.sleep(0.5)
picam2.set_controls({"AfMode": 0, "LensPosition": 9})

# Camera warm-up
GPIO.output(CONFIG["light_pin"], GPIO.LOW)
picam2.set_controls({"AeEnable": True, "AwbEnable": True})
report_phase("warming_up", pct=0, message="Camera warming up...")
time.sleep(3)
picam2.set_controls({"AeEnable": False, "AwbEnable": False})
GPIO.output(CONFIG["light_pin"], GPIO.HIGH)
report_phase("warming_up", pct=100, message="Camera warm-up done.")

U2NET_SESSION = new_session(model_name="u2net")

# ============================================================
# MOTOR CONTROL
# ============================================================
def pulse_motor(freq, steps):
    delay = 1 / freq / 2
    GPIO.output(CONFIG["enable_pin"], GPIO.LOW)
    for _ in range(steps):
        GPIO.output(CONFIG["step_pin"], GPIO.HIGH)
        time.sleep(delay)
        GPIO.output(CONFIG["step_pin"], GPIO.LOW)
        time.sleep(delay)
    GPIO.output(CONFIG["enable_pin"], GPIO.HIGH)

def move_steps(steps, direction):
    global current_pos
    GPIO.output(CONFIG["dir_pin"], direction)
    pulse_motor(CONFIG["max_freq"], steps)
    current_pos += steps if direction == GPIO.HIGH else -steps

def move_to_sensor(direction):
    GPIO.output(CONFIG["dir_pin"], direction)
    delay = 1 / CONFIG["max_freq"] / 2
    step_count = 0
    GPIO.output(CONFIG["enable_pin"], GPIO.LOW)
    while GPIO.input(CONFIG["ir_pin"]) != GPIO.HIGH:
        GPIO.output(CONFIG["step_pin"], GPIO.HIGH)
        time.sleep(delay)
        GPIO.output(CONFIG["step_pin"], GPIO.LOW)
        time.sleep(delay)
        step_count += 1
    GPIO.output(CONFIG["enable_pin"], GPIO.HIGH)
    return step_count

def home_motor(retries=2):
    global current_pos
    for attempt in range(retries):
        if GPIO.input(CONFIG["ir_pin"]) == GPIO.HIGH:
            current_pos = 0
            report_phase("homing", pct=100)
            return True
        move_to_sensor(GPIO.LOW)
        time.sleep(0.5)
        if GPIO.input(CONFIG["ir_pin"]) == GPIO.HIGH:
            current_pos = 0
            report_phase("homing", pct=100)
            return True
    results["errors"].append("Homing failed")
    report_phase("homing", pct=0, message="Homing failed")
    return True

# ============================================================
# IMAGE CAPTURE
# ============================================================
def capture_image(frame_num):
    filename = f"frame_{frame_num:02d}.jpg"
    GPIO.output(CONFIG["light_pin"], GPIO.LOW)
    time.sleep(0.5)
    picam2.capture_file(filename)
    GPIO.output(CONFIG["light_pin"], GPIO.HIGH)
    time.sleep(0.5)
    report_phase("capturing", pct=int((frame_num+1)/len(CONFIG["abs_positions"])*100), frame_index=frame_num, total_frames=len(CONFIG["abs_positions"]))
    return filename

# ============================================================
# SCANNING & STITCHING
# ============================================================
def scan_and_stitch():
    global current_pos
    # Capture frames
    for frame_idx, target_pos in enumerate(CONFIG["abs_positions"]):
        direction = GPIO.HIGH if target_pos > current_pos else GPIO.LOW
        steps = max(abs(target_pos - current_pos) - CONFIG["step_reduction"], 0)
        move_steps(steps, direction)
        capture_image(frame_idx)

    # Load and stitch images
    frames = [f"frame_{i:02d}.jpg" for i in range(len(CONFIG["abs_positions"]))]
    images = [cv2.imread(f) for f in frames]
    if any(img is None for img in images):
        results["errors"].append("Failed to load frames")
        report_phase("error", message="Failed to load frames")
        return False

    # Crop & stitch
    for i in range(1, 4):
        h = images[i].shape[0]
        crop_amt = min(CONFIG["crop_top_px"][i], h - 1)
        images[i] = images[i][crop_amt:, :].copy()

    width = max(img.shape[1] for img in images)
    total_height = sum(img.shape[0] for img in images)
    stitched = np.zeros((total_height, width, 3), dtype=np.uint8)
    current_y = 0
    for img, shift in zip(images, CONFIG["left_shifts"]):
        h, w = img.shape[:2]
        src_x_start = max(0, -shift)
        src_x_end = w
        x_start = max(0, shift)
        width_to_paste = src_x_end - src_x_start
        stitched[current_y:current_y+h, x_start:x_start+width_to_paste] = img[:, src_x_start:src_x_end]
        current_y += h
    cv2.imwrite(CONFIG["output_stitched"], stitched)
    report_phase("stitching", pct=100)
    return True

# ============================================================
# IMAGE PROCESSING
# ============================================================
def process_leaf_image(input_path, output_path):
    report_phase("processing", pct=0)
    img_pil = Image.open(input_path)
    img_no_bg = remove(img_pil, session=U2NET_SESSION)
    img_no_bg = img_no_bg.convert("RGBA")
    background = Image.new("RGB", img_no_bg.size, (255, 255, 255))
    background.paste(img_no_bg, mask=img_no_bg.split()[3])
    img_cv = cv2.cvtColor(np.array(background), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    _, leaf_mask = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    leaf_mask = cv2.morphologyEx(leaf_mask, cv2.MORPH_CLOSE, kernel)
    leaf_mask = cv2.morphologyEx(leaf_mask, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(leaf_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        results["errors"].append("No leaf detected")
        report_phase("error", message="No leaf detected")
        return False
    leaf_contour = max(contours, key=cv2.contourArea)
    x, y, w_crop, h_crop = cv2.boundingRect(leaf_contour)
    cropped_leaf = img_cv[y:y+h_crop, x:x+w_crop]
    Image.fromarray(cv2.cvtColor(cropped_leaf, cv2.COLOR_BGR2RGB)).save(CONFIG["input_image_path"])
    img_final = Image.fromarray(cv2.cvtColor(cropped_leaf, cv2.COLOR_BGR2RGB))
    img_ratio = img_final.width / img_final.height
    target_ratio = CONFIG["target_width"] / CONFIG["target_height"]
    if img_ratio > target_ratio:
        new_width = CONFIG["target_width"]
        new_height = int(CONFIG["target_width"] / img_ratio)
    else:
        new_height = CONFIG["target_height"]
        new_width = int(CONFIG["target_height"] * img_ratio)
    img_resized = img_final.resize((new_width, new_height), Image.Resampling.LANCZOS)
    img_final_padded = ImageOps.pad(img_resized, (CONFIG["target_width"], CONFIG["target_height"]), color="white")
    img_final_padded.save(output_path)
    report_phase("processing", pct=100, reduced_image=output_path)
    return True

# ============================================================
# CLASSIFICATION
# ============================================================
def classify_leaf():
    report_phase("classifying", pct=0)
    try:
        result = subprocess.run(
            [CONFIG["python_310_path"], CONFIG["classifier_script"], CONFIG["input_image_path"], CONFIG["model_path"]],
            capture_output=True, text=True, check=True, timeout=30
        )
        data = json.loads(result.stdout)
        report_phase("classifying", pct=100)
        return data
    except Exception as e:
        results["errors"].append(str(e))
        report_phase("error", message=f"Classification failed: {e}")
        return {"error": str(e)}

# ============================================================
# LEAF ANALYSIS
# ============================================================
def analyze_leaf_features():
    report_phase("analyzing", pct=0)
    try:
        leaf_id = int(datetime.now().timestamp())
        record, vis_img = analyze_leaf(CONFIG["input_image_path"], leaf_id=leaf_id, save_to_csv=True, save_json=True)
        report_phase("analyzing", pct=100)
        return record
    except Exception as e:
        results["errors"].append(str(e))
        report_phase("error", message=f"Analysis failed: {e}")
        return None

# ============================================================
# MAIN PIPELINE
# ============================================================
def run_pipeline():
    start_time = time.time()
    try:
        home_motor()
        scan_and_stitch()
        home_motor()
        process_leaf_image(CONFIG["output_stitched"], CONFIG["output_reduced"])
        classification = classify_leaf()
        results["classification"] = classification
        if "error" not in classification and classification.get("class") != "Healthy":
            analysis = analyze_leaf_features()
            results["analysis"] = analysis
        results["timings"]["total"] = time.time() - start_time
        results["status"] = "success"
        report_phase("complete", pct=100, reduced_image=CONFIG["output_reduced"])
        return True
    except Exception as e:
        results["status"] = "error"
        results["errors"].append(str(e))
        report_phase("error", message=f"Pipeline failed: {e}")
        results["timings"]["total"] = time.time() - start_time
        return False

# ============================================================
# EXECUTION
# ============================================================
if __name__ == "__main__":
    try:
        run_pipeline()
        with open(CONFIG["output_json"], "w") as f:
            json.dump(results, f, indent=2)
        # ===============================
        # FINAL PRINT OUTPUT
        # ===============================
        print("\n===== FINAL RESULTS =====")

        # Classification result
        cls = results.get("classification", {})
        disease_class = cls.get("class", "Unknown")
        confidence = cls.get("confidence", None)

        # print(f"Disease Type      : {disease_class}")

        # --- ADD THIS BLOCK ---
        # High-level disease group
        if disease_class.lower() == "anthracnose":
            final_label = "Anthracnose"
        elif disease_class.lower() == "healthy":
            final_label = "Healthy"
        else:
            final_label = "Non-anthracnose"

        print(f"Final Classification : {final_label}")
        # -----------------------

        if confidence is not None:
            print(f"Confidence Level  : {confidence * 100:.2f}%")
        else:
            print("Confidence Level  : N/A")

        # Severity (only if diseased)
        analysis = results.get("analysis", None)
        if analysis and isinstance(analysis, dict):
            severity = analysis.get("severity_percent", None)
            level = analysis.get("severity_level", None)

            if severity is not None:
                print(f"Severity Percent  : {severity:.2f}%")
            else:
                print("Severity Percent  : N/A")

            if level is not None:
                print(f"Severity Level    : {level}")
            else:
                print("Severity Level    : N/A")
        else:
            print("Severity Percent  : 0% (Healthy or No lesions)")
            print("Severity Level    : None / Healthy")

        print("==========================\n")

    finally:
        GPIO.output(CONFIG["light_pin"], GPIO.HIGH)
        GPIO.output(CONFIG["enable_pin"], GPIO.HIGH)
        picam2.stop()
        GPIO.cleanup()
