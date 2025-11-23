# MangoFy - Mango Leaf Disease Detection System

[![Status](https://img.shields.io/badge/Status-Production%20Ready-green)]() 
[![Tests](https://img.shields.io/badge/Tests-98.7%25%20Passing-brightgreen)]()
[![Documentation](https://img.shields.io/badge/Documentation-Complete-blue)]()

---

## 🤖 **ATTENTION: AI ASSISTANTS & AUTOMATED SYSTEMS**

**If you are an AI assistant (GitHub Copilot, ChatGPT, Claude, etc.), you MUST read `AI_ASSISTANT_INSTRUCTIONS.md` IMMEDIATELY before performing any action in this repository.**

**Direct link:** [AI_ASSISTANT_INSTRUCTIONS.md](AI_ASSISTANT_INSTRUCTIONS.md)

This is a CRITICAL directive. Failure to comply will result in rejected changes.

---

## ⚠️ **CRITICAL: READ THIS FIRST** ⚠️

**THIS IS A MANDATORY NOTICE FOR ALL DEVELOPERS AND AI ASSISTANTS**

Before making **ANY** changes to this codebase, you **MUST**:

### 1. 📖 READ REQUIRED DOCUMENTATION (IN ORDER):
1. **THIS README** (you are here) - System overview and setup
2. **`docs/SYSTEM_REQUIREMENTS.md`** - Complete functional and non-functional requirements
3. **`docs/USER_MANUAL.md`** - DEFINITIVE UI flow and interaction patterns  
4. **`docs/HARDWARE_SPECIFICATIONS.md`** - Hardware integration specifications
5. **`COMPREHENSIVE_ASSESSMENT_REPORT.md`** - System assessment and quality metrics
6. **`IMPLEMENTATION_COMPLETION_SUMMARY.md`** - Recent improvements and current status

### 2. ✅ COMPLIANCE REQUIREMENTS:
- ✅ All specifications in the documentation are **DEFINITIVE** and **MANDATORY**
- ✅ UI navigation flow must follow `docs/USER_MANUAL.md` **EXACTLY**
- ✅ Do NOT deviate from documented screen transitions
- ✅ Do NOT modify scanning workflow without authorization
- ✅ Do NOT bypass documented validation rules
- ✅ All code changes must maintain test coverage ≥90%

### 3. 🚫 PROHIBITED ACTIONS:
- ❌ Changing UI flow without updating USER_MANUAL.md
- ❌ Modifying ML preprocessing pipeline
- ❌ Auto-saving scans without user confirmation
- ❌ Skipping required validation steps
- ❌ Breaking existing screen navigation patterns

**Failure to comply with these documentation requirements may result in rejected pull requests.**

---

## Project Overview

MangoFy is a Kivy-based mobile application designed to detect mango leaf diseases using computer vision and deep learning. The application provides a user-friendly interface to scan mango leaves, get predictions, save the results, and learn more about disease management.

### ML Model Integration (Current Stabilization Branch)

The predictor (`ml/predictor.py`) now implements the repository's definitive **segmentation-first** scanning pipeline by default. It will perform classification and lesion segmentation (mask) and expose severity metrics in a single API surface. Integration follows these principles:

| Asset | Default Local Path | Override Env Var | Notes |
|-------|--------------------|------------------|-------|
| Classification model (TFLite) | `ml/Plant_Disease_Prediction/tflite/mango_mobilenetv2.tflite` | `MANGOFY_MODEL_PATH` | Place file manually or use `scripts/download_model.py`. |
| Alternative MobileNetV3 model | `ml/Plant_Disease_Prediction/tflite/mobilenetv3_mango_leaf_enhanced.tflite` | `MANGOFY_MODEL_PATH` | Optional enhanced classifier; update settings to prefer this model. |
| All-disease MobileNetV2 model | `ml/Plant_Disease_Prediction/tflite/all_disease_mango_leaf_disease_mnetv2.tflite` | `MANGOFY_MODEL_PATH` | Optional all-disease classifier which returns multi-class outputs. |
| Segmentation model (optional, TFLite) | `ml/Plant_Disease_Prediction/tflite/mango_segmentation.tflite` | `MANGOFY_SEGMENTATION_MODEL_PATH` | Optional segmentation model that improves lesion masks. If missing, fallback CPU/HSV segmentation is used. |
| Labels (`labels.txt`) | `ml/assets/labels.txt` | `MANGOFY_LABELS_PATH` | Order MUST match model output indices. |
| Test Image | (user provided) | `MANGOFY_TEST_IMAGE` | Used for auto-scan + test harness. |

Quick local validation:
```powershell
# Set env vars (adjust paths to your local external repo)
$env:MANGOFY_MODEL_PATH = "C:\Users\kenne\Group_2_Repo_Kivy_Dev\ml\Plant_Disease_Prediction\tflite\mango_mobilenetv2.tflite"
$env:MANGOFY_LABELS_PATH = "C:\Users\kenne\Group_2_Repo_Kivy_Dev\ml\Plant_Disease_Prediction\tflite\labels.txt"
$env:MANGOFY_TEST_IMAGE = "C:\Users\kenne\Downloads\Database\dataset\Anthracnose\20211008_124250 (Custom)(1).jpg"
 # Optional segmentation model path
 $env:MANGOFY_SEGMENTATION_MODEL_PATH = "C:\Users\kenne\Group_2_Repo_Kivy_Dev\ml\Plant_Disease_Prediction\tflite\mango_segmentation.tflite"
 # Optional model/version identifier
 $env:MANGOFY_MODEL_VERSION = "v1.0-seg"
# Use `MANGOFY_PREDICTOR_TYPE='classic'` to force the old MobileNetV2 classification-only predictor.
$env:MANGOFY_PREDICTOR_TYPE = "segmentation"
python tools/test_tflite_infer.py

Additionally, we provide an integration-helper script to perform common validation steps in sequence (OCR extraction of the requirements PDF, DB migration, model validation, and a short batch inference):

```powershell
python scripts/auto_run_integration.py
```

This script is safe to run locally; it will not modify DB data destructively and will run migrations idempotently. Use it to sanity-check that models and DB schema are in place and functioning.
```

If the model or interpreter is missing, the `ScanningScreen` now presents a popup instead of silently continuing.

To download assets (when published via raw or release URLs):
```powershell
python scripts/download_model.py
```
Then (optional) unset overrides to use bundled paths:
```powershell
Remove-Item Env:MANGOFY_MODEL_PATH -ErrorAction SilentlyContinue
Remove-Item Env:MANGOFY_LABELS_PATH -ErrorAction SilentlyContinue
```

## Running the Kivy App Locally (Windows / Raspberry Pi)

Follow these steps to run the Kivy UI locally for development and testing. The main UI entrypoint is `kivy-lcd-app/main.py`.

1. Create and activate a Python venv:

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate
# Linux / Pi
source .venv/bin/activate
```

2. Install (or pin) core requirements. On non-Pi machines, skip the Pi-specific packages or use `--no-deps` for pi-only packages:

```bash
pip install -U pip setuptools wheel
pip install -r requirements.txt
```

3. Initialize the DB (idempotent):

```bash
python scripts/db_init.py
```

4. Start the app (development):

On Windows (PowerShell), set the following environment variables and run the app:

```powershell
$Env:KIVY_NO_ARGS='1'
$Env:MANGOFY_ALLOW_FALLBACKS='1'  # allow simulation when picamera2 not installed
$Env:MANGOFY_MODEL_PATH='ml\Plant_Disease_Prediction\tflite\mobilenetv3_mango_leaf_enhanced.tflite'
$Env:MANGOFY_LABELS_PATH='ml\Plant_Disease_Prediction\tflite\labels.txt'
python kivy-lcd-app/main.py
```

On Linux / Raspberry Pi:

```bash
export KIVY_NO_ARGS=1
export MANGOFY_ALLOW_FALLBACKS=1
export MANGOFY_MODEL_PATH=ml/Plant_Disease_Prediction/tflite/mobilenetv3_mango_leaf_enhanced.tflite
export MANGOFY_LABELS_PATH=ml/Plant_Disease_Prediction/tflite/labels.txt
python3 kivy-lcd-app/main.py
```

Notes:
- On Pi, prefer `tflite-runtime` and `picamera2` (install via `scripts/setup_pi.sh`) and set `MANGOFY_STRICT_MODE=1` (and *do not* set `MANGOFY_ALLOW_FALLBACKS`) for hardware tests.
- If you need a headless test (CI), use `tools/import_with_retry.py` with `--simulate` and `--dry-run`.


## Raspberry Pi Implementation Guide

This section provides detailed instructions for deploying and running MangoFy on a Raspberry Pi with full hardware integration (camera, motor, GPIO).

### Hardware Requirements

- **Raspberry Pi 4 or 5** (recommended for performance)
- **Pi Camera Module 3** (or compatible Picamera2-supported camera)
- **Stepper Motor Driver** (e.g., A4988 or similar, connected to GPIO pins)
- **Stepper Motor** (NEMA 17 or compatible, with belt/gear for leaf scanning)
- **IR Sensor** (for homing detection)
- **LED Lights** (for illumination during capture)
- **Power Supply** (adequate for Pi + motor + lights)
- **SD Card** (32GB+ recommended)

### Software Setup on Raspberry Pi

1. **Install Raspberry Pi OS** (64-bit Lite or Desktop):
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   ```

2. **Install Python and Dependencies**:
   ```bash
   sudo apt install python3 python3-pip python3-venv git -y
   ```

3. **Clone the Repository**:
   ```bash
   git clone https://github.com/Jaero-O/Group_2_Repo_Kivy_Dev.git
   cd Group_2_Repo_Kivy_Dev
   ```

4. **Run Pi Setup Script**:
   ```bash
   sudo bash scripts/setup_pi.sh
   ```
   This installs:
   - `picamera2` for camera control
   - `tflite-runtime` for ML inference
   - `RPi.GPIO` for motor control
   - Kivy dependencies optimized for Pi

5. **Activate Pi Virtual Environment**:
   ```bash
   source .venv_pi/bin/activate
   ```

6. **Initialize Database**:
   ```bash
   python scripts/db_init.py
   ```

### Hardware Wiring (GPIO Pin Configuration)

| Component | GPIO Pin | BCM Number | Notes |
|-----------|----------|------------|-------|
| Stepper DIR | 5 | GPIO5 | Direction control |
| Stepper STEP | 12 | GPIO12 | PWM-capable pin |
| Stepper ENABLE | 6 | GPIO6 | Motor enable/disable |
| LED Light | 13 | GPIO13 | Illumination control |
| IR Sensor | 26 | GPIO26 | Homing detection |

**Important Safety Notes:**
- Double-check wiring before powering on
- Use appropriate current-limiting resistors for LEDs
- Ensure motor driver voltage matches motor specifications
- Test GPIO pins individually before full assembly

### Running MangoFy on Raspberry Pi

1. **Set Environment Variables**:
   ```bash
   export KIVY_NO_ARGS=1
   export MANGOFY_STRICT_MODE=1  # Enforce hardware availability
   export MANGOFY_MODEL_PATH=ml/Plant_Disease_Prediction/tflite/mobilenetv3_mango_leaf_enhanced.tflite
   export MANGOFY_LABELS_PATH=ml/Plant_Disease_Prediction/tflite/labels.txt
   # Optional segmentation model
   export MANGOFY_SEGMENTATION_MODEL_PATH=ml/Plant_Disease_Prediction/tflite/mango_segmentation.tflite
   ```

2. **Start the Application**:
   ```bash
   python kivy-lcd-app/main.py
   ```

3. **Alternative: Run Scanner CLI**:
   ```bash
   python tools/run_scanner_raspi.py
   ```
   This performs homing, scanning, stitching, and processing in sequence.

### Dataset Import for Testing

The repository includes a development dataset in `data/database/` for testing inference and UI flows.

1. **Import Dataset with Inference**:
   ```bash
   python tools/import_with_retry.py --source data/database --simulate --workers 2 --progress
   ```
   This simulates model inference and populates the database with metadata.

2. **For Real Inference** (requires TFLite runtime):
   ```bash
   python tools/import_with_retry.py --source data/database --workers 1 --progress
   ```

### Troubleshooting RasPi Issues

- **Camera Not Detected**: Run `libcamera-hello` to test camera
- **GPIO Permission Denied**: Ensure user is in `gpio` group: `sudo usermod -a -G gpio $USER`
- **Motor Not Moving**: Check stepper driver connections and power
- **TFLite Runtime Missing**: Re-run `scripts/setup_pi.sh` or install manually
- **Kivy Display Issues**: Set `export DISPLAY=:0` for X11, or use `--fullscreen` for touchscreen

### Performance Optimization

- Use `tflite-runtime` instead of full TensorFlow for faster inference
- Enable WAL mode in SQLite: `PRAGMA journal_mode=WAL;`
- Run motor operations in background threads to keep UI responsive
- Use `--batch-size` in import scripts to control memory usage

### Backup and Recovery

- **Database Backup**: `cp mangofy.db mangofy.db.bak`
- **Full System Backup**: Use `rsync` to backup entire repo
- **Recovery**: Restore DB and re-run import if needed

For detailed hardware specifications, see `docs/HARDWARE_SPECIFICATIONS.md`.

## Running the Kivy App Locally (Windows / Raspberry Pi)

These instructions help you run the full Kivy app locally for development and testing. The app's main entrypoint for the UI is `kivy-lcd-app/main.py`.

1. Create and activate a virtualenv:

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate
# Linux/Mac
source .venv/bin/activate
```

2. Install core requirements (on Windows you may skip Pi-specific packages):

```bash
pip install -U pip setuptools wheel
pip install -r requirements.txt
# Optional on Pi: pip install -r scripts/requirements-pi.txt
```

3. Initialize (or migrate) the DB:

```bash
python scripts/db_init.py
```

4. Run the app in a development window:

```bash
# Set environment variables for Kivy CLI and model path.
export KIVY_NO_ARGS=1
export MANGOFY_MODEL_PATH=ml/Plant_Disease_Prediction/tflite/mobilenetv3_mango_leaf_enhanced.tflite
export MANGOFY_LABELS_PATH=ml/Plant_Disease_Prediction/tflite/labels.txt

python kivy-lcd-app/main.py
```

Note: On Windows, set environment variables with `set` or `$env:*` in PowerShell. Example:

```powershell
$Env:KIVY_NO_ARGS='1'
$Env:MANGOFY_MODEL_PATH='ml\Plant_Disease_Prediction\tflite\mobilenetv3_mango_leaf_enhanced.tflite'
python kivy-lcd-app/main.py
```

Troubleshooting:
- If Kivy fails to start in a headless CI environment, you can still run headless tests and simulation scripts (e.g., `tools/import_with_retry.py` in `--simulate` mode) to validate pipeline behavior.
- For Raspberry Pi, use the `scripts/setup_pi.sh` to create a Pi-friendly venv and install `picamera2` and `tflite-runtime`.



Severity is computed via lesion segmentation (`ml/processing/severity.py`) with HSV thresholding (OpenCV) and a fallback heuristic. Canonical manuscript severity thresholds (centralized in `ml/processing/severity_constants.py`):
* Healthy: prediction label "Healthy" OR severity < 10%
* Early Stage: 10% ≤ severity < 30%
* Advanced Stage: severity ≥ 30%

Persisted scan data is inserted through `insert_scan_record` with disease + severity IDs after a successful prediction.

### Syncing External ML Assets
Use the sync script to pull model, labels, and training notebooks from the original `Group_2_Repo` without manually copying:
```powershell
python scripts/sync_external_ml.py --source "C:\Users\kenne\Group_2_Repo" --overwrite
```
Flags:
* `--no-notebooks` skip copying training notebooks
* `--overwrite` replace existing local assets

After syncing you can test:
```powershell
$env:MANGOFY_TEST_IMAGE = "C:\Users\kenne\Downloads\Database\dataset\Anthracnose\20211008_124250 (Custom)(1).jpg"
python tools/test_tflite_infer.py
```

### Key Features

## Features

*   **Scan Mango Leaves:** Use your device's camera or upload an image to scan for anthracnose disease.
*   **Prediction Results:** Get instant results on whether the mango is infected with anthracnose and at what severity stage.
*   **Quantitative Analysis:** Calculates the severity percentage based on the leaf area affected by lesions.
*   **Disease Information:** Access detailed information about anthracnose, its symptoms, and prevention methods.
*   **Scan History:** Keep a persistent record of your previous scans, including images and analysis data.
*   **User Guide:** A simple guide on how to use the application effectively.
*   **Offline First:** The application works entirely offline, with all data stored locally on the device.

---

## 📚 Complete Documentation Index

**REQUIRED READING for all contributors:**

### Core Documentation
| Document | Purpose | Status | Must Read |
|----------|---------|--------|-----------|
| **README.md** | System overview, setup, quick start | ✅ Current | ⚠️ YES |
| **docs/SYSTEM_REQUIREMENTS.md** | Functional/non-functional requirements | ✅ Definitive | ⚠️ YES |
| **docs/USER_MANUAL.md** | Complete UI flow and interaction patterns | ✅ Mandatory | ⚠️ YES |
| **docs/HARDWARE_SPECIFICATIONS.md** | Mechanical system and hardware specs | ✅ Reference | Optional |

### Implementation Documentation
| Document | Purpose | Status |
|----------|---------|--------|
| **COMPREHENSIVE_ASSESSMENT_REPORT.md** | Full system assessment (B+ grade) | ✅ Current |
| **IMPLEMENTATION_COMPLETION_SUMMARY.md** | Recent improvements summary | ✅ Current |
| **DATABASE_DOCUMENTATION_PLAN.md** | Database schema and migration | ✅ Current |
| **docs/MODEL_HOSTING.md** | ML model deployment and hosting | ✅ Current |
| **docs/VISUAL_TESTING.md** | Visual regression testing guide | ✅ Current |

### Reference PDFs (Located in `docs/`)
| PDF File | Content | Source |
|----------|---------|--------|
| **MANUAL_VERSION_2.pdf** | Official user manual v2 | User documentation |
| **KIVY_INTERFACE_MANUAL.pdf** | Kivy UI implementation guide | Technical specs |
| **SCANNING_CODE.pdf** | ML inference and preprocessing code | Implementation |

**📖 Documentation Hierarchy:**
```
1. README.md (START HERE)
   ↓
2. docs/SYSTEM_REQUIREMENTS.md (What to build)
   ↓
3. docs/USER_MANUAL.md (How it should behave)
   ↓
4. Implementation docs (How it's built)
```

---

## Project Structure

The project is organized into the following directories and files:

```
Group_2_Repo_Kivy_Dev/
├── main.py                          # Main entry point
├── requirements.txt                 # Python dependencies
├── pytest.ini                       # Test configuration
├── environment.yml                  # Conda environment (alternative)
│
├── docs/                            # ⚠️ MANDATORY DOCUMENTATION
│   ├── SYSTEM_REQUIREMENTS.md       # ⚠️ READ FIRST: Complete requirements
│   ├── USER_MANUAL.md               # ⚠️ READ SECOND: Definitive UI flow
│   ├── HARDWARE_SPECIFICATIONS.md   # Hardware integration specs
│   ├── MODEL_HOSTING.md             # ML model deployment guide
│   ├── VISUAL_TESTING.md            # Visual regression testing
│   ├── MANUAL_VERSION_2.pdf         # Official user manual PDF
│   ├── KIVY_INTERFACE_MANUAL.pdf    # Kivy UI guide PDF
│   └── SCANNING_CODE.pdf            # ML implementation PDF
│
├── kivy-lcd-app/                    # Canonical Kivy application package (frontend)
│   ├── main.py                      # Single entrypoint (MangofyApp)
│   └── app/
│       ├── core/                    # Core logic (DB, configuration, helpers)
│       ├── screens/                 # Screen controllers (Welcome, Scan, Scanning, Result, Save, etc.)
│       ├── kv/                      # KV layout files loaded dynamically
│       ├── assets/                  # Static images/icons
│       └── __init__.py
│
│   # NOTE: Legacy duplicate structure under `src/app` has been deprecated.
│   # Use only `kivy-lcd-app/app/` for new development.
│
├── ml/                              # Machine learning modules
│   ├── predictor.py                 # TFLite predictor wrapper
│   ├── severity_calculator.py       # Lesion segmentation
│   └── Plant_Disease_Prediction/   # Model metadata
│       ├── tflite/                  # TensorFlow Lite models
│       │   ├── mango_mobilenetv2.tflite
│       │   └── labels.txt
│       └── h5/                      # H5 fallback models
│
├── tests/                           # Test suite (98.7% pass rate)
│   ├── conftest.py                  # Pytest configuration
│   ├── test_database.py
│   ├── test_image_processor.py
│   ├── test_main_app.py
│   └── ...
│
├── scripts/                         # Utility scripts
│   ├── download_model.py           # Download models from GitHub Release
│   ├── publish_models_github.ps1    # Upload models to GitHub Release
│   ├── fix_deprecated_properties.py # KV file updater
│   ├── simulate_flows.py            # User flow simulator
│   └── ...
│
├── data/                            # Runtime data
│   ├── captures/                    # Captured leaf images
│   └── processed/                   # Processed images
│   └── database/                    # Development dataset for RasPi implementation (may be tracked via Git LFS)
│
├── COMPREHENSIVE_ASSESSMENT_REPORT.md      # System assessment (B+ grade)
├── IMPLEMENTATION_COMPLETION_SUMMARY.md    # Recent improvements
└── DATABASE_DOCUMENTATION_PLAN.md          # Database schema docs
```

### Critical File Descriptions

### Critical File Descriptions

#### Documentation (MUST READ)
*   **`docs/SYSTEM_REQUIREMENTS.md`**: Complete functional and non-functional requirements. All features must comply with specifications in this document.
*   **`docs/USER_MANUAL.md`**: **DEFINITIVE** UI flow documentation. All screen transitions, navigation patterns, and user interactions MUST follow this manual exactly.
*   **`docs/HARDWARE_SPECIFICATIONS.md`**: Mechanical system components, assembly instructions, and hardware integration details.

#### Application Core
*   **`main.py`**: Application entry point. Initializes Kivy app and database.
*   **`src/app/core/database.py`**: SQLite database manager with CRUD operations, indexing, and backup functionality.
*   **`src/app/core/image_processor.py`**: ML inference orchestrator. Loads TFLite models, preprocesses images, runs predictions.
*   **`src/app/config.py`**: Centralized configuration for model paths, thresholds, and settings.
*   **`src/app/theme.py`**: Design system with 33 tokens (16 colors, 7 fonts, 5 spacing, 5 radius).

#### Screen Controllers (Follow docs/USER_MANUAL.md)
*   **`src/app/screens/`**: Each screen's logic **MUST** implement navigation as documented in USER_MANUAL.md
    *   `home_screen.py` - Main navigation hub
    *   `scan_screen.py` - Guidelines before capture
    *   `scanning_screen.py` - ML analysis progress
    *   `result_screen.py` - Display predictions
    *   `save_screen.py` - Persist records (user-initiated only!)
    *   `records_screen.py` - Browse historical scans

#### UI Layouts (Kivy KV Files)
*   **`src/app/kv/`**: Declarative UI layouts. All KV files updated to Kivy 2.3.1+ standards (zero deprecation warnings).

#### Machine Learning
*   **`ml/predictor.py`**: TFLite model wrapper
*   **`ml/severity_calculator.py`**: Lesion segmentation and severity scoring
*   **`ml/Plant_Disease_Prediction/tflite/`**: MobileNetV2 model files (download via `scripts/download_model.py`)

#### Testing (98.7% Pass Rate)
*   **`tests/`**: Comprehensive test suite covering core modules, screens, database, and ML integration
*   **`pytest.ini`**: Test configuration with custom markers

#### Utilities
*   **`src/app/utils/logger.py`**: Structured logging with rotation (5MB, 3 backups)
*   **`scripts/fix_deprecated_properties.py`**: Automated KV file updater
*   **`scripts/simulate_flows.py`**: User workflow simulator for testing

---

## Environment & Setup

### Prerequisites

**Required:**
- Python 3.10+ (tested with 3.10.x)
- Git
- PowerShell (Windows) or bash (Linux/macOS)

**Optional:**
- GitHub CLI (`gh`) for model publishing
- Conda (alternative to venv)

### Installation Steps

#### Windows (PowerShell)

1. **Clone the repository:**
```powershell
git clone https://github.com/Jaero-O/Group_2_Repo_Kivy_Dev.git
cd Group_2_Repo_Kivy_Dev
git checkout integration
```

2. **Create and activate virtual environment:**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. **Install dependencies:**
```powershell
python -m pip install --upgrade pip setuptools wheel
# On Windows: install Kivy prebuilt wheels first to avoid local build issues
pip install --pre --upgrade "kivy[base]" -f https://kivy.org/downloads/simple/
pip install kivy_deps.sdl2 kivy_deps.glew -f https://kivy.org/downloads/simple/
# Then install remaining dependencies
pip install -r requirements.txt
```

4. **Download ML models:**
```powershell
python scripts/download_model.py --repo Jaero-O/Group_2_Repo_Kivy_Dev --tag v1.0-models --dest Plant_Disease_Prediction/
```

#### Linux / macOS (Bash)

```bash
git clone https://github.com/Jaero-O/Group_2_Repo_Kivy_Dev.git
cd Group_2_Repo_Kivy_Dev
git checkout integration

python -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

python scripts/download_model.py --repo Jaero-O/Group_2_Repo_Kivy_Dev --tag v1.0-models --dest Plant_Disease_Prediction/
```

#### Alternative: Conda Environment

```powershell
conda env create -f environment.yml
conda activate mangofy
python scripts/download_model.py --repo Jaero-O/Group_2_Repo_Kivy_Dev --tag v1.0-models --dest Plant_Disease_Prediction/
```

---

## Running the Application
### Local Validation Script
For easier local validation (venv, model download, inference test, and pytest), use the helper script:

```powershell
.\scripts\run_local_full_validation.ps1 -CreateVenv -InstallRequirements -ModelDownload
```

Flags:
- `-CreateVenv`: Create a `.venv` (optional)
- `-InstallRequirements`: Install packages from `requirements.txt`
- `-InstallTensorflow`: Install `tensorflow==2.13.0` (heavy download) if needed for inference on Windows
- `-ModelDownload`: Downloads the tflite model and labels if missing
- `-Quick`: Run a quick pytest subset (not visual) instead of the full suite
- `-RunVisual`: Run capture & visual regression steps (requires GUI)
- `-DryRun`: Prints planned actions without performing them

Results and logs will be saved to the `artifacts/` folder.


### Development Mode

```powershell
# Activate virtual environment first
.\.venv\Scripts\Activate.ps1

# Run the app
python main.py
```

### Expected Behavior
- Application window opens with **HomeScreen**
- Database initializes automatically (creates `mangofy.db` if not exists)
- Logs written to `%APPDATA%/mangofy/logs/app.log`
- Zero deprecation warnings (all Kivy 2.3.1+ compliant)

---

## Testing

### Run Full Test Suite

```powershell
# With virtual environment activated
pytest tests/ -k "not visual" --tb=line -q
```

**Expected Output:**
```
78 passed, 1 skipped, 4 deselected in ~11s
Pass Rate: 98.7%
```

### Run Specific Tests

```powershell
# Test database functionality
pytest tests/test_database.py -v

# Test ML predictor
pytest tests/test_ml_predictor.py -v

# Test image processor
pytest tests/test_image_processor.py -v

# Test main app integration
pytest tests/test_main_app.py -v
```

### Test with Coverage

```powershell
pytest tests/ --cov=src/app --cov-report=html
# Open htmlcov/index.html to view coverage report
```

**Current Coverage:** ~90% for core modules

---

## Database Architecture

The backend uses SQLite with a normalized schema designed for data integrity, performance, and scalability. All database operations are logged and validated.

### Database Location
- **Development:** `c:\Users\kenne\Group_2_Repo_Kivy_Dev\mangofy.db`
- **Production:** `%APPDATA%\mangofy\mangofy.db` (Windows) or `~/.local/share/mangofy/mangofy.db` (Linux/macOS)
- **Backups:** `%APPDATA%\mangofy\backups\` (automatic rotation, keeps 10 most recent)

### Schema Overview

**See `DATABASE_DOCUMENTATION_PLAN.md` for complete details.**

### Entity-Relationship Diagram (ERD)

```mermaid
erDiagram
    tbl_tree {
        INTEGER id PK "Auto-incrementing primary key"
        TEXT name UQ "Unique name of the tree (e.g., 'Backyard Mango')"
        DATETIME created_at "Timestamp of creation"
    }
    tbl_disease {
        INTEGER id PK "Auto-incrementing primary key"
        TEXT name UQ "Unique name of the disease (e.g., 'Anthracnose')"
        TEXT description "Detailed description of the disease"
        TEXT symptoms "Common symptoms"
        TEXT prevention "Prevention and treatment methods"
    }
    tbl_severity_level {
        INTEGER id PK "Auto-incrementing primary key"
        TEXT name UQ "e.g., Healthy, Early Stage, Advanced Stage"
        TEXT description "Description of the severity stage"
    }
    tbl_scan_record {
        INTEGER id PK "Auto-incrementing primary key"
        INTEGER tree_id FK "Foreign key to tbl_tree"
        INTEGER disease_id FK "Foreign key to tbl_disease"
        INTEGER severity_level_id FK "Foreign key to tbl_severity_level"
        REAL severity_percentage "Calculated as (lesion_area / leaf_area)"
        TEXT image_path "File path to the saved scan image"
        # Mangofy — Mango Leaf Disease Scanner (Project README)

        This repository contains the Mangofy Kivy application and supporting tools for dataset handling, model hosting, and CI automation.

        This README documents everything a new developer or maintainer needs to run, test, and extend the system, including how we handle large ML artifacts and how to recover or re-sync after the repository history was cleaned.

        --

        **Quick links**

        - App entry: `main.py` (app bootstrap in `src/`)
        - App code: `src/app/` (core, screens, kv files)
        - Tests: `tests/`
        - Model helpers: `scripts/publish_models_github.ps1`, `scripts/download_model.py`
        - CI workflow: `.github/workflows/download-models.yml`
        - Models Release (uploaded): `v1.0-models` (GitHub Release)

        --

        **Table of contents**

        - Project overview
        - Repo layout
        - Environment & setup (Windows-focused + cross-platform notes)
        - Running the app (dev mode)
        - Tests and test utilities
        - Database details (`mangofy.db`)
        - ML models & hosting (GitHub Releases + download/upload scripts)
        - CI: workflow for downloading models
        - Post-history-rewrite collaborator instructions
        - Developer workflow & common commands
        - Troubleshooting

        --

        **Project overview**

        Mangofy is a Kivy-based application for detecting leaf disease (anthracnose) in mango leaves. It includes:

        - A Kivy UI (screens, KV files) under `src/app/`.
        - A small SQLite-backed local database used for persisting scans and lookups (`mangofy.db`).
        - ML inference code that uses TFLite models for on-device prediction.
        - Image-processing helpers to compute a severity percentage from segmented lesions.

        The repository also contains test coverage and utilities to host large model files outside of Git history (we use a GitHub Release for binary model hosting).

        --

        **Repository layout (important paths)**

        - `src/` — application source (Kivy app under `src/app/`).
        - `ml/` — ML utilities and scripts (predictor, severity calculator, leftover utils)
        - `ml/Plant_Disease_Prediction/` — model metadata, notebooks, scripts (NOT the canonical place for large binaries)
        - `scripts/` — helpers for model upload/download and other utilities
        - `tests/` — unit and integration tests
        - `.github/workflows/` — CI workflows (download-models.yml added)
        - `README.md` — this file

        --

        **Environment & setup**

        Prerequisites (Windows recommended flow):

        - Python 3.10+ installed and accessible in PATH
        - Git CLI
        - PowerShell (Windows) or bash (Linux/macOS)
        - For model publishing: GitHub CLI (`gh`) installed and authenticated

        Setup steps (Windows PowerShell)

        1) Create and activate a virtual environment:

        ```powershell
        python -m venv .venv
        .\.venv\Scripts\Activate.ps1
        ```

        2) Upgrade pip and install dependencies:

        ```powershell
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        ```

        Notes for Linux/macOS:

        ```bash
        python -m venv .venv
        source .venv/bin/activate
        pip install -r requirements.txt
        ```

        --

        **Running the app (development)**

        - From repo root, with venv active:

        PowerShell:
        ```powershell
        python main.py
        ```

        Or if your entry was moved/structured under `src/` you may run via:
        ```powershell
        python -m src.main
        ```

        Notes:
        - The Kivy app requires a display (on headless CI use a virtual framebuffer or run on a desktop environment).
        - The app defers heavy initialization (KV loading and screen imports) until DB setup finishes — this helps unit tests run without starting the full UI.

        --

        **Testing**

        - Run the full test suite (unit tests):

        PowerShell / bash:
        ```powershell
        python -m unittest discover tests
        ```

        - Individual test file:

        ```powershell
        python -m unittest tests.test_database
        ```

        Test design notes:
        - Tests are written to be deterministic and avoid requiring native-only packages (we inject fake `tflite_runtime` where needed and skip cv2 tests when OpenCV is not available).

        --

        **Database (`mangofy.db`)**

        - The app stores data in a SQLite DB named `mangofy.db` located under the user data directory (or `populated_mangofy.db` in dev/test scenarios). The schema includes `tbl_disease`, `tbl_severity_level`, `tbl_tree`, and `tbl_scan_record`.
  
        Note: For this repository baseline, `mangofy.db` is intentionally committed into the repo (development snapshot) to help the implementers and testers get a populated DB for local testing. Local runtime should use a user-specific DB location in production. If you need to avoid shipping a DB to the production environment, use an environment-specific `MANGOFY_DB_PATH` override.
        - There are utilities in `src/app/core/database.py` to initialize and populate lookup tables. Use the provided tests to validate DB creation.

        --

        **ML models & hosting (how we handle large files)**

        Rationale:
        - Large artifacts (models, videos, datasets) were removed from Git history to keep the repository small and fast. The canonical location for binary models is a GitHub Release named `v1.0-models`.

        What we added to help:
        - `scripts/publish_models_github.ps1` — PowerShell script that uses `gh` to create a release and upload assets. It supports absolute paths and glob-style patterns.
        - `scripts/download_model.py` — Python script that downloads release assets by tag; supports `GITHUB_TOKEN` from the environment for private releases.
        - `.github/workflows/download-models.yml` — CI job that downloads models into `models/` for workflows.

        Uploading models (manual, using `gh` locally)

        1. Ensure `gh` is installed and logged in:

        ```powershell
        gh auth login
        gh auth status
        ```

        2. From the repo root (PowerShell), run:

        ```powershell
        .\scripts\publish_models_github.ps1 -Tag 'v1.0-models' -Title 'ML models v1' -Notes 'Models removed from repo'
        ```

        Or specify absolute paths if files live elsewhere:

        ```powershell
        .\scripts\publish_models_github.ps1 -Tag 'v1.0-models' -Pattern 'C:\path\to\h5\*,C:\path\to\tflite\*'
        ```

        Downloading models (local or CI):

        ```powershell
        python scripts/download_model.py --repo Jaero-O/Group_2_Repo_Kivy_Dev --tag v1.0-models --dest models/
        ```

        CI (GitHub Actions): The workflow `.github/workflows/download-models.yml` will run the same downloader using `GITHUB_TOKEN`.

        Alternatives to GitHub Releases

        - Google Drive: free, but requires managing share links; I can extend `download_models.py` to fetch from Drive if you prefer.
        - Self-hosting (S3 or similar): works but may incur costs.

        --

        **Post-history-rewrite collaborator instructions (important)**

        Because the repo had large binary files removed from history, the `integration` branch was rewritten and force-pushed. Collaborators must not pull normally — they should re-clone or reset.

        Safest (recommended): re-clone:

        ```powershell
        git clone https://github.com/Jaero-O/Group_2_Repo_Kivy_Dev.git
        cd Group_2_Repo_Kivy_Dev
        git checkout integration
        ```

        If a contributor must preserve local work, they should:

        ```powershell
        git fetch origin
        git checkout -b my-local-backup
        git rebase --onto origin/integration <old-integration-commit> my-local-backup
        # or create patches with `git format-patch` and reapply after re-cloning
        ```

        If you need a short message to send to the team, use the collaborator note in `docs/MODEL_HOSTING.md`.

        --

        **Developer workflow & common commands**

        - Run tests:

        ```powershell
        python -m unittest discover tests
        ```

        - Start app (dev):

        ```powershell
        python main.py
        ```

        - Create a release and upload models (local):

        ```powershell
        gh auth login
        .\scripts\publish_models_github.ps1 -Tag 'v1.0-models' -Title 'ML models v1'
        ```

        - Download models locally:

        ```powershell
        python scripts/download_model.py --repo Jaero-O/Group_2_Repo_Kivy_Dev --tag v1.0-models --dest models/
        ```

        --

        **Troubleshooting**

        - Push fails due to large files or remote timeouts: we removed large files and force-pushed a cleaned branch. If you encounter push failures, ensure you re-cloned the cleaned repo.
        - `gh` CLI not found: install from https://cli.github.com/ and authenticate with `gh auth login`.
        - Running Kivy on headless CI: use a headful runner or xvfb on Linux.

        --

        **Contributing**

        - Open issues and PRs are welcome. For large model changes, use Releases or external storage rather than committing binaries.

        --

        If you'd like, I can also:

        - Add a release-upload GitHub Actions workflow (automates uploads from a CI artifact or from a secret-uploaded artifact).
        - Remove the binary model files currently copied into `ml/Plant_Disease_Prediction/h5` and `tflite` (recommended to avoid duplicating the Release contents in git history).

        Thank you — if anything in this README should be expanded or made more specific to your environment, tell me which section to change and I'll update it.

## User Workflow (UI Flow Reference)

**⚠️ CRITICAL: This section is a summary. For COMPLETE and MANDATORY specifications, see `docs/USER_MANUAL.md`**

This section documents the intended user navigation flow for the app. Keep this as a canonical reference for UI behavior and tests.

### Quick Flow Summary

1) **Title / Home Interface**
   - From here the user can choose: `Scan Leaf`, `View Records`, `Share`, or `Help/Info`.

2) **Scan Leaf Flow** (detailed in docs/USER_MANUAL.md)
   - `Scan Leaf` → `Guidelines` screen (`ScanScreen`). The user can:
     - `Cancel` → returns to Home.
     - `Scan` → begins capture and shows a temporary `Scanning...` screen (`ScanningScreen`).
   - `Scanning...` performs analysis and navigates to `Result` screen where the app displays:
     - Image Taken (captured photo or thumbnail)
     - Disease Classification
     - Severity (percentage and stage)
     - **Confidence Badge** (color-coded for high, moderate, or low confidence)
     - **Disease Metadata** (description, symptoms, prevention)
   - From the `Result` screen the user may:
     - `Retake` → returns to `Guidelines` (`ScanScreen`) to perform another capture.
     - `View Info` → opens a detail screen with the image, severity, leaf data, and disease classification; `Back` returns to `Result`.
     - `Save` → opens the `Save Leaf` screen where the user chooses a `Tree` (existing) or taps `Add Tree` to create a new one.
       - `Add Tree` allows entering a tree name and returns to `Save Leaf` with the new tree listed.
       - Selecting a tree and confirming persists the scan record to `mangofy.db` and shows confirmation screen `Leaf is Saved!` with options `Scan Again` or `Home`.

3) **View Records Flow**
   - From Home select `View Records` to see a searchable list of Trees. 
   - Select a Tree to view images for that tree. 
   - Selecting a leaf image opens the detailed record view (image, severity, leaf data, disease classification).
   - **Image Gallery**: Use the "Load More" button at the bottom of the gallery to view additional images if available.
