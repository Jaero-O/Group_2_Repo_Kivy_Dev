# Hardware Scanning Implementation Guide

## Overview

This document describes the implementation of the hardware-integrated scanning system for MangoFy mango disease detection. The system combines **motor-controlled linear rail positioning** with **camera frame capture** to create high-resolution stitched images of mango leaves.

---

## Scanning Workflow

### Sequential Steps

The scanning process follows these steps in order:

1. **Home Motor** - Initialize stepper motor to home position (limit switch)
2. **Scan and Stitch** - Capture 4 frames while moving leaf across camera
3. **Multiprocess** - Parallel processing of motor homing and image preprocessing

### User Flow

```
ScanScreen (Tap "Scan" button)
    ↓
ScanningScreen (Shows live progress)
    ↓
    Step 1: "Homing motor..."
    Step 2: "Scanning 1 out of 4 Frames..."
    Step 3: "Scanning 2 out of 4 Frames..."
    Step 4: "Scanning 3 out of 4 Frames..."
    Step 5: "Scanning 4 out of 4 Frames..."
    Step 6: "Stitching Frames..."
    Step 7: "Processing image..."
    Step 8: "Analyzing disease..."
    ↓
CaptureResultScreen (Display results)
```

---

## Hardware Components

### Motor System

- **Type**: NEMA 17 Stepper Motor
- **Driver**: A4988/DRV8825
- **Steps/Revolution**: 200 (1.8° per step)
- **Linear Travel**: ~94.2mm per revolution
- **Total Travel**: 200mm (across linear rail)
- **GPIO Pins** (configurable in `motor_controller.py`):
  - STEP: GPIO 17
  - DIR: GPIO 27
  - ENABLE: GPIO 22
  - LIMIT_SWITCH: GPIO 23

### Camera System

- **Option A**: Raspberry Pi Camera Module V2
  - Sensor: Sony IMX219 8MP
  - Resolution: 3280×2464 pixels (configurable)
  - Interface: CSI ribbon cable
  
- **Option B**: USB Webcam (fallback)
  - Resolution: 1920×1080 or higher

### Linear Rail

- **Type**: MGN12H Linear Guide Rail
- **Length**: 250mm
- **Travel**: 200mm active, 50mm margin
- **Precision**: ±0.02mm

---

## Software Architecture

### Module Structure

```
kivy-lcd-app/app/
├── core/
│   ├── motor_controller.py    # Stepper motor GPIO control
│   └── capture.py              # Multi-frame capture & stitching
└── screens/
    ├── scan_screen.py          # Entry point (Scan button)
    └── scanning_screen.py      # Progress display during capture
```

### Key Classes

#### 1. `MotorController` (`motor_controller.py`)

Handles all stepper motor operations via Raspberry Pi GPIO.

**Key Methods:**
- `home_motor()` - Move backward to limit switch, reset position to 0mm
- `move_to_position(target_mm)` - Move to absolute position from home
- `scan_sequence(num_frames)` - Execute full scan (4 positions)
- `cleanup()` - Release GPIO resources

**Simulation Mode:**
If `RPi.GPIO` is not available (e.g., on Windows dev machine), the controller runs in **simulation mode** with time delays but no actual GPIO calls.

```python
motor = MotorController(use_gpio=True)  # Auto-detects GPIO availability
motor.home_motor()  # Returns to home position
positions = motor.scan_sequence(num_frames=4)  # Moves to 4 positions
```

#### 2. `MultiFrameCapture` (`capture.py`)

Orchestrates the complete capture pipeline.

**Key Methods:**
- `run(source_image, output_dir, callback)` - Execute full pipeline
- `_capture_frames()` - Capture frame at each motor position
- `_stitch_frames()` - Horizontally stitch frames with overlap
- `_preprocess_image()` - Enhance and resize stitched image

**Output Files:**
1. `stitched_raw.jpg` - Non-processed stitched (original pixels)
2. `stitched_processed.jpg` - Processed non-resized (contrast/color enhanced)
3. `stitched_processed_480x800.jpg` - Processed resized for LCD display

```python
capture = MultiFrameCapture(total_frames=4, overlap_percentage=15)
result_path = capture.run(test_image, output_dir, callback=progress_callback)
```

#### 3. `ScanningScreen` (`scanning_screen.py`)

Displays real-time progress during scanning.

**Properties:**
- `status_text` - Current operation message
- `progress_pct` - Progress bar (0-100%)
- `current_frame` - Current frame number
- `total_frames` - Total frames to capture

**Progress Phases:**
- `homing` → "Homing motor..."
- `positioning` → "Positioning for frame N..."
- `capturing` → "Scanning N out of 4 Frames..."
- `stitching` → "Stitching Frames..."
- `preprocessing` → "Processing image..."
- `analyzing` → "Analyzing disease..."
- `complete` → Navigate to results

---

## Frame Capture Process

### 1. Motor Positioning

The motor moves the leaf sample across 150mm in 4 positions:

```
Frame 1: 0mm    (home position)
Frame 2: 50mm   (25% through travel)
Frame 3: 100mm  (50% through travel)
Frame 4: 150mm  (75% through travel)
```

Each position is calculated with even spacing:
```python
frame_spacing = 150mm / (4 - 1) = 50mm
positions = [0, 50, 100, 150]
```

### 2. Camera Capture

At each position:
1. Motor moves to position
2. Wait 200ms for vibration to settle
3. Camera captures frame
4. Save frame as `frame_N.jpg`

**Simulation Mode** (no camera hardware):
Uses `MANGOFY_TEST_IMAGE` environment variable as source image.

**Hardware Mode** (Raspberry Pi Camera):
```python
camera = PiCamera()
camera.resolution = (1640, 1232)
camera.capture('frame_1.jpg')
```

### 3. Image Stitching

Frames are stitched horizontally with 15% overlap:

```
[Frame 1]
      [Frame 2]
            [Frame 3]
                  [Frame 4]
```

**Overlap Calculation:**
```python
overlap_px = width * (15 / 100)  # 15% overlap
total_width = width + (3 * (width - overlap_px))
```

Simple paste algorithm (alpha blending can be added for smoother transitions):
```python
stitched.paste(images[0], (0, 0))
current_x = width - overlap_px
for img in images[1:]:
    stitched.paste(img, (current_x, 0))
    current_x += width - overlap_px
```

### 4. Image Preprocessing

Three versions are generated:

1. **Raw Stitched** (`stitched_raw.jpg`)
   - Direct output from stitching
   - No enhancements
   - Original pixel dimensions

2. **Processed Original** (`stitched_processed.jpg`)
   - Contrast enhancement (+20%)
   - Color saturation (+10%)
   - Original pixel dimensions

3. **Processed Resized** (`stitched_processed_480x800.jpg`)
   - Same enhancements as #2
   - Resized to 480×800 (LCD display size)
   - Maintains aspect ratio with padding

```python
enhancer = ImageEnhance.Contrast(img)
img_enhanced = enhancer.enhance(1.2)  # 20% contrast boost

img_resized = ImageOps.fit(img_enhanced, (480, 800), Image.Resampling.LANCZOS)
```

---

## Multiprocessing Optimization

The system uses Python's `multiprocessing` module to run certain operations in parallel:

**Parallel Operations:**
- Motor homing (while preprocessing setup initializes)
- Image preprocessing (while motor returns to home)

**Implementation Note:**
The current implementation has infrastructure for multiprocessing but runs sequentially for safety. To enable true parallel processing, modify `capture.py` to use `Process` and `Queue` for motor homing and preprocessing.

Example:
```python
from multiprocessing import Process, Queue

def home_motor_async(motor, result_queue):
    success = motor.home_motor()
    result_queue.put(success)

# Start homing in background
queue = Queue()
p = Process(target=home_motor_async, args=(motor, queue))
p.start()

# Do preprocessing setup while motor homes
# ...

# Wait for motor to finish
p.join()
homing_success = queue.get()
```

---

## Configuration

### Environment Variables

```bash
# Test image for simulation mode (required if no camera)
export MANGOFY_TEST_IMAGE="/path/to/test_leaf.jpg"

# Model path for disease prediction
export MANGOFY_MODEL_PATH="ml/models/mango_mobilenetv2.tflite"

# Default tree name for scans
export MANGOFY_DEFAULT_TREE="Sample Tree"
```

### Motor Controller Parameters

Edit `motor_controller.py` to adjust GPIO pins or motor specs:

```python
motor = MotorController(
    step_pin=17,              # GPIO pin for STEP
    dir_pin=27,               # GPIO pin for DIR
    enable_pin=22,            # GPIO pin for ENABLE
    limit_switch_pin=23,      # GPIO pin for limit switch
    steps_per_revolution=200, # 1.8° stepper
    linear_travel_per_rev=94.2, # mm per revolution
    use_gpio=True             # False for simulation
)
```

### Capture Settings

Edit `capture.py` to adjust capture parameters:

```python
capture = MultiFrameCapture(
    total_frames=4,           # Number of frames to capture
    retry_limit=1,            # Retries per failed frame
    use_hardware=True,        # False for simulation
    camera_resolution=(1640, 1232),  # Camera resolution
    overlap_percentage=15     # Overlap between frames (%)
)
```

---

## Testing Without Hardware

The system is designed to work in **simulation mode** on development machines without GPIO/camera hardware.

### Development Workflow

1. **Set test image:**
   ```bash
   export MANGOFY_TEST_IMAGE="data/captures/sample_leaf.jpg"
   ```

2. **Run application:**
   ```bash
   python kivy-lcd-app/main.py
   ```

3. **Expected behavior:**
   - Motor controller prints "running in simulation mode"
   - Captures duplicate test image 4 times
   - Stitches frames (same image repeated)
   - Displays progress with simulated delays

### Hardware Testing

On Raspberry Pi with actual hardware:

1. **Install GPIO library:**
   ```bash
   pip install RPi.GPIO
   ```

2. **Install camera library:**
   ```bash
   pip install picamera
   ```

3. **Wire hardware:**
   - Connect stepper driver to GPIO pins (17, 27, 22)
   - Connect limit switch to GPIO 23 (active LOW)
   - Connect camera module to CSI port
   - Power stepper driver with 12V external supply

4. **Test motor only:**
   ```python
   from app.core.motor_controller import MotorController
   motor = MotorController()
   motor.home_motor()  # Should move until limit switch triggers
   motor.move_to_position(50)  # Move to 50mm
   motor.cleanup()
   ```

5. **Test camera only:**
   ```python
   from picamera import PiCamera
   camera = PiCamera()
   camera.resolution = (1640, 1232)
   camera.capture('test.jpg')
   camera.close()
   ```

6. **Full integration test:**
   Launch app and tap "Scan" button.

---

## Troubleshooting

### Motor Issues

**Motor doesn't move:**
- Check GPIO wiring (STEP, DIR, ENABLE pins)
- Verify stepper driver power supply (12V 2A)
- Check ENABLE pin is LOW (motor enabled)
- Verify driver microstepping settings

**Motor vibrates but doesn't rotate:**
- Check motor coil wiring (A+, A-, B+, B-)
- Reduce step speed (increase `speed_delay` parameter)
- Check driver current limit potentiometer

**Homing fails:**
- Verify limit switch wiring to GPIO 23
- Check switch is normally-open (NO), triggers to LOW
- Ensure switch is positioned at home position

### Camera Issues

**Camera not detected:**
```bash
# Check camera cable connection
vcgencmd get_camera  # Should show "detected=1"

# Enable camera interface
sudo raspi-config
# Interface Options → Camera → Enable
```

**Low quality images:**
- Increase camera resolution in `capture.py`
- Adjust lighting conditions
- Clean camera lens
- Reduce motor vibration with dampers

### Stitching Issues

**Visible seams:**
- Increase overlap percentage (15% → 25%)
- Implement alpha blending at overlap regions
- Ensure consistent lighting across frames

**Alignment errors:**
- Check linear rail for binding/friction
- Verify motor step accuracy
- Calibrate `steps_per_mm` parameter

### Performance Issues

**Slow scanning:**
- Increase motor speed (reduce `speed_delay`)
- Reduce camera resolution if acceptable
- Enable multiprocessing for parallel operations

**Memory errors:**
- Reduce camera resolution
- Process images in smaller chunks
- Clear old captures from `data/captures/`

---

## Future Enhancements

### Planned Features

1. **Alpha Blending for Stitching**
   - Smooth transitions at overlap regions
   - Use PIL alpha compositing or OpenCV

2. **Adaptive Lighting Control**
   - LED brightness adjustment based on ambient light
   - GPIO-controlled LED driver

3. **Auto-Focus Camera Support**
   - Trigger focus before each capture
   - USB camera autofocus via V4L2 controls

4. **Multi-Resolution Capture**
   - High-res for analysis
   - Low-res thumbnail for gallery

5. **Real-time Preview**
   - Show live camera feed before scan
   - Positioning guides overlay

### Hardware Upgrades

- **Servo motor** for Z-axis (focus adjustment)
- **Rotary encoder** for position feedback
- **LED ring light** for consistent illumination
- **Acrylic enclosure** for light control

---

## Code Reference

### Progress Callback Signature

```python
def progress_callback(phase: str, frame_index: int, total_frames: int, progress_pct: float):
    """
    Args:
        phase: Current operation phase
               ('homing', 'positioning', 'capturing', 'stitching', 
                'preprocessing', 'analyzing', 'complete', 
                'homing_failed', 'capture_failed', 'stitching_failed')
        frame_index: Current frame number (1-indexed)
        total_frames: Total number of frames
        progress_pct: Overall progress percentage (0-100)
    """
    print(f"{phase}: Frame {frame_index}/{total_frames} - {progress_pct:.1f}%")
```

### Complete Usage Example

```python
from app.core.motor_controller import MotorController
from app.core.capture import MultiFrameCapture
import os

# Initialize motor
motor = MotorController()

# Home motor
if not motor.home_motor():
    print("Homing failed!")
    exit(1)

# Create capture instance
capture = MultiFrameCapture(
    total_frames=4,
    use_hardware=True,
    camera_resolution=(1640, 1232),
    overlap_percentage=15
)

# Progress callback
def on_progress(phase, frame_idx, total, pct):
    print(f"[{pct:3.0f}%] {phase}: {frame_idx}/{total}")

# Run capture
output_dir = "data/captures"
test_img = os.getenv("MANGOFY_TEST_IMAGE", "")
result = capture.run(test_img, output_dir, callback=on_progress)

if result:
    print(f"Success! Stitched image: {result}")
else:
    print("Capture failed")

# Cleanup
capture.cleanup()
motor.cleanup()
```

---

## References

- **HARDWARE_SPECIFICATIONS.md** - Detailed hardware component specs
- **USER_MANUAL.md** - User-facing scanning instructions
- **SYSTEM_REQUIREMENTS.md** - Functional requirements (FR-001: Camera Integration)

## Author Notes

**Implementation Date**: November 21, 2025  
**Based on**: User description of hardware scanning workflow  
**Status**: Ready for hardware testing  
**Next Steps**: Test on actual Raspberry Pi with camera and motor hardware
