# USER MANUAL - MangoFy Application
## Complete User Guide and Interface Documentation

**Document Version:** 2.0  
**Date:** November 19, 2025  
**Status:** ⚠️ **DEFINITIVE - MUST BE FOLLOWED ABSOLUTELY**  
**Source:** Based on official user manuals and Figma UI specifications

---

## ⚠️ CRITICAL COMPLIANCE NOTICE

**THIS DOCUMENT IS MANDATORY AND AUTHORITATIVE**

All developers, AI assistants, and system modifications MUST:
- ✅ Read and understand this manual BEFORE making any changes
- ✅ Follow the specified UI flow EXACTLY as documented
- ✅ Maintain the screen navigation patterns described herein
- ✅ Preserve all user interaction behaviors
- ✅ Implement features according to these specifications

**Deviations from this manual are NOT permitted without explicit approval.**

---

## 1. APPLICATION OVERVIEW

### 1.1 Purpose
MangoFy is a mobile application designed to detect and diagnose mango leaf diseases using computer vision and machine learning. It provides farmers and agricultural professionals with instant disease identification, severity assessment, and treatment recommendations.

### 1.2 Key Features
- ✅ Real-time leaf disease detection via camera
- ✅ Severity percentage calculation
- ✅ Tree-based record organization
- ✅ Historical scan tracking
- ✅ Comprehensive disease information library
- ✅ Offline operation (no internet required)
- ✅ Data export capabilities

---

## 2. COMPLETE USER INTERFACE FLOW

### 2.1 HOME SCREEN (Title Interface)

**Screen Name:** `HomeScreen`  
**Purpose:** Main navigation hub

#### Available Actions:
1. **Scan Leaf** → Navigate to Guidelines Screen
2. **View Records** → Navigate to Records Screen
3. **Share** → Navigate to Share Screen
4. **Help/Info** → Navigate to Help Menu

#### UI Components:
- App logo and title banner
- 4 primary action buttons (equal prominence)
- Navigation drawer (accessible via hamburger menu)
- About Us link (footer)

#### Design Specifications:
```python
LAYOUT = {
    'orientation': 'vertical',
    'spacing': '20dp',
    'padding': ['28dp', '20dp', '28dp', '20dp']
}

BUTTON_SCAN_LEAF = {
    'text': 'Scan Leaf',
    'size_hint_y': None,
    'height': '56dp',
    'background_color': COLORS['accent'],  # Orange
    'on_release': lambda: navigate_to('scan_screen')
}

BUTTON_VIEW_RECORDS = {
    'text': 'View Records',
    'on_release': lambda: navigate_to('records_screen')
}

BUTTON_SHARE = {
    'text': 'Share',
    'on_release': lambda: navigate_to('share_screen')
}

BUTTON_HELP_INFO = {
    'text': 'Help/Info',
    'on_release': lambda: navigate_to('help_screen')
}
```

---

### 2.2 SCAN LEAF FLOW (Complete Workflow)

#### Step 1: GUIDELINES SCREEN (`ScanScreen`)

**Purpose:** Provide scanning instructions before capture

##### UI Components:
- **Content:** Guidelines text box with instructions
  - "Hold camera 15-20cm from leaf"
  - "Ensure good lighting (avoid shadows)"
  - "Place leaf on neutral background"
  - "Keep leaf flat and fully visible"

- **Action Buttons:**
  - `Cancel` → Return to HomeScreen
  - `Scan` → Proceed to image capture

##### Implementation Requirements:
```python
class ScanScreen(Screen):
    def on_scan_button(self):
        """Start camera capture or image selection"""
        # Show camera interface or file picker
        self.capture_image()
    
    def on_cancel_button(self):
        """Return to home without scanning"""
        self.manager.current = 'home_screen'
```

---

#### Step 2: IMAGE CAPTURE

**Purpose:** Acquire leaf image via camera or gallery

##### Capture Options:
1. **Live Camera Capture:**
   - Full-screen camera preview
   - Shutter button (center bottom)
   - Flash toggle (top right)
   - Gallery button (bottom left)
   - Cancel button (top left)

2. **Gallery Selection:**
   - System file picker
   - Filter: images only (JPEG, PNG)
   - Preview selected image

##### After Capture:
- Display preview with **Confirm** / **Retake** options
- If Confirmed → Navigate to ScanningScreen
- If Retake → Return to camera interface

---

#### Step 3: SCANNING SCREEN (`ScanningScreen`)

**Purpose:** Provide feedback during ML analysis

##### UI Components:
- **Progress Indicator:** Animated spinner or determinate progress bar
- **Status Text:** "Analyzing leaf image..."
- **Captured Image Thumbnail** (optional preview)
- **Cancel Button** (if analysis supports cancellation)

##### Behavior:
```python
class ScanningScreen(Screen):
    def on_enter(self):
        """Automatically start analysis on screen entry"""
        self.start_analysis()
    
    def start_analysis(self):
        """Perform ML inference"""
        # 1. Load captured image
        # 2. Preprocess (resize to 224x224, normalize)
        # 3. Run TFLite model inference
        # 4. Calculate severity from lesion segmentation
        # 5. Store results in app.analysis_result
        # 6. Navigate to ResultScreen
        
    def on_analysis_complete(self, result):
        """Navigate to result screen with analysis data"""
        self.manager.get_screen('result_screen').display_result(result)
        self.manager.current = 'result_screen'
```

##### Timeout Behavior:
- If analysis exceeds 30 seconds → Show error message
- Provide "Try Again" or "Cancel" options

---

#### Step 4: RESULT SCREEN (`ResultScreen` / `CaptureResultScreen`)

**Purpose:** Display analysis results and provide next actions

##### UI Components:

**Top Section (Image Display):**
- Captured leaf image (top half of screen)
- Zoom capability (pinch or double-tap)

**Middle Section (Analysis Results):**
```
┌─────────────────────────────────────┐
│  DISEASE: Anthracnose              │  ← Large heading
│                                     │
│  Confidence: 92%                    │  ← Gauge/progress bar
│  ├────────────────────────┤92%     │
│                                     │
│  Severity: 24% (Early Stage)       │  ← Color-coded badge
│  ├────────┤                        │
│  └─ Yellow badge for 10-30%        │
└─────────────────────────────────────┘
```

**Bottom Section (Action Buttons):**
1. **Retake** → Return to ScanScreen (discard current result)
2. **View Info** → Navigate to detailed information screen
3. **Save** → Navigate to SaveScreen

##### Confidence Score Display:
- **≥85%:** Green badge, "High Confidence"
- **60-84%:** Yellow badge, "Moderate Confidence"
- **<60%:** Red badge with warning "⚠ Low Confidence - Results may be unreliable"

##### Severity Color Coding:
```python
SEVERITY_COLORS = {
    'healthy': (0.2, 0.7, 0.3, 1.0),      # Green: 0-10%
    'early': (1.0, 0.75, 0.0, 1.0),       # Yellow: 10-30%
    'advanced': (0.8, 0.2, 0.2, 1.0)      # Red: >30%
}

def get_severity_color(percentage):
    if percentage < 10:
        return SEVERITY_COLORS['healthy']
    elif percentage < 30:
        return SEVERITY_COLORS['early']
    else:
        return SEVERITY_COLORS['advanced']
```

---

#### Step 5: VIEW INFO SCREEN (Detailed Result)

**Purpose:** Show comprehensive analysis details

##### UI Layout:
```
┌─────────────────────────────────────┐
│  [Full-size captured image]        │
│                                     │
├─────────────────────────────────────┤
│  Disease: Anthracnose               │
│  Confidence: 92%                    │
│  Severity: 24% (Early Stage)        │
│                                     │
│  Leaf Data:                         │
│  • Total Leaf Area: 1,234 px²      │
│  • Lesion Area: 296 px²            │
│  • Lesion Coverage: 24.0%          │
│                                     │
│  Captured: Nov 19, 2025 2:45 PM    │
└─────────────────────────────────────┘
        [Back Button]
```

##### Navigation:
- **Back** → Return to ResultScreen

---

#### Step 6: SAVE SCREEN (`SaveScreen`)

**Purpose:** Persist scan record with tree association

##### UI Components:

**Tree Selection:**
```
┌─────────────────────────────────────┐
│  Select Tree (Optional)             │
│  ┌───────────────────────────────┐ │
│  │ ▼ Choose a tree...            │ │  ← Dropdown
│  │   • Backyard Mango #1         │ │
│  │   • Orchard Tree A3           │ │
│  │   • Front Yard Tree           │ │
│  │   ─────────────────────       │ │
│  │   + Add New Tree              │ │  ← Special option
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
```

**Notes Field:**
```
┌─────────────────────────────────────┐
│  Notes (Optional)                   │
│  ┌───────────────────────────────┐ │
│  │                               │ │  ← Multiline text input
│  │                               │ │     Max 500 characters
│  │                               │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
```

**Action Buttons:**
- **Save** → Persist to database, navigate to confirmation
- **Cancel** → Return to ResultScreen (do not save)

##### Save Behavior:
```python
def on_save_button(self):
    """Save scan record to database"""
    tree_id = self.get_selected_tree_id()  # May be None
    notes = self.ids.notes_input.text
    
    # Insert into tbl_scan_record
    record_id = db_manager.insert_scan_record(
        tree_id=tree_id,
        disease_id=app.analysis_result['disease_id'],
        severity_level_id=app.analysis_result['severity_level_id'],
        severity_percentage=app.analysis_result['severity'],
        image_path=app.analysis_image_path,
        notes=notes
    )
    
    # Navigate to confirmation
    self.manager.current = 'save_confirmation_screen'
```

---

#### Step 7: ADD NEW TREE (Invoked from SaveScreen)

**Purpose:** Create new tree record

##### UI Components:
```
┌─────────────────────────────────────┐
│  Add New Tree                       │
│                                     │
│  Tree Name: *                       │
│  ┌───────────────────────────────┐ │
│  │                               │ │  ← Required field
│  └───────────────────────────────┘ │
│                                     │
│  Location (Optional):               │
│  ┌───────────────────────────────┐ │
│  │                               │ │
│  └───────────────────────────────┘ │
│                                     │
│  Variety (Optional):                │
│  ┌───────────────────────────────┐ │
│  │                               │ │
│  └───────────────────────────────┘ │
│                                     │
│    [Cancel]       [Add Tree]       │
└─────────────────────────────────────┘
```

##### Validation:
- Tree name is **required** (cannot be empty)
- Tree name must be **unique** (check against existing trees)
- Show error message if validation fails

##### Behavior:
```python
def on_add_tree_button(self):
    """Create new tree and return to SaveScreen"""
    name = self.ids.tree_name_input.text.strip()
    
    if not name:
        self.show_error("Tree name is required")
        return
    
    if db_manager.tree_exists(name):
        self.show_error("A tree with this name already exists")
        return
    
    tree_id = db_manager.insert_tree(
        name=name,
        location=self.ids.location_input.text,
        variety=self.ids.variety_input.text
    )
    
    # Return to SaveScreen with new tree selected
    save_screen = self.manager.get_screen('save_screen')
    save_screen.refresh_tree_list()
    save_screen.select_tree(tree_id)
    self.manager.current = 'save_screen'
```

---

#### Step 8: SAVE CONFIRMATION SCREEN

**Purpose:** Confirm successful save

##### UI Components:
```
┌─────────────────────────────────────┐
│                                     │
│         ✓ Leaf is Saved!           │  ← Success icon
│                                     │
│  Your scan has been saved to        │
│  the database successfully.         │
│                                     │
│    [Scan Again]      [Home]        │
└─────────────────────────────────────┘
```

##### Navigation:
- **Scan Again** → Navigate to ScanScreen (start new scan)
- **Home** → Navigate to HomeScreen

---

### 2.3 VIEW RECORDS FLOW

#### Step 1: RECORDS SCREEN (`RecordsScreen`)

**Purpose:** Browse historical scans organized by tree

##### View Modes:

**1. Tree List View (Default):**
```
┌─────────────────────────────────────┐
│  [Search Bar]                       │  ← Filter trees by name
│                                     │
│  My Trees                           │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ 🌳 Backyard Mango #1        │   │
│  │    12 scans                 │   │  ← Tap to view scans
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ 🌳 Orchard Tree A3          │   │
│  │    8 scans                  │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ 🌳 Unassigned Scans         │   │  ← Scans without tree
│  │    3 scans                  │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
        [Back to Home]
```

**2. Scan List View (After selecting tree):**
```
┌─────────────────────────────────────┐
│  ← Backyard Mango #1                │  ← Back to tree list
│                                     │
│  [Filter: All Diseases ▼]          │
│  [Sort: Newest First ▼]            │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ [Thumbnail]  Anthracnose    │   │
│  │              92% confidence │   │  ← Tap for detail
│  │              Nov 19, 2:45PM │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ [Thumbnail]  Healthy        │   │
│  │              88% confidence │   │
│  │              Nov 18, 9:30AM │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
        [Export Records]
```

##### Filtering Options:
- **By Disease:** All / Healthy / Anthracnose / Bacterial Canker / etc.
- **By Date Range:** Last 7 days / Last 30 days / All time / Custom
- **Sort Order:** Newest first / Oldest first / Highest severity

##### Scan Card Components:
```python
SCAN_CARD = {
    'height': '120dp',
    'orientation': 'horizontal',
    'spacing': '12dp',
    'padding': '8dp'
}

CARD_THUMBNAIL = {
    'size_hint_x': 0.3,
    'fit_mode': 'contain'
}

CARD_INFO = {
    'size_hint_x': 0.7,
    'orientation': 'vertical',
    'labels': ['disease_name', 'confidence', 'severity', 'timestamp']
}
```

---

#### Step 2: SCAN DETAIL VIEW

**Purpose:** Display full record details

##### UI Layout:
```
┌─────────────────────────────────────┐
│  ← Back to List                     │
│                                     │
│  [Full-size image]                  │
│                                     │
├─────────────────────────────────────┤
│  Disease: Anthracnose               │
│  Confidence: 92%                    │
│  Severity: 24% (Early Stage)        │
│                                     │
│  Tree: Backyard Mango #1            │
│  Scanned: Nov 19, 2025 2:45 PM      │
│                                     │
│  Notes: Found on lower branch,      │
│  will monitor progression           │
│                                     │
│  Leaf Data:                         │
│  • Total Area: 1,234 px²           │
│  • Lesion Area: 296 px²            │
│                                     │
│    [Delete Record]  [Export Data]  │
└─────────────────────────────────────┘
```

##### Actions:
- **Delete Record** → Show confirmation dialog, then remove from database
- **Export Data** → Generate JSON/CSV export of this record
- **Back** → Return to scan list

---

### 2.4 SHARE SCREEN

**Purpose:** Share treatment information and app details

##### UI Components:
```
┌─────────────────────────────────────┐
│  Share MangoFy                      │
│                                     │
│  ┌─────────────────────┐           │
│  │                     │           │
│  │   [QR Code]         │           │  ← App download link
│  │                     │           │
│  └─────────────────────┘           │
│                                     │
│  Scan to download MangoFy          │
│                                     │
│  Treatment Instructions:            │
│  • Remove infected leaves           │
│  • Apply fungicide spray            │
│  • Improve air circulation          │
│  • Monitor weekly                   │
│                                     │
│         [Back to Home]              │
└─────────────────────────────────────┘
```

---

### 2.5 HELP / INFO FLOW

#### Main Help Menu

**Purpose:** Access educational content and app information

##### Menu Options:
```
┌─────────────────────────────────────┐
│  Help & Information                 │
│                                     │
│  ┌───────────────────────────────┐ │
│  │  About Us                     │ │  → AboutUsScreen
│  └───────────────────────────────┘ │
│                                     │
│  ┌───────────────────────────────┐ │
│  │  System Specification         │ │  → SystemSpecScreen
│  └───────────────────────────────┘ │
│                                     │
│  ┌───────────────────────────────┐ │
│  │  Guidelines and Precautions   │ │  → PrecautionScreen
│  └───────────────────────────────┘ │
│                                     │
│  ┌───────────────────────────────┐ │
│  │  Anthracnose Disease          │ │  → Disease submenu
│  └───────────────────────────────┘ │
│                                     │
│         [Back to Home]              │
└─────────────────────────────────────┘
```

---

#### About Us Screen

**Content:**
- App name and version
- Development team credits
- Institution affiliation
- Contact information
- **[Back]** → Return to Help Menu

---

#### System Specification Screen

**Content:**
- Hardware requirements
- Software dependencies
- Model information (MobileNetV2, TFLite version)
- Database schema version
- **[Back]** → Return to Help Menu

---

#### Guidelines and Precautions Screen

**Content:**
- How to take quality photos
- Best practices for accurate results
- Safety precautions when handling diseased plants
- When to consult an expert
- **[Back]** → Return to Help Menu

---

#### Anthracnose Disease Submenu

**Purpose:** Detailed disease information library

##### Submenu Options:
```
┌─────────────────────────────────────┐
│  Anthracnose Disease                │
│                                     │
│  ┌───────────────────────────────┐ │
│  │  About Anthracnose Disease    │ │  → Description
│  └───────────────────────────────┘ │
│                                     │
│  ┌───────────────────────────────┐ │
│  │  Guidelines and Precautions   │ │  → Prevention tips
│  └───────────────────────────────┘ │
│                                     │
│  ┌───────────────────────────────┐ │
│  │  System Specification         │ │  → Technical details
│  └───────────────────────────────┘ │
│                                     │
│         [Back to Help Menu]         │
└─────────────────────────────────────┘
```

##### Content Screens:
Each option opens a scrollable content page with **[Back]** button returning to **Anthracnose Disease submenu** (NOT the main Help menu).

---

## 3. MANDATORY IMPLEMENTATION RULES

### 3.1 Navigation Constraints

**RULE 1: Scan Flow Isolation**
- Scanning workflow must NOT automatically save records
- User must explicitly choose **Save** from ResultScreen
- Retake must discard current analysis and return to ScanScreen

**RULE 2: Back Button Behavior**
```python
BACK_BUTTON_RULES = {
    'ScanningScreen': 'Cannot go back (analysis in progress)',
    'ResultScreen': 'Back → ScanScreen (discard result)',
    'SaveScreen': 'Back → ResultScreen (do not save)',
    'RecordsScreen': 'Back → HomeScreen',
    'DetailView': 'Back → RecordsScreen (list view)',
    'HelpSubmenu': 'Back → HelpMenuScreen (NOT HomeScreen)',
    'HelpContent': 'Back → Parent submenu'
}
```

**RULE 3: Screen Transitions**
- All transitions must use `self.manager.current = 'screen_name'`
- No direct screen instantiation (use ScreenManager)
- Preserve screen state when navigating back (except scan results)

---

### 3.2 Data Persistence Rules

**RULE 4: Save Timing**
```python
# ✅ CORRECT: Save only when user confirms
def on_save_button_click(self):
    db_manager.insert_scan_record(...)
    self.navigate_to_confirmation()

# ❌ INCORRECT: Auto-save after analysis
def on_analysis_complete(self, result):
    db_manager.insert_scan_record(...)  # NO!
    self.show_result(result)
```

**RULE 5: Image Storage**
- Captured images stored in `{APPDATA}/mangofy/captures/`
- Filename format: `scan_{timestamp}_{record_id}.jpg`
- Thumbnails generated at 150×150 for list views
- Delete orphaned images when records deleted

**RULE 6: Database Integrity**
- All foreign keys must reference valid records
- Tree deletion cascades to associated scans (with confirmation)
- Disease and severity level records are read-only lookup tables

---

### 3.3 UI/UX Constraints

**RULE 7: Accessibility**
- Minimum touch target: 44×44 dp
- Text contrast ratio: ≥4.5:1 (WCAG AA)
- All images must have text alternatives
- Support screen readers (future enhancement)

**RULE 8: Error Handling**
```python
ERROR_DISPLAY_RULES = {
    'model_not_found': 'Show warning badge, fallback to basic detection',
    'analysis_timeout': 'Show error message with "Try Again" button',
    'database_error': 'Show user-friendly message, log technical details',
    'low_confidence': 'Display confidence score with ⚠ warning icon'
}
```

**RULE 9: Loading States**
- Show spinner for operations >500ms
- Disable buttons during async operations
- Provide cancel option for long-running tasks (if feasible)
- Update progress indicators every 500ms

---

## 4. SCANNING CODE SPECIFICATIONS

### 4.1 Image Preprocessing Pipeline

**MANDATORY STEPS:**
```python
def preprocess_image(image_path):
    """
    Preprocess leaf image for ML model input.
    DO NOT modify this pipeline without authorization.
    """
    # Step 1: Load image
    img = cv2.imread(image_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Step 2: Resize to model input size
    img_resized = cv2.resize(img, (224, 224))
    
    # Step 3: Normalize pixel values to [0, 1]
    img_normalized = img_resized.astype(np.float32) / 255.0
    
    # Step 4: Add batch dimension
    img_batch = np.expand_dims(img_normalized, axis=0)
    
    return img_batch
```

### 4.2 ML Inference Requirements

**Model Loading:**
```python
MODEL_CONFIG = {
    'path': 'Plant_Disease_Prediction/tflite/mango_mobilenetv2.tflite',
    'input_shape': (1, 224, 224, 3),
    'output_classes': 7,
    'labels': ['Healthy', 'Anthracnose', 'Bacterial Canker', 
               'Cutting Weevil', 'Gall Midge', 'Powdery Mildew', 
               'Sooty Mould']
}
```

**Inference Execution:**
```python
def run_inference(preprocessed_image):
    """
    Execute TFLite model prediction.
    Returns: (predicted_class, confidence_score)
    """
    # Load TFLite interpreter
    interpreter = tf.lite.Interpreter(model_path=MODEL_CONFIG['path'])
    interpreter.allocate_tensors()
    
    # Get input/output tensors
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    
    # Set input tensor
    interpreter.set_tensor(input_details[0]['index'], preprocessed_image)
    
    # Run inference
    interpreter.invoke()
    
    # Get output (probabilities for each class)
    output_data = interpreter.get_tensor(output_details[0]['index'])
    
    # Extract prediction
    predicted_class_idx = np.argmax(output_data[0])
    confidence = output_data[0][predicted_class_idx]
    
    return MODEL_CONFIG['labels'][predicted_class_idx], float(confidence)
```

### 4.3 Severity Calculation Algorithm

**Lesion Segmentation:**
```python
def calculate_severity(image_path):
    """
    Calculate disease severity percentage from leaf image.
    Based on lesion area vs total leaf area.
    """
    # Step 1: Load image
    img = cv2.imread(image_path)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Step 2: Segment green leaf area (healthy + diseased)
    lower_green = np.array([35, 40, 40])
    upper_green = np.array([85, 255, 255])
    leaf_mask = cv2.inRange(hsv, lower_green, upper_green)
    
    # Step 3: Segment brown/yellow lesions
    lower_brown = np.array([10, 100, 20])
    upper_brown = np.array([30, 255, 200])
    lesion_mask = cv2.inRange(hsv, lower_brown, upper_brown)
    
    # Step 4: Calculate areas
    total_leaf_area = np.sum(leaf_mask > 0)
    lesion_area = np.sum(lesion_mask > 0)
    
    # Step 5: Compute severity percentage
    if total_leaf_area == 0:
        return 0.0
    
    severity_percentage = (lesion_area / total_leaf_area) * 100
    
    return round(severity_percentage, 2)
```

**Severity Level Mapping:**
```python
def get_severity_level(percentage):
    """Map severity percentage to categorical level"""
    if percentage < 10:
        return 'Healthy', 1  # severity_level_id = 1
    elif percentage < 30:
        return 'Early Stage', 2  # severity_level_id = 2
    else:
        return 'Advanced Stage', 3  # severity_level_id = 3
```

---

## 5. CRITICAL CONSTRAINTS

### 5.1 Performance Requirements
- Image analysis must complete within **5 seconds** (90th percentile)
- UI must remain responsive during analysis (run in background thread)
- Database queries must return within **500ms** for <1000 records
- App cold start must complete within **3 seconds**

### 5.2 Quality Assurance
- **Test Coverage:** ≥90% for core modules
- **Code Review:** All UI changes must be reviewed against this manual
- **Regression Testing:** Run full test suite before any commit
- **Visual Testing:** Compare screenshots against Figma designs

### 5.3 Documentation Compliance
- All new screens must be documented in this manual
- Navigation changes require manual update approval
- API changes must update relevant sections

---

## 6. TROUBLESHOOTING GUIDE

### Common Issues:

**Issue: Model not found**
- **Symptom:** "⚠ ML model unavailable" message
- **Solution:** Run `python scripts/download_models.py` to fetch models

**Issue: Low confidence scores**
- **Symptom:** Consistent confidence <60%
- **Solution:** Check image quality (lighting, focus, background)

**Issue: Incorrect severity calculation**
- **Symptom:** Severity percentage doesn't match visual assessment
- **Solution:** Verify HSV thresholds in `calculate_severity()` function

**Issue: App crashes on scan**
- **Symptom:** App closes during analysis
- **Solution:** Check logs at `%APPDATA%/mangofy/logs/app.log`

---

## 7. APPENDIX: FIGMA DESIGN REFERENCES

### Screen Mappings:
- **Home Screen:** Figma Frame "Title Interface Home"
- **Scan Screen:** Figma Frame "Scan Leaf Guidelines"
- **Result Screen:** Figma Frame "Capture Result"
- **Records Screen:** Figma Frame "View Records Tree List"
- **Help Menu:** Figma Frame "Help/Info"

### Design Tokens:
- All color values from `src/app/theme.py`
- Typography defined in FONTS dictionary
- Spacing follows 4dp grid system
- Border radius values from RADIUS dictionary

---

**Document Authority:**  
This manual represents the **definitive specification** for MangoFy application behavior. All implementation must conform to these requirements.

**Change Control:**  
Modifications require approval from project stakeholders and must update this document accordingly.

**Version History:**
- v2.0 (Nov 19, 2025): Complete manual with Figma flow integration
- v1.0 (Initial): Basic user guide

*End of User Manual*
