# HARDWARE SPECIFICATIONS
## Mango Leaf Disease Detection System - Mechanical Components

**Document Version:** 1.0  
**Date:** November 19, 2025  
**Based on:** System Architecture Diagram  
**Status:** Reference Specification

---

## 1. OVERVIEW

The MangoFy system consists of three primary hardware subsystems working together to enable precise image capture and processing:

1. **Mechanical System** - Physical positioning and movement control
2. **Data Capture System** - Image acquisition hardware
3. **Processing System** - Computation hardware (Raspberry Pi/Mobile Device)

---

## 2. MECHANICAL SYSTEM COMPONENTS

### 2.1 Mechanical Motor

**Purpose:** Provides rotational movement for precise leaf positioning

#### Specifications
| Parameter | Value | Notes |
|-----------|-------|-------|
| **Type** | Stepper Motor or DC Servo | Stepper preferred for precision |
| **Torque** | 1.5 - 3.0 Nm | Sufficient for small positioning stage |
| **Voltage** | 12V DC | Standard robotics voltage |
| **Steps/Revolution** | 200 (1.8° per step) | For stepper motor configuration |
| **Speed** | 60 RPM max | Slow rotation for stable imaging |
| **Current Draw** | 1-2A | Requires appropriate power supply |

#### Recommended Models
- **NEMA 17 Stepper Motor** (Budget option)
  - 42×42mm mounting
  - 1.8° step angle
  - Holding torque: 4.4 kg·cm
  
- **MG996R Servo Motor** (Alternative)
  - 180° rotation range
  - Metal gears for durability
  - PWM control via microcontroller

#### Control Interface
- **Stepper:** A4988/DRV8825 driver board
- **Servo:** PWM signal from Raspberry Pi GPIO
- **Power:** External 12V 2A supply (isolated from Pi)

---

### 2.2 Gear Rack and Pinion System

**Purpose:** Convert rotational motion to linear translation for leaf sample movement

#### Gear Specifications
| Component | Specification | Description |
|-----------|---------------|-------------|
| **Pinion Gear** | Module 1.5, 20 teeth | Mounted on motor shaft |
| **Rack Gear** | Module 1.5, 200mm length | Linear travel path |
| **Material** | Steel or reinforced nylon | Wear-resistant |
| **Pitch** | 4.7mm | Distance between teeth |
| **Travel Distance** | 200mm linear | Full rack length |

#### Gear Ratio Calculation
```
Linear travel per motor revolution = Pinion circumference
= π × Module × Number of teeth
= π × 1.5 × 20 = 94.2mm
```

#### Mounting
- Rack fixed to rigid aluminum extrusion frame
- Pinion pressed onto motor shaft with set screw
- Anti-backlash spring-loaded pinion recommended

---

### 2.3 Linear Rail Slider

**Purpose:** Provide smooth, low-friction linear motion for leaf sample stage

#### Rail Specifications
| Parameter | Value | Notes |
|-----------|-------|-------|
| **Type** | MGN12H Linear Guide Rail | Miniature linear guide |
| **Length** | 250mm | Allows 200mm travel + margin |
| **Width** | 12mm rail, 27mm carriage | Compact form factor |
| **Load Capacity** | 5kg (dynamic) | More than sufficient for leaf samples |
| **Accuracy** | ±0.02mm | High precision for repeatable imaging |
| **Material** | Stainless steel | Corrosion-resistant |

#### Carriage Block
- **Model:** MGN12H carriage block (2 units recommended)
- **Mounting:** M3 screws to sample platform
- **Lubrication:** Light machine oil or PTFE grease

#### Sample Platform
- **Dimensions:** 150×100mm acrylic or aluminum plate
- **Mounting:** Bolted to linear rail carriages
- **Features:** 
  - White or neutral background for imaging
  - Optional LED backlighting for transmitted light imaging
  - Clamping mechanism for leaf stabilization

---

## 3. DATA CAPTURE AND PROCESSING SYSTEM

### 3.1 Frame Capture Module

**Purpose:** High-resolution image acquisition of leaf samples

#### Camera Module Options

##### Option A: Raspberry Pi Camera Module V2
| Specification | Value |
|---------------|-------|
| **Sensor** | Sony IMX219 8MP |
| **Resolution** | 3280×2464 pixels |
| **Video** | 1080p @ 30fps |
| **Interface** | CSI ribbon cable to Pi |
| **Lens** | Fixed focus, 62.2° FOV |
| **Dimensions** | 25×24×9mm |
| **Price** | ~$25 USD |

**Pros:**
- Direct integration with Raspberry Pi
- Low cost
- Well-documented Kivy support

**Cons:**
- Fixed focus (limited macro capability)
- Lower sensitivity in low light

##### Option B: USB Webcam (Logitech C920)
| Specification | Value |
|---------------|-------|
| **Sensor** | 15MP interpolated (3MP native) |
| **Resolution** | 1920×1080 pixels |
| **Video** | 1080p @ 30fps |
| **Interface** | USB 2.0 |
| **Lens** | Autofocus, 78° FOV |
| **Features** | Auto light correction, stereo audio |
| **Price** | ~$70 USD |

**Pros:**
- Autofocus for macro shots
- Better low-light performance
- Universal USB compatibility

**Cons:**
- Higher cost
- Requires USB bandwidth

##### Option C: High-Res Industrial Camera (FLIR Blackfly S)
| Specification | Value |
|---------------|-------|
| **Sensor** | Sony IMX250 5MP |
| **Resolution** | 2448×2048 pixels |
| **Frame Rate** | 75 fps |
| **Interface** | USB3 Vision |
| **Lens Mount** | C-mount (interchangeable) |
| **Price** | ~$400 USD |

**Use Case:** Research/commercial deployments requiring highest quality

#### Recommended Configuration
**For MVP:** Raspberry Pi Camera V2 + macro lens attachment  
**For Production:** USB webcam with autofocus

---

### 3.2 Software Processing Unit

**Primary: Raspberry Pi 4 Model B**

| Component | Specification | Purpose |
|-----------|---------------|---------|
| **CPU** | Quad-core Cortex-A72 @ 1.8GHz | TensorFlow Lite inference |
| **RAM** | 4GB LPDDR4 | Image buffering, model loading |
| **Storage** | 32GB microSD (Class 10) | OS, app, database, images |
| **GPU** | VideoCore VI | Hardware video decode |
| **USB** | 2× USB 3.0, 2× USB 2.0 | Camera, peripherals |
| **GPIO** | 40-pin header | Motor control, sensors |
| **Power** | 5V 3A USB-C | Must support peak current |
| **Price** | ~$55 USD | |

#### Operating System
- **Recommended:** Raspberry Pi OS Lite (64-bit)
- **Alternatives:** Ubuntu Server 22.04 LTS (ARM64)

#### Performance Benchmarks
- **TFLite Inference Time:** 2-4 seconds (MobileNetV2, 224×224 input)
- **Image Preprocessing:** <500ms (resize, normalize)
- **Database Query:** <100ms (indexed queries)

---

### 3.3 Output/Display Module

#### Option A: Touchscreen Display (Primary)
| Specification | Value |
|---------------|-------|
| **Model** | Raspberry Pi Touch Display |
| **Size** | 7 inch diagonal |
| **Resolution** | 800×480 pixels |
| **Interface** | DSI ribbon cable |
| **Touch** | 10-point capacitive |
| **Power** | Powered from Pi GPIO |
| **Mounting** | VESA-compatible frame |

#### Option B: HDMI Monitor (Development)
- Any HDMI-compatible display
- Minimum 1280×720 resolution
- USB mouse/keyboard for input

---

## 4. SYSTEM INTEGRATION ARCHITECTURE

### 4.1 Wiring Diagram

```
┌─────────────────────────────────────────────────┐
│           Raspberry Pi 4 Model B                │
│  ┌──────────────────────────────────────────┐  │
│  │  GPIO Pins                                │  │
│  │  • GPIO 17,18 → Motor Driver (PWM)       │  │
│  │  • GPIO 22,23 → Limit Switches           │  │
│  │  • 5V, GND    → Sensor Power             │  │
│  └──────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────┐  │
│  │  CSI Port → Camera Module                │  │
│  │  DSI Port → Touch Display                │  │
│  │  USB 3.0  → (Optional) High-res Camera   │  │
│  │  USB 2.0  → Keyboard (development)       │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
           │                    │
           ▼                    ▼
    ┌─────────────┐      ┌──────────────┐
    │ Motor       │      │ Camera       │
    │ Driver      │      │ Module       │
    │ (A4988)     │      │ (IMX219)     │
    └──────┬──────┘      └──────────────┘
           │
           ▼
    ┌─────────────┐
    │ Stepper     │
    │ Motor       │──→ Pinion Gear
    └─────────────┘         │
                            ▼
                     ┌─────────────┐
                     │ Rack Gear   │
                     └──────┬──────┘
                            │
                            ▼
                     ┌─────────────┐
                     │ Linear Rail │
                     │ + Platform  │
                     └─────────────┘
```

### 4.2 Power Distribution

| Component | Voltage | Current | Power | Supply |
|-----------|---------|---------|-------|--------|
| Raspberry Pi | 5V | 3A max | 15W | USB-C PSU |
| Camera Module | 3.3V | 250mA | 0.8W | Pi GPIO |
| Touch Display | 5V | 500mA | 2.5W | Pi GPIO |
| Stepper Motor | 12V | 1.5A | 18W | External PSU |
| Motor Driver | 12V | 100mA | 1.2W | External PSU |
| **TOTAL** | - | - | **37.5W** | 5V@3A + 12V@2A |

**Recommended:** 
- Pi + Display: Official Pi 5V 3A USB-C adapter
- Motors: 12V 2A DC adapter with barrel jack
- **Do not** power motors from Pi GPIO (will cause voltage drop/damage)

---

## 5. ASSEMBLY INSTRUCTIONS

### 5.1 Mechanical Assembly Steps

1. **Mount Linear Rails** (30 min)
   - Secure rails to aluminum extrusion base using M3 screws
   - Ensure rails are parallel (use dial indicator for precision)
   - Install carriage blocks on rails

2. **Attach Sample Platform** (15 min)
   - Bolt platform to both carriage blocks
   - Verify smooth sliding motion (no binding)
   - Add lubrication if needed

3. **Install Rack Gear** (20 min)
   - Mount rack parallel to linear rails
   - Use alignment jig to ensure straightness
   - Secure with M4 screws every 50mm

4. **Mount Motor and Pinion** (30 min)
   - Install motor on adjustable bracket
   - Press pinion onto motor shaft
   - Adjust motor position to mesh pinion with rack (backlash <0.5mm)
   - Tighten motor mount bolts

5. **Install Limit Switches** (15 min)
   - Position switches at both ends of travel
   - Wire to Raspberry Pi GPIO (normally open configuration)

### 5.2 Electronics Assembly

1. **Prepare Raspberry Pi** (45 min)
   - Install heatsinks on CPU/RAM chips
   - Insert microSD card with OS image
   - Connect camera module via CSI cable
   - Attach touch display via DSI cable

2. **Wire Motor Driver** (30 min)
   - Connect motor driver to stepper motor (4-wire)
   - Connect driver power to 12V supply
   - Connect STEP/DIR pins to Pi GPIO 17/18
   - Add 100µF capacitor across motor power supply

3. **Test Systems** (60 min)
   - Power on Pi, verify boot
   - Test camera capture (`raspistill -o test.jpg`)
   - Test motor control (Python RPi.GPIO script)
   - Verify limit switch interrupts

---

## 6. PRECISION POSITIONING SYSTEM

### 6.1 Microstepping Configuration

**Purpose:** Achieve sub-millimeter positioning accuracy

| Setting | Steps/Rev | Resolution | Linear Resolution |
|---------|-----------|------------|-------------------|
| Full Step | 200 | 1.8° | 0.47mm |
| 1/2 Step | 400 | 0.9° | 0.24mm |
| 1/4 Step | 800 | 0.45° | 0.12mm |
| **1/8 Step** | **1600** | **0.225°** | **0.059mm** |
| 1/16 Step | 3200 | 0.1125° | 0.029mm |

**Recommended:** 1/8 microstepping (59µm resolution) balances precision and torque

#### A4988 Driver Configuration
```
MS1 = HIGH
MS2 = HIGH  
MS3 = LOW
→ 1/8 microstepping mode
```

### 6.2 Position Calibration Procedure

1. **Home Position Sequence**
   - Move platform to limit switch at one end
   - Trigger limit switch interrupt
   - Set position counter to 0
   - Back off 10mm from limit

2. **Travel Span Calibration**
   - Move platform to opposite limit switch
   - Record step count (should be ~3200 for 200mm travel)
   - Calculate steps/mm ratio: `steps_per_mm = step_count / 200`

3. **Repeatability Test**
   - Move to 5 random positions
   - Return to home after each move
   - Measure position error (should be <0.1mm)

---

## 7. LIGHTING SYSTEM (Optional Enhancement)

### 7.1 LED Ring Light

**Purpose:** Uniform illumination for consistent imaging

| Specification | Value |
|---------------|-------|
| **Type** | 144 LED ring (5050 SMD) |
| **Color Temperature** | 5500K (daylight) |
| **Power** | 12V 2A |
| **Dimming** | PWM control from Pi GPIO |
| **Mounting** | Surrounding camera lens |

### 7.2 Backlighting (Transmitted Light)

**Purpose:** Highlight lesions and vein structure

- **Type:** White LED strip under translucent platform
- **Power:** 12V 500mA
- **Control:** ON/OFF switch or Pi GPIO

---

## 8. ENCLOSURE DESIGN

### 8.1 Recommended Dimensions

| Measurement | Value | Notes |
|-------------|-------|-------|
| **Length** | 400mm | Accommodates 200mm travel + margin |
| **Width** | 250mm | Houses rail system + electronics |
| **Height** | 350mm | Camera height above sample stage |
| **Material** | Aluminum extrusion frame | 20×20mm or 30×30mm profile |
| **Panels** | Clear acrylic sides | For observation during operation |

### 8.2 Environmental Protection

- **Dust Cover:** Acrylic lid during storage
- **Ventilation:** 60mm fan for Pi cooling
- **Cable Management:** 3D printed cable clips/guides
- **Mounting Feet:** Rubber pads for vibration isolation

---

## 9. BILL OF MATERIALS (BOM)

| Item | Qty | Unit Price | Total | Supplier |
|------|-----|------------|-------|----------|
| Raspberry Pi 4 (4GB) | 1 | $55 | $55 | Pi Supply |
| Pi Camera Module V2 | 1 | $25 | $25 | Pi Supply |
| 7" Touch Display | 1 | $70 | $70 | Pi Supply |
| NEMA 17 Stepper Motor | 1 | $15 | $15 | Amazon |
| A4988 Driver Board | 1 | $5 | $5 | Amazon |
| MGN12H Linear Rail (250mm) | 1 | $25 | $25 | AliExpress |
| MGN12H Carriage Block | 2 | $8 | $16 | AliExpress |
| Gear Rack (200mm) | 1 | $12 | $12 | McMaster |
| Pinion Gear (20T) | 1 | $8 | $8 | McMaster |
| Aluminum Extrusion (20×20, 1m) | 2 | $10 | $20 | Amazon |
| Acrylic Sheet (3mm, 300×300) | 1 | $15 | $15 | Local |
| 12V 3A Power Supply | 1 | $12 | $12 | Amazon |
| 5V 3A USB-C Supply | 1 | $10 | $10 | Pi Supply |
| Limit Switches (mechanical) | 2 | $3 | $6 | Amazon |
| Fasteners/Hardware Kit | 1 | $20 | $20 | McMaster |
| **TOTAL** | | | **$314** | |

**Note:** Prices approximate as of November 2025, subject to availability

---

## 10. ALTERNATIVE: MOBILE-ONLY CONFIGURATION

For deployments without mechanical hardware:

### 10.1 Handheld Operation
- **Device:** Android/iOS smartphone or tablet
- **Camera:** Built-in rear camera (12MP minimum)
- **Processing:** On-device TFLite inference
- **Storage:** Local SQLite database
- **Cost:** $0 (uses existing hardware)

### 10.2 Advantages
- ✅ Portability for field use
- ✅ No assembly required
- ✅ Lower total cost
- ✅ GPS integration for location tagging

### 10.3 Disadvantages
- ❌ No automated positioning
- ❌ Manual focus and framing required
- ❌ Less repeatable image quality
- ❌ User skill-dependent results

---

## 11. MAINTENANCE SCHEDULE

| Task | Frequency | Procedure |
|------|-----------|-----------|
| **Lubricate Linear Rails** | Monthly | Apply 2 drops light machine oil |
| **Check Belt/Rack Tension** | Quarterly | Adjust motor mount if backlash present |
| **Clean Camera Lens** | Weekly | Microfiber cloth, lens cleaner |
| **Verify Limit Switches** | Monthly | Test triggering, clean contacts |
| **Tighten Fasteners** | Quarterly | Check all M3/M4 screws for loosening |
| **Update Software** | As needed | `sudo apt update && sudo apt upgrade` |

---

## 12. TROUBLESHOOTING

| Symptom | Possible Cause | Solution |
|---------|----------------|----------|
| Platform jerks during motion | Excessive friction | Lubricate rails, reduce speed |
| Motor skips steps | Insufficient current | Adjust A4988 current potentiometer |
| Blurry images | Camera focus/vibration | Use fixed-focus lens, add damping |
| Pi crashes during analysis | Insufficient power | Use 5V 3A official supply |
| Inconsistent positioning | Loose pinion gear | Tighten set screw on motor shaft |

---

**Document Control:**
- **Author:** Group 2 Hardware Team
- **Based on:** System Architecture Diagram
- **Status:** Reference Design
- **Implementation:** Optional (Mobile-only deployment also supported)

*End of Hardware Specifications*
