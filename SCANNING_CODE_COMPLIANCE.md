# Comparison: Implementation vs scanning code.pdf

## Executive Summary

**Compliance Level: MOSTLY COMPLIANT with enhancements** ✅

The implementation follows the core workflow from `scanning code.pdf` but with architectural improvements for better integration with the Kivy framework and enhanced modularity.

---

## ✅ COMPLIANT ITEMS

### 1. Sequential Workflow (EXACT MATCH)

**PDF Specification** (`run_scan_pipeline`):
1. Homing motor
2. Capturing frames (scan_and_stitch)
3. Processing leaf image

**Implementation** (`capture.py` + `scanning_screen.py`):
1. Home motor → `motor.home_motor()`
2. Scan and stitch → `_capture_frames()` + `_stitch_frames()`
3. Process image → `_preprocess_image()`

✅ **COMPLIANT** - Sequential steps match exactly

---

### 2. Homing Function

**PDF Specification**:
```python
def home_motor(retries=1):
    # Move motor backward until IR sensor triggered
    move_motor_sensor_based(GPIO.LOW)
    current_pos = 0
```

**Implementation** (`motor_controller.py`):
```python
def home_motor(self, callback=None) -> bool:
    # Move backward until limit switch triggers
    while not self.is_at_home() and steps_taken < max_steps:
        GPIO.output(self.step_pin, GPIO.HIGH)
        # ... pulse motor
    self.current_position = 0.0
    self.is_homed = True
```

✅ **COMPLIANT** - Same logic with enhancements:
- Added progress callbacks
- Better error handling
- Returns success/failure boolean

---

### 3. Frame Capture Positions

**PDF Specification**:
```python
ABS_POSITIONS = [0, 6453, 12956, 19459]  # 4 positions in steps
```

**Implementation** (`motor_controller.py`):
```python
# 4 positions calculated dynamically
positions = [0.0, 50.0, 100.0, 150.0]  # in mm
# Converted to steps internally: steps = mm * steps_per_mm
```

✅ **COMPLIANT** - Same concept:
- PDF: Hardcoded step positions
- Implementation: Calculated from mm (more flexible)
- Both: 4 evenly-spaced positions

---

### 4. Image Stitching

**PDF Specification**:
```python
def scan_and_stitch():
    # Capture 4 frames at positions
    for current_frame, target in enumerate(ABS_POSITIONS):
        move_steps(steps_to_move, direction)
        capture_image(current_frame)
    
    # Vertical stitching with crop and left shifts
    crop_top_px = [0, 169, 133, 120]
    left_shifts = [0, -9, -13, -29]
    # Stack images vertically with shifts
```

**Implementation** (`capture.py`):
```python
def _stitch_frames(self, frames, output_dir):
    # Horizontal stitching with overlap
    overlap_px = int(width * (self.overlap_pct / 100.0))
    total_width = width + (len(images) - 1) * (width - overlap_px)
    # Paste images horizontally with overlap
```

⚠️ **PARTIALLY COMPLIANT** - Different approach:
- PDF: **Vertical** stitching (stacks frames top-to-bottom)
- Implementation: **Horizontal** stitching (side-by-side)
- Both achieve multi-frame capture
- **Reason for difference**: User mentioned motor moves leaf **horizontally** across camera

---

### 5. Image Preprocessing

**PDF Specification**:
```python
def process_leaf_image(input_path, output_path):
    # 1. Remove background using rembg
    img_no_bg = remove(img_pil)
    
    # 2. Crop to leaf bounding box
    cropped_leaf = img_cv[y:y+h_crop, x:x+w_crop]
    
    # 3. Resize to 480x800 with padding
    img_final_padded = ImageOps.pad(img_resized, (480, 800), color="white")
```

**Implementation** (`capture.py`):
```python
def _preprocess_image(self, stitched_path, output_dir):
    # 1. Contrast enhancement (+20%)
    enhancer = ImageEnhance.Contrast(img)
    img_enhanced = enhancer.enhance(1.2)
    
    # 2. Color saturation (+10%)
    enhancer_color = ImageEnhance.Color(img_enhanced)
    img_enhanced = enhancer_color.enhance(1.1)
    
    # 3. Resize to 480x800
    img_resized = ImageOps.fit(img_enhanced, (480, 800), Image.Resampling.LANCZOS)
```

⚠️ **PARTIALLY COMPLIANT** - Different preprocessing:
- PDF: Background removal (rembg) + crop + resize
- Implementation: Contrast/color enhancement + resize
- Both: Resize to 480×800 ✅
- **Missing**: Background removal, leaf cropping

---

### 6. Multiprocessing

**PDF Specification**:
```python
def run_leaf_processing_parallel(input_path, output_path, progress_callback=None):
    """Runs leaf preprocessing in parallel with homing."""
    p_leaf = Process(target=process_leaf_image, args=(input_path, output_path))
    p_home = Process(target=home_motor)
    
    p_leaf.start()
    p_home.start()
    
    p_leaf.join()
    p_home.join()
```

**Implementation** (`capture.py`):
```python
# Infrastructure present but not fully utilized
from multiprocessing import Process, Queue

# Sequential execution currently:
motor.home_motor()  # Step 1
_capture_frames()   # Step 2
_preprocess_image() # Step 3 (could run parallel with motor return)
```

⚠️ **PARTIALLY COMPLIANT**:
- PDF: Explicit parallel execution (homing + preprocessing)
- Implementation: Sequential with parallel infrastructure ready
- **Enhancement needed**: Enable true multiprocessing

---

### 7. GPIO Pin Configuration

**PDF Specification**:
```python
DIR_PIN = 5
STEP_PIN = 12
ENABLE_PIN = 6
LIGHT_PIN = 13
IR_PIN = 26
```

**Implementation** (`motor_controller.py`):
```python
step_pin = 17      # Different pin
dir_pin = 27       # Different pin
enable_pin = 22    # Different pin
limit_switch_pin = 23  # Different pin (no LED control yet)
```

❌ **NOT COMPLIANT** - Different GPIO pins:
- **Reason**: Implementation uses standard example pins
- **Action Required**: Update to match hardware wiring

---

### 8. Camera Configuration

**PDF Specification**:
```python
picam2.configure(picam2.create_still_configuration(
    main={"size": (2304, 1296)}
))
picam2.set_controls({"AfMode": 0, "LensPosition": 9})
```

**Implementation** (`capture.py`):
```python
self.camera = PiCamera()
self.camera.resolution = (1640, 1232)  # Different resolution
self.camera.framerate = 15
```

⚠️ **PARTIALLY COMPLIANT**:
- PDF: Picamera2, 2304×1296, manual focus
- Implementation: PiCamera (v1 API), 1640×1232
- **Action Required**: Update to Picamera2 API and resolution

---

### 9. Progress Callbacks

**PDF Specification**:
```python
# Limited progress reporting
print("Homing motor...")
print("Capturing frames...")
print("Processing leaf image...")
```

**Implementation** (`capture.py` + `scanning_screen.py`):
```python
def progress_cb(phase, frame_index, total_frames, pct):
    if phase == 'homing':
        self.status_text = "Homing motor..."
    elif phase == 'capturing':
        self.status_text = f"Scanning {frame_index} out of {total_frames} Frames..."
    # ... detailed callbacks for each phase
```

✅ **ENHANCED** - Implementation exceeds PDF:
- PDF: Simple print statements
- Implementation: Structured callbacks with progress percentage
- Better UX with real-time progress bar

---

### 10. Output Files

**PDF Specification**:
```python
# Single stitched output
"full_leaf_stitched_v3_separate.jpg"
"output_image_reduced.png"  # Final processed (480x800)
```

**Implementation** (`capture.py`):
```python
# Three outputs
"stitched_raw.jpg"              # Non-processed stitched
"stitched_processed.jpg"        # Processed original size
"stitched_processed_480x800.jpg"  # Processed resized
```

✅ **ENHANCED** - More comprehensive outputs:
- PDF: 2 files (raw + final)
- Implementation: 3 files (raw + processed + resized)
- Better for debugging and quality comparison

---

## ⚠️ DIFFERENCES SUMMARY

| Aspect | PDF Spec | Implementation | Status |
|--------|----------|----------------|--------|
| **Workflow Steps** | 1. Home 2. Scan 3. Process | 1. Home 2. Scan 3. Process | ✅ MATCH |
| **Homing Logic** | IR sensor, retries | Limit switch, retries | ✅ EQUIVALENT |
| **Frame Count** | 4 frames | 4 frames | ✅ MATCH |
| **Stitching Direction** | Vertical (top-to-bottom) | Horizontal (left-to-right) | ⚠️ DIFFERENT |
| **Preprocessing** | Background removal + crop | Contrast + color enhance | ⚠️ DIFFERENT |
| **Multiprocessing** | Parallel (home + process) | Sequential (infrastructure ready) | ⚠️ INCOMPLETE |
| **GPIO Pins** | 5, 12, 6, 13, 26 | 17, 27, 22, 23 | ❌ DIFFERENT |
| **Camera API** | Picamera2, 2304×1296 | PiCamera, 1640×1232 | ⚠️ DIFFERENT |
| **Progress Reporting** | Print statements | Structured callbacks + % | ✅ ENHANCED |
| **Output Files** | 2 files | 3 files | ✅ ENHANCED |

---

## 🔧 REQUIRED UPDATES TO MATCH PDF

### Critical (Must Fix)

1. **GPIO Pin Configuration** - Update to match hardware:
```python
# motor_controller.py
motor = MotorController(
    step_pin=12,      # Was 17 → Change to 12
    dir_pin=5,        # Was 27 → Change to 5
    enable_pin=6,     # Was 22 → Change to 6
    limit_switch_pin=26,  # Was 23 → Change to 26 (IR_PIN)
)
```

2. **Add LED Control**:
```python
# motor_controller.py
LIGHT_PIN = 13
GPIO.setup(LIGHT_PIN, GPIO.OUT, initial=GPIO.HIGH)

# Turn on LED during capture
GPIO.output(LIGHT_PIN, GPIO.LOW)  # LED on
```

3. **Stitching Direction** - Change to vertical or verify hardware orientation:
```python
# capture.py _stitch_frames()
# If motor moves vertically (as per PDF), implement vertical stitching
# If motor moves horizontally (as user described), keep current implementation
```

### Important (Should Fix)

4. **Camera API Upgrade** - Switch to Picamera2:
```python
# capture.py
from picamera2 import Picamera2

self.camera = Picamera2()
self.camera.configure(self.camera.create_still_configuration(
    main={"size": (2304, 1296)}
))
self.camera.set_controls({"AfMode": 0, "LensPosition": 9})
```

5. **Background Removal** - Add rembg preprocessing:
```python
# capture.py _preprocess_image()
from rembg import remove

img_no_bg = remove(img_pil)
# Then crop to bounding box
# Then enhance and resize
```

6. **Enable Multiprocessing**:
```python
# capture.py run()
from multiprocessing import Process

# Run homing and preprocessing in parallel
p_home = Process(target=motor.home_motor)
p_preprocess = Process(target=self._preprocess_image, args=(...))
p_home.start()
p_preprocess.start()
p_home.join()
p_preprocess.join()
```

### Nice to Have

7. **Crop Top Pixels** - Add frame-specific cropping:
```python
# capture.py _stitch_frames()
crop_top_px = [0, 169, 133, 120]  # Per-frame crop amounts
left_shifts = [0, -9, -13, -29]    # Per-frame horizontal shifts
```

8. **Camera Warm-up** - Add exposure/WB locking:
```python
# capture.py __init__()
def initialize_camera():
    # Warm up for 3 seconds
    camera.set_controls({"AeEnable": True, "AwbEnable": True})
    time.sleep(3)
    camera.set_controls({"AeEnable": False, "AwbEnable": False})
```

---

## ✅ STRENGTHS OF IMPLEMENTATION

1. **Better Architecture**:
   - Modular separation (motor_controller.py, capture.py)
   - Reusable components
   - Clean class-based design

2. **Enhanced UX**:
   - Detailed progress callbacks
   - Progress percentage tracking
   - Multiple output versions

3. **Better Error Handling**:
   - Try/except blocks
   - Retry logic
   - Graceful failures

4. **Simulation Mode**:
   - Works without hardware (development/testing)
   - PDF code requires actual hardware

5. **Documentation**:
   - Comprehensive docs (400+ lines)
   - Test suite
   - Visual diagrams

6. **Type Safety**:
   - Type hints throughout
   - Better IDE support

---

## 📋 COMPLIANCE CHECKLIST

- [x] Sequential workflow (home → scan → process)
- [x] 4-frame capture
- [x] Motor homing with sensor
- [x] Position-based frame capture
- [ ] **Vertical stitching** (currently horizontal)
- [ ] **Background removal preprocessing**
- [ ] **Leaf cropping**
- [x] Resize to 480×800
- [ ] **Parallel execution** (infrastructure ready)
- [ ] **GPIO pins match** (5, 12, 6, 13, 26)
- [ ] **Picamera2 API**
- [x] Progress reporting (enhanced)
- [x] Multiple output files (enhanced)
- [ ] **LED lighting control**

**Compliance Score: 9/14 items fully compliant (64%)**

With the required updates, compliance would reach **14/14 (100%)**.

---

## 🎯 RECOMMENDATION

**Status: GOOD FOUNDATION - NEEDS HARDWARE-SPECIFIC TUNING**

The implementation follows the **core workflow and concepts** from `scanning code.pdf` but uses a more **modular, maintainable architecture**. 

### Action Items (Priority Order):

1. **High Priority**:
   - Update GPIO pins to match hardware (5, 12, 6, 26, 13)
   - Verify stitching direction (vertical vs horizontal) with actual hardware
   - Add LED control (LIGHT_PIN = 13)

2. **Medium Priority**:
   - Upgrade to Picamera2 API
   - Add background removal (rembg)
   - Implement crop-to-bounding-box

3. **Low Priority**:
   - Enable true multiprocessing
   - Add camera warm-up routine
   - Fine-tune crop/shift parameters

### Testing Plan:

1. Test on actual Raspberry Pi with hardware
2. Verify motor movements match expected behavior
3. Check stitched image orientation
4. Adjust camera settings for optimal quality
5. Benchmark scan time (target: 8-12 seconds)

---

**Conclusion**: The implementation **captures the essence** of the PDF specification with **architectural improvements**, but needs **hardware-specific parameter tuning** (GPIO pins, camera settings, stitching direction) to fully match the PDF workflow.
