"""
full_code_cleaned.py  (refactored as persistent pipeline)
==========================================================
Key changes:
  - Everything is inside ScanPipeline class — singleton
  - Camera, GPIO, model client initialized ONCE on first instantiation
  - run_pipeline() can be called repeatedly without restarting anything
  - Cancel flag checked after every blocking step so cancellation is fast
  - Recoverable errors (no leaf, bg removal) reported distinctly
"""

import os
import sys
import time
import json
import sqlite3
import threading
import cv2
import numpy as np
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageOps

import RPi.GPIO as GPIO
from picamera2 import Picamera2

os.environ["ORT_LOG_SEVERITY_LEVEL"] = "4"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# ── Model client ──────────────────────────────────────────────────────────────
sys.path.insert(0, "/home/kennethbinasa/kivy_v1/kivy-lcd-app")
from model_client import ModelClient

# ── Leaf analyser ─────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))
from analyze_leaf import analyze_leaf


class ScanPipeline:
    """
    Persistent scan pipeline. Instantiate once at app startup.
    Call run_pipeline(on_phase, cancel_flag) for each scan.
    Camera and models stay loaded between scans.
    """

    _instance = None  # Singleton

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        print("=== ScanPipeline Initializing ===", file=sys.stderr)

        # ── Paths ─────────────────────────────────────────────────────────────
        self.script_dir   = SCRIPT_DIR
        self.project_root = SCRIPT_DIR.parent.parent.parent
        self.data_dir     = self.project_root / "data"
        self.kivy_app_dir = self.project_root / "kivy-lcd-app"
        self.db_path      = self.kivy_app_dir / "mangofy.db"
        self.model_path   = SCRIPT_DIR / "resnet_leafdisease_datasetresized.onnx"

        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")

        # ── Config ────────────────────────────────────────────────────────────
        self.config = {
            "dir_pin":          5,
            "step_pin":         12,
            "enable_pin":       6,
            "light_pin":        13,
            "ir_pin":           26,
            "max_steps":        19322,
            "abs_positions":    [0, 6453, 12956, 19359],
            "max_freq":         8000,
            "step_distance_mm": 0.01,
            "step_reduction":   150,
            "camera_size":      (2304, 1296),
            "target_width":     480,
            "target_height":    800,
            # ~ "crop_top_px":  [0, 268, 0, 0],
            # ~ "left_shifts":  [0, -21, -27, -44],
            "crop_top_px":  [0, 152, 9, 4],
            "left_shifts":  [0, -29, -39, -56],
        }

        # ── GPIO ──────────────────────────────────────────────────────────────
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.config["dir_pin"],    GPIO.OUT)
        GPIO.setup(self.config["step_pin"],   GPIO.OUT)
        GPIO.setup(self.config["enable_pin"], GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(self.config["light_pin"],  GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(self.config["ir_pin"],     GPIO.IN)
        print("✓ GPIO initialized", file=sys.stderr)

        # ── Camera ────────────────────────────────────────────────────────────
        self.picam2 = Picamera2()
        self.picam2.configure(
            self.picam2.create_still_configuration(
                main={"size": self.config["camera_size"]}
            )
        )
        self.picam2.start()
        time.sleep(0.5)
        self.picam2.set_controls({"AfMode": 0, "LensPosition": 9})

        # One-time AE/AWB lock at startup
        GPIO.output(self.config["light_pin"], GPIO.LOW)
        self.picam2.set_controls({"AeEnable": True, "AwbEnable": True})
        print("✓ Camera warming up (one-time)...", file=sys.stderr)
        time.sleep(3)

        metadata = self.picam2.capture_metadata()
        self.locked_exposure = {
            "ExposureTime": metadata.get("ExposureTime"),
            "AnalogueGain": metadata.get("AnalogueGain"),
            "ColourGains":  metadata.get("ColourGains"),
        }
        self.picam2.set_controls({
            "AeEnable":     False,
            "AwbEnable":    False,
            "ExposureTime": self.locked_exposure["ExposureTime"],
            "AnalogueGain": self.locked_exposure["AnalogueGain"],
            "ColourGains":  self.locked_exposure["ColourGains"],
        })
        GPIO.output(self.config["light_pin"], GPIO.HIGH)
        print(f"✓ Exposure locked: {self.locked_exposure}", file=sys.stderr)

        # ── Model client ──────────────────────────────────────────────────────
        self.model_client = ModelClient()
        if not self.model_client.ping():
            raise RuntimeError(
                "Model server is not responding. Is model_server.py running?"
            )
        print("✓ Model server connected", file=sys.stderr)

        self.current_pos  = 0
        self._run_lock    = threading.Lock()   # prevents overlapping pipeline runs
        self._initialized = True
        print("=== ScanPipeline Ready ===", file=sys.stderr)

    # =========================================================================
    # PUBLIC: run a full scan
    # =========================================================================
    def run_pipeline(self, on_phase=None, cancel_flag=None):
        """
        Run a full scan. Camera and models stay warm between calls.

        on_phase(phase, pct, message, reduced_image) — UI update callback.
        cancel_flag — a callable that returns True if the user cancelled.
                      Checked after every blocking step.
        Returns the results dict.
        """

        if not self._run_lock.acquire(blocking=False):
            print("⚠ Pipeline already running — ignoring duplicate start", file=sys.stderr)
            return {"status": "busy", "errors": ["Pipeline already running"]}

        # ── Freeze the cancel state into a per-run Event ──────────────────────
        # This makes cancellation immune to the caller resetting the shared flag
        # between scans. The old run will always see its own _cancel_event, which
        # is never reset externally.
        _cancel_event = threading.Event()

        def is_cancelled():
            # Poll the live flag; if it fired, latch it permanently into the event.
            # This survives the caller resetting their flag for the next scan.
            if cancel_flag is not None and cancel_flag():
                _cancel_event.set()
            return _cancel_event.is_set()

        # Fresh scan directory per scan
        scan_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        scan_dir = self.data_dir / "scans" / f"scan_{scan_timestamp}"
        scan_dir.mkdir(parents=True, exist_ok=True)

        paths = {
            "scan_dir":    scan_dir,
            "input_image": scan_dir / "output_image_original.png",
            "stitched":    scan_dir / "full_leaf_stitched.jpg",
            "reduced":     scan_dir / "output_image_reduced.png",
            "bg_removed":  scan_dir / "output_bg_removed.png",
            "output_json": scan_dir / "scan_results.json",
        }

        results = {
            "timestamp":      datetime.now().isoformat(),
            "timings":        {},
            "classification": None,
            "analysis":       None,
            "errors":         [],
            "status":         "unknown",
        }

        def report(phase, pct=0, message=None, reduced_image=None):
            print(f"[Pipeline] {phase} {pct}% {message or ''}", file=sys.stderr)
            if on_phase:
                on_phase(phase, pct, message, reduced_image)

        start = time.time()
        try:
            # ── Home ──────────────────────────────────────────────────────────
            report("homing", 0)
            self._home_motor()
            #if not self._home_motor():
               # results["errors"].append("Homing failed")
                #results["status"] = "error"
               #return results

            if is_cancelled():
                results["status"] = "cancelled"
                return results

            # ── Scan & stitch ─────────────────────────────────────────────────
            report("scanning", 0)
            if not self._scan_and_stitch(paths, report, is_cancelled):
                results["status"] = "cancelled" if is_cancelled() else "error"
                return results

            if is_cancelled():
                results["status"] = "cancelled"
                return results

            # ── Home again (background) ───────────────────────────────────────
            home_thread = threading.Thread(target=self._home_motor_background, daemon=True)
            home_thread.start()

            if is_cancelled():
                results["status"] = "cancelled"
                return results

            # ~ # ── Check for leaf before expensive bg removal ────────────────────
            # ~ report("processing", 5, message="Checking for leaf...")
            # ~ if not self._has_leaf(paths["stitched"]):
                # ~ results["errors"].append("no_leaf_detected")
                # ~ results["status"] = "no_leaf"
                # ~ report("error", message="No leaf detected — please place a leaf and retry")
                # ~ return results

            # ── Process image ─────────────────────────────────────────────────
            report("processing", 0)
            if not self._process_leaf_image(paths, results, report, is_cancelled):
                # Status already set inside (error or cancelled)
                if results["status"] == "unknown":
                    results["status"] = "error"
                return results

            if is_cancelled():
                results["status"] = "cancelled"
                return results

            # ── Classify ──────────────────────────────────────────────────────
            report("classifying", 0)
            classification = self._classify(paths, results, report)
            results["classification"] = classification

            if is_cancelled():
                results["status"] = "cancelled"
                return results

            # ── Analyse (skip if healthy) ─────────────────────────────────────
            if "error" not in classification and classification.get("class") != "Healthy":
                report("analyzing", 0)
                results["analysis"] = self._analyze(paths, results, report, scan_dir)

            if is_cancelled():
                results["status"] = "cancelled"
                return results

            results["timings"]["total"] = time.time() - start
            results["status"] = "success"

            # ── Save to DB ────────────────────────────────────────────────────
            scan_id = self._save_to_database(paths, results)
            results["database_id"] = scan_id
            results["reduced_image"] = str(paths["reduced"])

            # ── Save JSON ─────────────────────────────────────────────────────
            with open(str(paths["output_json"]), "w") as f:
                json.dump(results, f, indent=2)

            report("complete", 100, reduced_image=str(paths["reduced"]))
            return results

        except Exception as e:
            import traceback
            traceback.print_exc()
            results["errors"].append(str(e))
            results["status"] = "error"
            results["timings"]["total"] = time.time() - start
            report("error", 0, message=str(e))
            return results

        finally:
            self._run_lock.release()

    # =========================================================================
    # MOTOR
    # =========================================================================
    def _pulse_motor(self, freq, steps):
        delay = 1 / freq / 2
        GPIO.output(self.config["enable_pin"], GPIO.LOW)
        for _ in range(steps):
            GPIO.output(self.config["step_pin"], GPIO.HIGH)
            time.sleep(delay)
            GPIO.output(self.config["step_pin"], GPIO.LOW)
            time.sleep(delay)
        GPIO.output(self.config["enable_pin"], GPIO.HIGH)

    def _move_steps(self, steps, direction):
        GPIO.output(self.config["dir_pin"], direction)
        self._pulse_motor(self.config["max_freq"], steps)
        self.current_pos += steps if direction == GPIO.HIGH else -steps

    def _move_to_sensor(self, direction):
        GPIO.output(self.config["dir_pin"], direction)
        delay = 1 / self.config["max_freq"] / 2
        GPIO.output(self.config["enable_pin"], GPIO.LOW)
        while GPIO.input(self.config["ir_pin"]) != GPIO.HIGH:
            GPIO.output(self.config["step_pin"], GPIO.HIGH)
            time.sleep(delay)
            GPIO.output(self.config["step_pin"], GPIO.LOW)
            time.sleep(delay)
        GPIO.output(self.config["enable_pin"], GPIO.HIGH)

    def _home_motor(self, retries=2):
        for _ in range(retries):
            if GPIO.input(self.config["ir_pin"]) == GPIO.HIGH:
                self.current_pos = 0
                return True
            self._move_to_sensor(GPIO.LOW)
            time.sleep(0.5)
            if GPIO.input(self.config["ir_pin"]) == GPIO.HIGH:
                self.current_pos = 0
                return True
        return False

    # =========================================================================
    # CAPTURE
    # =========================================================================
    def _capture_image(self, frame_num, scan_dir):
        filename = str(scan_dir / f"frame_{frame_num:02d}.jpg")
        GPIO.output(self.config["light_pin"], GPIO.LOW)
        self.picam2.set_controls({
            "AeEnable":     False,
            "AwbEnable":    False,
            "ExposureTime": self.locked_exposure["ExposureTime"],
            "AnalogueGain": self.locked_exposure["AnalogueGain"],
            "ColourGains":  self.locked_exposure["ColourGains"],
        })
        time.sleep(0.4)
        self.picam2.capture_file(filename)
        GPIO.output(self.config["light_pin"], GPIO.HIGH)
        time.sleep(0.4)
        return filename

    # =========================================================================
    # SCAN & STITCH
    # =========================================================================
    def _scan_and_stitch(self, paths, report, is_cancelled):
        n = len(self.config["abs_positions"])
        for frame_idx, target_pos in enumerate(self.config["abs_positions"]):
            if is_cancelled():
                return False

            direction = GPIO.HIGH if target_pos > self.current_pos else GPIO.LOW
            steps = max(
                abs(target_pos - self.current_pos) - self.config["step_reduction"], 0
            )
            self._move_steps(steps, direction)
            self._capture_image(frame_idx, paths["scan_dir"])
            report("capturing", int((frame_idx + 1) / n * 100),
                   message=f"Frame {frame_idx + 1}/{n}")

        if is_cancelled():
            return False

        frames = [str(paths["scan_dir"] / f"frame_{i:02d}.jpg") for i in range(n)]
        images = [cv2.imread(f) for f in frames]

        failed = [f for f, img in zip(frames, images) if img is None]
        if failed:
            print(f"✗ Failed to load: {failed}", file=sys.stderr)
            return False

        for i in range(1, 4):
            h        = images[i].shape[0]
            crop_amt = min(self.config["crop_top_px"][i], h - 1)
            images[i] = images[i][crop_amt:, :].copy()

        width        = max(img.shape[1] for img in images)
        total_height = sum(img.shape[0] for img in images)
        stitched     = np.zeros((total_height, width, 3), dtype=np.uint8)
        current_y    = 0
        for img, shift in zip(images, self.config["left_shifts"]):
            h, w        = img.shape[:2]
            src_x_start = max(0, -shift)
            x_start     = max(0,  shift)
            w_paste     = w - src_x_start
            stitched[current_y:current_y + h, x_start:x_start + w_paste] = \
                img[:, src_x_start:]
            current_y += h

        cv2.imwrite(str(paths["stitched"]), stitched)
        report("stitching", 100)
        return True

    # =========================================================================
    # BACKGROUND HOMING (jitter-tolerant, for use during image processing)
    # =========================================================================
    def _home_motor_background(self):
        """Slower, jitter-tolerant homing for running in a background thread."""
        GPIO.output(self.config["dir_pin"], GPIO.LOW)
        delay = 1 / 4000 / 2  # half the normal freq — tolerant of sleep jitter
        GPIO.output(self.config["enable_pin"], GPIO.LOW)
        while GPIO.input(self.config["ir_pin"]) != GPIO.HIGH:
            GPIO.output(self.config["step_pin"], GPIO.HIGH)
            time.sleep(delay)
            GPIO.output(self.config["step_pin"], GPIO.LOW)
            time.sleep(delay)
        GPIO.output(self.config["enable_pin"], GPIO.HIGH)
        self.current_pos = 0
        print("✓ Background homing complete", file=sys.stderr)

    # =========================================================================
    # LEAF DETECTION
    # =========================================================================
    def _has_leaf(self, image_path, min_area_fraction=0.02):
        """
        Returns True if a green leaf is detected in the stitched image.
        Uses HSV green masking — fast, no model needed.
        min_area_fraction — leaf must cover at least this fraction of the image.
        """
        img = cv2.imread(str(image_path))
        if img is None:
            return False

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        lower_green = np.array([25, 40, 40])
        upper_green = np.array([90, 255, 255])
        mask = cv2.inRange(hsv, lower_green, upper_green)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        total_pixels = img.shape[0] * img.shape[1]
        green_pixels = cv2.countNonZero(mask)
        fraction = green_pixels / total_pixels

        print(f"[LeafCheck] green fraction: {fraction:.3f}", file=sys.stderr)
        return fraction >= min_area_fraction

    # =========================================================================
    # ENHANCE LEAF IMAGE (applied to bg-removed image before cropping)
    # =========================================================================
    def _enhance_leaf(self, img: np.ndarray) -> np.ndarray:
        """
        Enhancement disabled — returns image as-is.
        Re-enable individual steps here once baseline is confirmed.
        """
        return img

    # =========================================================================
    # PROCESS LEAF IMAGE
    # =========================================================================
    def _process_leaf_image(self, paths, results, report, is_cancelled):
        report("processing", 10, message="Removing background...")

        # ── Background removal — biggest blocking call ────────────────────────
        try:
            self.model_client.remove_bg(
                str(paths["stitched"]),
                str(paths["bg_removed"]),
                timeout=120.0
            )
        except Exception as e:
            results["errors"].append(f"bg_removal_failed: {e}")
            report("error", message=f"Background removal failed: {e}")
            results["status"] = "error"
            return False

        # Check cancel immediately after the long blocking call
        if is_cancelled():
            results["status"] = "cancelled"
            return False

        # ── Enhance image quality ─────────────────────────────────────────────
        report("processing", 40, message="Enhancing leaf image quality...")
        raw = cv2.imread(str(paths["bg_removed"]), cv2.IMREAD_UNCHANGED)
        if raw is not None:
            enhanced = self._enhance_leaf(raw)
            cv2.imwrite(str(paths["bg_removed"]), enhanced)
        else:
            print("⚠ Enhancement skipped — could not read bg_removed image",
                  file=sys.stderr)

        # report("processing", 50, message="Detecting leaf...")

        img_raw = cv2.imread(str(paths["bg_removed"]), cv2.IMREAD_UNCHANGED)
        if img_raw is None:
            results["errors"].append("bg_removed_unreadable")
            results["status"] = "error"
            return False

        # ── Build leaf mask ───────────────────────────────────────────────────
        # Prefer alpha channel (bg-removed PNGs are RGBA — alpha=0 is transparent bg,
        # alpha=255 is leaf). Falling back to gray threshold only if no alpha exists.
        if img_raw.ndim == 3 and img_raw.shape[2] == 4:
            # Use alpha channel directly — exact leaf mask, no false positives
            leaf_mask = img_raw[:, :, 3]
            img_cv    = img_raw[:, :, :3]  # BGR only for processing downstream
        else:
            img_cv = img_raw
            gray   = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            _, leaf_mask = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)

        kernel    = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        leaf_mask = cv2.morphologyEx(leaf_mask, cv2.MORPH_CLOSE, kernel)
        leaf_mask = cv2.morphologyEx(leaf_mask, cv2.MORPH_OPEN,  kernel)

        contours, _ = cv2.findContours(
            leaf_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        # ~ if not contours:
            # ~ # Recoverable — user can reposition leaf and try again
            # ~ results["errors"].append("no_leaf_detected")
            # ~ results["status"] = "no_leaf"
            # ~ report("error", message="No leaf detected")
            # ~ return False

        x, y, w_crop, h_crop = cv2.boundingRect(max(contours, key=cv2.contourArea))
        cropped = img_cv[y:y + h_crop, x:x + w_crop]

        Image.fromarray(cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)).save(
            str(paths["input_image"])
        )

        img_ratio    = w_crop / h_crop
        target_ratio = self.config["target_width"] / self.config["target_height"]
        if img_ratio > target_ratio:
            new_w = self.config["target_width"]
            new_h = int(self.config["target_width"] / img_ratio)
        else:
            new_h = self.config["target_height"]
            new_w = int(self.config["target_height"] * img_ratio)

        img_resized = Image.fromarray(
            cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
        ).resize((new_w, new_h), Image.Resampling.LANCZOS)
        img_padded = ImageOps.pad(
            img_resized,
            (self.config["target_width"], self.config["target_height"]),
            color="white",
            centering=(0.5, 0.5),   # explicitly center — older Pillow defaults to (0,0)
        )
        img_padded.save(str(paths["reduced"]))

        report("processing", 100, reduced_image=str(paths["reduced"]))
        return True

    # =========================================================================
    # CLASSIFY
    # =========================================================================
    def _classify(self, paths, results, report):
        try:
            data = self.model_client.classify(str(paths["input_image"]), timeout=30.0)
            report("classifying", 100)
            return data
        except Exception as e:
            results["errors"].append(str(e))
            report("error", message=f"Classification failed: {e}")
            return {"error": str(e)}

    # =========================================================================
    # ANALYSE
    # =========================================================================
    def _analyze(self, paths, results, report, scan_dir):
        try:
            leaf_id = int(datetime.now().timestamp())

            # ── FIX #10 + #11: pass scan_dir and the alpha mask ───────────────
            # Load the bg-removed PNG to extract the alpha channel as leaf mask.
            # This is passed into analyze_leaf() so it skips HSV green segmentation
            # (which misses brown/diseased areas) and uses the accurate bg-removal
            # silhouette instead.
            leaf_mask_override = None
            bg_removed = cv2.imread(str(paths["bg_removed"]), cv2.IMREAD_UNCHANGED)
            if bg_removed is not None and bg_removed.ndim == 3 and bg_removed.shape[2] == 4:
                leaf_mask_override = bg_removed[:, :, 3]

            record, _ = analyze_leaf(
                str(paths["input_image"]),
                leaf_id=leaf_id,
                save_to_csv=True,
                save_json=True,
                scan_dir=paths["scan_dir"],          # fix #6: save to scan folder
                leaf_mask_input=leaf_mask_override,  # fix #2/#11: use alpha silhouette
            )
            report("analyzing", 100)
            return record
        except Exception as e:
            results["errors"].append(str(e))
            report("error", message=f"Analysis failed: {e}")
            return None

    # =========================================================================
    # DATABASE
    # =========================================================================
    def _save_to_database(self, paths, results):
        try:
            conn = sqlite3.connect(str(self.db_path))
            cur  = conn.cursor()

            classification = results.get("classification", {}) or {}
            analysis       = results.get("analysis", {})       or {}

            disease_class = classification.get("class", "Unknown")
            confidence    = classification.get("confidence", 0.0)
            all_preds     = classification.get("probabilities", {})

            disease_map = {
                "Anthracnose": 1, "Healthy": None, "Bacterial Canker": 2,
                "Cutting Weevil": 3, "Powdery Mildew": 4, "Sooty Mould": 5,
                "Die Back": 6, "Gall Midge": 7,
            }
            disease_id = disease_map.get(disease_class)

            severity_pct   = analysis.get("severity_percent", 0.0)  # FIX #1: was "severity_percent" mismatch
            severity_level = analysis.get("severity_level",   "None") # FIX #5: now populated by analyze_leaf
            severity_map   = {"None": None, "Low": 1, "Moderate": 2, "High": 3}
            severity_id    = severity_map.get(severity_level)

            scan_dir_name  = paths["scan_dir"].name
            image_path     = (
                f"../data/scans/{scan_dir_name}/{paths['reduced'].name}"
                if paths["reduced"].exists() else None
            )
            thumbnail_path = (
                f"../data/scans/{scan_dir_name}/{paths['stitched'].name}"
                if paths["stitched"].exists() else image_path
            )
            json_path = (
                f"../data/scans/{scan_dir_name}/{paths['output_json'].name}"
                if paths["output_json"].exists() else None
            )

            notes = f"Scan: {scan_dir_name} | Disease: {disease_class}"
            if severity_level != "None":
                notes += f" | Severity: {severity_level} ({severity_pct:.1f}%)"

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
                    exg_mean, grvi_mean,
                    leaf_solidity, leaf_circularity, leaf_aspect_ratio,
                    damage_pct_inpaint,
                    lesion_glcm_contrast, lesion_glcm_dissimilarity,
                    lesion_glcm_energy, lesion_glcm_homogeneity, lesion_glcm_correlation,
                    image_path, thumbnail_path, json_path, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                None, disease_id, severity_id,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                results.get("timings", {}).get("total", 0.0),
                results.get("status", "unknown"),
                disease_class, confidence,
                all_preds.get("Anthracnose",      0.0),
                all_preds.get("Healthy",          0.0),
                all_preds.get("Bacterial Canker", 0.0),
                all_preds.get("Cutting Weevil",   0.0),
                all_preds.get("Powdery Mildew",   0.0),
                all_preds.get("Sooty Mould",      0.0),
                severity_pct, severity_level,
                analysis.get("leaf_area_cm2",       0.0),
                analysis.get("lesion_area_cm2",     0.0),
                analysis.get("lesion_count",        0),
                analysis.get("mean_lesion_size_px", 0.0),
                analysis.get("leaf_mean_r",  0.0),
                analysis.get("leaf_mean_g",  0.0),
                analysis.get("leaf_mean_b",  0.0),
                analysis.get("lesion_mean_r", 0.0),
                analysis.get("lesion_mean_g", 0.0),
                analysis.get("lesion_mean_b", 0.0),
                analysis.get("lesion_to_leaf_color_ratio_g", 0.0),
                analysis.get("exg_mean",            0.0),
                analysis.get("grvi_mean",           0.0),  # was ndvi_proxy_mean
                analysis.get("leaf_solidity",       0.0),
                analysis.get("leaf_circularity",    0.0),
                analysis.get("leaf_aspect_ratio",   0.0),
                analysis.get("damage_pct_inpaint",  0.0),
                analysis.get("lesion_glcm_contrast",      0.0),
                analysis.get("lesion_glcm_dissimilarity", 0.0),
                analysis.get("lesion_glcm_energy",        0.0),  # new
                analysis.get("lesion_glcm_homogeneity",   0.0),  # new
                analysis.get("lesion_glcm_correlation",   0.0),  # new
                image_path, thumbnail_path, json_path, notes
            ))
            conn.commit()
            scan_id = cur.lastrowid
            conn.close()
            print(f"✓ Saved to database (scan_id: {scan_id})", file=sys.stderr)
            return scan_id

        except Exception as e:
            print(f"✗ Database save failed: {e}", file=sys.stderr)
            results["errors"].append(f"Database error: {e}")
            return None

    # =========================================================================
    # CLEANUP (call on app exit)
    # =========================================================================
    def cleanup(self):
        try:
            GPIO.output(self.config["light_pin"],  GPIO.HIGH)
            GPIO.output(self.config["enable_pin"], GPIO.HIGH)
            self.picam2.stop()
            GPIO.cleanup()
            print("✓ ScanPipeline cleaned up", file=sys.stderr)
        except Exception as e:
            print(f"Cleanup error: {e}", file=sys.stderr)
