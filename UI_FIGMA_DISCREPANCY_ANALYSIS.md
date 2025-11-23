# UI to Figma Reference Discrepancy Analysis

**Date**: November 19, 2025  
**Status**: Analysis Complete - Awaiting User Approval for Fixes

---

## Overview

This document identifies all discrepancies between the current Kivy UI implementation and the Figma reference designs located in `screenshots/references_figma/`.

**Threshold Data** (from `thresholds_figma.json`):
- Default percent_diff threshold: **0.60** (60% difference allowed)
- Welcome Screen: **0.40** (40% difference allowed)
- Home Screen: **0.45** (45% difference allowed)
- Scan Screen: **0.50** (50% difference allowed)
- Scanning Screen: **0.55** (55% difference allowed)
- Result Screen: **0.45** (45% difference allowed)

---

## 🔴 CRITICAL ISSUES (High Priority)

### 1. Welcome Screen (`WelcomeScreen.kv`)
**Reference**: `welcome.png` / `First Screen.png`

**Current Implementation Issues**:
- ❌ **Missing Logo**: Figma shows MangoFy logo, current only has text
- ❌ **Wrong Background**: Should have branded background, currently plain white (90% opacity)
- ❌ **Text Color**: Using greenish (105/255, 133/255, 105/255), should match Figma
- ❌ **Font Size**: 36px may not match Figma specifications
- ❌ **Missing Branding Elements**: No app name/tagline visible

**Severity**: CRITICAL - First impression screen

---

### 2. Home Screen (`HomeScreen.kv`)
**Reference**: `home.png` / `Home Screen.png`

**Current Implementation Issues**:
- ❌ **Inner Panel Color**: Using (237/255, 255/255, 218/255) - verify against Figma
- ❌ **Logo Size**: 300x300 may not match Figma proportions
- ❌ **Logo Position**: center_y: 0.6 may be off
- ❌ **Scan Button**: Position y: 0.20 may not match Figma
- ❌ **Button Shadows**: shadow_offset values may differ from Figma
- ❌ **Missing Bottom Navigation**: Figma may show navigation icons/labels

**Partial Implementation**:
- ⚠️ Lines 102-157 show incomplete `TouchableButton` grid (Help, About Us, System Spec buttons)
- ⚠️ Button layout may not match Figma grid spacing

**Severity**: CRITICAL - Main navigation screen

---

### 3. Scan Screen (`ScanScreen.kv`)
**Reference**: `scan.png` / `Scan Screen.png`

**Current Implementation Issues**:
- ❌ **Background Image**: Using `placeholder_bg1.png` - should match Figma camera preview style
- ❌ **Button Sizes**: Cancel (70x70), Scan (110x110) - verify against Figma
- ❌ **Button Positions**: 
  - Cancel: x: 0.20, y: 0.07
  - Scan: x: 0.50, y: 0.04
  - May not match Figma alignment
- ❌ **Button Colors**: White cancel button - verify if Figma uses different color
- ❌ **Gradient**: GradientScanButton may not match Figma gradient direction/colors
- ❌ **Missing Camera UI Elements**: No viewfinder guides, frame indicators

**Severity**: HIGH - Core functionality screen

---

### 4. Result Screen (`ResultScreen.kv`)
**Reference**: `Result.png` / `Full Result Screen.png` (4 variants)

**Current Implementation Issues**:
- ❌ **Generic Layout**: Uses basic BoxLayout, Figma likely has custom card design
- ❌ **No Visual Styling**: Plain labels, missing:
  - Rounded cards/panels
  - Color-coded severity indicators
  - Icons for disease/severity
  - Proper spacing/padding
- ❌ **Image Display**: Basic Image widget, should be styled preview card
- ❌ **Severity Legend**: Plain labels in BoxLayout, should be visual scale/bar
- ❌ **Save Button**: Basic button, should match Figma button style
- ❌ **Back Button**: Basic button (80px width), should match Figma design
- ❌ **Missing Elements**:
  - Confidence visualization (progress bar?)
  - Disease icon/illustration
  - Severity color indicators
  - Card shadows/borders

**Severity**: CRITICAL - Shows analysis results to user

---

### 5. Records Screen (`RecordsScreen.kv`)
**Reference**: `records.png` / `Records Screen Version 2.png`

**Current Implementation Issues**:
- ❌ **Header Layout**: Separate BoxLayouts for icon and label - should be unified
- ❌ **Header Position**: Using pos_hint with hardcoded values (0.06, 0.92), (0.17, 0.91) - brittle
- ❌ **Back Button**: Style may not match Figma
- ❌ **RecordTreeItem**: 
  - Background color: (232/255, 255/255, 208/255) - verify against Figma
  - Border radius: 11 - verify
  - Height: 49 - verify
- ❌ **Missing Elements**:
  - Search functionality (Figma shows search icon)
  - Filtering/sorting UI
  - Empty state design
  - Record item details (date, severity indicators)

**Severity**: HIGH - Data viewing screen

---

## 🟡 MODERATE ISSUES (Medium Priority)

### 6. Scanning Screen (`ScanningScreen.kv`)
**Reference**: `scanning.png` / `Scanning Screen.png`

**Issues to Verify**:
- ⚠️ Loading animation style
- ⚠️ Progress indicator design
- ⚠️ Background color/pattern
- ⚠️ Cancel button presence/style

**Severity**: MEDIUM - Transitional screen

---

### 7. Image Selection Screen (`ImageSelection.kv`)
**Reference**: `image_selection.png` / `Image Selection Screen.png`

**Issues to Verify**:
- ⚠️ Gallery grid layout
- ⚠️ Image preview thumbnails
- ⚠️ Selection indicators
- ⚠️ Action buttons (Retake, Confirm)

**Severity**: MEDIUM - User interaction screen

---

### 8. Save Screen (`SaveScreen.kv`)
**Reference**: `save.png` / `Save Capture Screen.png` (2 variants)

**Issues to Verify**:
- ⚠️ Form field styling
- ⚠️ Input validation indicators
- ⚠️ Save/Cancel button designs
- ⚠️ Tree name input field

**Severity**: MEDIUM - Data entry screen

---

### 9. Capture Result Screen (`CaptureResultScreen.kv`)
**Reference**: `Capture Result Screen.png`

**Issues to Verify**:
- ⚠️ Image preview style
- ⚠️ Retake/Confirm button layout
- ⚠️ Background design

**Severity**: MEDIUM - Transitional screen

---

## 🟢 LOW PRIORITY ISSUES

### 10. Help Screen (`HelpScreen.kv`)
**Reference**: `help.png` / `Help Screen.png`

**Issues to Verify**:
- Content layout and styling
- Icon usage
- Typography hierarchy

---

### 11. About Us Screen (`AboutUsScreen.kv`)
**Reference**: `about_us.png` / `About Us Screen.png`

**Issues to Verify**:
- Logo placement
- Text content styling
- Background design

---

### 12. System Specification Screen (`SystemSpecScreen.kv`)
**Reference**: `system_spec.png` / `System Specification Screen.png`

**Issues to Verify**:
- Information card design
- Icon placement
- Text formatting

---

### 13. Precaution Screen (`PrecautionScreen.kv`)
**Reference**: `precaution.png` / `Guidelines and Precautions Screen.png`

**Issues to Verify**:
- List item styling
- Icon usage
- Section headers

---

### 14. Guide Screen (`GuideScreen.kv`)
**Reference**: `guide.png` / `Guide Modal.png`

**Issues to Verify**:
- Modal/popup design
- Step-by-step layout
- Navigation controls

---

### 15. Anthracnose Screen (`AnthracnoseScreen.kv`)
**Reference**: `anthracnose.png` / `Anthracnose Disease Screen.png`

**Issues to Verify**:
- Disease information layout
- Image gallery
- Symptom descriptions

---

### 16. Share Screen (`ShareScreen.kv`)
**Reference**: `share.png` / `Share Screen.png`

**Issues to Verify**:
- Share options layout
- Icon design
- Export functionality UI

---

## 📋 Common Issues Across Screens

### Typography Issues
- Font sizes may not match Figma specifications
- Font weights (bold/regular) may differ
- Line heights and letter spacing not specified

### Color Issues
- Colors defined as fractions (e.g., 3/255, 30/255, 0/255)
- May not exactly match Figma color palette
- Missing color constants/theme system

### Spacing/Padding Issues
- Hardcoded padding/spacing values
- Not using consistent spacing scale
- pos_hint values may not match Figma

### Button/Component Issues
- Custom components (RoundedButton, GradientScanButton, ScanButton) may not match Figma
- Shadow effects may differ
- Border radius values may not match
- Icon sizes may not match

### Missing Design System
- No centralized theme/style definitions
- Inconsistent component styling
- No design tokens (colors, spacing, typography)

---

## 🛠️ Recommended Fix Approach

### Phase 1: Critical Screens (Consult Before Each)
1. **Welcome Screen** - First impression
2. **Home Screen** - Main navigation
3. **Result Screen** - Core functionality output
4. **Scan Screen** - Core functionality input
5. **Records Screen** - Data access

### Phase 2: Moderate Screens (Batch Approval)
6. Scanning Screen
7. Image Selection Screen
8. Save Screen
9. Capture Result Screen

### Phase 3: Low Priority Screens (Final Polish)
10-16. Information/Help screens

---

## 📸 Next Steps

**Before I make ANY fixes, please review this analysis and:**

1. ✅ **Confirm priority order** - Should I start with Welcome → Home → Result → Scan → Records?
2. ✅ **Provide Figma access** - Do you have Figma links or more detailed specs (colors, spacing)?
3. ✅ **Approve fix approach** - Fix one screen at a time, show you the changes, get approval before next?
4. ✅ **Specify critical elements** - Which discrepancies are most important to fix first?

**I will NOT make changes until you approve the plan and first screen to fix.**

---

## 📝 Notes

- Some Figma references have multiple variants (Full Result Screen has 4 versions)
- Icon assets exist in `screenshots/references_figma/` but may not be integrated
- Current implementation uses custom widgets (RoundedButton, GradientScanButton) that need verification
- Database-driven content (Records) may have additional dynamic styling requirements

