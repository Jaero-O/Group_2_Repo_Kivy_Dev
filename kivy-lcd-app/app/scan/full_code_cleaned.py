"""
Mango Leaf Disease Detection System
Professional production-ready pipeline
"""

# Suppress ONNX and other warnings BEFORE any imports
import os
import sys
os.environ["ORT_LOG_SEVERITY_LEVEL"] = "4"  # 4 = Fatal only
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["GLOG_minloglevel"] = "3"

import RPi.GPIO as GPIO
import time
from picamera2 import Picamera2
import cv2
import numpy as np
import json
import subprocess
from datetime import datetime
from multiprocessing import Process
from PIL import Image, ImageOps
import sqlite3
from pathlib import Path

from rembg.bg import remove
from rembg.session_factory import new_session

# Print startup message to stderr for debugging
print("=== Scan Script Starting ===", file=sys.stderr)
print(f"Script location: {__file__}", file=sys.stderr)
print(f"Working directory: {os.getcwd()}", file=sys.stderr)

try:
    from analyze_leaf import analyze_leaf
    print("✓ analyze_leaf imported successfully", file=sys.stderr)
except ImportError as e:
    print(f"✗ Failed to import analyze_leaf: {e}", file=sys.stderr)
    print(f"  Python path: {sys.path}", file=sys.stderr)
    sys.exit(1)

# ============================================================
# CONFIGURATION
# ============================================================
# Determine base paths relative to this script
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent  # Go up to mangofy-system root
DATA_DIR = PROJECT_ROOT / "data"
KIVY_APP_DIR = PROJECT_ROOT / "kivy-lcd-app"

print(f"SCRIPT_DIR: {SCRIPT_DIR}", file=sys.stderr)
print(f"PROJECT_ROOT: {PROJECT_ROOT}", file=sys.stderr)
print(f"DATA_DIR: {DATA_DIR}", file=sys.stderr)

# Create base scans directory
SCANS_BASE_DIR = DATA_DIR / "scans"
SCANS_BASE_DIR.mkdir(parents=True, exist_ok=True)
print(f"✓ Scans directory ready: {SCANS_BASE_DIR}", file=sys.stderr)

# Generate unique scan directory with timestamp
SCAN_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
SCAN_DIR = SCANS_BASE_DIR / f"scan_{SCAN_TIMESTAMP}"
SCAN_DIR.mkdir(exist_ok=True)
print(f"✓ Created scan directory: {SCAN_DIR}", file=sys.stderr)

# Determine Python executable for ONNX environment
ONNX_PYTHON = os.getenv("ONNX_PYTHON_PATH", "python3")  # Default to system python3

# Verify critical files exist
model_path = SCRIPT_DIR / "resnet_leafdisease_datasetresized.onnx"
classifier_path = SCRIPT_DIR / "classify_leaf.py"
db_path = KIVY_APP_DIR / "mangofy.db"

print(f"Checking model: {model_path} - {'EXISTS' if model_path.exists() else 'MISSING'}", file=sys.stderr)
print(f"Checking classifier: {classifier_path} - {'EXISTS' if classifier_path.exists() else 'MISSING'}", file=sys.stderr)
print(f"Checking database: {db_path} - {'EXISTS' if db_path.exists() else 'MISSING'}", file=sys.stderr)

if not model_path.exists():
    print(f"ERROR: Model file not found at {model_path}", file=sys.stderr)
    sys.exit(1)
if not classifier_path.exists():
    print(f"ERROR: Classifier script not found at {classifier_path}", file=sys.stderr)
    sys.exit(1)

CONFIG = {
    "model_path": str(model_path),
    "classifier_script": str(classifier_path),
    "python_310_path": ONNX_PYTHON,
    "database_path": str(db_path),
    "scan_dir": str(SCAN_DIR),
    "input_image_path": str(SCAN_DIR / "output_image_original.png"),
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
    # Output (all in scan directory)
    "output_stitched": str(SCAN_DIR / "full_leaf_stitched.jpg"),
    "output_reduced": str(SCAN_DIR / "output_image_reduced.png"),
    "output_json": str(SCAN_DIR / "scan_results.json")
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
            curstr(SCAN_DIR / f"frame_{frame_num:02d}.jpg")
            report_phase("homing", pct=100)
            return True
    results["errors"].append("Homing failed")
    report_phase("homing", pct=0, message="Homing failed")
    return True

# ============================================================
# IMAGE CAPTURE
# ============================================================
def capture_image(frame_num):
    filename = str(SCAN_DIR / f"frame_{frame_num:02d}.jpg")
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
    frames = [str(SCAN_DIR / f"frame_{i:02d}.jpg") for i in range(len(CONFIG["abs_positions"]))]
    print(f"Loading frames from: {frames[0]}", file=sys.stderr)
    
    images = [cv2.imread(f) for f in frames]
    
    # Check which frames failed to load
    failed_frames = [f for i, (f, img) in enumerate(zip(frames, images)) if img is None]
    if failed_frames:
        print(f"✗ Failed to load frames: {failed_frames}", file=sys.stderr)
        for frame_path in frames:
            exists = Path(frame_path).exists()
            print(f"  {frame_path}: {'EXISTS' if exists else 'MISSING'}", file=sys.stderr)
        results["errors"].append("Failed to load frames")
        report_phase("error", message="Failed to load frames")
        return False
    
    print(f"✓ All {len(images)} frames loaded successfully", file=sys.stderr)

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
# DATABASE STORAGE
# ============================================================
def save_to_database():
    """Save complete scan results to database."""
    try:
        db_path = CONFIG["database_path"]
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Extract results
        classification = results.get("classification", {})
        analysis = results.get("analysis", {})
        
        disease_class = classification.get("class", "Unknown")
        confidence = classification.get("confidence", 0.0)
        all_preds = classification.get("all_predictions", {})
        
        # Map disease class to disease_id
        disease_map = {
            "Anthracnose": 1,
            "Healthy": None,
            "Bacterial Canker": 2,
            "Cutting Weevil": 3,
            "Powdery Mildew": 4,
            "Sooty Mould": 5,
        }
        disease_id = disease_map.get(disease_class, None)
        
        # Extract severity info
        severity_pct = analysis.get("severity_percent", 0.0) if analysis else 0.0
        severity_level = analysis.get("severity_level", "None") if analysis else "None"
        
        # Map severity level to severity_level_id
        severity_map = {"None": None, "Low": 1, "Moderate": 2, "High": 3}
        severity_id = severity_map.get(severity_level, None)
        
        # Construct relative image paths
        scan_dir_name = Path(CONFIG["scan_dir"]).name
        
        # Image paths with existence verification
        reduced_image = Path(CONFIG["output_reduced"])
        image_path = f"../data/scans/{scan_dir_name}/{reduced_image.name}" if reduced_image.exists() else None
        
        stitched_image = Path(CONFIG["output_stitched"])
        thumbnail_path = f"../data/scans/{scan_dir_name}/{stitched_image.name}" if stitched_image.exists() else image_path
        
        json_file = Path(CONFIG["output_json"])
        json_path = f"../data/scans/{scan_dir_name}/{json_file.name}" if json_file.exists() else None
        
        # Build comprehensive notes
        notes = f"Scan: {scan_dir_name} | Disease: {disease_class}"
        if severity_level != "None":
            notes += f" | Severity: {severity_level} ({severity_pct:.1f}%)"
        
        # Insert complete scan record
        cur.execute("""
            INSERT INTO tbl_scan_record (
                tree_id, disease_id, severity_level_id,
                scan_timestamp, scan_duration, scan_status,
                disease_class, confidence_score,
                pred_anthracnose, pred_healthy, pred_bacterial_canker,
                pred_cutting_weevil, pred_powdery_mildew, pred_sooty_mould,
                severity_percentage, severity_level,
                leaf_area_cm2, lesion_area_cm2, lesion_count, mean_lesion_size_px,
                leaf_mean_r, leaf_mean_g, leaf_mean_b,
                lesion_mean_r, lesion_mean_g, lesion_mean_b,
                lesion_to_leaf_color_ratio_g,
                exg_mean, ndvi_proxy_mean,
                leaf_solidity, leaf_circularity, leaf_aspect_ratio,
                damage_pct_inpaint, lesion_glcm_contrast, lesion_glcm_dissimilarity,
                image_path, thumbnail_path, json_path, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            None,  # tree_id - can be set later
            disease_id,
            severity_id,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            results.get("timings", {}).get("total", 0.0),
            results.get("status", "unknown"),
            disease_class,
            confidence,
            all_preds.get("Anthracnose", 0.0),
            all_preds.get("Healthy", 0.0),
            all_preds.get("Bacterial Canker", 0.0),
            all_preds.get("Cutting Weevil", 0.0),
            all_preds.get("Powdery Mildew", 0.0),
            all_preds.get("Sooty Mould", 0.0),
            severity_pct,
            severity_level,
            analysis.get("leaf_area_cm2", 0.0) if analysis else 0.0,
            analysis.get("lesion_area_cm2", 0.0) if analysis else 0.0,
            analysis.get("lesion_count", 0) if analysis else 0,
            analysis.get("mean_lesion_size_px", 0.0) if analysis else 0.0,
            analysis.get("leaf_mean_r", 0.0) if analysis else 0.0,
            analysis.get("leaf_mean_g", 0.0) if analysis else 0.0,
            analysis.get("leaf_mean_b", 0.0) if analysis else 0.0,
            analysis.get("lesion_mean_r", 0.0) if analysis else 0.0,
            analysis.get("lesion_mean_g", 0.0) if analysis else 0.0,
            analysis.get("lesion_mean_b", 0.0) if analysis else 0.0,
            analysis.get("lesion_to_leaf_color_ratio_g", 0.0) if analysis else 0.0,
            analysis.get("exg_mean", 0.0) if analysis else 0.0,
            analysis.get("ndvi_proxy_mean", 0.0) if analysis else 0.0,
            analysis.get("leaf_solidity", 0.0) if analysis else 0.0,
            analysis.get("leaf_circularity", 0.0) if analysis else 0.0,
            analysis.get("leaf_aspect_ratio", 0.0) if analysis else 0.0,
            analysis.get("damage_pct_inpaint", 0.0) if analysis else 0.0,
            analysis.get("lesion_glcm_contrast", 0.0) if analysis else 0.0,
            analysis.get("lesion_glcm_dissimilarity", 0.0) if analysis else 0.0,
            image_path,
            thumbnail_path,
            json_path,
            notes
        ))
        
        conn.commit()
        scan_id = cur.lastrowid
        results["database_id"] = scan_id
        conn.close()
        
        print(f"✓ Saved to database (scan_id: {scan_id})", file=sys.stderr)
        print(f"  Image: {image_path}", file=sys.stderr)
        print(f"  Thumbnail: {thumbnail_path}", file=sys.stderr)
        print(f"  JSON: {json_path}", file=sys.stderr)
        return scan_id
        
    except Exception as e:
        print(f"✗ Database save failed: {e}", file=sys.stderr)
        results["errors"].append(f"Database error: {e}")
        return None

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
        
        # Scan and stitch - abort if it fails
        if not scan_and_stitch():
            results["timings"]["total"] = time.time() - start_time
            results["status"] = "error"
            return False
        
        home_motor()
        
        # Process image - abort if it fails
        if not process_leaf_image(CONFIG["output_stitched"], CONFIG["output_reduced"]):
            results["timings"]["total"] = time.time() - start_time
            results["status"] = "error"
            return False
        
        classification = classify_leaf()
        results["classification"] = classification
        if "error" not in classification and classification.get("class") != "Healthy":
            analysis = analyze_leaf_features()
            results["analysis"] = analysis
        results["timings"]["total"] = time.time() - start_time
        results["status"] = "success"
        
        # Save to database
        scan_id = save_to_database()
        
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
        
        # Save results JSON to file
        with open(CONFIG["output_json"], "w") as f:
            json.dump(results, f, indent=2)
        
        # Print summary to stderr (keeps stdout clean for JSON)
        print("\n" + "="*50, file=sys.stderr)
        print(f"SCAN COMPLETE - Saved to: {CONFIG['scan_dir']}", file=sys.stderr)
        print("="*50, file=sys.stderr)
        
        # ===============================
        # FINAL PRINT OUTPUT TO STDERR
        # ===============================
        print("\n===== FINAL RESULTS =====", file=sys.stderr)

        # Classification result
        cls = results.get("classification") or {}
        disease_class = cls.get("class", "Unknown")
        confidence = cls.get("confidence", None)

        # High-level disease group
        if disease_class.lower() == "anthracnose":
            final_label = "Anthracnose"
        elif disease_class.lower() == "healthy":
            final_label = "Healthy"
        else:
            final_label = "Non-anthracnose"

        print(f"Final Classification : {final_label}", file=sys.stderr)

        if confidence is not None:
            print(f"Confidence Level  : {confidence * 100:.2f}%", file=sys.stderr)
        else:
            print("Confidence Level  : N/A", file=sys.stderr)

        # Severity (only if diseased)
        analysis = results.get("analysis", None)
        if analysis and isinstance(analysis, dict):
            severity = analysis.get("severity_percent", None)
            level = analysis.get("severity_level", None)

            if severity is not None:
                print(f"Severity Percent  : {severity:.2f}%", file=sys.stderr)
            else:
                print("Severity Percent  : N/A", file=sys.stderr)

            if level is not None:
                print(f"Severity Level    : {level}", file=sys.stderr)
            else:
                print("Severity Level    : N/A", file=sys.stderr)
        else:
            print("Severity Percent  : 0% (Healthy or No lesions)", file=sys.stderr)
            print("Severity Level    : None / Healthy", file=sys.stderr)

        print("==========================\n", file=sys.stderr)
        
        # Output final JSON to stdout for parent process to read
        print(json.dumps(results), flush=True)

    finally:
        GPIO.output(CONFIG["light_pin"], GPIO.HIGH)
        GPIO.output(CONFIG["enable_pin"], GPIO.HIGH)
        picam2.stop()
        GPIO.cleanup()
