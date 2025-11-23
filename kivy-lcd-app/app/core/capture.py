import time
import os
from typing import Callable, List, Optional, Tuple
from PIL import Image, ImageEnhance, ImageOps
import numpy as np
from multiprocessing import Process, Queue

# Try to import cv2 for hardware scanning (optional)
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    print("OpenCV (cv2) not available - hardware scanning features limited")

# Try to import picamera2 for Raspberry Pi Camera Module
try:
    from picamera2 import Picamera2
    HAS_PICAMERA2 = True
except ImportError:
    HAS_PICAMERA2 = False
    print("Picamera2 not available - using fallback mode")

# Try to import rembg for background removal
try:
    from rembg import remove
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False
    print("rembg not available - background removal disabled")

# Import motor controller
try:
    from app.core.motor_controller import MotorController
    HAS_MOTOR = True
except ImportError:
    HAS_MOTOR = False
    print("Motor controller not available")


class MultiFrameCapture:
    """
    Hardware-integrated multi-frame capture pipeline for mango leaf scanning.
    
    Scanning Process:
    1. Home motor to initial position
    2. Move motor to each frame position (4 positions across 150mm)
    3. At each position: capture frame with camera
    4. Stitch frames horizontally
    5. Preprocess: crop, enhance, resize
    6. Save 3 versions: non-processed stitched, processed original, processed resized (480x800)
    
    Provides progress callbacks: callback(phase:str, frame_index:int, total_frames:int, progress_pct:float).
    """

    def __init__(self, 
                 total_frames: int = 4, 
                 retry_limit: int = 1, 
                 use_hardware: bool = True,
                 camera_resolution: Tuple[int, int] = (1640, 1232),
                 overlap_percentage: int = 15):
        """
        Initialize capture pipeline.
        
        Args:
            total_frames: Number of frames to capture and stitch (default 4)
            retry_limit: Number of retries per frame on failure
            use_hardware: Whether to use actual camera/motor (False for testing)
            camera_resolution: Camera capture resolution (width, height)
            overlap_percentage: Overlap between adjacent frames for stitching (%)
        """
        self.total_frames = total_frames
        self.retry_limit = retry_limit
        self.use_hardware = use_hardware and (HAS_PICAMERA2 or HAS_MOTOR)
        self.camera_resolution = camera_resolution
        self.overlap_pct = overlap_percentage
        
        # PDF-specific stitching parameters (vertical stitching)
        self.crop_top_px = [0, 169, 133, 120]  # Top crop per frame
        self.left_shifts = [0, -9, -13, -29]   # Horizontal shift per frame
        
        # Initialize hardware components
        self.motor = None
        self.camera = None
        
        if self.use_hardware and HAS_MOTOR:
            try:
                self.motor = MotorController(use_gpio=True)
            except Exception as e:
                print(f"Failed to initialize motor: {e}")
                self.use_hardware = False
        
        if self.use_hardware and HAS_PICAMERA2:
            try:
                self.camera = self._initialize_camera()
            except Exception as e:
                print(f"Failed to initialize camera: {e}")
                self.use_hardware = False
    
    def _initialize_camera(self):
        """
        Initialize Picamera2 with PDF specifications:
        - Resolution: 2304x1296
        - Manual focus: AfMode 0, LensPosition 9
        - Warm-up: 3 seconds with AE/AWB lock
        """
        picam2 = Picamera2()
        picam2.configure(picam2.create_still_configuration(
            main={"size": (2304, 1296)}
        ))
        picam2.start()
        time.sleep(0.5)
        
        # Set manual focus
        picam2.set_controls({"AfMode": 0, "LensPosition": 9})
        
        # Camera warm-up (with LED on if motor available)
        if self.motor:
            self.motor.led_on()
        
        picam2.set_controls({"AeEnable": True, "AwbEnable": True})
        print("⏳ Warming up camera for consistent exposure and color...")
        time.sleep(3)
        picam2.set_controls({"AeEnable": False, "AwbEnable": False})
        
        if self.motor:
            self.motor.led_off()
        
        print("✅ Camera warm-up done. Exposure and WB locked.")
        return picam2

    def _run_parallel_homing_and_preprocessing(self, stitched_path: str, output_dir: str,
                                                callback: Optional[Callable] = None) -> Optional[dict]:
        """
        Run motor homing and image preprocessing in parallel using multiprocessing.
        
        Per PDF spec: While motor returns home, simultaneously process the stitched image
        (background removal + cropping + enhancements). This reduces total scan time by ~2-3s.
        
        Args:
            stitched_path: Path to stitched image to preprocess
            output_dir: Output directory for processed images
            callback: Progress callback
        
        Returns:
            Dictionary with preprocessing outputs, or None on failure
        """
        # Wrapper functions for multiprocessing
        def homing_worker(motor, result_queue):
            """Worker process for motor homing."""
            try:
                success = motor.home_motor()
                result_queue.put(('homing', success))
            except Exception as e:
                print(f"Homing process error: {e}")
                result_queue.put(('homing', False))
        
        def preprocessing_worker(stitched_path, output_dir, result_queue):
            """Worker process for image preprocessing."""
            try:
                outputs = self._preprocess_image(stitched_path, output_dir)
                result_queue.put(('preprocessing', outputs))
            except Exception as e:
                print(f"Preprocessing process error: {e}")
                result_queue.put(('preprocessing', None))
        
        # Create result queue
        result_queue = Queue()
        
        # Create processes
        processes = []
        
        # Motor homing process
        if self.use_hardware and self.motor:
            if callback:
                callback('homing_parallel', 0, self.total_frames, 85.0)
            p_homing = Process(target=homing_worker, args=(self.motor, result_queue))
            processes.append(p_homing)
            p_homing.start()
        
        # Preprocessing process
        if callback:
            callback('preprocessing_parallel', 0, self.total_frames, 85.0)
        p_preprocessing = Process(target=preprocessing_worker, args=(stitched_path, output_dir, result_queue))
        processes.append(p_preprocessing)
        p_preprocessing.start()
        
        # Wait for both processes and collect results
        results = {}
        for _ in range(len(processes)):
            process_name, result = result_queue.get()
            results[process_name] = result
        
        # Join all processes
        for p in processes:
            p.join()
        
        # Check results
        if self.use_hardware and not results.get('homing', False):
            print("⚠ Homing failed during parallel execution")
        
        preprocessing_outputs = results.get('preprocessing')
        if not preprocessing_outputs:
            print("⚠ Preprocessing failed during parallel execution")
            return None
        
        return preprocessing_outputs

    def run(self, source_image: str, output_dir: str, 
            callback: Optional[Callable[[str, int, int, float], None]] = None) -> Optional[str]:
        """
        Execute full capture pipeline.
        
        Args:
            source_image: Fallback test image if hardware not available
            output_dir: Directory to save captured frames and stitched output
            callback: Progress callback(phase, frame_index, total_frames, progress_pct)
        
        Returns:
            Path to final processed/resized stitched image, or None on failure
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Step 1: Home motor (runs in parallel with preprocessing setup via multiprocessing)
        if self.use_hardware and self.motor:
            if callback:
                callback('homing', 0, self.total_frames, 5.0)
            
            def motor_progress(status, pct):
                if callback:
                    callback('homing', 0, self.total_frames, 5.0 + (pct * 0.10))
            
            success = self.motor.home_motor(callback=motor_progress)
            if not success:
                if callback:
                    callback('homing_failed', 0, self.total_frames, 0.0)
                return None
        
        # Step 2: Scan and capture frames
        frames = self._capture_frames(output_dir, callback)
        if not frames or len(frames) < self.total_frames:
            if callback:
                callback('capture_failed', len(frames), self.total_frames, 0.0)
            return None
        
        # Step 3: Stitch frames
        if callback:
            callback('stitching', self.total_frames, self.total_frames, 70.0)
        
        stitched_path = self._stitch_frames(frames, output_dir)
        if not stitched_path:
            if callback:
                callback('stitching_failed', self.total_frames, self.total_frames, 0.0)
            return None
        
        # Step 4: Parallel execution - Preprocess image while motor returns home
        # Per PDF spec: Run multiprocessing to save 2-3 seconds total scan time
        enable_parallel = os.getenv('MANGOFY_ENABLE_PARALLEL', 'true').lower() == 'true'
        
        if enable_parallel and self.use_hardware:
            if callback:
                callback('parallel_processing', self.total_frames, self.total_frames, 85.0)
            
            outputs = self._run_parallel_homing_and_preprocessing(stitched_path, output_dir, callback)
        else:
            # Sequential fallback (for debugging or when multiprocessing disabled)
            if callback:
                callback('preprocessing', self.total_frames, self.total_frames, 85.0)
            
            outputs = self._preprocess_image(stitched_path, output_dir)
        
        if not outputs:
            if callback:
                callback('preprocessing_failed', self.total_frames, self.total_frames, 0.0)
            return None
        
        # Analysis phase marker
        if callback:
            callback('analyzing', self.total_frames, self.total_frames, 92.0)
        
        # Final completion
        if callback:
            callback('complete', self.total_frames, self.total_frames, 100.0)
        
        # Return the processed resized version (for LCD display)
        return outputs.get('processed_resized', stitched_path)
    
    def _capture_frames(self, output_dir: str, 
                       callback: Optional[Callable[[str, int, int, float], None]] = None) -> List[str]:
        """Capture frames at each motor position."""
        frames: List[str] = []
        
        # Get scan positions from motor
        if self.use_hardware and self.motor:
            def scan_progress(status, frame_idx, pct):
                if callback:
                    callback('positioning', frame_idx, self.total_frames, 15.0 + (pct * 0.05))
            
            positions = self.motor.scan_sequence(self.total_frames, callback=scan_progress)
        else:
            positions = list(range(self.total_frames))  # Dummy positions for simulation
        
        # Capture frame at each position
        for i, pos in enumerate(positions):
            if callback:
                callback('capturing', i + 1, self.total_frames, 20.0 + (i / self.total_frames) * 45.0)
            
            frame_path = os.path.join(output_dir, f"frame_{i+1}.jpg")
            
            # Capture with hardware camera or use test image
            if self.use_hardware and self.camera:
                try:
                    # Turn on LED for consistent lighting
                    if self.motor:
                        self.motor.led_on()
                    time.sleep(0.5)  # Stabilization delay
                    
                    # Capture using Picamera2
                    self.camera.capture_file(frame_path)
                    
                    # Turn off LED
                    if self.motor:
                        self.motor.led_off()
                except Exception as e:
                    if callback:
                        callback('capture_error', i + 1, self.total_frames, 0.0)
                    print(f"Camera capture failed: {e}")
                    if self.retry_limit > 0:
                        self.retry_limit -= 1
                        continue
                    return frames
            else:
                # Simulation mode - duplicate test image
                try:
                    source = os.getenv("MANGOFY_TEST_IMAGE", "")
                    if source and os.path.exists(source):
                        with Image.open(source) as img:
                            img.save(frame_path, format='JPEG', quality=90)
                    time.sleep(0.3)  # Simulate capture time
                except Exception as e:
                    if callback:
                        callback('capture_error', i + 1, self.total_frames, 0.0)
                    return frames
            
            frames.append(frame_path)
        
        return frames
    
    def _stitch_frames(self, frames: List[str], output_dir: str) -> Optional[str]:
        """
        Stitch frames vertically (top-to-bottom) with PDF specifications:
        - Crop top pixels per frame: [0, 169, 133, 120]
        - Horizontal shifts per frame: [0, -9, -13, -29]
        
        Args:
            frames: List of frame file paths
            output_dir: Output directory
        
        Returns:
            Path to stitched image
        """
        if not frames:
            return None
        
        # Check if cv2 is available for advanced stitching
        if not HAS_CV2:
            # Fallback to simple PIL-based horizontal stitching
            return self._stitch_frames_fallback(frames, output_dir)
        
        try:
            # Load images using OpenCV for consistency with PDF
            images = [cv2.imread(f) for f in frames]
            
            for i, img in enumerate(images):
                if img is None:
                    raise FileNotFoundError(f"{frames[i]} not found")
            
            # Apply vertical crop (top pixels) to frames 1-3
            for i in range(1, min(4, len(images))):
                h = images[i].shape[0]
                crop_amt = min(self.crop_top_px[i], h - 1)
                if crop_amt > 0:
                    images[i] = images[i][crop_amt:, :].copy()
            
            # Compute stitched canvas size (vertical stacking)
            width = max(img.shape[1] for img in images)
            total_height = sum(img.shape[0] for img in images)
            stitched = np.zeros((total_height, width, 3), dtype=np.uint8)
            
            # Stitch with horizontal shifts (vertical stacking)
            current_y = 0
            for img, shift in zip(images, self.left_shifts):
                h, w = img.shape[:2]
                
                # Calculate source and destination regions based on shift
                if shift < 0:
                    src_x_start = -shift
                    src_x_end = w
                    x_start = 0
                else:
                    src_x_start = 0
                    src_x_end = w
                    x_start = shift
                
                width_to_paste = src_x_end - src_x_start
                stitched[current_y:current_y + h, x_start:x_start + width_to_paste] = \
                    img[:, src_x_start:src_x_end]
                
                current_y += h
            
            # Save stitched image with PDF filename
            stitched_path = os.path.join(output_dir, 'full_leaf_stitched_v3_separate.jpg')
            cv2.imwrite(stitched_path, stitched)
            print(f"\u2705 Saved {stitched_path}")
            
            return stitched_path
            
        except Exception as e:
            print(f"Stitching failed: {e}")
            return None
    
    def _stitch_frames_fallback(self, frames: List[str], output_dir: str) -> Optional[str]:
        """
        Fallback stitching using PIL when cv2 is not available.
        Simple horizontal stitching without advanced alignment.
        
        Args:
            frames: List of frame file paths
            output_dir: Output directory
        
        Returns:
            Path to stitched image
        """
        try:
            images = [Image.open(f) for f in frames]
            
            # Calculate total width and max height
            widths, heights = zip(*(i.size for i in images))
            total_width = sum(widths)
            max_height = max(heights)
            
            # Create new image and paste frames horizontally
            stitched = Image.new('RGB', (total_width, max_height))
            x_offset = 0
            for img in images:
                stitched.paste(img, (x_offset, 0))
                x_offset += img.width
            
            # Save stitched image
            stitched_path = os.path.join(output_dir, 'stitched_raw.jpg')
            stitched.save(stitched_path, format='JPEG', quality=92)
            print(f"✅ Saved (fallback) {stitched_path}")
            
            return stitched_path
            
        except Exception as e:
            print(f"Fallback stitching failed: {e}")
            return None
    
    def _preprocess_image(self, stitched_path: str, output_dir: str) -> dict:
        """
        Preprocess stitched image per PDF specification:
        1. Remove background using rembg (if available)
        2. Crop to leaf bounding box
        3. Save original cropped version
        4. Apply contrast/color enhancements
        5. Resize to 480x800 with white padding
        
        Generates 3 outputs:
        1. full_leaf_stitched_v3_separate.jpg (raw stitched - already saved)
        2. output_image_original.png (cropped with white background)
        3. output_image_reduced.png (enhanced + resized 480x800)
        
        Args:
            stitched_path: Path to raw stitched image
            output_dir: Output directory
        
        Returns:
            Dictionary with paths
        """
        outputs = {'raw': stitched_path}
        
        # If cv2 not available, use simplified PIL-based processing
        if not HAS_CV2:
            return self._preprocess_image_fallback(stitched_path, output_dir)
        
        try:
            # Load stitched image
            img_cv = cv2.imread(stitched_path)
            if img_cv is None:
                raise ValueError(f"Failed to load {stitched_path}")
            
            # Step 1: Background removal (if rembg available)
            if HAS_REMBG and os.getenv('MANGOFY_ENABLE_REMBG', 'true').lower() == 'true':
                print("\u23f3 Removing background...")
                img_pil = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
                img_no_bg = remove(img_pil)
                img_no_bg = img_no_bg.convert("RGBA")
                
                # Create white background
                background = Image.new("RGB", img_no_bg.size, (255, 255, 255))
                background.paste(img_no_bg, mask=img_no_bg.split()[3])
                img_cv = cv2.cvtColor(np.array(background), cv2.COLOR_RGB2BGR)
            
            # Step 2: Crop to leaf bounding box
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            _, leaf_mask = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY_INV)
            
            # Morphological operations to clean mask
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            leaf_mask = cv2.morphologyEx(leaf_mask, cv2.MORPH_CLOSE, kernel)
            leaf_mask = cv2.morphologyEx(leaf_mask, cv2.MORPH_OPEN, kernel)
            
            # Find contours and get bounding box
            contours, _ = cv2.findContours(leaf_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                leaf_contour = max(contours, key=cv2.contourArea)
                x, y, w_crop, h_crop = cv2.boundingRect(leaf_contour)
                cropped_leaf = img_cv[y:y + h_crop, x:x + w_crop]
            else:
                print("\u26a0 No leaf detected, using full image")
                cropped_leaf = img_cv
            
            # Step 3: Save cropped original
            white_bg_output = os.path.join(output_dir, "output_image_original.png")
            Image.fromarray(cv2.cvtColor(cropped_leaf, cv2.COLOR_BGR2RGB)).save(white_bg_output)
            outputs['processed_original'] = white_bg_output
            print(f"\u2705 Cropped leaf saved: {white_bg_output}")
            
            # Step 4: Apply enhancements
            img_pil = Image.fromarray(cv2.cvtColor(cropped_leaf, cv2.COLOR_BGR2RGB))
            
            # Contrast enhancement (+20%)
            enhancer = ImageEnhance.Contrast(img_pil)
            img_enhanced = enhancer.enhance(1.2)
            
            # Color saturation (+10%)
            enhancer_color = ImageEnhance.Color(img_enhanced)
            img_enhanced = enhancer_color.enhance(1.1)
            
            # Step 5: Resize to 480x800 maintaining aspect ratio with white padding
            img_ratio = img_enhanced.width / img_enhanced.height
            target_ratio = 480 / 800
            
            if img_ratio > target_ratio:
                new_width = 480
                new_height = int(480 / img_ratio)
            else:
                new_height = 800
                new_width = int(800 * img_ratio)
            
            img_resized = img_enhanced.resize((new_width, new_height), Image.Resampling.LANCZOS)
            img_final_padded = ImageOps.pad(img_resized, (480, 800), color="white")
            
            # Save final processed/resized version
            processed_resized = os.path.join(output_dir, 'output_image_reduced.png')
            img_final_padded.save(processed_resized)
            outputs['processed_resized'] = processed_resized
            print(f"\u2705 Processed and resized: {processed_resized}")
            
            return outputs
            
        except Exception as e:
            print(f"Preprocessing failed: {e}")
            return outputs
    
    def _preprocess_image_fallback(self, stitched_path: str, output_dir: str) -> dict:
        """
        Fallback preprocessing using PIL when cv2 is not available.
        Simplified processing without background removal.
        
        Args:
            stitched_path: Path to raw stitched image
            output_dir: Output directory
        
        Returns:
            Dictionary with paths
        """
        outputs = {'raw': stitched_path}
        
        try:
            with Image.open(stitched_path) as img:
                # Simple preprocessing: enhance contrast and color
                enhancer = ImageEnhance.Contrast(img)
                img_enhanced = enhancer.enhance(1.2)  # 20% contrast boost
                
                enhancer_color = ImageEnhance.Color(img_enhanced)
                img_enhanced = enhancer_color.enhance(1.1)  # 10% color saturation
                
                # Save processed original size
                processed_original = os.path.join(output_dir, 'output_image_original.png')
                img_enhanced.save(processed_original, format='PNG')
                outputs['processed_original'] = processed_original
                
                # Resize to 480x800 (maintain aspect ratio with padding)
                img_resized = ImageOps.fit(img_enhanced, (480, 800), Image.Resampling.LANCZOS)
                
                # Save processed resized
                processed_resized = os.path.join(output_dir, 'output_image_reduced.png')
                img_resized.save(processed_resized, format='PNG')
                outputs['processed_resized'] = processed_resized
                
                print(f"✅ Preprocessed (fallback): {processed_resized}")
            
            return outputs
            
        except Exception as e:
            print(f"Fallback preprocessing failed: {e}")
            return outputs
    
    def cleanup(self):
        """Cleanup hardware resources."""
        if self.camera:
            try:
                self.camera.close()
            except:
                pass
        
        if self.motor:
            try:
                self.motor.cleanup()
            except:
                pass
    
    def __del__(self):
        """Destructor - ensure cleanup."""
        self.cleanup()
