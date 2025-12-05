"""
Raspberry Pi Hardware Pipeline
Wrapper for Kivy integration
"""

import RPi.GPIO as GPIO
import time
from picamera2 import Picamera2
import cv2
import numpy as np
import os
import json
import subprocess
from datetime import datetime
from PIL import Image, ImageOps


# Suppress ONNX warnings
os.environ["ORT_LOG_SEVERITY_LEVEL"] = "3"

# Try to import analyze_leaf
try:
    from analyze_leaf import analyze_leaf
except ImportError:
    analyze_leaf = None


class RPiPipeline:
    """
    Raspberry Pi hardware pipeline for mango leaf disease detection.
    Integrates motor control, camera capture, stitching, and analysis.
    """

    def __init__(self, config=None, callback=None):
        """
        Initialize pipeline with configuration and progress callback.

        Args:
            config: Optional config dict to override defaults
            callback: Progress callback function(phase: str, data: dict) -> bool
                     Returns False to cancel operation
        """
        self.config = self._get_config(config)
        self.callback = callback
        self.cancel_requested = False
        self.current_pos = 0

        self.results = {
            "timestamp": datetime.now().isoformat(),
            "timings": {},
            "classification": None,
            "analysis": None,
            "errors": [],
            "status": "initializing"
        }

        # Initialize hardware
        self._init_gpio()
        self._init_camera()

    def _get_config(self, custom_config):
        """Get configuration with defaults"""
        config = {
            "model_path": "/home/kennethbinasa/kivy_v1/ml/resnet_leafdisease_datasetresized.onnx",
            "python_310_path": "/home/kennethbinasa/onnx_venv/bin/python",
            "python_313_path": "/home/kennethbinasa/system_venv/bin/python",
            "remove_bg_path": "/home/kennethbinasa/kivy_v1/kivy-lcd-app/app/core/remove_bg.py",
            "classify_leaf_path": "/home/kennethbinasa/kivy_v1/kivy-lcd-app/app/core/classify_leaf.py",
            "input_image_path": "output_image_original.png",

            # GPIO Pins
            "dir_pin": 5,
            "step_pin": 12,
            "enable_pin": 6,
            "light_pin": 13,
            "ir_pin": 26,

            # Motion parameters
            "max_steps": 19322,
            "abs_positions": [0, 6453, 12956, 19459],
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
            "output_stitched": "full_leaf_stitched.jpg",
            "output_reduced": "output_image_reduced.png",
            "output_json": "scan_results.json"
        }

        if custom_config:
            config.update(custom_config)

        return config

    def _init_gpio(self):
        """Initialize GPIO pins"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.config["dir_pin"], GPIO.OUT)
        GPIO.setup(self.config["step_pin"], GPIO.OUT)
        GPIO.setup(self.config["enable_pin"], GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(self.config["light_pin"], GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(self.config["ir_pin"], GPIO.IN)

    def _init_camera(self):
        """Initialize camera with settings"""
        self.picam2 = Picamera2()
        self.picam2.configure(self.picam2.create_still_configuration(
            main={"size": self.config["camera_size"]}
        ))
        self.picam2.start()
        time.sleep(0.5)
        self.picam2.set_controls({"AfMode": 0, "LensPosition": 9})

        # Camera warm-up
        GPIO.output(self.config["light_pin"], GPIO.LOW)
        self.picam2.set_controls({"AeEnable": True, "AwbEnable": True})
        time.sleep(3)
        self.picam2.set_controls({"AeEnable": False, "AwbEnable": False})
        GPIO.output(self.config["light_pin"], GPIO.HIGH)

    def _progress(self, phase: str, data: dict = None) -> bool:
        """
        Report progress to callback.

        Returns:
            True to continue, False to cancel
        """
        if self.cancel_requested:
            return False

        if self.callback:
            data = data or {}
            return self.callback(phase, data) != False

        return True

    def cancel(self):
        """Request cancellation of pipeline"""
        self.cancel_requested = True

    # ============================================================
    # MOTOR CONTROL
    # ============================================================

    def _pulse_motor(self, freq, steps):
        """Execute motor steps at specified frequency"""
        delay = 1 / freq / 2
        GPIO.output(self.config["enable_pin"], GPIO.LOW)
        for _ in range(steps):
            if self.cancel_requested:
                break
            GPIO.output(self.config["step_pin"], GPIO.HIGH)
            time.sleep(delay)
            GPIO.output(self.config["step_pin"], GPIO.LOW)
            time.sleep(delay)
        GPIO.output(self.config["enable_pin"], GPIO.HIGH)

    def _move_steps(self, steps, direction):
        """Move motor specified number of steps"""
        GPIO.output(self.config["dir_pin"], direction)
        self._pulse_motor(self.config["max_freq"], steps)
        self.current_pos += steps if direction == GPIO.HIGH else -steps

    def _move_to_sensor(self, direction):
        """Move until IR sensor is triggered"""
        GPIO.output(self.config["dir_pin"], direction)
        delay = 1 / self.config["max_freq"] / 2
        step_count = 0
        GPIO.output(self.config["enable_pin"], GPIO.LOW)

        while GPIO.input(self.config["ir_pin"]) != GPIO.HIGH:
            if self.cancel_requested:
                break
            GPIO.output(self.config["step_pin"], GPIO.HIGH)
            time.sleep(delay)
            GPIO.output(self.config["step_pin"], GPIO.LOW)
            time.sleep(delay)
            step_count += 1

        GPIO.output(self.config["enable_pin"], GPIO.HIGH)
        return step_count

    def _home_motor(self, retries=2):
        """Home motor to IR sensor position"""
        if not self._progress("homing", {"pct": 0}):
            return False

        for attempt in range(retries):
            if self.cancel_requested:
                return False

            if GPIO.input(self.config["ir_pin"]) == GPIO.HIGH:
                self.current_pos = 0
                return True

            self._move_to_sensor(GPIO.LOW)
            time.sleep(0.5)

            if GPIO.input(self.config["ir_pin"]) == GPIO.HIGH:
                self.current_pos = 0
                return True

        self.results["errors"].append("Homing failed after retries")
        self._progress("error", {"message": "Homing failed", "pct": 0})
        return False

    # ============================================================
    # IMAGE CAPTURE
    # ============================================================

    def _capture_image(self, frame_num):
        """Capture single frame"""
        if not self._progress("capturing", {
            "frame_index": frame_num + 1,
            "total_frames": len(self.config["abs_positions"]),
            "pct": (frame_num / len(self.config["abs_positions"])) * 40 + 10
        }):
            return None

        filename = f"frame_{frame_num:02d}.jpg"
        GPIO.output(self.config["light_pin"], GPIO.LOW)
        time.sleep(0.5)
        self.picam2.capture_file(filename)
        GPIO.output(self.config["light_pin"], GPIO.HIGH)
        time.sleep(0.5)
        return filename

    # ============================================================
    # SCANNING & STITCHING
    # ============================================================

    def _scan_and_stitch(self):
        """Execute full scan and stitch images"""
        if not self._home_motor():
            return False

        # Capture all frames
        frames = []
        total_positions = len(self.config["abs_positions"])

        for frame_idx, target_pos in enumerate(self.config["abs_positions"]):
            if self.cancel_requested:
                return False

            # Position motor
            if not self._progress("positioning", {
                "frame_index": frame_idx + 1,
                "total_frames": total_positions,
                "pct": (frame_idx / total_positions) * 10 + 5
            }):
                return False

            direction = GPIO.HIGH if target_pos > self.current_pos else GPIO.LOW
            steps = max(abs(target_pos - self.current_pos) - self.config["step_reduction"], 0)
            self._move_steps(steps, direction)

            # Capture frame
            frame_file = self._capture_image(frame_idx)
            if frame_file:
                frames.append(frame_file)

        # Stitch images
        if not self._progress("stitching", {"pct": 50}):
            return False

        images = [cv2.imread(f) for f in frames]

        if any(img is None for img in images):
            self.results["errors"].append("Failed to load captured frames")
            self._progress("error", {"message": "Frame load failed", "pct": 50})
            return False

        # Crop frames
        for i in range(1, 4):
            h = images[i].shape[0]
            crop_amt = min(self.config["crop_top_px"][i], h - 1)
            images[i] = images[i][crop_amt:, :].copy()

        # Stitch
        width = max(img.shape[1] for img in images)
        total_height = sum(img.shape[0] for img in images)
        stitched = np.zeros((total_height, width, 3), dtype=np.uint8)

        current_y = 0
        for img, shift in zip(images, self.config["left_shifts"]):
            h, w = img.shape[:2]
            src_x_start = max(0, -shift)
            src_x_end = w
            x_start = max(0, shift)
            width_to_paste = src_x_end - src_x_start
            stitched[current_y:current_y + h, x_start:x_start + width_to_paste] = img[:, src_x_start:src_x_end]
            current_y += h

        cv2.imwrite(self.config["output_stitched"], stitched)
        return True

    # ============================================================
    # IMAGE PROCESSING
    # ============================================================

    def _process_leaf_image(self):
        """Remove background and prepare image"""
        if not self._progress("processing", {"pct": 60}):
            return False

        try:
            # 1. Call REMBG via subprocess
            stitched = self.config["output_stitched"]
            no_bg_path = "temp_no_bg.png"

            result = subprocess.run(
                [
                    self.config["python_310_path"],
                    self.config["remove_bg_path"],
                    stitched,
                    no_bg_path
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=60
            )

            if result.returncode != 0:
                self.results["errors"].append(
                    f"REMBG subprocess failed: {result.stderr}"
                )
                self._progress("error", {"message": "Background removal failed"})
                return False

            # 2. Load background-removed image
            img_pil = Image.open(no_bg_path).convert("RGBA")

            # 3. Create white background
            background = Image.new("RGB", img_pil.size, (255, 255, 255))
            background.paste(img_pil, mask=img_pil.split()[3])

            # ---- Continue processing ----
            img_cv = cv2.cvtColor(np.array(background), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            _, leaf_mask = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY_INV)

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            leaf_mask = cv2.morphologyEx(leaf_mask, cv2.MORPH_CLOSE, kernel)
            leaf_mask = cv2.morphologyEx(leaf_mask, cv2.MORPH_OPEN, kernel)

            contours, _ = cv2.findContours(
                leaf_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            if not contours:
                self.results["errors"].append("No leaf detected in image")
                self._progress("error", {"message": "No leaf detected", "pct": 60})
                return False

            # Crop leaf
            leaf_contour = max(contours, key=cv2.contourArea)
            x, y, w_crop, h_crop = cv2.boundingRect(leaf_contour)
            cropped_leaf = img_cv[y:y + h_crop, x:x + w_crop]

            # Save original
            Image.fromarray(
                cv2.cvtColor(cropped_leaf, cv2.COLOR_BGR2RGB)
            ).save(self.config["input_image_path"])

            # Resize and pad
            img_final = Image.fromarray(
                cv2.cvtColor(cropped_leaf, cv2.COLOR_BGR2RGB)
            )

            img_ratio = img_final.width / img_final.height
            target_ratio = self.config["target_width"] / self.config["target_height"]

            if img_ratio > target_ratio:
                new_width = self.config["target_width"]
                new_height = int(self.config["target_width"] / img_ratio)
            else:
                new_height = self.config["target_height"]
                new_width = int(self.config["target_height"] * img_ratio)

            img_resized = img_final.resize(
                (new_width, new_height),
                Image.Resampling.LANCZOS
            )

            img_final_padded = ImageOps.pad(
                img_resized,
                (self.config["target_width"], self.config["target_height"]),
                color="white"
            )

            img_final_padded.save(self.config["output_reduced"])
            return True

        except Exception as e:
            self.results["errors"].append(f"Processing error: {str(e)}")
            self._progress("error", {"message": str(e), "pct": 60})
            return False

    # ============================================================
    # CLASSIFICATION & ANALYSIS
    # ============================================================

    def _classify_leaf(self):
        """Run classification"""
        if not self._progress("classifying", {"pct": 75}):
            return None

        try:
            result = subprocess.run(
                [self.config["python_310_path"], self.config["classify_leaf_path"],
                 self.config["input_image_path"], self.config["model_path"]],
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
            return json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            self.results["errors"].append("Classification timeout")
            return {"error": "timeout"}
        except subprocess.CalledProcessError as e:
            self.results["errors"].append(f"Classification failed: {e.stderr}")
            return {"error": e.stderr}
        except json.JSONDecodeError:
            self.results["errors"].append("Failed to parse classification result")
            return {"error": "invalid_json"}

    def _analyze_leaf_features(self):
        """Run detailed leaf analysis"""
        if analyze_leaf is None:
            return None

        if not self._progress("analyzing", {"pct": 85}):
            return None

        try:
            leaf_id = int(datetime.now().timestamp())
            record, vis_img = analyze_leaf(
                self.config["input_image_path"],
                leaf_id=leaf_id,
                save_to_csv=True,
                save_json=True
            )

            if vis_img is not None:
                cv2.imwrite(f"leaf_analysis_{leaf_id}.jpg", vis_img)

            return record
        except Exception as e:
            self.results["errors"].append(f"Analysis error: {str(e)}")
            return None

    # ============================================================
    # MAIN PIPELINE
    # ============================================================

    def run_pipeline(self):
        """
        Execute complete detection pipeline.

        Returns:
            (success: bool, results: dict)
        """
        start_time = time.time()

        try:
            # Stage 1: Homing
            t0 = time.time()
            if not self._home_motor():
                self.results["status"] = "homing_failed"
            self.results["timings"]["homing_initial"] = time.time() - t0

            # Stage 2: Scan and stitch
            t0 = time.time()
            if not self._scan_and_stitch():
                self.results["status"] = "scan_failed"
                return False, self.results
            self.results["timings"]["scan_stitch"] = time.time() - t0

            # Stage 3: Process image
            t0 = time.time()
            if not self._process_leaf_image():
                self.results["status"] = "processing_failed"
                return False, self.results
            self.results["timings"]["processing"] = time.time() - t0

            # Stage 4: Home motor (parallel with classification preparation)
            self._home_motor()
            GPIO.output(self.config["light_pin"], GPIO.HIGH)
            GPIO.output(self.config["enable_pin"], GPIO.HIGH)

            # Stage 5: Classification
            t0 = time.time()
            classification = self._classify_leaf()
            if classification is None or "error" in classification:
                self.results["status"] = "classification_failed"
                return False, self.results
            self.results["timings"]["classification"] = time.time() - t0
            self.results["classification"] = classification

            # Stage 6: Detailed analysis (if diseased)
            if classification.get("class") != "Healthy":
                t0 = time.time()
                analysis = self._analyze_leaf_features()
                self.results["timings"]["analysis"] = time.time() - t0
                self.results["analysis"] = analysis

            self.results["timings"]["total"] = time.time() - start_time
            self.results["status"] = "success"
            self.results["output_image"] = self.config["output_reduced"]

            # Save results
            with open(self.config["output_json"], "w") as f:
                json.dump(self.results, f, indent=2)

            self._progress("complete", {"pct": 100})

            return True, self.results

        except Exception as e:
            self.results["status"] = "error"
            self.results["errors"].append(f"Pipeline error: {str(e)}")
            self.results["timings"]["total"] = time.time() - start_time
            self._progress("error", {"message": str(e), "pct": 0})
            return False, self.results

    def cleanup(self):
        """Clean up hardware resources"""
        try:
            GPIO.output(self.config["light_pin"], GPIO.HIGH)
            GPIO.output(self.config["enable_pin"], GPIO.HIGH)
            # GPIO.cleanup()
        except Exception as e:
            print(f"Cleanup error: {e}")
    
    # def __del__(self):
        # ""Destructor - ensure cleanup"""
        # self.cleanup()
